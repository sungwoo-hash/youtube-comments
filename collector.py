from database import get_comment_ids, upsert_comments, mark_deleted, get_all_comments
from youtube_api import fetch_all_comments, extract_video_id


def collect(api_key, url):
    """URL에서 댓글을 수집하고 삭제된 댓글을 감지한다.

    Returns:
        dict: video_id, total, new, deleted, comments
    Raises:
        ValueError: "invalid_url" — URL에서 영상 ID를 추출할 수 없는 경우
        googleapiclient.errors.HttpError: API 호출 실패 시
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("invalid_url")

    new_comments = fetch_all_comments(api_key, video_id)
    new_ids = {c["comment_id"] for c in new_comments}
    existing_ids = get_comment_ids(video_id)

    deleted_ids = existing_ids - new_ids
    added_ids = new_ids - existing_ids

    upsert_comments(new_comments)
    if deleted_ids:
        mark_deleted(deleted_ids)

    return {
        "video_id": video_id,
        "total": len(new_comments),
        "new": len(added_ids),
        "deleted": len(deleted_ids),
        "comments": get_all_comments(video_id),
    }
