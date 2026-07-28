from models.CCTV import CCTV
from models import SessionLocal 
from schemas.CctvSchemas import (
    CCTVCreate, 
    CCTVResponse,
    CCTVLineUpdate, 
    CCTVToogleAnalytic
    )
from typing import List
import time
from sqlalchemy.exc import OperationalError

def create_cctv(cctv_data: List[CCTVCreate]):
    db = SessionLocal() 
    try:
        cctv_objects = []
        for item in cctv_data:
            data_dict = item.model_dump()
            
            data_dict['active'] = 0 
            
            cctv_objects.append(CCTV(**data_dict))
            
        db.add_all(cctv_objects)
        db.commit()

        for obj in cctv_objects:
            db.refresh(obj)

        print(f"Successfully inserted {len(cctv_objects)} CCTV entries.")
        return cctv_objects
    
    except Exception as e:
        print(f"Error occurred: {e}")
        db.rollback()
        raise e
    finally:
        db.close()
def get_all_cctv():
    db = SessionLocal()
    try:
        cameras = db.query(CCTV).all() 
        return cameras
    except Exception as e:
        raise e
    finally:
        db.close()

def get_cctv_by_id(cctv_id: int):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        return camera
    except Exception as e:
        raise e
    finally:
        db.close()

def update_line_trigger(cctv_id: int, line_data: CCTVLineUpdate):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
            return None

        camera.line_x1 = line_data.line_x1
        camera.line_y1 = line_data.line_y1
        camera.line_x2 = line_data.line_x2
        camera.line_y2 = line_data.line_y2

        db.commit()
        db.refresh(camera)
        db.expunge_all()
        return camera
    except Exception as e:
        db.rollback()
        raise e  
    finally:
        db.close()

def toggle_cctv_analytic(cctv_id: int, status_data: CCTVToogleAnalytic):
    db = SessionLocal()
    try:
        if status_data.active:
            db.query(CCTV).update({CCTV.active: 0})
            db.commit()

        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
            return None

        camera.active = 1 if status_data.active else 0

        db.commit()
        db.refresh(camera)
        db.expunge_all()
        return camera
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def get_cctv_for_snapshot(cctv_id: int):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
            return None
        return camera
    except Exception as e:
        raise e
    finally:
        db.close()

def save_path_hls_detection(cctv_id: int, path: str):
    max_retries = 10
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
            if not camera:
                print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
                return None

            # Hindari write yang tidak perlu untuk mengurangi beban write ke database.
            if camera.hls_output == path:
                return camera

            camera.hls_output = path
            db.commit()
            db.refresh(camera)
            db.expunge_all()
            print(f"[*] Path HLS otomatis tersimpan ke DB untuk CCTV ID {cctv_id}")
            return camera

        except OperationalError as e:
            db.rollback()
            err_msg = str(e).lower()
            is_locked = "database is locked" in err_msg or "database table is locked" in err_msg
            if is_locked and attempt < (max_retries - 1):
                backoff = min(3.0, 0.25 * (2 ** attempt))
                time.sleep(backoff)
                continue
            print(f"[!] Gagal menyimpan path HLS (operational): {e}")
            raise e

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

def reverse_direction(cctv_id: int):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
            return None

        camera.is_reversed = 0 if camera.is_reversed == 1 else 1

        db.commit()
        db.refresh(camera)
        db.expunge_all()
        return camera
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def delete_cctv(cctv_id: int):
    db = SessionLocal()
    try:
        camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
        if not camera:
            print(f"CCTV dengan ID {cctv_id} tidak ditemukan.")
            return None

        db.delete(camera)
        db.commit()
        print(f"CCTV dengan ID {cctv_id} berhasil dihapus.")
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()