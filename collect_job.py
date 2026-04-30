import os
import sys
from pathlib import Path
from datetime import datetime

# 로컬 실행 시에만 .env 로드 (클라우드에서는 환경변수로 주입됨)
if not os.getenv("DATABASE_URL"):
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from watch_list import get_watch_list
from database import init_db
from collector import collect


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    # 로컬에서만 파일 로그 저장
    if not os.getenv("DATABASE_URL"):
        log_path = Path(__file__).parent / "collect_job.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def main():
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        log("ERROR: YOUTUBE_API_KEY not set.")
        sys.exit(1)

    init_db()
    urls = get_watch_list()

    if not urls:
        log("No URLs registered. Add URLs via the app.")
        return

    log(f"Auto-collect start — {len(urls)} video(s)")
    for url in urls:
        try:
            result = collect(api_key, url)
            log(f"[done] {url} -> total {result['total']} (new {result['new']}, deleted {result['deleted']})")
        except Exception as e:
            log(f"[error] {url} -> {e}")

    log("Auto-collect complete")


if __name__ == "__main__":
    main()
