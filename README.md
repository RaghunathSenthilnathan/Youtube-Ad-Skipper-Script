# YouTube Ad Skipper - Optimized Edition

This is a friendly Python program that helps you skip ads on YouTube videos. 
It opens the video in Chrome and tries to press the Skip button automatically.

## 🌟 What is new in this version

- The program is split into small parts so it is easy to understand:
  - `AdDetector` checks if an ad is playing.
  - `SkipButton` finds and clicks the skip button.
  - `VideoPlayer` checks how the video is going (time and speed).
  - `Config` keeps all settings in one place.
- Use it the same way as before:
  - `YouTubeAdSkipper.run(video_url)` works the same.
- It now works for the whole video, not just 120 seconds.
- It adjusts for different video speeds (slow or fast).
- It waits a bit after video end to catch last ads.

## 🧠 How it works (simple)

1. Start the program. It asks if you want to enter a YouTube link or quit.
2. If you enter a link, the program opens Chrome and loads the video.
3. It sets a watch inside the page (DOM monitor) to check for ads.
4. During the video, it keeps looking for ad signs (skip button, ad text).
5. If it finds an ad, it tries to click skip using many ways.
6. It checks the video time and speed so it keeps going until the video ends.
7. When the video is done, it waits a few seconds and then stops and shows results.

## 🚀 Features

- Automatic ad detection with 4 independent methods
- Multi-method skipping with 6 strategies and retries
- DOM MutationObserver injection for instant detection
- Adaptive duration monitoring
- Configurable and extensible architecture
- Supports varying playback speed (0.25x to over 2x)

## ✅ Requirements

- Python 3.7 or higher
- Chrome/Chromium browser installed
- Internet connection (for webdriver-manager driver download)

## ✅ Quick Start

### 1. Setup

- Clone or download the project and go to the folder:
  `cd Youtube-Adskip`
- Install requirements:
  `pip install -r requirements.txt`
- Optionally use a virtual environment (recommended):
  `python -m venv .venv` then activate and install dependencies.

### 2. Run with URL Input

Run the helper script:
`python run_specific_url.py`

Then type the full YouTube video URL when prompted.

### 3. One-step command (shortcut)

You can run URL directly (replace with desired video link):
`python run_specific_url.py --url "https://www.youtube.com/watch?v=Rq5gJVxz55Q"`

### 4. Expected behavior

- The script opens Chrome and loads the video.
- It logs ad detection and skip attempts.
- It keeps watching until the video ends and prints a summary.

---

## 🎯 Programmatic Usage

```python
from youtube_ad_skipper import YouTubeAdSkipper

skipper = YouTubeAdSkipper(log_file='youtube_ad_skipper.log', headless=False, debug=True)
skipper.run(video_url='https://www.youtube.com/watch?v=Rq5gJVxz55Q')
```

## 🗂️ Key File Description

- `youtube_ad_skipper.py`: main restructured engine (entrypoint + classes)
- `run_specific_url.py`: script for URL input and reliability tests
- `OPTIMIZATION_TEST.py`: suite verifying components and config
- `OPTIMIZATION_REPORT.md`: report of changes + metrics

## 🛠️ Troubleshooting

### 1) `AttributeError: 'YouTubeAdSkipper' object has no attribute 'inject_dom_monitor'`
- Legacy path from previous versions. Now `load_video()` calls `detector.inject_monitor()`.
- Use `run_specific_url.py` or `YouTubeAdSkipper.run(video_url=...)`.

### 2) ChromeDriver / Browser not found
- Install Chrome/Chromium, then rerun.
- Fix:
```bash
pip install webdriver-manager
```

### 3) No ads or unreliable skipping
- Activate `debug=True` for verbose logging.
- Adjust selector rules in `Config` as needed, then re-run.

## 📌 Output Example

```
[MONITOR] Starting ad monitoring for entire video...
[VIDEO] Duration: 300s, Current: 134.8s, Speed: 1.0x
[AD] Advertisement detected! (Total: 6)
[OK] Ad skipped! (Found: XPath-2, Clicked: DirectClick)
[VIDEO] Video playback ended
SESSION SUMMARY
Ads Detected: 8
Ads Skipped: 8
Skip Attempts: 10
Success Rate: 100.0%
```

## 📝 Final Notes

This codebase has been tested with URL `https://www.youtube.com/watch?v=Rq5gJVxz55Q` and confirmed to detect and skip ads while keeping the video playback flowing. Continue using `run_specific_url.py` or the direct API for stable behavior across playback rates and video duration.