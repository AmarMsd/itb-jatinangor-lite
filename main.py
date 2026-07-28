import os
import sys
import subprocess
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes.route import router

from workers.yolo_worker import run_hls_worker 

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

# 2. Opsional: Mount root statis untuk file seperti favicon.ico, vite.svg, dll 
# (Jangan gunakan html=True agar tidak bentrok dengan catch-all)
if os.path.exists(vue_dir):
    app.mount("/static_root", StaticFiles(directory=vue_dir), name="static_root")

# 3. Catch-All Route untuk Vue Router
@app.get("/{full_path:path}")
async def serve_vue_app(full_path: str):
    index_path = os.path.join(vue_dir, "index.html")
    
    # Jika file yang diminta ada di root folder Vue (misal favicon), layani langsung
    potential_file = os.path.join(vue_dir, full_path)
    if os.path.isfile(potential_file):
        return FileResponse(potential_file)
        
    # Jika bukan file statis spesifik, selalu kembalikan index.html (biarkan Vue Router bekerja)
    if os.path.exists(index_path):
        return FileResponse(index_path)
        
    return {"error": "Halaman tidak ditemukan dan Frontend belum di-build."}
    
if __name__ == "__main__":
    
    # A. MENYALAKAN BACKEND NODE.JS
    node_exe = os.path.join(current_dir, "be-people-count-node.exe")
    if os.path.exists(node_exe):
        try:
            # cwd=current_dir memastikan Node membaca .env dan database di folder yang sama
            subprocess.Popen([node_exe], cwd=current_dir)
            print("[INFO] Backend Node.js berhasil dijalankan.")
        except Exception as e:
            print(f"[ERROR] Gagal menyalakan Node.js: {e}")
    else:
        print("[WARNING] be-people-count-node.exe tidak ditemukan di folder utama.")

    # B. MENYALAKAN YOLO WORKER (Background Thread)
    try:
        # PERBAIKAN: Sesuaikan dengan path file koneksi MySQL Anda
        # Misalnya jika SessionLocal didefinisikan di dalam folder 'models' atau 'database'
        from models import SessionLocal  
        from models.CCTV import CCTV 

        db = SessionLocal()
        active_camera = db.query(CCTV).filter(CCTV.active == 1).first()
        db.close()

        if active_camera:
            worker_thread = threading.Thread(target=run_hls_worker, args=(active_camera.id,), daemon=True)
            worker_thread.start()
            print(f"[INFO] YOLO Worker berhasil dijalankan untuk CCTV ID: {active_camera.id}")
        else:
            print("[INFO] Tidak ada CCTV yang aktif. YOLO Worker dalam posisi standby.")

    except Exception as e:
        print(f"[ERROR] Gagal menyalakan YOLO Worker: {e}")

    print("[INFO] Memulai Server Uvicorn...")
    uvicorn.run(app, host="0.0.0.0", port=8000)