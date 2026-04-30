import os
from pathlib import Path

# DATABASE_URL이 있으면 DB 모드, 없으면 로컬 파일 모드
_USE_DB = bool(os.getenv("DATABASE_URL", ""))

WATCH_LIST_PATH = Path(__file__).parent / "watch_list.txt"


def _db_get():
    from database import get_connection
    import psycopg2
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT url FROM watch_list ORDER BY added_at")
            return [row[0] for row in cur.fetchall()]


def _db_add(url):
    from database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO watch_list (url) VALUES (%s) ON CONFLICT (url) DO NOTHING",
                (url,)
            )
        conn.commit()


def _db_remove(url):
    from database import get_connection
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watch_list WHERE url = %s", (url,))
        conn.commit()


def get_watch_list():
    if _USE_DB:
        return _db_get()
    if not WATCH_LIST_PATH.exists():
        return []
    lines = WATCH_LIST_PATH.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def add_url(url):
    if _USE_DB:
        _db_add(url)
        return
    urls = get_watch_list()
    if url not in urls:
        urls.append(url)
        WATCH_LIST_PATH.write_text("\n".join(urls) + "\n", encoding="utf-8")


def remove_url(url):
    if _USE_DB:
        _db_remove(url)
        return
    urls = get_watch_list()
    urls = [u for u in urls if u != url]
    WATCH_LIST_PATH.write_text("\n".join(urls) + "\n", encoding="utf-8")
