import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))

from watch_list import get_watch_list
from database import init_db
from collector import collect

LOG_PATH = Path(__file__).parent / "collect_job.log"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        log("ERROR: YOUTUBE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        sys.exit(1)

    init_db()
    urls = get_watch_list()

    if not urls:
        log("수집할 URL이 없습니다. 앱에서 URL을 등록해 주세요.")
        return

    log(f"자동 수집 시작 — {len(urls)}개 영상")
    for url in urls:
        try:
            result = collect(api_key, url)
            log(f"[완료] {url} → 전체 {result['total']}개 (신규 {result['new']}개, 삭제 {result['deleted']}개)")
        except Exception as e:
            log(f"[오류] {url} → {e}")

    log("자동 수집 완료")


if __name__ == "__main__":
    main()
