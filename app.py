import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from database import init_db
from collector import collect

load_dotenv()
init_db()

st.set_page_config(page_title="YouTube 댓글 수집기", layout="wide")
st.title("📋 YouTube 댓글 수집기")

# API 키 확인
api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
if not api_key:
    st.error(
        "⚠️ API 키가 설정되지 않았습니다. "
        "프로젝트 폴더에 `.env` 파일을 만들고 `YOUTUBE_API_KEY=키값` 을 입력해 주세요."
    )
    st.stop()

st.success("✅ API 키 확인됨")

url = st.text_input(
    "YouTube 영상 URL",
    placeholder="https://www.youtube.com/watch?v=..."
)

if st.button("댓글 수집", disabled=not url.strip()):
    with st.spinner("댓글을 수집하는 중입니다..."):
        try:
            result = collect(api_key, url.strip())

            st.success(
                f"수집 완료 — 전체 **{result['total']}개** "
                f"(신규 {result['new']}개 / 삭제 감지 {result['deleted']}개)"
            )

            comments = result["comments"]
            df = pd.DataFrame(comments)
            df["parent_id"] = df["parent_id"].fillna("")
            df["deleted_at"] = df["deleted_at"].fillna("")

            df["유형"] = df["parent_id"].apply(lambda x: "  └ 답글" if x else "댓글")
            df["상태표시"] = df.apply(
                lambda r: f"삭제됨 ({r['deleted_at'][:10]})" if r["status"] == "deleted" else "활성",
                axis=1
            )
            display_df = df[["유형", "author", "text", "like_count", "published_at", "상태표시"]].copy()
            display_df.columns = ["유형", "작성자", "댓글 내용", "좋아요", "작성일", "상태"]

            def highlight_deleted(row):
                if "삭제됨" in row["상태"]:
                    return ["background-color: #ffcccc"] * len(row)
                return [""] * len(row)

            styled = display_df.style.apply(highlight_deleted, axis=1)
            st.dataframe(styled, use_container_width=True, height=500)

            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="⬇️ CSV 다운로드",
                data=csv_data,
                file_name=f"comments_{result['video_id']}.csv",
                mime="text/csv"
            )

        except ValueError as e:
            if str(e) == "invalid_url":
                st.error("올바른 YouTube 영상 URL을 입력해 주세요.")
            else:
                st.error(f"오류: {e}")

        except HttpError as e:
            status = e.resp.status
            content = str(e)
            if status == 403:
                if "quotaExceeded" in content or "dailyLimitExceeded" in content:
                    st.error("오늘 API 한도를 초과했습니다. 내일 다시 시도해 주세요.")
                elif "commentsDisabled" in content:
                    st.error("이 영상은 댓글이 비활성화되어 있습니다.")
                else:
                    st.error("API 키를 확인해 주세요.")
            elif status == 400:
                st.error("올바른 YouTube 영상 URL을 입력해 주세요.")
            else:
                st.error(f"API 오류 ({status}): {e}")

        except Exception as e:
            msg = str(e).lower()
            if "connection" in msg or "network" in msg or "timeout" in msg:
                st.error("네트워크 오류가 발생했습니다. 인터넷 연결을 확인해 주세요.")
            else:
                st.error(f"오류가 발생했습니다: {e}")
