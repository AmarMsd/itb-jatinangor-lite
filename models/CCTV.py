from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CCTV(Base):
    __tablename__ = 'cctv'

    id = Column(Integer, primary_key=True)
    lokasi = Column(String(255), nullable=False)
    link = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)  # 1 for active, 0 for inactive
    is_reversed = Column(Boolean, default=False)
    line_x1 = Column(Integer, default=0)
    line_y1 = Column(Integer, default=0)
    line_x2 = Column(Integer, default=0)
    line_y2 = Column(Integer, default=0)

    created_at = Column(DateTime, default=func.now())