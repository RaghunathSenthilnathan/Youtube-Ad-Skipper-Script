#!/usr/bin/env python3
"""
YouTube Ad Skipper - Optimized Edition
Automatically detects and skips ads on YouTube using Selenium WebDriver.
Features: Multiple detection methods, aggressive skip techniques, real-time monitoring, detailed logging.
"""

import sys
import logging
import time
from io import TextIOWrapper
from typing import Optional, Tuple, List, Any

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
# CONSTANTS AND CONFIGURATION
# ============================================================================

# XPath patterns for skip button detection
SKIP_BUTTON_XPATHS = [
    "//button[@aria-label='Skip ad']",
    "//button[@aria-label='Skip']",
    "//span[text()='Skip']//ancestor::button",
    "//button[contains(@aria-label, 'Skip')]",
    "//button[contains(., 'Skip')]",
    "//div[@role='button'][contains(@aria-label, 'Skip')]",
    "//button[descendant-or-self::*[contains(text(), 'Skip')]]",
    "//button[contains(@class, 'skip')]",
]

# CSS selectors for skip button detection
SKIP_BUTTON_CSS = [
    "button[aria-label*='Skip']",
    "button.ytp-ad-skip-button",
    "button.skip-button",
    "[data-test-id='skip-button']",
    "button[aria-label='Skip navigation']",
    "button.ytp-skip-ad-button",
]

# XPath patterns for ad detection
AD_DETECTION_XPATHS = [
    "//span[contains(text(), 'Ad')]",
    "//div[contains(@class, 'ad')]",
    "//*[@aria-label*='Ad']",
    "//div[contains(@class, 'ytp-ad')]",
    "//div[contains(@data-test-id, 'ad')]",
    "//span[contains(text(), 'Advertisement')]",
    "//div[@role='alertdialog']",
]

# Timeouts (seconds)
PAGE_LOAD_TIMEOUT = 3
AD_DETECTION_TIMEOUT = 0.2
CLICK_WAIT_TIMEOUT = 1
SKIP_RETRY_COUNT = 5
SKIP_RETRY_DELAY = 0.1
DEFAULT_MONITOR_DURATION = 120


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(log_file: str, debug: bool = False) -> logging.Logger:
    """Setup logging with UTF-8 encoding."""
    if sys.platform == "win32":
        sys.stdout = TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    level = logging.DEBUG if debug else logging.INFO

    logger = logging.getLogger("YouTubeAdSkipper")
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

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
# MAIN CLASS
# ============================================================================

