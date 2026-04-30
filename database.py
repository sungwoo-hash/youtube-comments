import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "")

# SQLite fallback for local development
if DATABASE_URL:
    import psycopg2
    import psycopg2.extras

    def get_connection():
        return psycopg2.connect(DATABASE_URL)

    def init_db():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS comments (
                        comment_id       TEXT PRIMARY KEY,
                        video_id         TEXT NOT NULL,
                        parent_id        TEXT,
                        author           TEXT,
                        text             TEXT,
                        like_count       INTEGER DEFAULT 0,
                        published_at     TEXT,
                        first_collected_at TEXT NOT NULL,
                        status           TEXT NOT NULL DEFAULT 'active',
                        deleted_at       TEXT
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS watch_list (
                        url      TEXT PRIMARY KEY,
                        added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
            conn.commit()

    def get_comment_ids(video_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT comment_id FROM comments WHERE video_id = %s AND status = 'active'",
                    (video_id,)
                )
                rows = cur.fetchall()
        return {row[0] for row in rows}

    def upsert_comments(comments):
        now = datetime.now().isoformat()
        with get_connection() as conn:
            with conn.cursor() as cur:
                for c in comments:
                    cur.execute(
                        "SELECT comment_id FROM comments WHERE comment_id = %s",
                        (c["comment_id"],)
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            """UPDATE comments
                               SET like_count = %s, status = 'active', deleted_at = NULL
                               WHERE comment_id = %s""",
                            (c["like_count"], c["comment_id"])
                        )
                    else:
                        cur.execute(
                            """INSERT INTO comments
                               (comment_id, video_id, parent_id, author, text,
                                like_count, published_at, first_collected_at, status)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active')""",
                            (c["comment_id"], c["video_id"], c["parent_id"],
                             c["author"], c["text"], c["like_count"],
                             c["published_at"], now)
                        )
            conn.commit()

    def mark_deleted(comment_ids):
        now = datetime.now().isoformat()
        with get_connection() as conn:
            with conn.cursor() as cur:
                for cid in comment_ids:
                    cur.execute(
                        "UPDATE comments SET status = 'deleted', deleted_at = %s WHERE comment_id = %s",
                        (now, cid)
                    )
            conn.commit()

    def get_all_comments(video_id):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT comment_id, parent_id, author, text, like_count,
                              published_at, first_collected_at, status, deleted_at
                       FROM comments
                       WHERE video_id = %s
                       ORDER BY
                           COALESCE(parent_id, comment_id),
                           parent_id IS NOT NULL,
                           published_at""",
                    (video_id,)
                )
                rows = cur.fetchall()
        columns = ["comment_id", "parent_id", "author", "text", "like_count",
                   "published_at", "first_collected_at", "status", "deleted_at"]
        return [dict(zip(columns, row)) for row in rows]

else:
    import sqlite3
    from pathlib import Path

    DB_PATH = Path(__file__).parent / "comments.db"

    def get_connection():
        return sqlite3.connect(DB_PATH)

    def init_db():
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    comment_id       TEXT PRIMARY KEY,
                    video_id         TEXT NOT NULL,
                    parent_id        TEXT,
                    author           TEXT,
                    text             TEXT,
                    like_count       INTEGER DEFAULT 0,
                    published_at     TEXT,
                    first_collected_at TEXT NOT NULL,
                    status           TEXT NOT NULL DEFAULT 'active',
                    deleted_at       TEXT
                )
            """)
            conn.commit()

    def get_comment_ids(video_id):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT comment_id FROM comments WHERE video_id = ? AND status = 'active'",
                (video_id,)
            ).fetchall()
        return {row[0] for row in rows}

    def upsert_comments(comments):
        now = datetime.now().isoformat()
        with get_connection() as conn:
            for c in comments:
                existing = conn.execute(
                    "SELECT comment_id FROM comments WHERE comment_id = ?",
                    (c["comment_id"],)
                ).fetchone()
                if existing:
                    conn.execute(
                        """UPDATE comments
                           SET like_count = ?, status = 'active', deleted_at = NULL
                           WHERE comment_id = ?""",
                        (c["like_count"], c["comment_id"])
                    )
                else:
                    conn.execute(
                        """INSERT INTO comments
                           (comment_id, video_id, parent_id, author, text,
                            like_count, published_at, first_collected_at, status)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
                        (c["comment_id"], c["video_id"], c["parent_id"],
                         c["author"], c["text"], c["like_count"],
                         c["published_at"], now)
                    )
            conn.commit()

    def mark_deleted(comment_ids):
        now = datetime.now().isoformat()
        with get_connection() as conn:
            for cid in comment_ids:
                conn.execute(
                    "UPDATE comments SET status = 'deleted', deleted_at = ? WHERE comment_id = ?",
                    (now, cid)
                )
            conn.commit()

    def get_all_comments(video_id):
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT comment_id, parent_id, author, text, like_count,
                          published_at, first_collected_at, status, deleted_at
                   FROM comments
                   WHERE video_id = ?
                   ORDER BY
                       COALESCE(parent_id, comment_id),
                       parent_id IS NOT NULL,
                       published_at""",
                (video_id,)
            ).fetchall()
        columns = ["comment_id", "parent_id", "author", "text", "like_count",
                   "published_at", "first_collected_at", "status", "deleted_at"]
        return [dict(zip(columns, row)) for row in rows]
