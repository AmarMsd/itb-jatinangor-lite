from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Detection(Base):
    __tablename__ = 'result'

    id = Column(Integer, primary_key=True)
    cctv_id = Column(String(255), nullable=False)
    mobil = Column(Integer, default=0)
    motor = Column(Integer, default=0)
    person = Column(Integer, default=0)
    direction = Column(String(50), nullable=True)
    timestamps = Column(DateTime, default=func.now())