import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def extract_video_id(url):
    """URL에서 유튜브 영상 ID(11자리)를 추출한다."""
    patterns = [
        r"[?&]v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_all_comments(api_key, video_id):
    """최상위 댓글과 모든 답글을 수집하여 리스트로 반환한다."""
    service = build("youtube", "v3", developerKey=api_key)
    comments = []

    request = service.commentThreads().list(
        part="snippet,replies",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )
    while request:
        response = request.execute()
        for item in response.get("items", []):
            top_snippet = item["snippet"]["topLevelComment"]["snippet"]
            top_id = item["snippet"]["topLevelComment"]["id"]
            comments.append({
                "comment_id": top_id,
                "video_id": video_id,
                "parent_id": None,
                "author": top_snippet["authorDisplayName"],
                "text": top_snippet["textDisplay"],
                "like_count": top_snippet["likeCount"],
                "published_at": top_snippet["publishedAt"],
            })

            total_replies = item["snippet"].get("totalReplyCount", 0)
            if total_replies > 0:
                reply_request = service.comments().list(
                    part="snippet",
                    parentId=top_id,
                    maxResults=100,
                    textFormat="plainText"
                )
                while reply_request:
                    reply_response = reply_request.execute()
                    for reply in reply_response.get("items", []):
                        rs = reply["snippet"]
                        comments.append({
                            "comment_id": reply["id"],
                            "video_id": video_id,
                            "parent_id": top_id,
                            "author": rs["authorDisplayName"],
                            "text": rs["textDisplay"],
                            "like_count": rs["likeCount"],
                            "published_at": rs["publishedAt"],
                        })
                    reply_request = service.comments().list_next(
                        reply_request, reply_response
                    )

        request = service.commentThreads().list_next(request, response)

    return comments
