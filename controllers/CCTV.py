from utils.connection import get_connection_mysql

def create_cctv(cctv_data):
    db = get_connection_mysql()

    try:
        entries = cctv_data or []
        inserted_rows = []
        
        for e in entries:
            if not isinstance(e, dict):
                continue
            result = db.execute(
                
            )

        return inserted_rows
    except Exception as e: 
        print("{e}")

    finally:
        db.close()