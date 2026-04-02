#!/usr/bin/env python3
"""
Run YouTube Ad Skipper on a specific URL with error handling and logging
"""

import sys
import logging
from youtube_ad_skipper import YouTubeAdSkipper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_on_url(url):
    """Run ad skipper on specific URL"""
    try:
        logger.info(f"Starting YouTube Ad Skipper on URL: {url}")
        
        # Initialize the ad skipper
        skipper = YouTubeAdSkipper()
        logger.info("Ad Skipper initialized successfully")
        
        # Setup Chrome driver
        skipper.setup_driver()
        logger.info("WebDriver initialized")
        
        # Load video with DOM monitor injection
        skipper.load_video(url)
        logger.info("Video loaded with monitoring active")
        
        # Start monitoring and skipping ads
        logger.info("Starting ad monitoring...")
        skipper.monitor_and_skip()
        
        # Print session summary
        skipper.print_summary()
        logger.info("Ad skipping session completed")
        
    except Exception as e:
        logger.error(f"Error during execution: {type(e).__name__}: {str(e)}", exc_info=True)
        return False
    finally:
        try:
            if hasattr(skipper, 'driver') and skipper.driver:
                skipper.driver.quit()
                logger.info("WebDriver closed")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")
    
    return True

def validate_youtube_url(url):
    """Validate if the URL is a valid YouTube video URL"""
    if not url.strip():
        logger.error("URL cannot be empty")
        return False
    
    if "youtube.com" not in url and "youtu.be" not in url:
        logger.error("Invalid URL. Please provide a valid YouTube URL")
        return False
    
    return True

if __name__ == "__main__":
    print("\n" + "="*60)
    print("YouTube Ad Skipper - URL Demo")
    print("="*60)
    
    # Get URL from user
    url = input("\nEnter YouTube URL: ").strip()
    
    if not validate_youtube_url(url):
        logger.error("Invalid YouTube URL provided")
        sys.exit(1)
    
    # Ensure URL has protocol
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    logger.info(f"Using URL: {url}")
    success = run_on_url(url)
    sys.exit(0 if success else 1)
