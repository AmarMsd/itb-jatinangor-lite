import os
import sys
import subprocess
import threading
import uvicorn
import time
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import Request
from routes.route import router

from workers.yolo_worker import run_hls_worker 

from models import SessionLocal
from models.CCTV import CCTV

app = FastAPI()

# origins = [
#     "http://localhost",
#     "http://localhost:8080",
#     "http://localhost:5173", # Example for Vite/React
# ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

stream_dir = os.path.join(current_dir, "stream")
os.makedirs(stream_dir, exist_ok=True)
app.mount("/stream", StaticFiles(directory=stream_dir), name="stream")

app.include_router(router)

vue_dir = os.path.join(current_dir, "frontend_vue")
assets_dir = os.path.join(vue_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

if os.path.exists(vue_dir):
    app.mount("/static_root", StaticFiles(directory=vue_dir), name="static_root")

@app.get("/{full_path:path}")
async def serve_vue_app(full_path: str):
    if full_path.startswith("stream"):
        file_path = os.path.join(current_dir, full_path)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return {"error": "File stream tidak ditemukan."}, 404

    index_path = os.path.join(vue_dir, "index.html")
    
    # Jika file statis spesifik di root Vue diminta
    potential_file = os.path.join(vue_dir, full_path)
    if os.path.isfile(potential_file):
        return FileResponse(potential_file)
        
    # Kembalikan index.html untuk Vue Router
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return {"error": "Halaman tidak ditemukan dan Frontend belum di-build."}    

@app.middleware("http")
async def add_hls_cache_control(request: Request, call_next):
    response = await call_next(request)
    
    # Jangan pernah cache file playlist m3u8 agar selalu minta yang terbaru
    if request.url.path.endswith(".m3u8"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response

if __name__ == "__main__":
    
    node_exe = os.path.join(current_dir, "be-people-count-node.exe")
    if os.path.exists(node_exe):
        try:
            subprocess.Popen([node_exe], cwd=current_dir)
            print("[INFO] Backend Node.js berhasil dijalankan.")
        except Exception as e:
            print(f"[ERROR] Gagal menyalakan Node.js: {e}")
    else:
        print("[WARNING] be-people-count-node.exe tidak ditemukan di folder utama.")

    def yolo_worker_manager():
       
        
        print("[*] Memulai Radar Worker CCTV (Manager Mode)...", flush=True)
        last_active_id = None  

        while True:
            try:
                db = SessionLocal()
                try:
                    db.expire_all() 
                    db.commit() 
                    
                    active_camera = db.query(CCTV).filter(CCTV.active == 1).first()
                    target_id = active_camera.id if active_camera else None
                finally:
                    db.close()
                
                if target_id:
                    if target_id != last_active_id:
                        print(f"\n==================================================", flush=True)
                        print(f"[*] MANAGER -> Mendeteksi dan Beralih ke CCTV ID: {target_id}", flush=True)
                        print(f"==================================================", flush=True)
                        last_active_id = target_id
                        
                    run_hls_worker(cctv_id=target_id)
                    
                    last_active_id = None 
                    time.sleep(2) 
                else:
                    # Heartbeat log agar kita TAHU bahwa manager masih hidup dan tidak hang
                    print("[*] MANAGER: Tidak ada CCTV aktif...", flush=True)
                    time.sleep(2) # Percepat polling dari 5 detik jadi 2 detik agar lebih responsif

            except Exception as e:
                # Jika terjadi error sistem, paksa print ke layar!
                print(f"\n[FATAL ERROR IN MANAGER] {e}", file=sys.stderr, flush=True)
                traceback.print_exc()
                time.sleep(3)

    try:
        worker_thread = threading.Thread(target=yolo_worker_manager, daemon=True)
        worker_thread.start()
    except Exception as e:
        print(f"[ERROR] Gagal menyalakan YOLO Worker Manager: {e}")

    print("[INFO] Memulai Server Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
