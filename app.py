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


def to_kst(utc_str):
    if not utc_str:
        return ""
    try:
        from datetime import datetime, timezone, timedelta
        KST = timezone(timedelta(hours=9))
        # Z 또는 +00:00 형식 모두 처리
        utc_str = utc_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(utc_str)
        return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return utc_str[:16].replace("T", " ")

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

tab1, tab2, tab3, tab4 = st.tabs(["댓글 수집", "자동 수집 관리", "수집 내역 조회", "댓글 분석"])

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
                    lambda r: f"삭제됨 ({to_kst(r['deleted_at'])[:10]})" if r["status"] == "deleted" else "활성",
                    axis=1
                )
                df["작성일(KST)"] = df["published_at"].apply(to_kst)
                display_df = df[["유형", "author", "text", "like_count", "작성일(KST)", "상태표시"]].copy()
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
                last_collected = to_kst(df["first_collected_at"].max()) if not df.empty else "-"

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
                    lambda r: f"삭제됨 ({to_kst(r['deleted_at'])[:10]})" if r["status"] == "deleted" else "활성",
                    axis=1
                )
                df["작성일(KST)"] = df["published_at"].apply(to_kst)
                display_df = df[["유형", "author", "text", "like_count", "작성일(KST)", "상태표시"]].copy()
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

