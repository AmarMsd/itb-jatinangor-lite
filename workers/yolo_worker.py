import sys
import os
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

import cv2
import subprocess
import numpy as np
from ultralytics import YOLO
import time
from sqlalchemy.exc import OperationalError

from models import SessionLocal 
from models.CCTV import CCTV
from models.Detection import Detection
from controllers.CctvController import save_path_hls_detection
from models import SessionLocal  
from models.CCTV import CCTV 
import time
import traceback
import sys

def run_hls_worker(cctv_id: int):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"[!] Error: CCTV ID {cctv_id} tidak ditemukan.")
            return
        
        stream_url = camera.link
        lokasi = camera.lokasi.lower().replace(" ", "_")
        
        line_coords = {
            "x1": camera.line_x1, "y1": camera.line_y1,
            "x2": camera.line_x2, "y2": camera.line_y2
        }
        is_analytic_active = camera.active
        is_reversed = camera.is_reversed
    finally:
        db.close() 

    print(f"[*] Memulai Worker HLS untuk {lokasi}...")

    print("[*] Memuat Model YOLOv8")
    model = YOLO("yolov8n.pt")
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    model.track(dummy_frame, persist=True, verbose=False, device='cpu')
    print("[*] Memulai stream...")
    
    WIDTH, HEIGHT = 1280, 720
    FRAME_SIZE = WIDTH * HEIGHT * 3

    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    stream_dir = os.path.join(root_dir, 'stream')
    os.makedirs(stream_dir, exist_ok=True)

    nama_file = f'cctv_{cctv_id}.m3u8'
    hls_output_path = os.path.join(stream_dir, nama_file)
    hls_url_for_frontend = f'/stream/{nama_file}'

    try:
        save_path_hls_detection(cctv_id, hls_url_for_frontend)
        print(f"[*] Path HLS otomatis disimpan ke DB: {hls_url_for_frontend}")
    except Exception as e:
        pass 

    print("[*] Membuka koneksi RTSP...")
    is_rtsp = stream_url.lower().startswith("rtsp://")
    command_in = ['ffmpeg', '-y']

    if is_rtsp:
        command_in.extend([
            '-fflags', 'nobuffer',        
            '-flags', 'low_delay',        
            '-rtsp_transport', 'tcp'
        ])
    else:
        command_in.extend([
            '-reconnect', '1', 
            '-reconnect_streamed', '1', 
            '-reconnect_delay_max', '5'
        ])

    command_in.extend([
        '-i', stream_url,
        '-r', '10',
        '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{WIDTH}x{HEIGHT}', 'pipe:'
    ])
    
    # process_in = subprocess.Popen(command_in, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    process_in = subprocess.Popen(command_in, stdout=subprocess.PIPE)

    print("[*] Menunggu frame pertama dari kamera...")
    first_frame_bytes = process_in.stdout.read(FRAME_SIZE)
    
    if len(first_frame_bytes) != FRAME_SIZE:
        print(f"[!] GAGAL: Tidak bisa mendapatkan video dari CCTV ID {cctv_id}.")
        process_in.kill()
        return  

    print("[*] Frame pertama diterima! Menyalakan stream HLS...")
    command_out = [
        'ffmpeg', '-y', 
        '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{WIDTH}x{HEIGHT}', '-r', '10', 
        '-i', '-', 
        '-an', 
        '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', 
        '-pix_fmt', 'yuv420p',
        '-f', 'hls',
        '-hls_time', '2', '-hls_list_size', '3', '-hls_flags', 'delete_segments', 
        '-g', '20',
        hls_output_path
    ]
    process_out = subprocess.Popen(command_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    try:
        process_out.stdin.write(first_frame_bytes)
        process_out.stdin.flush()
    except:
        pass

    frame_count = 1
    track_history = {}
    last_logged_time = {}
    COOLDOWN_SECOND = 10
    last_db_check_time = time.time()
    
    try:
        while True:
            if process_out.poll() is not None:
                print(f"\n[!] ERROR FATAL: FFmpeg HLS mati tiba-tiba!")
                break

            raw_bytes = process_in.stdout.read(FRAME_SIZE)
            if len(raw_bytes) != FRAME_SIZE:
                print(f"\n[!] Koneksi RTSP terputus di tengah jalan.")
                break
                
            frame_count += 1
            current_time = time.time()

            if current_time - last_db_check_time >= 3.0:
                last_db_check_time = current_time
                db_refresh = SessionLocal()
                try:
                    db_cam = db_refresh.query(CCTV).filter(CCTV.id == cctv_id).first()
                    active_cam = db_refresh.query(CCTV).filter(CCTV.active == 1).first()

                    if db_cam:
                        line_coords = {
                            "x1": db_cam.line_x1, "y1": db_cam.line_y1,
                            "x2": db_cam.line_x2, "y2": db_cam.line_y2
                        }
                        is_analytic_active = db_cam.active 
                        is_reversed = db_cam.is_reversed   
                finally:
                    db_refresh.close()
                
                if is_analytic_active == 0 or (active_cam and active_cam.id != cctv_id):
                    print(f"\n[!] CCTV ID {cctv_id} dinonaktifkan. Menghentikan proses...")
                    break

            if frame_count % 5000 == 0:
                current_time = time.time()
                track_history = {k: v for k, v in track_history.items() if (current_time - last_logged_time.get(k, 0)) < 30}
                last_logged_time = {k: v for k, v in last_logged_time.items() if (current_time - v) < 30}
                
            if is_analytic_active == 1:
                frame = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
                results = model.track(frame, persist=True, verbose=False, classes=[0, 2, 3], imgsz=480, conf=0.5, iou=0.5, device='cpu')  
                annotated_frame = results[0].plot()

                cv2.line(annotated_frame, (line_coords["x1"], line_coords["y1"]), (line_coords["x2"], line_coords["y2"]), (0, 255, 0), 3)
                garis_y_tengah = (line_coords["y1"] + line_coords["y2"]) // 2

                if results[0].boxes.id is not None:
                    boxes = results[0].boxes.xywh.cpu()
                    track_ids = results[0].boxes.id.int().cpu().tolist()
                    class_ids = results[0].boxes.cls.int().cpu().tolist()

                    for box, track_id, cls_id in zip(boxes, track_ids, class_ids):
                        _, y_center, _, _ = box
                        y_center = int(y_center)

                        if track_id in track_history:
                            prev_y = track_history[track_id]
                            arah_atas_ke_bawah = "in" if is_reversed else "out"
                            arah_bawah_ke_atas = "out" if is_reversed else "in"
                            detected_direction = None

                            if prev_y < garis_y_tengah and y_center >= garis_y_tengah:
                                detected_direction = arah_atas_ke_bawah
                            elif prev_y > garis_y_tengah and y_center <= garis_y_tengah:
                                detected_direction = arah_bawah_ke_atas
                            
                            if detected_direction:
                                if (current_time - last_logged_time.get(track_id, 0)) >= COOLDOWN_SECOND:
                                    print(f"[{detected_direction.upper()}] Kendaraan ID {track_id} (Class {cls_id})")
                                    save_detection(cctv_id, cls_id, detected_direction)
                                    last_logged_time[track_id] = current_time

                        track_history[track_id] = y_center
                
                try:
                    process_out.stdin.write(annotated_frame.tobytes())
                    process_out.stdin.flush() 
                except Exception as e:
                    print(f"\n[!] Gagal mengirim frame hasil analitik ke M3U8: {e}")
                    break
            else:
                try:
                    process_out.stdin.write(raw_bytes)
                    process_out.stdin.flush()
                except Exception as e:
                    print(f"\n[!] Gagal mengirim frame mentah ke M3U8: {e}")
                    break

    except KeyboardInterrupt:
        print("[*] Worker dihentikan oleh pengguna.")
    except Exception as e:
        print(f"[!] Terjadi kesalahan internal: {e}")
    finally:
        try:
            if process_in:
                process_in.kill()
            if process_out:
                process_out.kill()
            
            if process_in:
                process_in.communicate()
            if process_out:
                process_out.communicate()
        except Exception:
            pass
        
        print("[*] Proses stream dimatikan dengan aman.")
    

def save_detection(cctv_id: int, cls_id: int, direction: str):
    mobil_val = 1 if cls_id == 2 else 0
    motor_val = 1 if cls_id == 3 else 0
    person_val = 1 if cls_id == 0 else 0

    max_retries = 5
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            new_record = Detection(
                cctv_id=cctv_id,
                mobil=mobil_val,
                motor=motor_val,
                person=person_val,
                direction=direction
            )
            db.add(new_record)
            db.commit()
            print(f"[DB] Sukses menyimpan: {direction.upper()} (Person:{person_val}, Mobil:{mobil_val}, Motor:{motor_val})")
            return
        
        except Exception as e:
            db.rollback()
            print(f"[!] Gagal menyimpan ke database: {e}")
            return
        finally:
            db.close()

def get_active_cctv_id():
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.active == 1).first()
        if camera:
            return camera.id
        return None
    finally:
        db.close()

