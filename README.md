
# TG Text Site (RSS)

Лёгкий сайт на FastAPI, который показывает **текстовые посты** из Telegram-каналов через **RSS** (без Telethon, без TG API ключей).
- Главная: список каналов из `channels.yml`.
- Страница канала: текстовые посты без медиа, пагинация.
- Источник: RSS (по прямой ссылке `rss` или через `username` + `RSSHUB_BASE`).

## Быстрый старт (Docker)
```bash
cp .env.example .env
docker compose up --build -d
```
Откройте: http://localhost:8000

## Настройка каналов
В `channels.yml` можно задать:
- `username`: короткое имя TG-канала — RSS будет взят по `RSSHUB_BASE/telegram/channel/<username>`
- **или** `rss`: прямая RSS-ссылка.

Пример:
```yaml
channels:
  - slug: topor
    title: Топор
    username: "topor"
  - slug: some
    title: Канал по RSS
    rss: "https://rsshub.app/telegram/channel/some"
```

## Локальный запуск
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
