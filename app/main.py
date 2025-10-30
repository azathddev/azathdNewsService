
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from fastapi.responses import JSONResponse 

from .config import load_settings
from .models import DB
from .fetcher import refresh_channel_from_rss

settings = load_settings()
app = FastAPI(title="TG Text Reader (RSS)", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=500)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
db = DB(settings.db_path)

def get_channel_or_404(slug: str):
    for c in settings.channels:
        if c.slug == slug:
            return c
    return None

def build_rss_url(channel) -> str:
    if channel.rss:
        return channel.rss
    if channel.username:
        base = settings.rsshub_base.rstrip("/")
        return f"{base}/telegram/channel/{channel.username}"
    raise ValueError("Channel has neither rss nor username")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "channels": settings.channels, "title": "Каналы"})

@app.get("/api/debug/feed/{slug}")
async def debug_feed(slug: str):
    c = get_channel_or_404(slug)
    if not c:
        return PlainTextResponse("Канал не найден", status_code=404)

    rss_url = build_rss_url(c)
    from .fetcher import fetch_rss_items, entry_text
    feed = await fetch_rss_items(rss_url)
    demo = []
    for e in feed.entries[:5]:
        demo.append({
            "title": getattr(e, "title", None),
            "link": getattr(e, "link", None),
            "has_summary": bool(getattr(e, "summary", None)),
            "has_content": bool(getattr(e, "content", None)),
            "text_preview": (entry_text(e) or "")[:140]
        })
    return JSONResponse({"rss": rss_url, "count": len(feed.entries), "sample": demo})

@app.get("/c/{slug}", response_class=HTMLResponse)
async def channel_page(request: Request, slug: str, page: int = 1, limit: int = None):
    c = get_channel_or_404(slug)
    if not c:
        return PlainTextResponse("Канал не найден", status_code=404)
    limit = limit or settings.page_size
    total = db.count_posts(slug)
    pages = max(1, (total + limit - 1) // limit)
    page = max(1, min(page, pages))
    offset = (page - 1) * limit
    posts = db.list_posts(slug, limit=limit, offset=offset)

    resp = templates.TemplateResponse("channel.html", {
        "request": request,
        "channel": c,
        "posts": posts,
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit,
        "title": c.title
    })
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp

@app.get("/refresh/{slug}")
async def refresh(slug: str):
    c = get_channel_or_404(slug)
    if not c:
        return PlainTextResponse("Канал не найден", status_code=404)

    rss_url = build_rss_url(c)
    scanned, saved = await refresh_channel_from_rss(db, rss_url, c.slug)
    return JSONResponse({"slug": slug, "rss": rss_url, "scanned": scanned, "saved": saved})
