
import httpx, feedparser, re, hashlib
from datetime import datetime, timezone
from typing import List, Optional
from .models import Post, DB

def strip_html(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">"))
    return " ".join(text.split())

def to_iso_z(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def stable_int_id(s: str) -> int:
    h = hashlib.sha1(s.encode("utf-8")).digest()
    return int.from_bytes(h[:6], "big")

def guess_msg_id(entry) -> int:
    cand = None
    for key in ("id", "guid", "link"):
        if getattr(entry, key, None):
            cand = getattr(entry, key)
            break
    if not cand:
        return stable_int_id(str(entry))
    m = re.search(r"(\d{1,12})(?:\D*$|$)", str(cand))
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return stable_int_id(str(cand))

def entry_text(entry) -> str:
    """Достаём текст из content → summary → title (без HTML)."""
    if getattr(entry, "content", None):
        for c in entry.content:
            if c and getattr(c, "value", None):
                t = strip_html(c.value)
                if t:
                    return t
    if getattr(entry, "summary", None):
        t = strip_html(entry.summary)
        if t:
            return t
    if getattr(entry, "title", None):
        t = strip_html(entry.title)
        if t:
            return t
    return ""  # может быть пусто у медиа-постов

async def fetch_rss_items(rss_url: str, timeout_s: int = 20):
    headers = {
        "User-Agent": "tg-text-site/1.0",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True, headers=headers) as client:
        r = await client.get(rss_url)
        r.raise_for_status()
        return feedparser.parse(r.content)

async def refresh_channel_from_rss(db: DB, rss_url: str, slug: str, pull_limit: int = 400):
    feed = await fetch_rss_items(rss_url)
    items: List[Post] = []
    entries = feed.entries[:pull_limit]
    for e in entries:
        text = entry_text(e)

        # если совсем нет текста — подставим заголовок/ссылку, чтобы не терять пост
        fallback_parts = []
        if not text:
            if getattr(e, "title", None):
                fallback_parts.append(strip_html(e.title))
            if getattr(e, "link", None):
                fallback_parts.append(str(e.link))
        if not text and fallback_parts:
            text = " | ".join(fallback_parts)
        if not text:
            text = "[без текста]"  # минимальный маркер, чтобы запись попала в БД

        # дата
        if getattr(e, "published_parsed", None):
            dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        elif getattr(e, "updated_parsed", None):
            dt = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        msg_id = guess_msg_id(e)
        items.append(Post(channel_slug=slug, msg_id=msg_id, date_iso=to_iso_z(dt), text=text))
