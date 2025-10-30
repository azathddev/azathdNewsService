
from pydantic import BaseModel
import yaml, os
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent

class Channel(BaseModel):
    slug: str
    title: str
    username: Optional[str] = None
    rss: Optional[str] = None

class Settings(BaseModel):
    rsshub_base: str = "https://rsshub.app"
    db_path: str = str(ROOT / "data.db")
    page_size: int = 30
    channels: List[Channel]

def load_settings() -> Settings:
    with open(ROOT / "channels.yml", "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    channels = [Channel(**c) for c in cfg.get("channels", [])]
    rsshub_base = os.getenv("RSSHUB_BASE", "https://rsshub.app")
    db_path = os.getenv("DB_PATH", str(ROOT / "data.db"))
    page_size = int(os.getenv("PAGE_SIZE", "30"))
    return Settings(
        rsshub_base=rsshub_base,
        db_path=db_path,
        page_size=page_size,
        channels=channels,
    )
