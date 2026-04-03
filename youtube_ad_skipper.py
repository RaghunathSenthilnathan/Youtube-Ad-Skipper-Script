#!/usr/bin/env python3
"""
YouTube Ad Skipper - Optimized & Restructured Edition
Automatically detects and skips ads on YouTube using Selenium WebDriver.

Architecture:
  - Config: Centralized configuration and patterns
  - AdDetector: Multi-method ad detection
  - SkipButton: Skip button finding and clicking
  - VideoPlayer: Video progress tracking and analysis
  - YouTubeAdSkipper: Main orchestration
"""

import sys
import logging
import time
import threading
import os
from io import TextIOWrapper
from typing import Optional, Tuple, List, Any
from dataclasses import dataclass
from enum import Enum

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================================
# CONFIGURATION & ENUMS
# ============================================================================

class DetectionMethod(Enum):
    """Ad detection method identifiers."""
    SKIP_BUTTON = "skip_button"
    AD_INDICATOR = "ad_indicator"
    JAVASCRIPT = "javascript"
    DOM_MONITOR = "dom_monitor"


class ClickTechnique(Enum):
    """Skip button click techniques."""
    DIRECT = "DirectClick"
    JAVASCRIPT = "JS-click"
    ACTION_CHAINS = "ActionChains"
    FOCUS_ENTER = "Focus-Enter"
    FOCUS_SPACE = "Focus-Space"
    REMOVE_OVERLAY = "RemoveOverlay"


@dataclass
class Config:
    """Centralized configuration."""
    # Skip button detection patterns
    skip_button_xpaths = [
        "//button[@aria-label='Skip ad']",
        "//button[@aria-label='Skip']",
        "//span[text()='Skip']//ancestor::button",
        "//button[contains(@aria-label, 'Skip')]",
        "//button[contains(., 'Skip')]",
        "//div[@role='button'][contains(@aria-label, 'Skip')]",
        "//button[descendant-or-self::*[contains(text(), 'Skip')]]",
        "//button[contains(@class, 'skip')]",
    ]
    
    skip_button_css = [
        "button[aria-label*='Skip']",
        "button.ytp-ad-skip-button",
        "button.skip-button",
        "[data-test-id='skip-button']",
        "button[aria-label='Skip navigation']",
        "button.ytp-skip-ad-button",
    ]
    
    # Ad detection patterns
    ad_detection_xpaths = [
        "//span[contains(text(), 'Ad')]",
        "//div[contains(@class, 'ad')]",
        "//*[@aria-label*='Ad']",
        "//div[contains(@class, 'ytp-ad')]",
        "//div[contains(@data-test-id, 'ad')]",
        "//span[contains(text(), 'Advertisement')]",
        "//div[@role='alertdialog']",
    ]
    
    # Timeouts and retry settings
    page_load_timeout = 3
    ad_detection_timeout = 0.2
    click_wait_timeout = 1
    skip_retry_count = 5
    skip_retry_delay = 0.1
    default_monitor_duration = 120
    
    # Video monitoring
    duration_lock_threshold = 5
    consecutive_zero_attempts_limit = 30
    post_roll_buffer_seconds = 5
    monitoring_loop_buffer_seconds = 10
    periodic_log_interval_seconds = 5


def setup_logging(log_file: str, debug: bool = False) -> logging.Logger:
    """Setup logging with UTF-8 encoding."""
    if sys.platform == "win32":
        sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    level = logging.DEBUG if debug else logging.INFO
    logger = logging.getLogger("YouTubeAdSkipper")
    
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


# ============================================================================
# SPECIALIZED CLASSES
# ============================================================================