# ── 탭 4: 댓글 분석 ──────────────────────────────────────────
with tab4:
    st.subheader("댓글 분석")
    st.caption("수집 내역 조회 탭에서 다운로드한 CSV 파일을 업로드하면 Groq AI가 여론을 분석합니다.")

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        st.error("⚠️ GROQ_API_KEY가 설정되지 않았습니다. Render 환경변수에 추가해 주세요.")
        st.stop()

    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

    if uploaded_file:
        df_csv = pd.read_csv(uploaded_file)

        # 댓글 텍스트 컬럼 확인
        text_col = None
        for col in ["댓글 내용", "text"]:
            if col in df_csv.columns:
                text_col = col
                break

        if text_col is None:
            st.error("올바른 형식의 CSV 파일이 아닙니다. '수집 내역 조회' 탭에서 다운로드한 파일을 사용해 주세요.")
        else:
            total_comments = len(df_csv)
            st.info(f"총 **{total_comments}개** 댓글이 로드됐습니다.")

            if st.button("🔍 분석 시작"):
                with st.spinner("AI가 댓글을 분석하는 중입니다..."):
                    try:
                        from groq import Groq
                        import json
                        import math

                        client = Groq(api_key=groq_key)

                        # 활성 댓글 전체 사용
                        active_mask = df_csv.get("상태", df_csv.get("status", pd.Series(["활성"] * len(df_csv)))) == "활성"
                        df_active = df_csv[active_mask] if active_mask.any() else df_csv
                        all_comments = df_active[text_col].dropna().tolist()

                        CHUNK_SIZE = 80
                        chunks = [all_comments[i:i+CHUNK_SIZE] for i in range(0, len(all_comments), CHUNK_SIZE)]

                        def analyze_chunk(comments):
                            comments_text = "\n".join([f"- {c}" for c in comments])
                            prompt = f"""아래는 유튜브 영상에 달린 댓글 목록입니다. 한국어로 분석해 주세요.

댓글 목록:
{comments_text}

반드시 한국어로만 작성하세요. 다른 언어는 절대 사용하지 마세요.

다음 형식의 JSON으로만 응답해 주세요. JSON 외 다른 텍스트는 포함하지 마세요:
{{
  "summary": "이 댓글들의 여론을 2~3문장으로 요약",
  "sentiment": {{"긍정": 숫자, "부정": 숫자, "중립": 숫자}},
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "notable_comments": ["주목할 댓글1", "주목할 댓글2", "주목할 댓글3"]
}}

sentiment의 숫자는 전체 합이 100이 되는 퍼센트 값으로 입력해 주세요."""
                            response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0
                            )
                            raw = response.choices[0].message.content.strip()
                            if raw.startswith("```"):
                                raw = "\n".join(raw.split("\n")[1:-1])
                            return json.loads(raw)

                        # 청크별 분석
                        chunk_results = []
                        progress = st.progress(0, text="분석 중...")
                        for i, chunk in enumerate(chunks):
                            chunk_results.append(analyze_chunk(chunk))
                            progress.progress((i + 1) / len(chunks), text=f"분석 중... ({i+1}/{len(chunks)})")
                        progress.empty()

                        # 청크가 1개면 바로 사용, 여러 개면 최종 통합 분석
                        if len(chunk_results) == 1:
                            result = chunk_results[0]
                        else:
                            summaries = "\n".join([f"- {r['summary']}" for r in chunk_results])
                            all_keywords = [kw for r in chunk_results for kw in r["keywords"]]
                            all_notable = [c for r in chunk_results for c in r["notable_comments"]]

                            # 감성 평균
                            avg_sentiment = {
                                "긍정": round(sum(r["sentiment"]["긍정"] for r in chunk_results) / len(chunk_results)),
                                "부정": round(sum(r["sentiment"]["부정"] for r in chunk_results) / len(chunk_results)),
                                "중립": round(sum(r["sentiment"]["중립"] for r in chunk_results) / len(chunk_results)),
                            }

                            # 최종 요약 생성
                            final_prompt = f"""아래는 유튜브 영상 댓글을 여러 구간으로 나눠 분석한 요약들입니다. 이를 종합해서 전체 여론을 한국어로 3~5문장으로 요약해 주세요. JSON 외 다른 텍스트 없이 아래 형식으로만 응답해 주세요:
{{"final_summary": "전체 여론 요약"}}

구간별 요약:
{summaries}"""
                            final_response = client.chat.completions.create(
                                model="llama-3.3-70b-versatile",
                                messages=[{"role": "user", "content": final_prompt}],
                                temperature=0
                            )
                            final_raw = final_response.choices[0].message.content.strip()
                            if final_raw.startswith("```"):
                                final_raw = "\n".join(final_raw.split("\n")[1:-1])
                            final_json = json.loads(final_raw)

                            result = {
                                "summary": final_json["final_summary"],
                                "sentiment": avg_sentiment,
                                "keywords": list(dict.fromkeys(all_keywords))[:10],
                                "notable_comments": all_notable[:5]
                            }

                        # 여론 요약
                        st.subheader("📝 전체 여론 요약")
                        st.write(result["summary"])

                        st.divider()

                        # 감성 분포
                        st.subheader("📊 감성 분포")
                        import plotly.graph_objects as go
                        sentiment_labels = list(result["sentiment"].keys())
                        sentiment_values = list(result["sentiment"].values())
                        colors = {"긍정": "#4CAF50", "부정": "#F44336", "중립": "#9E9E9E"}
                        fig = go.Figure(go.Bar(
                            x=sentiment_labels,
                            y=sentiment_values,
                            text=[f"{v}%" for v in sentiment_values],
                            textposition="auto",
                            marker_color=[colors.get(k, "#2196F3") for k in sentiment_labels]
                        ))
                        fig.update_layout(
                            yaxis_title="비율(%)",
                            yaxis_range=[0, 100],
                            showlegend=False,
                            height=300,
                            margin=dict(t=20, b=20)
                        )
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.plotly_chart(fig, use_container_width=True)
                        with col2:
                            st.write("")
                            for k, v in result["sentiment"].items():
                                st.metric(k, f"{v}%")

                        st.divider()

                        # 주요 키워드
                        st.subheader("🔑 주요 키워드")
                        keywords = result["keywords"]
                        cols = st.columns(5)
                        for i, kw in enumerate(keywords):
                            cols[i % 5].markdown(f"**#{kw}**")

                        st.divider()

                        # 주목할 댓글
                        st.subheader("💬 주목할 댓글")
                        for i, comment in enumerate(result["notable_comments"], 1):
                            st.markdown(f"**{i}.** {comment}")

                    except json.JSONDecodeError:
                        st.error("분석 결과를 파싱하는 데 실패했습니다. 다시 시도해 주세요.")
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {e}")
