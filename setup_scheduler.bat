@echo off
chcp 65001 > nul
echo YouTube 댓글 자동 수집 - 작업 스케줄러 등록
echo.

schtasks /delete /tn "YouTubeCommentCollector" /f 2>nul

schtasks /create /tn "YouTubeCommentCollector" /tr "py C:\Users\user\youtube-comments\collect_job.py" /sc hourly /mo 1 /st 00:00 /f

if %errorlevel% == 0 (
    echo.
    echo 성공! 작업 스케줄러가 등록되었습니다.
    echo 매 시간 정각에 자동으로 댓글을 수집합니다.
) else (
    echo.
    echo 오류가 발생했습니다. 관리자 권한으로 다시 실행해 주세요.
)

echo.
pause