class YouTubeAdSkipper:
    """Optimized YouTube Ad Skipper with multiple detection and skip techniques."""

    def __init__(self, log_file: str = "youtube_ad_skipper.log", headless: bool = False, debug: bool = False):
        """
        Initialize YouTube Ad Skipper.

        Args:
            log_file: Path to log file
            headless: Run browser in headless mode
            debug: Enable debug logging
        """
        self.logger = setup_logging(log_file, debug=debug)
        self.headless = headless
        self.debug = debug
        self.driver: Optional[webdriver.Chrome] = None

        # Statistics
        self.ads_detected = 0
        self.ads_skipped = 0
        self.skip_attempts = 0
        self.mutation_observer_active = False

        self.logger.info("[INIT] YouTube Ad Skipper initialized")

    def setup_driver(self) -> None:
        """Setup Chrome WebDriver with optimized options."""
        self.logger.info("[SETUP] Configuring Chrome WebDriver...")
        try:
            chrome_options = ChromeOptions()

            if self.headless:
                chrome_options.add_argument("--headless=new")

            # Performance and security options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")

            # User agent spoofing
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            # Disable automation detection
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("useAutomationExtension", False)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            self.logger.info("[OK] WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to initialize WebDriver: {e}")
            raise

    def inject_dom_monitor(self) -> None:
        """Inject JavaScript to monitor DOM changes for ads."""
        monitor_script = """
        window.adSkipperMonitor = {
            adEvents: [],
            skipButtonDetected: false,
            adIndicatorDetected: false,
            
            checkForAdElements: function() {
                // Check for skip buttons
                let skipBtn = document.querySelector('button[aria-label*="Skip"]') || 
                              document.querySelector('button.ytp-ad-skip-button') ||
                              document.querySelector('button[aria-label*="Skip ad"]');
                
                if (skipBtn) {
                    this.skipButtonDetected = true;
                    this.adEvents.push({type: 'skip_button', time: Date.now()});
                }
                
                // Check for ad indicators
                let adSpans = document.querySelectorAll('span');
                for (let span of adSpans) {
                    let text = span.textContent || '';
                    if (text.includes('Ad') || text.includes('Advertisement')) {
                        this.adIndicatorDetected = true;
                        this.adEvents.push({type: 'ad_indicator', time: Date.now()});
                        break;
                    }
                }
            }
        };
        
        // Monitor DOM changes
        const observer = new MutationObserver(() => {
            window.adSkipperMonitor.checkForAdElements();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['aria-label', 'class']
        });
        
        // Initial check
        window.adSkipperMonitor.checkForAdElements();
        console.log('[MONITOR] Ad detection monitor activated');
        """
        try:
            self.driver.execute_script(monitor_script)
            self.mutation_observer_active = True
            self.logger.info("[OK] DOM monitor injected")
        except Exception as e:
            self.logger.debug(f"[DEBUG] DOM monitor injection failed: {e}")

    def find_skip_button(self) -> Tuple[Optional[Any], List[str]]:
        """Find skip button using multiple methods. Returns (element, methods_used)."""
        methods_used = []

        # Method 1: XPath patterns
        for i, xpath in enumerate(SKIP_BUTTON_XPATHS):
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    if self._is_visible_and_clickable(elem):
                        methods_used.append(f"XPath-{i+1}")
                        return elem, methods_used
            except Exception:
                continue

        # Method 2: CSS selectors
        for i, css in enumerate(SKIP_BUTTON_CSS):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, css)
                for elem in elements:
                    if self._is_visible_and_clickable(elem):
                        methods_used.append(f"CSS-{i+1}")
                        return elem, methods_used
            except Exception:
                continue

        # Method 3: WebDriverWait with explicit wait
        try:
            wait = WebDriverWait(self.driver, CLICK_WAIT_TIMEOUT)
            elem = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(@aria-label, 'Skip')]")
            ))
            methods_used.append("WebDriverWait")
            return elem, methods_used
        except TimeoutException:
            pass

        # Method 4: JavaScript DOM search
        try:
            elem = self.driver.execute_script("""
                let skipBtn = document.querySelector('button[aria-label*="Skip"]');
                if (skipBtn && skipBtn.offsetParent) return skipBtn;
                
                let buttons = Array.from(document.querySelectorAll('button'));
                return buttons.find(b => 
                    b.textContent.includes('Skip') && 
                    b.offsetParent !== null
                ) || null;
            """)
            if elem:
                methods_used.append("JavaScript")
                return elem, methods_used
        except Exception:
            pass

        return None, methods_used

    def click_skip_button(self, element) -> Tuple[bool, List[str]]:
        """Click skip button using multiple aggressive techniques."""
        techniques = []

        # Technique 1: Direct click
        try:
            element.click()
            techniques.append("DirectClick")
            return True, techniques
        except ElementClickInterceptedException:
            techniques.append("DirectClick-blocked")
        except Exception as e:
            techniques.append(f"DirectClick-failed")

        # Technique 2: JavaScript click
        try:
            self.driver.execute_script("arguments[0].click();", element)
            techniques.append("JS-click")
            return True, techniques
        except Exception:
            techniques.append("JS-click-failed")

        # Technique 3: ActionChains
        try:
            ActionChains(self.driver).move_to_element(element).click().perform()
            techniques.append("ActionChains")
            return True, techniques
        except Exception:
            techniques.append("ActionChains-failed")

        # Technique 4: Focus and Enter
        try:
            self.driver.execute_script("arguments[0].focus();", element)
            element.send_keys(Keys.RETURN)
            techniques.append("Focus-Enter")
            return True, techniques
        except Exception:
            techniques.append("Focus-Enter-failed")

        # Technique 5: Focus and Space
        try:
            self.driver.execute_script("arguments[0].focus();", element)
            element.send_keys(Keys.SPACE)
            techniques.append("Focus-Space")
            return True, techniques
        except Exception:
            techniques.append("Focus-Space-failed")

        # Technique 6: Remove overlays and click
        try:
            self.driver.execute_script("""
                document.querySelectorAll('[role="presentation"]').forEach(el => {
                    el.style.display = 'none';
                });
            """)
            element.click()
            techniques.append("RemoveOverlay")
            return True, techniques
        except Exception:
            techniques.append("RemoveOverlay-failed")

        return False, techniques

    def detect_ads(self) -> bool:
        """Detect if ad is currently playing using multiple methods."""
        # Method 1: Check for skip button
        try:
            skip_btn = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Skip')]")
            if skip_btn.is_displayed():
                return True
        except NoSuchElementException:
            pass

        # Method 2: Check for ad indicators
        for xpath in AD_DETECTION_XPATHS:
            try:
                elements = self.driver.find_elements(By.XPATH, xpath)
                if elements and any(e.is_displayed() for e in elements):
                    return True
            except Exception:
                continue

        # Method 3: JavaScript-based detection
        try:
            is_ad = self.driver.execute_script("""
                // Check skip button
                if (document.querySelector('button[aria-label*="Skip"]')) return true;
                
                // Check for ad text
                let allText = document.body.innerText;
                if (allText.includes('Advertisement') || allText.includes('Ad in')) return true;
                
                // Check for ad containers
                if (document.querySelector('[data-test-id="ad"]')) return true;
                
                return false;
            """)
            if is_ad:
                return True
        except Exception:
            pass

        # Method 4: Check DOM monitor events
        if self.mutation_observer_active:
            try:
                monitor = self.driver.execute_script(
                    "return window.adSkipperMonitor || null;"
                )
                if monitor and (monitor.get("skipButtonDetected") or monitor.get("adIndicatorDetected")):
                    return True
            except Exception:
                pass

        return False

    def skip_ad(self) -> bool:
        """Attempt to skip a single ad."""
        self.skip_attempts += 1

        elem, search_methods = self.find_skip_button()
        if not elem:
            self.logger.debug(f"[DEBUG] Skip button not found. Methods tried: {search_methods}")
            return False

        success, click_methods = self.click_skip_button(elem)
        if success:
            self.ads_skipped += 1
            self.logger.info(
                f"[OK] Ad skipped! (Found via {search_methods[0]}, "
                f"clicked via {click_methods[0]})"
            )
            return True

        self.logger.debug(f"[DEBUG] Skip failed. Techniques: {', '.join(click_methods[:3])}")
        return False

    def _is_visible_and_clickable(self, element) -> bool:
        """Check if element is visible and clickable."""
        try:
            return element.is_displayed() and element.is_enabled()
        except StaleElementReferenceException:
            return False
        except Exception:
            return False

    def navigate_to_video(self, video_url: str) -> None:
        """Navigate to YouTube video."""
        self.logger.info(f"[NAVIGATE] Opening: {video_url}")
        try:
            self.driver.get(video_url)
            time.sleep(PAGE_LOAD_TIMEOUT)
            self.inject_dom_monitor()
            self.logger.info("[OK] Video page loaded")
        except Exception as e:
            self.logger.error(f"[ERROR] Navigation failed: {e}")
            raise

    def get_video_duration_and_playback_info(self) -> Tuple[float, float, float]:
        """Get video duration, current playback time, and playback rate.
        Returns: (duration_seconds, current_time_seconds, playback_rate)
        """
        try:
            script = """
            var video = document.querySelector('video');
            if (!video) {
                return [0, 0, 1];
            }
            var duration = isNaN(video.duration) ? 0 : video.duration;
            var currentTime = video.currentTime;
            var playbackRate = video.playbackRate || 1.0;
            return [duration, currentTime, playbackRate];
            """
            result = self.driver.execute_script(script)
            duration, current_time, playback_rate = result[0], result[1], result[2]
            return float(duration), float(current_time), float(playback_rate)
        except Exception as e:
            self.logger.debug(f"[DEBUG] Error getting video info: {e}")
            return 0, 0, 1.0

    def monitor_and_skip_ads(self, duration: int = DEFAULT_MONITOR_DURATION) -> None:
        """Monitor and skip ads for entire video duration, accounting for playback speed."""
        self.logger.info("[MONITOR] Starting ad monitoring for entire video...")
        
        start_time = time.time()
        last_log_time = 0
        last_video_duration = 0
        consecutive_zero_duration = 0
        monitoring_duration = duration  # Fallback if video duration unavailable
        duration_lock_threshold = 5  # Require 5 consecutive reads of same duration to confirm
        duration_confirms = 0
        playback_started = False
        
        try:
            while time.time() - start_time < (monitoring_duration + 10):  # +10s buffer for post-roll ads
                try:
                    # Get current video playback info
                    video_duration, current_time, playback_rate = self.get_video_duration_and_playback_info()
                    
                    # Detect ads and skip
                    if self.detect_ads():
                        self.ads_detected += 1
                        current_log_time = time.time()

                        # Log ad detection every 2 seconds to avoid spam
                        if current_log_time - last_log_time >= 2:
                            self.logger.info(
                                f"[AD] Advertisement detected! (Total: {self.ads_detected})"
                            )
                            last_log_time = current_log_time

                        # Aggressive retry
                        for _ in range(SKIP_RETRY_COUNT):
                            if self.skip_ad():
                                break
                            time.sleep(SKIP_RETRY_DELAY)
                    
                    # Track video duration
                    if video_duration > 0:
                        playback_started = True
                        if video_duration == last_video_duration:
                            duration_confirms += 1
                        else:
                            duration_confirms = 1
                            last_video_duration = video_duration
                        
                        # After confirming duration hasn't changed, calculate monitoring time
                        if duration_confirms >= duration_lock_threshold:
                            # Calculate required monitoring duration accounting for playback rate
                            # If video is 50% through at 2x speed, we need ~25s more (at real time)
                            remaining_video_time = max(0, video_duration - current_time)
                            adjusted_remaining_time = remaining_video_time / max(playback_rate, 0.25)  # Min 0.25x speed
                            monitoring_duration = int(time.time() - start_time) + int(adjusted_remaining_time) + 10
                            
                            # Log video info periodically
                            if int(current_time) % 5 == 0 and current_time > 0:
                                self.logger.debug(
                                    f"[VIDEO] Duration: {video_duration:.0f}s, "
                                    f"Current: {current_time:.1f}s, "
                                    f"Speed: {playback_rate}x, "
                                    f"Elap: {time.time() - start_time:.0f}s"
                                )
                        
                        consecutive_zero_duration = 0
                    else:
                        consecutive_zero_duration += 1
                        # If we can't get duration after 30+ attempts, use fallback
                        if consecutive_zero_duration > 30 and playback_started:
                            self.logger.warning("[WARNING] Video duration unavailable, using fallback monitor")
                            break
                    
                    # Check if video has ended
                    try:
                        is_ended = self.driver.execute_script("return document.querySelector('video')?.ended || false;")
                        if is_ended and video_duration > 0 and current_time >= (video_duration - 1):
                            self.logger.info("[VIDEO] Video playback ended")
                            time.sleep(5)  # Wait 5 more seconds for post-roll ads
                            break
                    except Exception:
                        pass
                    
                    time.sleep(0.2)

                except Exception as e:
                    self.logger.debug(f"[DEBUG] Monitoring error: {e}")
                    time.sleep(0.5)

        except KeyboardInterrupt:
            self.logger.info("[STOP] Monitoring stopped by user")
        finally:
            self.logger.info("[STOP] Ad monitoring stopped")

    def print_summary(self) -> None:
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
            # Show menu BEFORE initializing driver
            if not video_url:
                print("\n" + "=" * 60)
                print("YOUTUBE AD SKIPPER")
                print("=" * 60)
                print("\nOptions:")
                print("1. Skip ads on sample video")
                print("2. Enter custom YouTube URL")
                print("3. Exit")
                print("-" * 60)

                choice = input("\nSelect option (1-3): ").strip()

                if choice == "1":
                    video_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
                elif choice == "2":
                    video_url = input("Enter YouTube URL: ").strip()
                    if not video_url:
                        self.logger.info("[EXIT] No URL provided")
                        return
                else:
                    self.logger.info("[EXIT] Exiting...")
                    return

            # Initialize driver ONLY after user confirms they want to proceed
            self.setup_driver()
            self.navigate_to_video(video_url)
            self.monitor_and_skip_ads(DEFAULT_MONITOR_DURATION)
            self.print_summary()

        except KeyboardInterrupt:
            self.logger.info("[STOP] Interrupted by user")
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
    skipper = YouTubeAdSkipper(
        log_file="youtube_ad_skipper.log",
        headless=False,
        debug=True
    )
    skipper.run()


if __name__ == "__main__":
    main()
