from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import List

@dataclass
class Post:
    channel_slug: str
    msg_id: int
    date_iso: str
    text: str

class DB:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._connect() as con:
            con.execute("""
            CREATE TABLE IF NOT EXISTS posts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              channel_slug TEXT NOT NULL,
              msg_id INTEGER NOT NULL,
              date_iso TEXT NOT NULL,
              text TEXT NOT NULL,
              UNIQUE(channel_slug, msg_id)
            )
            """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_posts_chan_date ON posts(channel_slug, date_iso DESC)")
            con.commit()

    def upsert_posts(self, items: List[Post]):
        if not items:
            return
        with self._connect() as con:
            con.executemany(
                """
                  INSERT INTO posts(channel_slug, msg_id, date_iso, text)
                  VALUES(?,?,?,?)
                  ON CONFLICT(channel_slug, msg_id) DO UPDATE SET
                    date_iso=excluded.date_iso,
                    text=excluded.text
                """,
                [(p.channel_slug, p.msg_id, p.date_iso, p.text) for p in items],
            )
            con.commit()

    def list_posts(self, channel_slug: str, limit: int, offset: int) -> List[Post]:
        with self._connect() as con:
            cur = con.execute(
                """
                  SELECT channel_slug, msg_id, date_iso, text
                  FROM posts
                  WHERE channel_slug=?
                  ORDER BY date_iso DESC, msg_id DESC
                  LIMIT ? OFFSET ?
                """,
                (channel_slug, limit, offset),
            )
            rows = cur.fetchall()
        return [Post(*row) for row in rows]

    def count_posts(self, channel_slug: str) -> int:
        with self._connect() as con:
            cur = con.execute("SELECT COUNT(*) FROM posts WHERE channel_slug=?", (channel_slug,))
            (n,) = cur.fetchone()
        return int(n)
