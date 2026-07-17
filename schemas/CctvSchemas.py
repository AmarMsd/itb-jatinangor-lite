from pydantic import BaseModel, Field
from datetime import datetime

class CCTVCreate(BaseModel):
    lokasi: str = Field(
        ..., 
        title="Lokasi CCTV",
        description="Kode lokasi atau nama tempat penempatan CCTV", 
        examples=["TGCL"]
    )
    link: str = Field(
        ..., 
        title="Link RTSP",
        description="URL stream dari kamera CCTV", 
        examples=["rtsp://admin:p@ssNVR2024!@10.97.110.19/axis-media/media.amp?stream=1"]
    )
    active: int = Field(
        1, 
        title="Status Aktif",
        description="Status aktif CCTV, 1 untuk aktif dan 0 untuk tidak aktif", 
        examples=[1]
    )
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "lokasi": "TGCL",
                    "link": "rtsp://admin:p@ssNVR2024!@10.97.110.19/axis-media/media.amp?stream=1",
                    "active": 1
                }
            ]
        }
    }

class CCTVResponse(BaseModel):
    id: int
    lokasi: str
    link: str
    active: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CCTVLineUpdate(BaseModel):
    line_x1: int
    line_y1: int
    line_x2: int
    line_y2: int

class CCTVToogleAnalytic(BaseModel):
    active: bool