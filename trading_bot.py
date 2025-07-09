#!/usr/bin/env python3
"""
TradingView Screenshot Automation para Trading AI
Capturas H4, H1, M15 de EURUSD con anti-detección
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
from webdriver_manager.chrome import ChromeDriverManager
import os
import random

class TradingViewAutomation:
    def __init__(self):
        self.driver = None
        self.screenshots_dir = "trading_screenshots"
        self.setup_driver()
        self.create_directories()
    
    def setup_driver(self):
        """Setup Chrome driver with anti-detection options"""
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        
        # Auto-download ChromeDriver with WebDriverManager
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("Chrome driver configurado con anti-detección")
    
    def create_directories(self):
        """Create directories for screenshots"""
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.today_dir = os.path.join(self.screenshots_dir, today)
        if not os.path.exists(self.today_dir):
            os.makedirs(self.today_dir)
    
    def human_like_delay(self, min_seconds=2, max_seconds=5):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def random_mouse_movement(self):
        """Random mouse movements to avoid detection"""
        try:
            actions = ActionChains(self.driver)
            x_offset = random.randint(50, 300)
            y_offset = random.randint(50, 200)
            actions.move_by_offset(x_offset, y_offset).perform()
            time.sleep(random.uniform(0.5, 1.5))
        except:
            pass
    
    def login_tradingview(self):
        """Login to TradingView with anti-detection"""
        print("Accediendo a TradingView...")
        self.driver.get("https://www.tradingview.com")
        
        # Random delay
        self.human_like_delay(3, 6)
        
        # Random mouse movements
        self.random_mouse_movement()
        
        print("TradingView cargado con comportamiento humano")
    
    def navigate_to_eurusd(self, timeframe):
        """Navigate to EURUSD with specific timeframe"""
        # Use direct URL approach to avoid cloudfront issues
        url = f"https://www.tradingview.com/chart/?symbol=FX%3AEURUSD&interval={timeframe}"
        print(f"Navegando a EURUSD {timeframe}...")
        
        self.driver.get(url)
        
        # Wait for chart to load with random delay
        self.human_like_delay(4, 7)
        
        # Random mouse movement
        self.random_mouse_movement()
        
        # Wait for chart container
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-name='legend-source-item']"))
            )
            print(f"Gráfico {timeframe} cargado correctamente")
        except Exception as e:
            print(f"Warning: Elemento específico no encontrado, continuando: {e}")
        
        # Additional wait for data
        self.human_like_delay(2, 4)
    
    def take_screenshot(self, timeframe):
        """Take screenshot of current chart"""
        timestamp = datetime.now().strftime("%H-%M-%S")
        filename = f"EURUSD_{timeframe}_{timestamp}.png"
        filepath = os.path.join(self.today_dir, filename)
        
        # Random delay before screenshot
        time.sleep(random.uniform(1, 2))
        
        # Full page screenshot
        self.driver.save_screenshot(filepath)
        print(f"Screenshot guardado: {filename}")
        return filepath
    
    def capture_all_timeframes(self):
        """Main function to capture H4, H1, M15"""
        timeframes = {
            'H4': '240',  # 4 hours in minutes
            'H1': '60',   # 1 hour in minutes
            'M15': '15'   # 15 minutes
        }
        
        screenshots = {}
        
        try:
            print("Iniciando automatización TradingView con anti-detección...")
            self.login_tradingview()
            
            for tf_name, tf_value in timeframes.items():
                print(f"Capturando {tf_name} timeframe...")
                
                try:
                    self.navigate_to_eurusd(tf_value)
                    filepath = self.take_screenshot(tf_name)
                    screenshots[tf_name] = filepath
                    
                    # Random delay between captures
                    self.human_like_delay(2, 4)
                    
                except Exception as e:
                    print(f"Error capturando {tf_name}: {e}")
                    # Continue with next timeframe
                    continue
            
            print("Capturas completadas!")
            return screenshots
            
        except Exception as e:
            print(f"Error durante captura: {e}")
            return None
        
        finally:
            if self.driver:
                # Random delay before closing
                time.sleep(random.uniform(1, 3))
                self.driver.quit()
    
    def daily_analysis_job(self):
        """Job that runs at 13:00 UTC+8"""
        print(f"Análisis diario iniciando en {datetime.now()}")
        screenshots = self.capture_all_timeframes()
        
        if screenshots:
            print("Screenshots listos para análisis IA:")
            for tf, path in screenshots.items():
                print(f"{tf}: {path}")
        
        return screenshots

def main():
    """Main function to setup scheduler"""
    automation = TradingViewAutomation()
    
    # Schedule daily run at 13:00 UTC+8
    schedule.every().day.at("13:00").do(automation.daily_analysis_job)
    
    print("TradingView automation programado para 13:00 UTC+8")
    print("Presiona Ctrl+C para detener...")
    
    # For testing, run immediately:
    automation.daily_analysis_job()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
