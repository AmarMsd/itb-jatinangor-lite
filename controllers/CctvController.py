
from utils.connection.connection_db import get_db_context
from models.CCTV import CCTV
from schemas.CctvSchemas import (
    CCTVCreate, 
    CCTVResponse,
    CCTVLineUpdate, 
    CCTVToogleAnalytic
    )
from typing import List

def create_cctv(cctv_data: List[CCTVCreate]):
    with get_db_context() as db:
        try:
            # entries = [e for e in (cctv_data or []) if isinstance (e, dict)]

            # if not entries:
            #     return []
            
            cctv_objects = [
                CCTV(**item.model_dump()) for item in cctv_data
            ]
            db.add_all(cctv_objects)
            db.commit()

            for obj in cctv_objects:
                db.refresh(obj)

            print(f"Successfully inserted {len(cctv_objects)} CCTV entries.")
            return cctv_objects
        
        except Exception as e:
            print(f"Error occurred: {e}")

        finally:
            db.close()  

def update_line_trigger(cctv_id: int, line_data: CCTVLineUpdate):
    with get_db_context() as db:
        try:
            camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
            if not camera:
                print(f"CCTV entry with ID {cctv_id} not found.")
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

def toggle_cctv_analytic(cctv_id: int, status_data: CCTVToogleAnalytic):
    with get_db_context() as db:
        try:
            camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
            if not camera:
                print(f"CCTV entry with ID {cctv_id} not found.")
                return None

            camera.active = status_data.active

            db.commit()
            db.refresh(camera)
            db.expunge_all()
            return camera
        except Exception as e:
            db.rollback()
            raise e

def get_cctv_for_snapshot(cctv_id: int):
    with get_db_context() as db:
        try:
            camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
            if not camera:
                print(f"CCTV entry with ID {cctv_id} not found.")
                return None
            return camera
        except Exception as e:
            raise e

def reverse_direction(cctv_id: int):
    with get_db_context() as db:
        try:
            camera = db.query(CCTV).filter(CCTV.id == cctv_id).first()
            if not camera:
                print(f"CCTV entry with ID {cctv_id} not found.")
                return None

            camera.is_reversed = not camera.is_reversed

            db.commit()
            db.refresh(camera)
            db.expunge_all()
            return camera
        except Exception as e:
            db.rollback()
            raise e