class AdDetector:
    """Handles ad detection using multiple methods."""
    
    def __init__(self, driver, logger, config: Config):
        self.driver = driver
        self.logger = logger
        self.config = config
        self.dom_monitor_active = False
    
    def inject_monitor(self) -> None:
        """Inject JavaScript DOM monitor."""
        script = """
        window.adSkipperMonitor = {
            skipButtonDetected: false,
            adIndicatorDetected: false,
            
            checkForAdElements: function() {
                let skipBtn = document.querySelector('button[aria-label*="Skip"]') || 
                              document.querySelector('button.ytp-ad-skip-button') ||
                              document.querySelector('button[aria-label*="Skip ad"]');
                this.skipButtonDetected = !!skipBtn;
                
                let adSpans = document.querySelectorAll('span');
                for (let span of adSpans) {
                    let text = span.textContent || '';
                    if (text.includes('Ad') || text.includes('Advertisement')) {
                        this.adIndicatorDetected = true;
                        break;
                    }
                }
            }
        };
        
        const observer = new MutationObserver(() => {
            window.adSkipperMonitor.checkForAdElements();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['aria-label', 'class']
        });
        
        window.adSkipperMonitor.checkForAdElements();
        """
        try:
            self.driver.execute_script(script)
            self.dom_monitor_active = True
            self.logger.info("[OK] DOM monitor injected")
        except Exception as e:
            self.logger.debug(f"[DEBUG] DOM monitor injection failed: {e}")
    
    def detect_via_skip_button(self) -> bool:
        """Check if skip button is visible."""
        try:
            skip_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Skip')]")
            return skip_btn.is_displayed()
        except:
            return False
    
    def detect_via_ad_indicators(self) -> bool:
        """Check for ad indicator elements."""
        for xpath in self.config.ad_detection_xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements and any(e.is_displayed() for e in elements):
                    return True
            except:
                continue
        return False
    
    def detect_via_javascript(self) -> bool:
        """Detect ads using JavaScript."""
        try:
            return self.driver.execute_script("""
                if (document.querySelector('button[aria-label*="Skip"]')) return true;
                if (document.body.innerText.includes('Advertisement') || 
                    document.body.innerText.includes('Ad in')) return true;
                return !!document.querySelector('[data-test-id="ad"]');
            """)
        except:
            return False
    
    def detect_via_dom_monitor(self) -> bool:
        """Check DOM monitor for ad signals."""
        if not self.dom_monitor_active:
            return False
        try:
            monitor = self.driver.execute_script("return window.adSkipperMonitor || null;")
            return monitor and (monitor.get("skipButtonDetected") or monitor.get("adIndicatorDetected"))
        except:
            return False
    
    def detect_skip_buttons_advanced(self) -> Optional[Any]:
        """Enhanced skip button detection with multiple patterns."""
        patterns = [
            "//button[contains(@class, 'skip')]",
            "//button[contains(text(), 'Skip')]", 
            "//div[contains(@class, 'ad-interrupting')]/button",
            "//button[@aria-label='Skip ad']",
            "//yt-button-renderer//button[contains(text(), 'Skip')]"
        ]
        
        for pattern in patterns:
            try:
                buttons = self.driver.find_elements(By.XPATH, pattern)
                if buttons:
                    # Return first visible and clickable button
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            return button
            except:
                continue
        return None
    
    def is_ad_present(self) -> bool:
        """Comprehensive ad detection using all methods."""
        return (
            self.detect_via_skip_button() or
            self.detect_via_ad_indicators() or
            self.detect_via_javascript() or
            self.detect_via_dom_monitor()
        )


