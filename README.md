# TG Text Site (FastAPI + Telethon + SQLite)

Минимальный сайт: главная со списком каналов, страница канала с текстовыми постами (без медиа).

## Быстрый старт (Docker)
```bash
cp .env.example .env
# отредактируйте .env и channels.yml
docker compose up --build -d
```

Первый запуск может потребовать авторизацию Telethon внутри контейнера (см. инструкцию в ответе чата).

## Локальный запуск
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export TG_API_ID=...
export TG_API_HASH=...
uvicorn app.main:app --reload
```

Откройте http://localhost:8000
