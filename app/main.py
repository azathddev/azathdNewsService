import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask

from telethon import TelegramClient
from telethon.errors import FloodWaitError

from .config import load_settings
from .models import DB
from .fetcher import refresh_channel

settings = load_settings()
app = FastAPI(title="TG Text Reader", version="1.0.0")
app.add_middleware(GZipMiddleware, minimum_size=500)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
db = DB(settings.db_path)

client = TelegramClient(settings.session_name, settings.api_id, settings.api_hash)

@app.on_event("startup")
async def startup():
    await client.connect()

@app.on_event("shutdown")
async def shutdown():
    await client.disconnect()

def get_channel_or_404(slug: str):
    for c in settings.channels:
        if c.slug == slug:
            return c
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "channels": settings.channels, "title": "Каналы"})

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
async def refresh(slug: str, next: str = "/"):
    c = get_channel_or_404(slug)
    if not c:
        return PlainTextResponse("Канал не найден", status_code=404)

    async def do_update():
        try:
            await refresh_channel(db, client, c.ref, c.slug)
        except FloodWaitError:
            pass

    task = BackgroundTask(do_update)
    return RedirectResponse(url=next or f"/c/{slug}", background=task)
