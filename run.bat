@echo off
REM YouTube Ad Skipper Launcher for Windows

echo.
echo ================================================
echo YOUTUBE AD SKIPPER - Windows Launcher
echo ================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    echo.
    echo Installing dependencies...
    call .venv\Scripts\pip install -r requirements.txt
    echo.
)

echo Launching YouTube Ad Skipper...
echo.
call .venv\Scripts\python youtube_ad_skipper.py

if errorlevel 1 (
    echo.
    echo Error occurred. Press any key to exit.
    pause
)

exit /b 0
