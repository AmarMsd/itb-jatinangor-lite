import sys
import os
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

import cv2
import subprocess
import numpy as np
from ultralytics import YOLO
import time

from models.CCTV import CCTV
from utils.connection.connection_db import get_db_context
from models.Detection import Detection

def run_hls_worker(cctv_id: int):
    # 1. Inisialisasi awal
    with get_db_context() as db:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"[!] Error: CCTV ID {cctv_id} tidak ditemukan.")
            return
        
        rtsp_link = camera.link
        lokasi = camera.lokasi.lower().replace(" ", "_")
        
        line_coords = {
            "x1": camera.line_x1, "y1": camera.line_y1,
            "x2": camera.line_x2, "y2": camera.line_y2
        }
        is_analytic_active = camera.active
        is_reversed = camera.is_reversed

    print(f"[*] Memulai Worker HLS untuk {lokasi}...")

    WIDTH, HEIGHT = 1280, 720
    FRAME_SIZE = WIDTH * HEIGHT * 3

    command_in = [
        'ffmpeg', '-y', 
        '-fflags', 'nobuffer',        
        '-flags', 'low_delay',        
        '-rtsp_transport', 'tcp',
        '-i', rtsp_link, 
        '-r', '10',           # fps       
        '-f', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{WIDTH}x{HEIGHT}', 'pipe:'
    ]
    process_in = subprocess.Popen(command_in, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    stream_dir = os.path.join(root_dir, 'stream')
    os.makedirs(stream_dir, exist_ok=True)
    
    hls_output_path = os.path.join(stream_dir, f'{lokasi}.m3u8')
    # hls_output_path = f'./stream/{lokasi}.m3u8' 
    
    command_out = [
        'ffmpeg', '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'bgr24',
        '-s', f'{WIDTH}x{HEIGHT}', '-r', '10', '-i', '-', 
        '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', '-f', 'hls',
        '-hls_time', '2', '-hls_list_size', '3', '-hls_flags', 'delete_segments',
        hls_output_path
    ]
    process_out = subprocess.Popen(command_out, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    print("[*] Memuat Model YOLOv8...")
    model = YOLO("yolov8n.pt") 
    
    frame_count = 0
    track_history = {}

    last_logged_time = {}
    COOLDOWN_SECOND = 10

    try:
        while True:
            raw_bytes = process_in.stdout.read(FRAME_SIZE)
            if len(raw_bytes) != FRAME_SIZE:
                print("[!] Stream terputus.")
                break
                
            frame_count += 1

            # Refresh data dari database setiap 30 frame
            if frame_count % 30 == 0:
                with get_db_context() as db:
                    db_cam = db.query(CCTV).filter(CCTV.id == cctv_id).first()
                    if db_cam:
                        line_coords = {
                            "x1": db_cam.line_x1, "y1": db_cam.line_y1,
                            "x2": db_cam.line_x2, "y2": db_cam.line_y2
                        }
                        is_analytic_active = db_cam.active # Update status aktif/mati
                        is_reversed = db_cam.is_reversed   # Update status arah

            if frame_count % 5000 == 0:
                current_time = time.time()
                track_history = {k: v for k, v in track_history.items() if (current_time - last_logged_time.get(k, 0)) < 30}
                last_logged_time = {k: v for k, v in last_logged_time.items() if (current_time - v) < 30}
                
            if is_analytic_active == 1:
                frame = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((HEIGHT, WIDTH, 3))
                
                results = model.track(frame, persist=True, verbose=False, classes=[0, 2, 3], imgsz=480, conf=0.5, iou=0.5, device='cpu')  
                annotated_frame = results[0].plot()

                cv2.line(
                    annotated_frame, 
                    (line_coords["x1"], line_coords["y1"]), 
                    (line_coords["x2"], line_coords["y2"]), 
                    (0, 255, 0), 3
                )

                garis_y_tengah = (line_coords["y1"] + line_coords["y2"]) // 2
                
                

                if results[0].boxes.id is not None:
                    boxes = results[0].boxes.xywh.cpu()
                    track_ids = results[0].boxes.id.int().cpu().tolist()
                    class_ids = results[0].boxes.cls.int().cpu().tolist() # Ambil ID Kelas

                    # Masukkan class_ids ke dalam loop
                    for box, track_id, cls_id in zip(boxes, track_ids, class_ids):
                        _, y_center, _, _ = box
                        y_center = int(y_center)

                        if track_id in track_history:
                            prev_y = track_history[track_id]
                            
                            # Logika Arah Dinamis
                            arah_atas_ke_bawah = "out"
                            arah_bawah_ke_atas = "in"
                            
                            if is_reversed:
                                arah_atas_ke_bawah = "in"
                                arah_bawah_ke_atas = "out"
                            
                            detected_direction = None

                            # Deteksi pergerakan: Atas -> Bawah
                            if prev_y < garis_y_tengah and y_center >= garis_y_tengah:
                                print(f"[{arah_atas_ke_bawah.upper()}] Kendaraan ID {track_id} (Class {cls_id})")
                                save_detection(cctv_id, cls_id, arah_atas_ke_bawah)

                            # Deteksi pergerakan: Bawah -> Atas
                            elif prev_y > garis_y_tengah and y_center <= garis_y_tengah:
                                print(f"[{arah_bawah_ke_atas.upper()}] Kendaraan ID {track_id} (Class {cls_id})")
                                save_detection(cctv_id, cls_id, arah_bawah_ke_atas)
                            
                            if detected_direction:
                                current_time = time.time()
                                last_time = last_logged_time.get(track_id, 0)

                                if (current_time - last_time) >= COOLDOWN_SECOND:
                                    print(f"[{detected_direction.upper()}] Kendaraan ID {track_id} (Class {cls_id})")
                                    save_detection(cctv_id, cls_id, detected_direction)

                                    last_logged_time[track_id] = current_time
                                else:
                                    pass

                        track_history[track_id] = y_center

                process_out.stdin.write(annotated_frame.tobytes())
                
            else:
                process_out.stdin.write(raw_bytes)

    except KeyboardInterrupt:
        print("[*] Worker dihentikan oleh pengguna.")
    except Exception as e:
        print(f"[!] Terjadi kesalahan internal: {e}")
    finally:
        process_in.kill()
        process_out.kill()
        print("[*] Proses FFmpeg dimatikan dengan aman.")
    
def save_detection(cctv_id: int, cls_id: int, direction: str):
    """Menyimpan log in/out ke tabel result sesuai class objeknya."""
    
    mobil_val = 1 if cls_id == 2 else 0
    motor_val = 1 if cls_id == 3 else 0
    person_val = 1 if cls_id == 0 else 0

    with get_db_context() as db:
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
        except Exception as e:
            db.rollback()
            print(f"[!] Gagal menyimpan ke database: {e}")

if __name__ == "__main__":
    run_hls_worker(cctv_id=1)