from contextlib import contextmanager

from models import SessionLocal, engine

@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()