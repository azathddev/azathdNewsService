from datetime import timezone
from typing import List, Optional
from telethon import TelegramClient
from telethon.tl.types import Message
from .models import Post, DB

def to_iso_z(dt) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    return " ".join(s.replace("\u0000", "").split())

async def fetch_latest_text_posts(
    client: TelegramClient, ref: str, channel_slug: str, limit: int = 300
) -> List[Post]:
    items: List[Post] = []
    async for msg in client.iter_messages(ref, limit=limit):
        if not isinstance(msg, Message):
            continue
        text = clean_text(getattr(msg, "message", None))
        if not text:
            continue
        items.append(Post(
            channel_slug=channel_slug,
            msg_id=msg.id,
            date_iso=to_iso_z(msg.date),
            text=text
        ))
    return items

async def refresh_channel(db: DB, client: TelegramClient, ref: str, slug: str, pull_limit: int = 400):
    posts = await fetch_latest_text_posts(client, ref, slug, limit=pull_limit)
    db.upsert_posts(posts)
    return len(posts)
