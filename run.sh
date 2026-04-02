#!/bin/bash

# YouTube Ad Skipper Launcher for Linux/macOS

echo ""
echo "================================================"
echo "YOUTUBE AD SKIPPER - Unix Launcher"
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -f ".venv/bin/python" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv .venv
    echo ""
    echo "Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
    deactivate
    echo ""
fi

echo "Launching YouTube Ad Skipper..."
echo ""

# Activate virtual environment and run
source .venv/bin/activate
python youtube_ad_skipper.py
deactivate

echo ""
echo "Thank you for using YouTube Ad Skipper!"
echo ""