class SkipButton:
    """Handles skip button finding and clicking."""
    
    def __init__(self, driver, logger, config: Config):
        self.driver = driver
        self.logger = logger
        self.config = config
    
    def _is_visible_and_clickable(self, element) -> bool:
        """Check if element is visible and clickable."""
        try:
            return element.is_displayed() and element.is_enabled()
        except (StaleElementReferenceException, Exception):
            return False
    
    def _find_via_xpaths(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using XPath patterns."""
        for i, xpath in enumerate(self.config.skip_button_xpaths):
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if self._is_visible_and_clickable(elem):
                        return elem, f"XPath-{i+1}"
            except:
                continue
        return None, None
    
    def _find_via_css(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using CSS selectors."""
        for i, css in enumerate(self.config.skip_button_css):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, css)
                for elem in elements:
                    if self._is_visible_and_clickable(elem):
                        return elem, f"CSS-{i+1}"
            except:
                continue
        return None, None
    
    def _find_via_webdriver_wait(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using WebDriverWait."""
        try:
            wait = WebDriverWait(self.driver, self.config.click_wait_timeout)
            elem = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label, 'Skip')]")
            ))
            return elem, "WebDriverWait"
        except:
            return None, None
    
    def _find_via_javascript(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using JavaScript."""
        try:
            elem = self.driver.execute_script("""
                let skipBtn = document.querySelector('button[aria-label*="Skip"]');
                if (skipBtn && skipBtn.offsetParent) return skipBtn;
                
                let buttons = Array.from(document.querySelectorAll('button'));
                return buttons.find(b => 
                    b.textContent.includes('Skip') && b.offsetParent !== null
                ) || null;
            """)
            return (elem, "JavaScript") if elem else (None, None)
        except:
            return None, None
    
    def _find_via_advanced_patterns(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using advanced multi-pattern detection."""
        patterns = [
            "//button[contains(@class, 'skip')]",
            "//button[contains(text(), 'Skip')]", 
            "//div[contains(@class, 'ad-interrupting')]/button",
            "//button[@aria-label='Skip ad']",
            "//yt-button-renderer//button[contains(text(), 'Skip')]"
        ]
        
        for i, pattern in enumerate(patterns):
            try:
                buttons = self.driver.find_elements(By.XPATH, pattern)
                for button in buttons:
                    if self._is_visible_and_clickable(button):
                        return button, f"Advanced-{i+1}"
            except:
                continue
        return None, None
    
    def find(self) -> Tuple[Optional[Any], Optional[str]]:
        """Find skip button using multiple methods in order."""
        methods = [
            self._find_via_xpaths,
            self._find_via_css,
            self._find_via_webdriver_wait,
            self._find_via_javascript,
            self._find_via_advanced_patterns,
        ]
        
        for method in methods:
            elem, method_name = method()
            if elem:
                return elem, method_name
        
        return None, None
    
    def click(self, element) -> Tuple[bool, Optional[str]]:
        """Click skip button using multiple techniques."""
        techniques = [
            (self._direct_click, "DirectClick"),
            (self._javascript_click, "JS-click"),
            (self._action_chains_click, "ActionChains"),
            (self._focus_enter_click, "Focus-Enter"),
            (self._focus_space_click, "Focus-Space"),
            (self._remove_overlay_click, "RemoveOverlay"),
        ]
        
        for click_func, technique_name in techniques:
            try:
                if click_func(element):
                    return True, technique_name
            except:
                continue
        
        return False, None
    
    def _direct_click(self, element) -> bool:
        """Technique 1: Direct click."""
        element.click()
        return True
    
    def _javascript_click(self, element) -> bool:
        """Technique 2: JavaScript click."""
        self.driver.execute_script("arguments[0].click();", element)
        return True
    
    def _action_chains_click(self, element) -> bool:
        """Technique 3: ActionChains click."""
        ActionChains(self.driver).move_to_element(element).click().perform()
        return True
    
    def _focus_enter_click(self, element) -> bool:
        """Technique 4: Focus and Enter."""
        self.driver.execute_script("arguments[0].focus();", element)
        element.send_keys(Keys.RETURN)
        return True
    
    def _focus_space_click(self, element) -> bool:
        """Technique 5: Focus and Space."""
        self.driver.execute_script("arguments[0].focus();", element)
        element.send_keys(Keys.SPACE)
        return True
    
    def _remove_overlay_click(self, element) -> bool:
        """Technique 6: Remove overlays and click."""
        self.driver.execute_script("""
            document.querySelectorAll('[role="presentation"]').forEach(el => {
                el.style.display = 'none';
            });
        """)
        element.click()
        return True


class VideoPlayer:
    """Handles video progress tracking and analysis."""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    def get_playback_info(self) -> Tuple[float, float, float]:
        """Get video duration, current time, and playback rate.
        Returns: (duration, current_time, playback_rate)
        """
        try:
            result = self.driver.execute_script("""
                var video = document.querySelector('video');
                if (!video) return [0, 0, 1];
                return [
                    isNaN(video.duration) ? 0 : video.duration,
                    video.currentTime,
                    video.playbackRate || 1.0
                ];
            """)
            return tuple(float(x) for x in result)
        except Exception as e:
            self.logger.debug(f"[DEBUG] Error getting playback info: {e}")
            return 0, 0, 1.0
    
    def has_ended(self, duration: float, current_time: float) -> bool:
        """Check if video has ended."""
        try:
            is_ended = self.driver.execute_script(
                "return document.querySelector('video')?.ended || false;"
            )
            return is_ended and duration > 0 and current_time >= (duration - 1)
        except:
            return False


# ============================================================================
# MAIN AD SKIPPER CLASS
# ============================================================================

class YouTubeAdSkipper:
    """Main orchestrator for YouTube ad skipping."""
    
    def __init__(self, log_file: str = "youtube_ad_skipper.log", headless: bool = False, debug: bool = False):
        self.logger = setup_logging(log_file, debug=debug)
        self.config = Config()
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        self.debug = debug
        
        # Statistics
        self.ads_detected = 0
        self.ads_skipped = 0
        self.skip_attempts = 0
        
        # Lazy-initialized components
        self._detector: Optional[AdDetector] = None
        self._skipper: Optional[SkipButton] = None
        self._player: Optional[VideoPlayer] = None
        
        # Kill functionality
        self.stop_monitoring = False
        
        self.logger.info("[INIT] YouTube Ad Skipper initialized")
    
    @property
    def detector(self) -> AdDetector:
        """Lazy-load detector component."""
        if self._detector is None:
            self._detector = AdDetector(self.driver, self.logger, self.config)
        return self._detector
    
    @property
    def skipper(self) -> SkipButton:
        """Lazy-load skipper component."""
        if self._skipper is None:
            self._skipper = SkipButton(self.driver, self.logger, self.config)
        return self._skipper
    
    @property
    def player(self) -> VideoPlayer:
        """Lazy-load player component."""
        if self._player is None:
            self._player = VideoPlayer(self.driver, self.logger)
        return self._player
    
    def setup_driver(self) -> None:
        """Setup Chrome WebDriver with optimized options."""
        self.logger.info("[SETUP] Configuring Chrome WebDriver...")
        try:
            chrome_options = ChromeOptions()
            
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            # Performance and security
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            
            # User agent
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            # Anti-automation
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.logger.info("[OK] WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"[ERROR] WebDriver initialization failed: {e}")
            raise
    
    def load_video(self, url: str) -> None:
        """Load YouTube video and inject monitoring."""
        self.logger.info(f"[NAVIGATE] Opening: {url}")
        try:
            self.driver.get(url)
            time.sleep(self.config.page_load_timeout)
            self.detector.inject_monitor()
            self.logger.info("[OK] Video page loaded")
        except Exception as e:
            self.logger.error(f"[ERROR] Navigation failed: {e}")
            raise
    
    def skip_current_ad(self) -> bool:
        """Attempt to skip current ad."""
        self.skip_attempts += 1
        
        element, find_method = self.skipper.find()
        if not element:
            self.logger.debug("[DEBUG] Skip button not found")
            return False
        
        success, click_method = self.skipper.click(element)
        if success:
            self.ads_skipped += 1
            self.logger.info(f"[OK] Ad skipped! (Found: {find_method}, Clicked: {click_method})")
            return True
        
        return False
    
    def monitor_and_skip(self) -> None:
        """Main monitoring loop - runs until video ends."""
        self.logger.info("[MONITOR] Starting ad monitoring for entire video...")
        
        start_time = time.time()
        last_log_time = 0
        last_duration = 0
        zero_duration_count = 0
        duration_confirms = 0
        playback_started = False
        monitoring_duration = self.config.default_monitor_duration
        
        try:
            while time.time() - start_time < (monitoring_duration + self.config.monitoring_loop_buffer_seconds) and not self.stop_monitoring:
                try:
                    # Get video state
                    duration, current_time, playback_rate = self.player.get_playback_info()
                    
                    # Detect and skip ads
                    if self.detector.is_ad_present():
                        self.ads_detected += 1
                        current_time_log = time.time()
                        
                        if current_time_log - last_log_time >= 2:
                            self.logger.info(f"[AD] Advertisement detected! (Total: {self.ads_detected})")
                            last_log_time = current_time_log
                        
                        # Retry skip
                        for _ in range(self.config.skip_retry_count):
                            if self.skip_current_ad():
                                break
                            time.sleep(self.config.skip_retry_delay)
                    
                    # Track video duration
                    if duration > 0:
                        playback_started = True
                        if duration == last_duration:
                            duration_confirms += 1
                        else:
                            duration_confirms = 1
                            last_duration = duration
                        
                        # Update monitoring duration after duration locks in
                        if duration_confirms >= self.config.duration_lock_threshold:
                            remaining = max(0, duration - current_time)
                            adjusted_remaining = remaining / max(playback_rate, 0.25)
                            monitoring_duration = int(time.time() - start_time) + int(adjusted_remaining) + self.config.post_roll_buffer_seconds
                            
                            # Periodic playback log
                            if int(current_time) % self.config.periodic_log_interval_seconds == 0 and current_time > 0:
                                self.logger.debug(
                                    f"[VIDEO] Duration: {duration:.0f}s, "
                                    f"Current: {current_time:.1f}s, "
                                    f"Speed: {playback_rate}x"
                                )
                        
                        zero_duration_count = 0
                    else:
                        zero_duration_count += 1
                        if zero_duration_count > self.config.consecutive_zero_attempts_limit and playback_started:
                            self.logger.warning("[WARNING] Video duration unavailable")
                            break
                    
                    # Check video end
                    if self.player.has_ended(duration, current_time):
                        self.logger.info("[VIDEO] Video playback ended")
                        time.sleep(self.config.post_roll_buffer_seconds)
                        break
                    
                    time.sleep(self.config.ad_detection_timeout)
                
                except Exception as e:
                    self.logger.debug(f"[DEBUG] Monitoring error: {e}")
                    time.sleep(0.5)
        
        except KeyboardInterrupt:
            self.logger.info("[STOP] Monitoring stopped by user")
        finally:
            self.logger.info("[STOP] Ad monitoring stopped")
    
    def handle_multiple_urls(self, urls: List[str]) -> Optional[str]:
        """Handle multiple URLs by opening in tabs and letting user choose."""
        if not self.driver:
            self.setup_driver()
        
        # Open first URL in current tab
        self.driver.get(urls[0])
        time.sleep(self.config.page_load_timeout)
        
        # Open others in new tabs
        for url in urls[1:]:
            self.driver.execute_script(f"window.open('{url}', '_blank');")
            time.sleep(1)
        
        # Get window handles
        handles = self.driver.window_handles
        print(f"\nOpened {len(handles)} tabs:")
        for i, handle in enumerate(handles):
            self.driver.switch_to.window(handle)
            title = self.driver.title or f"Tab {i+1}"
            print(f"{i+1}. {title}")
        
        print("\nWARNING: Please watch only ONE video at a time. Playing multiple may interfere with ad skipping.")
        
        while True:
            try:
                choice = int(input(f"\nChoose which tab to monitor (1-{len(handles)}): ").strip())
                if 1 <= choice <= len(handles):
                    selected_handle = handles[choice - 1]
                    self.driver.switch_to.window(selected_handle)
                    current_url = self.driver.current_url
                    self.logger.info(f"[SELECTED] Monitoring tab: {current_url}")
                    self.detector.inject_monitor()
                    return current_url
                else:
                    print("Invalid choice.")
            except ValueError:
                print("Please enter a number.")
        
        return None
        """Print session statistics."""
        self.logger.info("=" * 50)
        self.logger.info("SESSION SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Ads Detected: {self.ads_detected}")
        self.logger.info(f"Ads Skipped: {self.ads_skipped}")
        self.logger.info(f"Skip Attempts: {self.skip_attempts}")
        
        if self.ads_detected > 0:
            success_rate = (self.ads_skipped / self.ads_detected) * 100
            self.logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if self.ads_skipped > 0:
            self.logger.info("[SUCCESS] Ad skipping is working!")
        else:
            self.logger.warning("[WARNING] No ads were skipped")
        
        self.logger.info("=" * 50)
    
    def run(self, video_url: str = None) -> None:
        """Main execution flow."""
        try:
            while True:  # Loop to allow restarting with new URL
                if not video_url:
                    print("\n" + "=" * 60)
                    print("YOUTUBE AD SKIPPER")
                    print("=" * 60)
                    print("\nOptions:")
                    print("1. Enter single YouTube URL")
                    print("2. Enter multiple YouTube URLs (up to 3)")
                    print("3. Exit")
                    print("-" * 60)

                    choice = input("\nSelect option (1-3): ").strip()

                    if choice == "1":
                        video_url = input("Enter YouTube URL: ").strip()
                        if not video_url:
                            self.logger.info("[EXIT] No URL provided")
                            continue
                    elif choice == "2":
                        urls = []
                        for i in range(3):
                            url = input(f"Enter YouTube URL {i+1} (or press Enter to skip): ").strip()
                            if url:
                                urls.append(url)
                            else:
                                break
                        if not urls:
                            self.logger.info("[EXIT] No URLs provided")
                            continue
                        video_url = self.handle_multiple_urls(urls)
                        if not video_url:
                            continue
                    elif choice == "3":
                        self.logger.info("[EXIT] Exiting...")
                        return
                    else:
                        print("Invalid choice. Try again.")
                        continue

                self.setup_driver()
                self.load_video(video_url)
                # Reset stop flag
                self.stop_monitoring = False
                # Run monitoring in thread
                monitor_thread = threading.Thread(target=self.monitor_and_skip)
                monitor_thread.start()
                # Wait for thread or user input
                print("Monitoring started. Type 'kill' to stop and choose new URL, or wait for video to end.")
                while monitor_thread.is_alive():
                    try:
                        import select
                        if sys.platform == "win32":
                            # On Windows, use msvcrt for non-blocking input
                            import msvcrt
                            if msvcrt.kbhit():
                                cmd = input().strip().lower()
                                if cmd == 'kill':
                                    self.stop_monitoring = True
                                    monitor_thread.join(timeout=5)
                                    print("Monitoring stopped. You can now choose a new URL.")
                                    break
                        else:
                            # Unix-like
                            import select
                            if select.select([sys.stdin], [], [], 1)[0]:
                                cmd = input().strip().lower()
                                if cmd == 'kill':
                                    self.stop_monitoring = True
                                    monitor_thread.join(timeout=5)
                                    print("Monitoring stopped. You can now choose a new URL.")
                                    break
                    except:
                        pass
                    time.sleep(1)
                self.print_summary()
                video_url = None  # Reset for next iteration
        
        except KeyboardInterrupt:
            self.logger.info("[STOP] Interrupted by user")
            self.stop_monitoring = True
        except Exception as e:
            self.logger.error(f"[ERROR] Fatal error: {e}")
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    self.logger.info("[OK] Browser closed")
            except Exception as e:
                self.logger.debug(f"[DEBUG] Error closing browser: {e}")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point."""
    # Save PID for kill script
    with open("youtube_ad_skipper.pid", "w") as f:
        f.write(str(os.getpid()))
    
    skipper = YouTubeAdSkipper(
        log_file="youtube_ad_skipper.log",
        headless=False,
        debug=True
    )
    try:
        skipper.run()
    finally:
        # Clean up PID file
        if os.path.exists("youtube_ad_skipper.pid"):
            os.remove("youtube_ad_skipper.pid")


if __name__ == "__main__":
    main()
