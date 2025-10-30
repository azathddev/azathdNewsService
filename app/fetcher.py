# app/fetcher.py
import httpx, feedparser, re, hashlib
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from .models import Post, DB

def strip_html(html: str) -> str:
    if not html:
        return ""
    # переносы из <br> -> \n
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    # режем все теги
    text = re.sub(r"<[^>]+>", " ", text)
    # декод некоторых сущностей
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">"))
    # чистим пробелы и лишние \n
    text = re.sub(r"[ \t\xa0]+", " ", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

def to_iso_z(dt: Optional[datetime]) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def stable_int_id(s: str) -> int:
    h = hashlib.sha1(s.encode("utf-8")).digest()
    return int.from_bytes(h[:6], "big")  # ~2^48

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
    # content -> summary/description -> title
    if getattr(entry, "content", None):
        for c in entry.content:
            v = getattr(c, "value", None)
            if v:
                t = strip_html(v)
                if t:
                    return t
    # feedparser кладёт description -> summary
    if getattr(entry, "summary", None):
        t = strip_html(entry.summary)
        if t:
            return t
    if getattr(entry, "title", None):
        t = strip_html(entry.title)
        if t:
            return t
    return ""

async def fetch_rss_items(rss_url: str, timeout_s: int = 25):
    headers = {
        "User-Agent": "tg-text-site/1.0",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True, headers=headers) as client:
        r = await client.get(rss_url)
        r.raise_for_status()
        return feedparser.parse(r.content)

async def refresh_channel_from_rss(db: DB, rss_url: str, slug: str, pull_limit: int = 400) -> Tuple[int, int]:
    feed = await fetch_rss_items(rss_url)
    scanned = 0
    items: List[Post] = []
    for e in feed.entries[:pull_limit]:
        scanned += 1
        text = entry_text(e)
        if not text:
            # не теряем записи с одними медиа — оставим маркеры
            parts = []
            if getattr(e, "title", None):
                parts.append(strip_html(e.title))
            if getattr(e, "link", None):
                parts.append(str(e.link))
            text = " | ".join([p for p in parts if p]) or "[без текста]"

        if getattr(e, "published_parsed", None):
            dt = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
        elif getattr(e, "updated_parsed", None):
            dt = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
        else:
            dt = datetime.now(timezone.utc)

        msg_id = guess_msg_id(e)
        items.append(Post(channel_slug=slug, msg_id=msg_id, date_iso=to_iso_z(dt), text=text))

    before = db.count_posts(slug)
    db.upsert_posts(items)
    after = db.count_posts(slug)
    saved = max(0, after - before)
    return scanned, saved
