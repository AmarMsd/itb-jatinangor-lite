from fastapi import APIRouter
from typing import Dict, Optional

router = APIRouter()

@router.get("/")
def read_root() -> Dict[str, str]:
    return {"message": "Welcome To API Register Face INAHEF"}