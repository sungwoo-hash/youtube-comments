from pathlib import Path

WATCH_LIST_PATH = Path(__file__).parent / "watch_list.txt"


def get_watch_list():
    if not WATCH_LIST_PATH.exists():
        return []
    lines = WATCH_LIST_PATH.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def add_url(url):
    urls = get_watch_list()
    if url not in urls:
        urls.append(url)
        WATCH_LIST_PATH.write_text("\n".join(urls) + "\n", encoding="utf-8")


def remove_url(url):
    urls = get_watch_list()
    urls = [u for u in urls if u != url]
    WATCH_LIST_PATH.write_text("\n".join(urls) + "\n", encoding="utf-8")
