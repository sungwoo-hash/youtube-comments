import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import watch_list


@pytest.fixture
def temp_list(tmp_path, monkeypatch):
    list_file = tmp_path / "watch_list.txt"
    monkeypatch.setattr(watch_list, "WATCH_LIST_PATH", list_file)
    return list_file


def test_get_watch_list_empty(temp_list):
    assert watch_list.get_watch_list() == []


def test_add_url(temp_list):
    watch_list.add_url("https://youtube.com/watch?v=abc")
    assert "https://youtube.com/watch?v=abc" in watch_list.get_watch_list()


def test_add_url_no_duplicate(temp_list):
    watch_list.add_url("https://youtube.com/watch?v=abc")
    watch_list.add_url("https://youtube.com/watch?v=abc")
    assert watch_list.get_watch_list().count("https://youtube.com/watch?v=abc") == 1


def test_remove_url(temp_list):
    watch_list.add_url("https://youtube.com/watch?v=abc")
    watch_list.remove_url("https://youtube.com/watch?v=abc")
    assert watch_list.get_watch_list() == []


def test_multiple_urls(temp_list):
    watch_list.add_url("https://youtube.com/watch?v=aaa")
    watch_list.add_url("https://youtube.com/watch?v=bbb")
    assert len(watch_list.get_watch_list()) == 2
