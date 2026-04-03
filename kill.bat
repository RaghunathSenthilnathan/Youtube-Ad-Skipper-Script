@echo off
if exist youtube_ad_skipper.pid (
    for /f %%i in (youtube_ad_skipper.pid) do (
        taskkill /PID %%i /F >nul 2>&1
        if errorlevel 1 (
            echo Failed to kill process %%i
        ) else (
            echo Killed YouTube Ad Skipper process %%i
        )
    )
    del youtube_ad_skipper.pid
) else (
    echo No running YouTube Ad Skipper process found
)