from pydantic import BaseModel
import yaml
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent

class Channel(BaseModel):
    slug: str
    title: str
    ref: str

class Settings(BaseModel):
    api_id: int
    api_hash: str
    session_name: str = "tg_session"
    db_path: str = str(ROOT / "data.db")
    page_size: int = 30
    channels: List[Channel]

def load_settings() -> Settings:
    import os
    with open(ROOT / "channels.yml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    channels = [Channel(**c) for c in cfg.get("channels", [])]
    api_id = int(os.getenv("TG_API_ID", "0"))
    api_hash = os.getenv("TG_API_HASH", "")
    session_name = os.getenv("TG_SESSION", "tg_session")
    db_path = os.getenv("DB_PATH", str(ROOT / "data.db"))
    page_size = int(os.getenv("PAGE_SIZE", "30"))
    return Settings(
        api_id=api_id,
        api_hash=api_hash,
        session_name=session_name,
        db_path=db_path,
        page_size=page_size,
        channels=channels,
    )
