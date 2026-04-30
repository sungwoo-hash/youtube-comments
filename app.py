import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from database import init_db, get_all_comments
from collector import collect
from watch_list import get_watch_list, add_url, remove_url
from youtube_api import extract_video_id

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

tab1, tab2, tab3 = st.tabs(["댓글 수집", "자동 수집 관리", "수집 내역 조회"])

# ── 탭 1: 댓글 수집 ──────────────────────────────────────────
with tab1:
    url = st.text_input(
        "YouTube 영상 URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key="manual_url"
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

# ── 탭 2: 자동 수집 관리 ─────────────────────────────────────
with tab2:
    st.subheader("자동 수집 URL 관리")
    st.caption("등록된 URL은 Windows 작업 스케줄러에 의해 1시간마다 자동으로 수집됩니다.")

    new_url = st.text_input(
        "수집할 YouTube 영상 URL 추가",
        placeholder="https://www.youtube.com/watch?v=...",
        key="watch_url"
    )

    if st.button("➕ 등록", disabled=not new_url.strip()):
        url_to_add = new_url.strip()
        if not extract_video_id(url_to_add):
            st.error("올바른 YouTube 영상 URL을 입력해 주세요.")
        else:
            add_url(url_to_add)
            st.success(f"등록되었습니다: {url_to_add}")
            st.rerun()

    st.divider()

    urls = get_watch_list()
    if not urls:
        st.info("등록된 URL이 없습니다. 위에서 URL을 추가해 주세요.")
    else:
        st.markdown(f"**등록된 영상: {len(urls)}개**")
        for i, u in enumerate(urls):
            col1, col2 = st.columns([6, 1])
            with col1:
                st.text(u)
            with col2:
                if st.button("삭제", key=f"remove_{i}"):
                    remove_url(u)
                    st.rerun()

    st.divider()
    st.subheader("작업 스케줄러 설정")
    st.caption("아직 작업 스케줄러를 등록하지 않았다면 아래 파일을 실행하세요.")
    st.code("C:\\Users\\user\\youtube-comments\\setup_scheduler.bat", language="text")
    st.markdown("**실행 방법:** 파일 탐색기에서 `setup_scheduler.bat`을 **우클릭 → 관리자 권한으로 실행**")

# ── 탭 3: 수집 내역 조회 ─────────────────────────────────────
with tab3:
    st.subheader("수집된 댓글 조회")
    st.caption("자동 수집 또는 수동 수집으로 저장된 댓글을 API 호출 없이 바로 조회합니다.")

    view_url = st.text_input(
        "YouTube 영상 URL",
        placeholder="https://www.youtube.com/watch?v=...",
        key="view_url"
    )

    if view_url.strip():
        video_id = extract_video_id(view_url.strip())
        if not video_id:
            st.error("올바른 YouTube 영상 URL을 입력해 주세요.")
        else:
            comments = get_all_comments(video_id)
            if not comments:
                st.info("수집된 댓글이 없습니다. 먼저 댓글을 수집해 주세요.")
            else:
                df = pd.DataFrame(comments)
                df["parent_id"] = df["parent_id"].fillna("")
                df["deleted_at"] = df["deleted_at"].fillna("")

                total = len(df)
                active = (df["status"] == "active").sum()
                deleted = (df["status"] == "deleted").sum()
                last_collected = df["first_collected_at"].max()[:16].replace("T", " ") if not df.empty else "-"

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("전체 댓글", f"{total}개")
                col2.metric("활성", f"{active}개")
                col3.metric("삭제됨", f"{deleted}개")
                col4.metric("최근 수집", last_collected)

                st.divider()

                show_deleted = st.checkbox("삭제된 댓글 포함", value=True)
                if not show_deleted:
                    df = df[df["status"] == "active"]

                df["유형"] = df["parent_id"].apply(lambda x: "  └ 답글" if x else "댓글")
                df["상태표시"] = df.apply(
                    lambda r: f"삭제됨 ({r['deleted_at'][:10]})" if r["status"] == "deleted" else "활성",
                    axis=1
                )
                display_df = df[["유형", "author", "text", "like_count", "published_at", "상태표시"]].copy()
                display_df.columns = ["유형", "작성자", "댓글 내용", "좋아요", "작성일", "상태"]

                def highlight_deleted2(row):
                    if "삭제됨" in row["상태"]:
                        return ["background-color: #ffcccc"] * len(row)
                    return [""] * len(row)

                styled = display_df.style.apply(highlight_deleted2, axis=1)
                st.dataframe(styled, use_container_width=True, height=500)

                csv_data = df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="⬇️ CSV 다운로드",
                    data=csv_data,
                    file_name=f"comments_{video_id}.csv",
                    mime="text/csv"
                )
