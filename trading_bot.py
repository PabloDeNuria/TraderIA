#!/usr/bin/env python3
"""
TradingView Screenshot Automation - VERSIÓN CORREGIDA
Sin duplicados, mejor anti-detección, configuración arreglada
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
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import os
import random
import logging
from pathlib import Path
from typing import Dict, Optional, List
import json

class TradingViewAutomation:
    def __init__(self, headless: bool = False, max_retries: int = 2):
        """Initialize with conservative settings to avoid detection"""
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
        
        # Track captured timeframes to avoid duplicates
        self.captured_today = set()
        self._load_today_captures()
    
    def _setup_logging(self):
        """Setup logging for automation"""
        self.logger = logging.getLogger("TradingViewAutomation")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _load_config(self) -> Dict:
        """Load conservative configuration - FIXED"""
        default_config = {
            "timeframes": {
                'H4': '240',
                'H1': '60', 
                'M15': '15'
            },
            "pairs": ["EURUSD"],
            "delays": {
                "min_page_load": 8,
                "max_page_load": 15,
                "min_action": 3,
                "max_action": 6,
                "screenshot_delay": 5,
                "between_captures": 10
            },
            "selectors": {
                "chart_container": "[data-name='legend-source-item']",
                "chart_loaded": ".chart-container",
                "price_scale": ".price-axis"
            },
            "anti_detection": {
                "user_agents": [
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ],
                "viewport_sizes": [
                    "1920,1080",
                    "1440,900", 
                    "1366,768"
                ]
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Deep merge with defaults
                self._merge_configs(default_config, loaded_config)
                return default_config
            else:
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
        except Exception as e:
            self.logger.error(f"Error loading config: {e}, using defaults")
            return default_config
    
    def _merge_configs(self, default: Dict, loaded: Dict):
        """Recursively merge configurations"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_configs(default[key], value)
                else:
                    default[key] = value
    
    def _load_today_captures(self):
        """Load list of already captured timeframes today"""
        today = datetime.now().strftime("%Y-%m-%d")
        today_dir = Path(self.screenshots_dir) / today
        
        if today_dir.exists():
            for tf_dir in today_dir.iterdir():
                if tf_dir.is_dir() and tf_dir.name in self.config["timeframes"]:
                    # Check if this timeframe has screenshots
                    screenshots = list(tf_dir.glob("*.png"))
                    if screenshots:
                        self.captured_today.add(tf_dir.name)
                        self.logger.info(f"Found existing {tf_dir.name} screenshots")
    
    def setup_driver(self):
        """Setup Chrome driver with enhanced stealth"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            # Random viewport
            viewport = random.choice(self.config["anti_detection"]["viewport_sizes"])
            chrome_options.add_argument(f"--window-size={viewport}")
            
            # Essential stealth options only
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            user_agent = random.choice(self.config["anti_detection"]["user_agents"])
            chrome_options.add_argument(f"--user-agent={user_agent}")
            
            # Minimal additional options
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            
            # Auto-download ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Essential stealth scripts
            essential_scripts = [
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            ]
            
            for script in essential_scripts:
                try:
                    self.driver.execute_script(script)
                except:
                    pass
            
            self.logger.info("Chrome driver configured with conservative stealth")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def create_directories(self):
        """Create directories for screenshots"""
        base_dir = Path(self.screenshots_dir)
        base_dir.mkdir(exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = base_dir / today
        self.today_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for timeframes
        for tf in self.config["timeframes"].keys():
            tf_dir = self.today_dir / tf
            tf_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Screenshot directories ready: {self.today_dir}")
    
    def human_like_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Conservative human-like delays"""
        if min_seconds is None:
            min_seconds = self.config["delays"]["min_action"]
        if max_seconds is None:
            max_seconds = self.config["delays"]["max_action"]
            
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.debug(f"Waiting {delay:.1f} seconds...")
        time.sleep(delay)
    
    def gentle_mouse_movement(self):
        """Very gentle mouse movements"""
        try:
            actions = ActionChains(self.driver)
            
            # Single, small movement
            x_offset = random.randint(50, 150)
            y_offset = random.randint(50, 150)
            actions.move_by_offset(x_offset, y_offset).perform()
            
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            self.logger.debug(f"Mouse movement failed: {e}")
    
    def check_for_cloudflare(self) -> bool:
        """Check for Cloudflare challenge"""
        try:
            page_source = self.driver.page_source.lower()
            cloudflare_indicators = [
                "checking your browser",
                "cloudflare",
                "security check",
                "please wait",
                "ray id"
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    self.logger.warning(f"Cloudflare challenge detected: {indicator}")
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for Cloudflare: {e}")
            return False
    
    def wait_for_page_ready(self, timeout: int = 30) -> bool:
        """Wait for page to be fully ready"""
        try:
            # Wait for document ready
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Check for Cloudflare
            if self.check_for_cloudflare():
                self.logger.info("Waiting for Cloudflare challenge...")
                time.sleep(10)  # Wait for challenge to resolve
                
                # Check again
                if self.check_for_cloudflare():
                    self.logger.error("Cloudflare challenge not resolved")
                    return False
            
            # Additional wait for TradingView to load
            time.sleep(self.config["delays"]["screenshot_delay"])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Page ready check failed: {e}")
            return False
    
    def navigate_to_chart(self, pair: str, timeframe: str) -> bool:
        """Navigate to chart with single attempt"""
        try:
            # Check if already captured
            timeframe_name = None
            for tf_name, tf_value in self.config["timeframes"].items():
                if tf_value == timeframe:
                    timeframe_name = tf_name
                    break
            
            if timeframe_name and timeframe_name in self.captured_today:
                self.logger.info(f"⏭️ {timeframe_name} already captured today, skipping")
                return False
            
            # Setup driver if not already done
            if not self.driver:
                self.setup_driver()
            
            url = f"https://www.tradingview.com/chart/?symbol=FX%3A{pair}&interval={timeframe}"
            self.logger.info(f"🌐 Navigating to {pair} {timeframe_name or timeframe}")
            
            self.driver.get(url)
            
            # Conservative wait for page load
            if not self.wait_for_page_ready():
                self.logger.error(f"Page not ready for {pair} {timeframe_name or timeframe}")
                return False
            
            # Gentle interaction
            self.gentle_mouse_movement()
            
            self.logger.info(f"✅ Successfully loaded {pair} {timeframe_name or timeframe}")
            return True
            
        except Exception as e:
            self.logger.error(f"Navigation error for {pair} {timeframe}: {e}")
            return False
    
    def take_screenshot(self, pair: str, timeframe_name: str) -> Optional[str]:
        """Take screenshot with duplicate prevention"""
        try:
            # Double-check not already captured
            if timeframe_name in self.captured_today:
                self.logger.info(f"⏭️ {timeframe_name} already captured, skipping")
                return None
            
            timestamp = datetime.now().strftime("%H-%M-%S")
            filename = f"{pair}_{timeframe_name}_{timestamp}.png"
            
            tf_dir = self.today_dir / timeframe_name
            filepath = tf_dir / filename
            
            # Extra wait before screenshot
            time.sleep(3)
            
            # Take screenshot
            self.driver.save_screenshot(str(filepath))
            
            # Validate
            if self.validate_screenshot(filepath):
                # Mark as captured
                self.captured_today.add(timeframe_name)
                self.logger.info(f"📸 Screenshot saved: {filename}")
                return str(filepath)
            else:
                self.logger.error(f"Screenshot validation failed: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"Screenshot error: {e}")
            return None
    
    def validate_screenshot(self, filepath: Path) -> bool:
        """Validate screenshot file"""
        try:
            if not filepath.exists():
                return False
            
            file_size = filepath.stat().st_size
            min_size = 30 * 1024  # 30KB minimum
            
            if file_size < min_size:
                self.logger.warning(f"Screenshot too small: {file_size} bytes")
                return False
            
            self.logger.debug(f"Screenshot validated: {file_size} bytes")
            return True
            
        except Exception as e:
            self.logger.error(f"Screenshot validation error: {e}")
            return False
    
    def capture_all_timeframes(self, pairs: List[str] = None) -> Dict[str, str]:
        """Capture all timeframes with duplicate prevention"""
        if pairs is None:
            pairs = self.config["pairs"]
        
        screenshots = {}
        
        try:
            self.logger.info("🚀 Starting conservative TradingView automation...")
            
            # Get timeframes that need capturing
            timeframes_needed = []
            for tf_name, tf_value in self.config["timeframes"].items():
                if tf_name not in self.captured_today:
                    timeframes_needed.append((tf_name, tf_value))
            
            if not timeframes_needed:
                self.logger.info("✅ All timeframes already captured today!")
                # Return existing screenshots
                for tf_name in self.config["timeframes"].keys():
                    tf_dir = self.today_dir / tf_name
                    existing_screenshots = list(tf_dir.glob("*.png"))
                    if existing_screenshots:
                        screenshots[tf_name] = str(existing_screenshots[-1])  # Most recent
                return screenshots
            
            self.logger.info(f"📋 Need to capture: {[tf[0] for tf in timeframes_needed]}")
            
            for pair in pairs:
                for tf_name, tf_value in timeframes_needed:
                    try:
                        # Navigate and capture
                        if self.navigate_to_chart(pair, tf_value):
                            filepath = self.take_screenshot(pair, tf_name)
                            
                            if filepath:
                                key = f"{pair}_{tf_name}" if len(pairs) > 1 else tf_name
                                screenshots[key] = filepath
                                self.logger.info(f"✅ Captured {tf_name}")
                            else:
                                self.logger.error(f"❌ Failed to capture {tf_name}")
                        
                        # Wait between captures
                        if tf_name != timeframes_needed[-1][0]:  # Not the last one
                            wait_time = self.config["delays"]["between_captures"]
                            self.logger.info(f"⏳ Waiting {wait_time}s before next capture...")
                            time.sleep(wait_time)
                        
                    except Exception as e:
                        self.logger.error(f"Error capturing {pair} {tf_name}: {e}")
                        continue
            
            if screenshots:
                self.logger.info(f"🎉 Session completed! Captured: {len(screenshots)}")
                self.log_session_summary(screenshots)
            else:
                self.logger.error("😞 No new screenshots were captured")
            
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
                time.sleep(2)  # Brief pause
                self.driver.quit()
                self.logger.info("🔌 Chrome driver closed")
            except Exception as e:
                self.logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
    
    def log_session_summary(self, screenshots: Dict[str, str]):
        """Log session summary"""
        self.logger.info("📊 === SESSION SUMMARY ===")
        self.logger.info(f"New screenshots: {len(screenshots)}")
        self.logger.info(f"Session time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for key, path in screenshots.items():
            try:
                file_size = Path(path).stat().st_size / 1024
                self.logger.info(f"  📸 {key}: {file_size:.1f} KB")
            except:
                self.logger.info(f"  📸 {key}: {path}")
    
    def daily_analysis_job(self) -> Dict[str, str]:
        """Daily analysis job"""
        self.logger.info(f"📅 Daily analysis starting at {datetime.now()}")
        
        screenshots = self.capture_all_timeframes()
        
        if screenshots:
            self.logger.info("✅ Screenshots ready for analysis")
        else:
            self.logger.warning("⚠️ No screenshots available")
        
        return screenshots
    
    def test_connection(self) -> bool:
        """Test connection to TradingView"""
        try:
            self.logger.info("Testing TradingView connection...")
            
            if not self.driver:
                self.setup_driver()
            
            self.driver.get("https://www.tradingview.com")
            time.sleep(5)
            
            # Simple page check
            if "TradingView" in self.driver.title:
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
    """Main function for testing"""
    try:
        automation = TradingViewAutomation()
        result = automation.daily_analysis_job()
        
        if result:
            print("✅ Automation test successful!")
            for key, path in result.items():
                print(f"  {key}: {path}")
        else:
            print("❌ Automation test failed!")
            
    except KeyboardInterrupt:
        print("\n🛑 Automation stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
