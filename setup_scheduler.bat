@echo off
schtasks /delete /tn "YouTubeCommentCollector" /f 2>nul
schtasks /create /tn "YouTubeCommentCollector" /tr "py C:\Users\user\youtube-comments\collect_job.py" /sc hourly /mo 1 /st 00:00 /f
if %errorlevel% == 0 (
    echo Success! Task scheduled every hour.
) else (
    echo Failed. Please run as Administrator.
)
pause
