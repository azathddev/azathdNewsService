# app/main.py (добавьте/замените эти хендлеры)

from fastapi.responses import JSONResponse  # в начале файла добавьте импорт

def build_rss_url(channel) -> str:
    if channel.rss:
        return channel.rss
    if channel.username:
        base = settings.rsshub_base.rstrip("/")
        return f"{base}/telegram/channel/{channel.username}"
    raise ValueError("Channel has neither rss nor username")

@app.get("/refresh/{slug}")
async def refresh(slug: str):
    c = get_channel_or_404(slug)
    if not c:
        return PlainTextResponse("Канал не найден", status_code=404)

    rss_url = build_rss_url(c)
    scanned, saved = await refresh_channel_from_rss(db, rss_url, c.slug)
    return JSONResponse({"slug": slug, "rss": rss_url, "scanned": scanned, "saved": saved})

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
