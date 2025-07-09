#!/usr/bin/env python3
"""
TradingView Screenshot Automation - VERSIÓN MEJORADA
Capturas H4, H1, M15 de EURUSD con anti-detección y manejo robusto de errores
"""

import time
import schedule
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import os
import random
import logging
from pathlib import Path
from typing import Dict, Optional, List
import json

class TradingViewAutomation:
    def __init__(self, headless: bool = False, max_retries: int = 3):
        """Initialize with enhanced configuration options"""
        self.driver = None
        self.headless = headless
        self.max_retries = max_retries
        self.screenshots_dir = "trading_screenshots"
        self.config_file = Path("tradingview_config.json")
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self.config = self._load_config()
        
        # Setup directories
        self.create_directories()
        
        # Initialize driver
        self.setup_driver()
    
    def _setup_logging(self):
        """Setup logging for automation"""
        self.logger = logging.getLogger("TradingViewAutomation")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        log_file = Path("tradingview_automation.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _load_config(self) -> Dict:
        """Load configuration from file or create default"""
        default_config = {
            "timeframes": {
                'H4': '240',
                'H1': '60', 
                'M15': '15'
            },
            "pairs": ["EURUSD"],
            "delays": {
                "min_page_load": 4,
                "max_page_load": 8,
                "min_action": 1,
                "max_action": 3,
                "screenshot_delay": 2
            },
            "selectors": {
                "chart_container": "[data-name='legend-source-item']",
                "chart_loaded": ".chart-container",
                "price_scale": ".price-axis"
            },
            "anti_detection": {
                "user_agents": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                return loaded_config
            else:
                # Save default config
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
        except Exception as e:
            self.logger.error(f"Error loading config: {e}, using defaults")
            return default_config
    
    def setup_driver(self):
        """Setup Chrome driver with enhanced anti-detection"""
        try:
            chrome_options = Options()
            
            # ✅ IMPROVED: Enhanced anti-detection options
            if self.headless:
                chrome_options.add_argument("--headless=new")  # New headless mode
            
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            user_agent = random.choice(self.config["anti_detection"]["user_agents"])
            chrome_options.add_argument(f"--user-agent={user_agent}")
            
            # Additional stealth options
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-default-apps")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            
            # Performance optimizations
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-hang-monitor")
            chrome_options.add_argument("--disable-prompt-on-repost")
            
            # Auto-download ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # ✅ IMPROVED: Enhanced stealth scripts
            stealth_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})",
                "window.chrome = { runtime: {} }",
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})"
            ]
            
            for script in stealth_scripts:
                self.driver.execute_script(script)
            
            self.logger.info("Chrome driver configured with enhanced anti-detection")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def create_directories(self):
        """Create directories for screenshots with better organization"""
        base_dir = Path(self.screenshots_dir)
        base_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = base_dir / today
        self.today_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different timeframes
        for tf in self.config["timeframes"].keys():
            tf_dir = self.today_dir / tf
            tf_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Screenshot directories created: {self.today_dir}")
    
    def human_like_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Random delay to mimic human behavior with config support"""
        if min_seconds is None:
            min_seconds = self.config["delays"]["min_action"]
        if max_seconds is None:
            max_seconds = self.config["delays"]["max_action"]
            
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def random_mouse_movement(self):
        """Enhanced random mouse movements to avoid detection"""
        try:
            actions = ActionChains(self.driver)
            
            # Multiple random movements
            for _ in range(random.randint(1, 3)):
                x_offset = random.randint(-100, 300)
                y_offset = random.randint(-50, 200)
                actions.move_by_offset(x_offset, y_offset)
                
                # Random pause between movements
                time.sleep(random.uniform(0.1, 0.5))
            
            actions.perform()
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            self.logger.debug(f"Mouse movement failed: {e}")
    
    def check_page_health(self) -> bool:
        """Check if the page loaded correctly and is responsive"""
        try:
            # Check if basic elements exist
            self.driver.find_element(By.TAG_NAME, "body")
            
            # Check if page is not showing error
            page_source = self.driver.page_source.lower()
            error_indicators = ["error", "403", "404", "blocked", "access denied"]
            
            for indicator in error_indicators:
                if indicator in page_source:
                    self.logger.warning(f"Page health check failed: {indicator} detected")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Page health check failed: {e}")
            return False
    
    def wait_for_chart_load(self, timeout: int = 20) -> bool:
        """Wait for chart to fully load with multiple indicators"""
        try:
            # Wait for basic chart container
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.config["selectors"]["chart_container"]))
            )
            
            # Additional wait for chart data to load
            time.sleep(self.config["delays"]["screenshot_delay"])
            
            # Verify chart actually has content
            return self.verify_chart_content()
            
        except TimeoutException:
            self.logger.error("Chart load timeout")
            return False
        except Exception as e:
            self.logger.error(f"Chart load error: {e}")
            return False
    
    def verify_chart_content(self) -> bool:
        """Verify that chart actually contains trading data"""
        try:
            # Look for price data indicators
            indicators = [
                "svg",  # Chart SVG
                "[data-name='legend-source-item']",  # TradingView specific
                ".chart-container",
                "canvas"  # Chart canvas
            ]
            
            for indicator in indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    if elements:
                        self.logger.debug(f"Chart content verified: {indicator}")
                        return True
                except:
                    continue
            
            self.logger.warning("No chart content indicators found")
            return False
            
        except Exception as e:
            self.logger.error(f"Chart content verification failed: {e}")
            return False
    
    def navigate_to_chart(self, pair: str, timeframe: str, retry_count: int = 0) -> bool:
        """Navigate to specific pair and timeframe with retry logic"""
        if retry_count >= self.max_retries:
            self.logger.error(f"Max retries reached for {pair} {timeframe}")
            return False
        
        try:
            # Construct URL
            url = f"https://www.tradingview.com/chart/?symbol=FX%3A{pair}&interval={timeframe}"
            self.logger.info(f"Navigating to {pair} {timeframe} (attempt {retry_count + 1})")
            
            self.driver.get(url)
            
            # Wait for page load
            page_load_delay = random.uniform(
                self.config["delays"]["min_page_load"],
                self.config["delays"]["max_page_load"]
            )
            time.sleep(page_load_delay)
            
            # Check page health
            if not self.check_page_health():
                self.logger.warning(f"Page health check failed, retrying...")
                return self.navigate_to_chart(pair, timeframe, retry_count + 1)
            
            # Random mouse movement
            self.random_mouse_movement()
            
            # Wait for chart to load
            if not self.wait_for_chart_load():
                self.logger.warning(f"Chart load failed, retrying...")
                return self.navigate_to_chart(pair, timeframe, retry_count + 1)
            
            self.logger.info(f"Successfully loaded {pair} {timeframe}")
            return True
            
        except Exception as e:
            self.logger.error(f"Navigation error for {pair} {timeframe}: {e}")
            return self.navigate_to_chart(pair, timeframe, retry_count + 1)
    
    def take_screenshot(self, pair: str, timeframe: str) -> Optional[str]:
        """Take screenshot with enhanced naming and validation"""
        try:
            timestamp = datetime.now().strftime("%H-%M-%S")
            filename = f"{pair}_{timeframe}_{timestamp}.png"
            
            # Save to timeframe subdirectory
            tf_dir = self.today_dir / timeframe
            filepath = tf_dir / filename
            
            # Additional delay before screenshot
            time.sleep(random.uniform(1, 2))
            
            # Take screenshot
            self.driver.save_screenshot(str(filepath))
            
            # Validate screenshot
            if self.validate_screenshot(filepath):
                self.logger.info(f"Screenshot saved: {filename}")
                return str(filepath)
            else:
                self.logger.error(f"Screenshot validation failed: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return None
    
    def validate_screenshot(self, filepath: Path) -> bool:
        """Validate that screenshot was saved correctly and has content"""
        try:
            # Check if file exists and has reasonable size
            if not filepath.exists():
                return False
            
            file_size = filepath.stat().st_size
            min_size = 50 * 1024  # 50KB minimum
            
            if file_size < min_size:
                self.logger.warning(f"Screenshot too small: {file_size} bytes")
                return False
            
            self.logger.debug(f"Screenshot validated: {file_size} bytes")
            return True
            
        except Exception as e:
            self.logger.error(f"Screenshot validation error: {e}")
            return False
    
    def capture_timeframe(self, pair: str, timeframe: str) -> Optional[str]:
        """Capture a single timeframe with full error handling"""
        self.logger.info(f"Capturing {pair} {timeframe}...")
        
        try:
            # Navigate to chart
            if not self.navigate_to_chart(pair, timeframe):
                return None
            
            # Take screenshot
            filepath = self.take_screenshot(pair, timeframe)
            
            if filepath:
                # Random delay between captures
                self.human_like_delay(2, 4)
                return filepath
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error capturing {pair} {timeframe}: {e}")
            return None
    
    def capture_all_timeframes(self, pairs: List[str] = None) -> Dict[str, str]:
        """Main function to capture all timeframes for specified pairs"""
        if pairs is None:
            pairs = self.config["pairs"]
        
        screenshots = {}
        
        try:
            self.logger.info("Starting TradingView automation with enhanced anti-detection...")
            
            for pair in pairs:
                pair_screenshots = {}
                
                for tf_name, tf_value in self.config["timeframes"].items():
                    try:
                        filepath = self.capture_timeframe(pair, tf_value)
                        if filepath:
                            # Store with combined key for backward compatibility
                            key = f"{pair}_{tf_name}" if len(pairs) > 1 else tf_name
                            screenshots[key] = filepath
                            pair_screenshots[tf_name] = filepath
                        else:
                            self.logger.error(f"Failed to capture {pair} {tf_name}")
                        
                    except Exception as e:
                        self.logger.error(f"Error capturing {pair} {tf_name}: {e}")
                        continue
                
                if pair_screenshots:
                    self.logger.info(f"Completed {pair}: {len(pair_screenshots)} screenshots")
                else:
                    self.logger.error(f"No screenshots captured for {pair}")
            
            if screenshots:
                self.logger.info(f"All captures completed! Total: {len(screenshots)}")
                self.log_session_summary(screenshots)
            else:
                self.logger.error("No screenshots were captured!")
            
            return screenshots
            
        except Exception as e:
            self.logger.error(f"Error during capture session: {e}")
            return screenshots
        
        finally:
            self.cleanup_driver()
    
    def cleanup_driver(self):
        """Safely cleanup Chrome driver"""
        if self.driver:
            try:
                # Random delay before closing
                time.sleep(random.uniform(1, 3))
                self.driver.quit()
                self.logger.info("Chrome driver closed")
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
    
    def log_session_summary(self, screenshots: Dict[str, str]):
        """Log detailed session summary"""
        self.logger.info("=== SESSION SUMMARY ===")
        self.logger.info(f"Screenshots captured: {len(screenshots)}")
        self.logger.info(f"Session date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for key, path in screenshots.items():
            file_size = Path(path).stat().st_size / 1024  # KB
            self.logger.info(f"  {key}: {file_size:.1f} KB - {path}")
    
    def daily_analysis_job(self) -> Dict[str, str]:
        """Job that runs for daily analysis"""
        self.logger.info(f"Daily analysis starting at {datetime.now()}")
        
        screenshots = self.capture_all_timeframes()
        
        if screenshots:
            self.logger.info("Screenshots ready for AI analysis:")
            for tf, path in screenshots.items():
                self.logger.info(f"  {tf}: {path}")
        else:
            self.logger.error("No screenshots captured for analysis")
        
        return screenshots
    
    def test_connection(self) -> bool:
        """Test connection to TradingView"""
        try:
            self.logger.info("Testing TradingView connection...")
            
            self.driver.get("https://www.tradingview.com")
            time.sleep(5)
            
            if self.check_page_health():
                self.logger.info("✅ TradingView connection test passed")
                return True
            else:
                self.logger.error("❌ TradingView connection test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return False
        finally:
            self.cleanup_driver()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.cleanup_driver()

def main():
    """Main function with enhanced scheduler and error handling"""
    try:
        # Test connection first
        with TradingViewAutomation() as test_automation:
            if not test_automation.test_connection():
                print("❌ Connection test failed. Please check your internet connection.")
                return
        
        # Create main automation instance
        automation = TradingViewAutomation()
        
        # Schedule daily run at 13:00 UTC+8
        schedule.every().day.at("13:00").do(automation.daily_analysis_job)
        
        print("TradingView automation scheduled for 13:00 UTC+8")
        print("Enhanced features: Anti-detection, retries, validation")
        print("Press Ctrl+C to stop...")
        
        # For testing, run immediately
        print("\n🧪 Running test capture...")
        result = automation.daily_analysis_job()
        
        if result:
            print("✅ Test capture successful!")
        else:
            print("❌ Test capture failed!")
        
        # Keep the script running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n🛑 Automation stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()
