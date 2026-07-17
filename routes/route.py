import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Dict, Optional, List
import cv2
import io
import subprocess

from schemas.CctvSchemas import (
    CCTVResponse, 
    CCTVCreate,
    CCTVLineUpdate,
    CCTVToogleAnalytic
    )
    
from controllers.CctvController import (
    create_cctv,
    reverse_direction,
    update_line_trigger,
    toggle_cctv_analytic,
    get_cctv_for_snapshot,
    reverse_direction
)

router = APIRouter()

@router.get("/")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome To API Register Face INAHEF"}


@router.get("/cctv/{cctv_id}/snapshot")
def get_snapshot(cctv_id: int):
    # Asumsikan fungsi get_cctv_for_snapshot sudah ada
    camera = get_cctv_for_snapshot(cctv_id) 
    if not camera:
        raise HTTPException(status_code=404, detail=f"CCTV entry with ID {cctv_id} not found.")
    
    # Ambil URL murni. FFmpeg asli biasanya pintar membaca '@' di password
    rtsp_link = camera.link.strip()
    
    print(f"\n[*] Meminta FFmpeg mengambil 1 frame dari RTSP...")
    
    # Perintah memanggil FFmpeg untuk mengambil 1 gambar (vframes 1)
    command = [
        'ffmpeg',
        '-y',                           # Timpa file jika ada (meski kita pakai pipe)
        '-rtsp_transport', 'tcp',       # Paksa TCP agar stabil
        '-i', rtsp_link,                # Link CCTV
        '-vframes', '1',                # Ambil tepat 1 frame saja
        '-f', 'image2pipe',             # Format output langsung ke Pipa (memori)
        '-vcodec', 'mjpeg',             # Encode sebagai JPEG
        '-'                             # Output diarahkan ke standard-out (Python)
    ]
    
    try:
        # Jalankan FFmpeg, tunggu maksimal 10 detik
        process = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=10
        )
        
        # Cek apakah FFmpeg gagal (exit code bukan 0)
        if process.returncode != 0:
            error_log = process.stderr.decode()
            print(f"[!] FFmpeg Gagal: {error_log}")
            raise HTTPException(status_code=500, detail="Gagal mengambil gambar. Cek log terminal.")
            
        # Jika sukses, ambil byte gambarnya
        image_bytes = process.stdout
        print("[*] SUKSES: Gambar berhasil diekstrak dengan FFmpeg!")
        
        # Langsung tembakkan ke frontend
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/jpeg")
        
    except subprocess.TimeoutExpired:
        print("[!] ERROR: Koneksi ke CCTV Timeout (Terlalu lama).")
        raise HTTPException(status_code=504, detail="Koneksi CCTV Timeout.")
    except Exception as e:
        print(f"[!] ERROR INTERNAL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cctv", response_model=List[CCTVResponse], status_code=status.HTTP_201_CREATED)
def store_cctv(cctv_data: list[CCTVCreate]):
    try:
        inserted_data = create_cctv(cctv_data)
        return inserted_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")
    
@router.patch("/cctv/{cctv_id}/line")
def set_cctv_line(cctv_id: int, line_data: CCTVLineUpdate):
    try:
        updated_camera = update_line_trigger(cctv_id, line_data)
        if not updated_camera:
            raise HTTPException(status_code=404, detail=f"CCTV entry with ID {cctv_id} not found.")
        return {
            "message": f"CCTV entry with ID {cctv_id} line trigger updated successfully.",
            "data": {
                "id": updated_camera.id,
                "lokasi": updated_camera.lokasi,
                "line_x1": updated_camera.line_x1,
                "line_y1": updated_camera.line_y1,
                "line_x2": updated_camera.line_x2,
                "line_y2": updated_camera.line_y2
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")
    

@router.patch("/cctv/{cctv_id}/toggle", response_model=CCTVResponse)
def set_analytic_status(cctv_id: int, status_data: CCTVToogleAnalytic):
    try:
        updated_camera = toggle_cctv_analytic(cctv_id, status_data)
        if not updated_camera:
            raise HTTPException(status_code=404, detail=f"CCTV entry with ID {cctv_id} not found.")
        return  updated_camera
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")
    

@router.patch("/cctv/{cctv_id}/reverse")
def toggle_reverse_direction(cctv_id: int):
    try:
        updated_camera = reverse_direction(cctv_id)
        if not updated_camera:
            raise HTTPException(status_code=404, detail=f"CCTV entry with ID {cctv_id} not found.")
        return {
            "message": f"CCTV entry with ID {cctv_id} reverse direction toggled successfully.",
            "data": {
                "id": updated_camera.id,
                "lokasi": updated_camera.lokasi,
                "is_reversed": updated_camera.is_reversed
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")