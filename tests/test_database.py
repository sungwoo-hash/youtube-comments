import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import database


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    return db_file


SAMPLE_COMMENTS = [
    {
        "comment_id": "abc123",
        "video_id": "vid001",
        "parent_id": None,
        "author": "홍길동",
        "text": "좋은 영상이네요",
        "like_count": 5,
        "published_at": "2026-04-01T10:00:00Z",
    },
    {
        "comment_id": "abc124",
        "video_id": "vid001",
        "parent_id": "abc123",
        "author": "김철수",
        "text": "동의합니다",
        "like_count": 1,
        "published_at": "2026-04-01T11:00:00Z",
    },
]


def test_init_db_creates_table(temp_db):
    import sqlite3
    with sqlite3.connect(temp_db) as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
        ).fetchone()
    assert tables is not None


def test_upsert_adds_new_comments(temp_db):
    database.upsert_comments(SAMPLE_COMMENTS)
    ids = database.get_comment_ids("vid001")
    assert "abc123" in ids
    assert "abc124" in ids


def test_upsert_updates_like_count(temp_db):
    database.upsert_comments(SAMPLE_COMMENTS)
    updated = [{"comment_id": "abc123", "video_id": "vid001", "parent_id": None,
                "author": "홍길동", "text": "좋은 영상이네요", "like_count": 99,
                "published_at": "2026-04-01T10:00:00Z"}]
    database.upsert_comments(updated)
    comments = database.get_all_comments("vid001")
    top = next(c for c in comments if c["comment_id"] == "abc123")
    assert top["like_count"] == 99


def test_mark_deleted(temp_db):
    database.upsert_comments(SAMPLE_COMMENTS)
    database.mark_deleted({"abc123"})
    ids = database.get_comment_ids("vid001")
    assert "abc123" not in ids
    all_comments = database.get_all_comments("vid001")
    deleted = next(c for c in all_comments if c["comment_id"] == "abc123")
    assert deleted["status"] == "deleted"
    assert deleted["deleted_at"] is not None


def test_get_all_comments_returns_both_statuses(temp_db):
    database.upsert_comments(SAMPLE_COMMENTS)
    database.mark_deleted({"abc123"})
    all_comments = database.get_all_comments("vid001")
    assert len(all_comments) == 2
