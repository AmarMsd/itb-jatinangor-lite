from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime 
from models import Base


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
    hls_output = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    