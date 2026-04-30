import pytest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import database
import collector


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_file)
    database.init_db()
    return db_file


FAKE_COMMENTS = [
    {
        "comment_id": "c1",
        "video_id": "vid001",
        "parent_id": None,
        "author": "유저A",
        "text": "첫 댓글",
        "like_count": 3,
        "published_at": "2026-04-01T10:00:00Z",
    },
    {
        "comment_id": "c2",
        "video_id": "vid001",
        "parent_id": "c1",
        "author": "유저B",
        "text": "답글",
        "like_count": 1,
        "published_at": "2026-04-01T11:00:00Z",
    },
]


def test_collect_inserts_new_comments(temp_db):
    with patch("collector.extract_video_id", return_value="vid001"), \
         patch("collector.fetch_all_comments", return_value=FAKE_COMMENTS):
        result = collector.collect("fake_key", "https://youtube.com/watch?v=vid001")
    assert result["total"] == 2
    assert result["new"] == 2
    assert result["deleted"] == 0


def test_collect_detects_deleted_comment(temp_db):
    with patch("collector.extract_video_id", return_value="vid001"), \
         patch("collector.fetch_all_comments", return_value=FAKE_COMMENTS):
        collector.collect("fake_key", "https://youtube.com/watch?v=vid001")

    only_c1 = [FAKE_COMMENTS[0]]
    with patch("collector.extract_video_id", return_value="vid001"), \
         patch("collector.fetch_all_comments", return_value=only_c1):
        result = collector.collect("fake_key", "https://youtube.com/watch?v=vid001")

    assert result["deleted"] == 1
    all_comments = database.get_all_comments("vid001")
    deleted = next(c for c in all_comments if c["comment_id"] == "c2")
    assert deleted["status"] == "deleted"


def test_collect_raises_on_invalid_url(temp_db):
    with patch("collector.extract_video_id", return_value=None):
        with pytest.raises(ValueError, match="invalid_url"):
            collector.collect("fake_key", "https://invalid.com")
