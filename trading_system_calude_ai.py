#!/usr/bin/env python3
"""
Sistema Trading IA - VERSIÓN FINAL CON CLAUDE API INTEGRADO
Sistema completo automático con análisis de Claude
"""

import time
import schedule
from datetime import datetime, time as dt_time
import os
import sys
import platform
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
import json
import signal
import threading
from contextlib import contextmanager

# Import our components
try:
    from local_memory_system import LocalTradingMemory
    from claude_trader import ClaudeTrader
except ImportError as e:
    print(f"❌ Error importing modules: {e}")
    print("Ensure you have: local_memory_system.py, claude_trader.py")
    sys.exit(1)

class SistemaTradingClaudeAI:
    def __init__(self, config_file: str = "trading_system_config.json"):
        """Initialize trading system with Claude AI integration"""
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.memory = LocalTradingMemory()
        self.claude_trader = ClaudeTrader()  # Initialize Claude API
        self.screenshots_dir = Path(self.config["directories"]["screenshots"])
        
        # Setup MT5 communication
        self.setup_mt5_paths()
        
        # Trading state
        self.current_trade = None
        self.waiting_for_setup = False
        self.is_running = False
        self.shutdown_requested = False
        self.session_active = False
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        self.logger.info("🤖 SISTEMA TRADING IA + CLAUDE API - TOTALMENTE AUTOMÁTICO")
        self.logger.info(f"📈 MT5 Commands: {self.mt5_commands_file}")
        self.logger.info(f"📊 MT5 Status: {self.mt5_status_file}")
        
        # Ensure all files exist
        self.ensure_all_files_exist()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration optimized for Claude automation"""
        default_config = {
            "automation": {
                "mode": "claude_ai",
                "claude_timeout": 120,  # 2 minutes for Claude analysis
                "screenshot_validation": True,
                "auto_backup": True,
                "error_recovery": True,
                "headless_mode": True
            },
            "trading": {
                "pairs": ["EURUSD"],
                "timeframes": ["H4", "H1", "M15"],
                "daily_session_time": "13:00",
                "monitoring_interval": 15,
                "trading_hours": {
                    "start": "14:00",
                    "end": "17:00"
                },
                "max_retries": 3
            },
            "directories": {
                "screenshots": "trading_screenshots",
                "logs": "logs",
                "backups": "backups"
            },
            "mt5": {
                "auto_detect_path": True,
                "custom_path": None,
                "command_timeout": 30,
                "status_check_interval": 5
            },
            "claude_ai": {
                "enabled": True,
                "model": "claude-3-5-sonnet-20241022",
                "max_retries": 2,
                "fallback_decision": "1"  # WAIT if Claude fails
            },
            "notifications": {
                "log_level": "INFO",
                "file_logging": True,
                "console_logging": True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                self._merge_config(default_config, loaded_config)
                return default_config
            else:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return default_config
    
    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge configs"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = Path(self.config["directories"]["logs"])
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("TradingClaudeAI")
        self.logger.setLevel(getattr(logging, self.config["notifications"]["log_level"]))
        self.logger.handlers.clear()
        
        # File handler
        if self.config["notifications"]["file_logging"]:
            log_file = log_dir / f"trading_claude_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
        # Console handler  
        if self.config["notifications"]["console_logging"]:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        if self.config["notifications"]["file_logging"]:
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        if self.config["notifications"]["console_logging"]:
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers"""
        def signal_handler(signum, frame):
            self.logger.info(f"🛑 Shutdown signal received...")
            self.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def setup_mt5_paths(self):
        """Setup MT5 paths"""
        if self.config["mt5"]["auto_detect_path"]:
            self._auto_detect_mt5_paths()
        else:
            custom_path = self.config["mt5"]["custom_path"]
            if custom_path:
                base_path = Path(custom_path)
                self.mt5_commands_file = base_path / "trading_commands.txt"
                self.mt5_status_file = base_path / "trade_status.txt"
            else:
                self._auto_detect_mt5_paths()
    
    def _auto_detect_mt5_paths(self):
        """Auto-detect MT5 paths"""
        home = Path.home()
        
        if platform.system() == "Darwin":  # macOS
            possible_paths = [
                home / "Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files",
                home / ".wine/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files",
                home / "Documents/MT5_Files",
                home / "Desktop/MT5_Files"
            ]
        elif platform.system() == "Windows":
            possible_paths = [
                Path(os.environ.get('APPDATA', '')) / "MetaQuotes/Terminal/Common/Files",
                home / "AppData/Roaming/MetaQuotes/Terminal/Common/Files",
                Path("C:/Program Files/MetaTrader 5/MQL5/Files"),
                Path("C:/Program Files (x86)/MetaTrader 5/MQL5/Files")
            ]
        else:  # Linux
            possible_paths = [
                home / ".wine/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files",
                home / ".mt5/Files",
                home / "Documents/MT5_Files"
            ]
        
        mt5_dir = None
        for path in possible_paths:
            if path.exists():
                mt5_dir = path
                self.logger.info(f"✅ MT5 directory found: {mt5_dir}")
                break
        
        if not mt5_dir:
            mt5_dir = possible_paths[0]
            self.logger.warning(f"⚠️ MT5 directory not found, will create: {mt5_dir}")
        
        self.mt5_commands_file = mt5_dir / "trading_commands.txt"
        self.mt5_status_file = mt5_dir / "trade_status.txt"
    
    def ensure_all_files_exist(self):
        """Ensure all files exist"""
        try:
            # MT5 files
            self.mt5_commands_file.parent.mkdir(parents=True, exist_ok=True)
            
            if not self.mt5_commands_file.exists():
                with open(self.mt5_commands_file, 'w', encoding='ascii') as f:
                    f.write("")
                self.logger.info(f"📁 Created MT5 commands file")
            
            if not self.mt5_status_file.exists():
                default_status = "WAITING|0|0|0|0|20250710|System starting"
                with open(self.mt5_status_file, 'w', encoding='ascii') as f:
                    f.write(default_status)
                self.logger.info(f"📁 Created MT5 status file")
            
            self.logger.info("✅ All files validated")
            
        except Exception as e:
            self.logger.error(f"❌ Error creating files: {e}")
            raise
    
    @contextmanager
    def automation_context(self):
        """Context manager for trading automation"""
        automation = None
        try:
            automation_class = self._import_trading_automation()
            if automation_class:
                automation = automation_class(
                    headless=self.config["automation"]["headless_mode"],
                    max_retries=self.config["trading"]["max_retries"]
                )
                yield automation
            else:
                yield None
        except Exception as e:
            self.logger.error(f"❌ Automation error: {e}")
            yield None
        finally:
            if automation and hasattr(automation, 'cleanup_driver'):
                automation.cleanup_driver()
    
    def _import_trading_automation(self):
        """Import TradingView automation"""
        import_attempts = [
            ('trading_bot', 'TradingViewAutomation'),
            ('Trading_bot', 'TradingViewAutomation'),
            ('tradingview_automation', 'TradingViewAutomation')
        ]
        
        for module_name, class_name in import_attempts:
            try:
                module = __import__(module_name, fromlist=[class_name])
                return getattr(module, class_name)
            except (ImportError, AttributeError):
                continue
        return None
    
    def take_screenshots(self) -> Optional[Dict[str, str]]:
        """Take trading screenshots"""
        self.logger.info("📸 Taking trading screenshots...")
        
        try:
            with self.automation_context() as automation:
                if not automation:
                    return None
                
                screenshots = automation.capture_all_timeframes(
                    pairs=self.config["trading"]["pairs"]
                )
                
                if screenshots:
                    self.logger.info("✅ Screenshots captured:")
                    for tf, path in screenshots.items():
                        size_kb = Path(path).stat().st_size / 1024
                        self.logger.info(f"   {tf}: {size_kb:.1f} KB")
                    
                    if self.config["automation"]["screenshot_validation"]:
                        screenshots = self._validate_screenshots(screenshots)
                    
                    return screenshots
                else:
                    self.logger.error("❌ Screenshot capture failed")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Screenshot error: {e}")
            return None
    
    def _validate_screenshots(self, screenshots: Dict[str, str]) -> Dict[str, str]:
        """Validate screenshots"""
        validated = {}
        min_size = 50 * 1024
        
        for key, filepath in screenshots.items():
            try:
                path = Path(filepath)
                if path.exists() and path.stat().st_size >= min_size:
                    validated[key] = filepath
                else:
                    self.logger.warning(f"⚠️ Invalid screenshot: {key}")
            except Exception as e:
                self.logger.error(f"❌ Screenshot validation error {key}: {e}")
        
        return validated
    
    def get_memory_context(self) -> str:
        """Get memory context for Claude analysis"""
        try:
            recent_lessons = self.memory.get_recent_lessons(limit=10, min_relevance=4)
            memory_text = self.memory.format_memory_for_ai(recent_lessons)
            
            # Add current context
            context_info = [
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Estado actual: {self.current_trade or 'Sin trades activos'}",
                f"Esperando setup: {'Sí' if self.waiting_for_setup else 'No'}"
            ]
            
            return "\n".join(context_info) + "\n\n" + memory_text
            
        except Exception as e:
            self.logger.error(f"❌ Memory context error: {e}")
            return "MEMORIA: [Error cargando memoria]"
    
    def send_command_to_mt5(self, command: str) -> bool:
        """Send command to MT5 EA"""
        try:
            if command not in ['1', '2', '3', '4']:
                self.logger.error(f"❌ Invalid MT5 command: {command}")
                return False
            
            with open(self.mt5_commands_file, 'w', encoding='ascii') as f:
                f.write(command)
                f.flush()
            
            command_names = {'1': 'WAIT', '2': 'LONG', '3': 'SHORT', '4': 'CLOSE'}
            self.logger.info(f"📤 MT5 command sent: {command_names[command]}")
            
            time.sleep(0.1)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MT5 command error: {e}")
            return False
    
    def read_mt5_status(self) -> Dict[str, Any]:
        """Read MT5 status"""
        try:
            if not self.mt5_status_file.exists():
                return {'status': 'FILE_NOT_FOUND', 'message': 'Status file does not exist'}
            
            for encoding in ['ascii', 'utf-8', 'latin1', 'cp1252']:
                try:
                    with open(self.mt5_status_file, 'r', encoding=encoding) as f:
                        content = f.read().strip()
                    
                    if content and all(ord(c) < 128 for c in content):
                        break
                except:
                    continue
            else:
                return {'status': 'UNREADABLE', 'message': 'File contains unreadable data'}
            
            parts = content.split('|')
            if len(parts) < 6:
                return {'status': 'PARSE_ERROR', 'message': f'Invalid format: {content}'}
            
            status_data = {
                'status': parts[0],
                'ticket': int(parts[1]) if parts[1].isdigit() else 0,
                'entry': self._safe_float_parse(parts[2]),
                'sl': self._safe_float_parse(parts[3]),
                'tp': self._safe_float_parse(parts[4]),
                'timestamp': parts[5],
                'message': parts[6] if len(parts) > 6 else "",
                'raw_data': content
            }
            
            status_data['is_active'] = status_data['status'] in ['LONG_ACTIVE', 'SHORT_ACTIVE']
            status_data['direction'] = 'LONG' if 'LONG' in status_data['status'] else 'SHORT' if 'SHORT' in status_data['status'] else None
            
            return status_data
            
        except Exception as e:
            self.logger.error(f"❌ MT5 status read error: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def _safe_float_parse(self, value: str) -> float:
        """Safely parse float"""
        try:
            return float(value) if value and value != '0' else 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def daily_trading_session(self):
        """MAIN AUTOMATED TRADING SESSION WITH CLAUDE AI"""
        session_start = datetime.now()
        self.logger.info("🚀 ===== DAILY TRADING SESSION WITH CLAUDE AI =====")
        self.logger.info(f"⏰ Time: {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.session_active = True
        
        try:
            # Step 1: Take screenshots
            self.logger.info("📸 Step 1: Capturing market screenshots...")
            screenshots = self.take_screenshots()
            
            if not screenshots:
                self.logger.error("❌ Screenshot capture failed, aborting session")
                return
            
            # Step 2: Get memory context
            self.logger.info("🧠 Step 2: Loading trading memory...")
            memory_context = self.get_memory_context()
            
            # Step 3: Claude AI Analysis
            self.logger.info("🤖 Step 3: Sending to Claude AI for analysis...")
            
            # Use Claude to analyze the market
            claude_decision = self.claude_trader.analyze_market(screenshots, memory_context)
            
            if not claude_decision:
                self.logger.error("❌ Claude analysis failed")
                return
            
            # Step 4: Process Claude's decision
            self.logger.info("⚡ Step 4: Processing Claude's trading decision...")
            decision = claude_decision.get("decision", "1")
            reasoning = claude_decision.get("reasoning", "No reasoning provided")
            confidence = claude_decision.get("confidence", 0)
            
            self.logger.info(f"🎯 Claude Decision: {decision}")
            self.logger.info(f"🧠 Reasoning: {reasoning}")
            self.logger.info(f"📊 Confidence: {confidence}/10")
            
            # Step 5: Execute decision
            success = self.execute_trading_decision(decision, reasoning)
            
            # Step 6: Save analysis log
            self.claude_trader.save_analysis_log(screenshots, claude_decision)
            
            # Step 7: Start monitoring if trade executed
            if success and decision in ['2', '3']:
                self.logger.info("👁️ Step 7: Starting trade monitoring...")
                self._start_trade_monitoring()
            
            # Session summary
            session_duration = (datetime.now() - session_start).total_seconds()
            self.logger.info("📊 ===== SESSION SUMMARY =====")
            self.logger.info(f"⏱️ Duration: {session_duration:.1f} seconds")
            self.logger.info(f"📸 Screenshots: {len(screenshots)}")
            self.logger.info(f"🤖 Claude Decision: {decision} (confidence: {confidence}/10)")
            self.logger.info(f"✅ Execution: {'Success' if success else 'Failed'}")
            self.logger.info("=" * 50)
            
        except Exception as e:
            self.logger.error(f"❌ Daily session error: {e}")
        finally:
            self.session_active = False
    
    def execute_trading_decision(self, decision: str, reasoning: str) -> bool:
        """Execute trading decision"""
        self.logger.info(f"📊 Executing decision: {decision}")
        self.logger.info(f"💭 Claude reasoning: {reasoning}")
        
        if self.send_command_to_mt5(decision):
            decision_names = {'1': 'WAIT', '2': 'LONG', '3': 'SHORT', '4': 'CLOSE'}
            action_name = decision_names[decision]
            
            if decision in ['2', '3']:
                self.current_trade = action_name
                self.logger.info(f"✅ {action_name} trade executed")
            elif decision == '1':
                self.logger.info(f"⏳ Waiting for better conditions")
            elif decision == '4':
                self.current_trade = None
                self.logger.info(f"🛑 All positions closed")
            
            return True
        else:
            self.logger.error(f"❌ Failed to execute {decision}")
            return False
    
    def _start_trade_monitoring(self):
        """Start trade monitoring in background"""
        def monitor_trade():
            self.logger.info("👁️ Trade monitoring started...")
            
            while self.current_trade and not self.shutdown_requested:
                try:
                    if self.monitor_active_trade():
                        self.logger.info("✅ Trade monitoring completed - trade closed")
                        break
                    
                    time.sleep(self.config["mt5"]["status_check_interval"])
                    
                except Exception as e:
                    self.logger.error(f"❌ Trade monitoring error: {e}")
                    break
        
        monitor_thread = threading.Thread(target=monitor_trade)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def monitor_active_trade(self) -> bool:
        """Monitor active trade"""
        status = self.read_mt5_status()
        
        if status['status'] in ['TP_HIT', 'SL_HIT', 'CLOSED', 'MANUAL_CLOSE']:
            self.logger.info(f"🚨 TRADE CLOSED: {status['status']}")
            
            if status.get('entry', 0) > 0:
                self.logger.info(f"📈 Entry: {status['entry']}")
                if status.get('sl'): self.logger.info(f"🛑 SL: {status['sl']}")
                if status.get('tp'): self.logger.info(f"🎯 TP: {status['tp']}")
            
            # Generate lesson
            self.generate_post_trade_lesson(status)
            
            self.current_trade = None
            return True
        
        elif status['status'] in ['LONG_ACTIVE', 'SHORT_ACTIVE']:
            direction = status.get('direction', 'UNKNOWN')
            entry = status.get('entry', 0)
            self.logger.info(f"📈 Active {direction} trade @ {entry}")
            return False
        
        return False
    
    def generate_post_trade_lesson(self, trade_result: Dict[str, Any]):
        """Generate post-trade lesson"""
        self.logger.info("🧠 Generating post-trade lesson...")
        
        # Calculate pips result
        pips_result = self._calculate_pips_result(trade_result)
        
        # Create basic lesson
        try:
            context = f"{trade_result.get('direction', 'Unknown')} trade - {trade_result['status']}"
            rule = f"Trade closed: {trade_result['status']} - Review execution and Claude analysis"
            
            auto_tags = []
            if trade_result.get('direction'): 
                auto_tags.append(trade_result['direction'].lower())
            if 'TP_HIT' in trade_result['status']: 
                auto_tags.append('win')
            elif 'SL_HIT' in trade_result['status']: 
                auto_tags.append('loss')
            auto_tags.extend(['post_trade', 'claude_decision'])
            
            lesson_id = self.memory.add_lesson(
                pair="EURUSD",
                lesson_type="Post-Trade Claude",
                context=context,
                rule=rule,
                result=pips_result,
                relevance=4,
                tags=auto_tags
            )
            
            self.logger.info(f"✅ Post-trade lesson {lesson_id} created")
            
        except Exception as e:
            self.logger.error(f"❌ Post-trade lesson error: {e}")
    
    def _calculate_pips_result(self, trade_data: Dict) -> str:
        """Calculate pips result"""
        if trade_data.get('entry', 0) <= 0:
            return "N/A"
        
        try:
            if trade_data['status'] == 'TP_HIT' and trade_data.get('tp', 0) > 0:
                if trade_data.get('direction') == 'LONG':
                    pips = (trade_data['tp'] - trade_data['entry']) * 10000
                else:
                    pips = (trade_data['entry'] - trade_data['tp']) * 10000
                return f"+{pips:.1f} pips"
            elif trade_data['status'] == 'SL_HIT' and trade_data.get('sl', 0) > 0:
                if trade_data.get('direction') == 'LONG':
                    pips = (trade_data['sl'] - trade_data['entry']) * 10000
                else:
                    pips = (trade_data['entry'] - trade_data['sl']) * 10000
                return f"{pips:.1f} pips"
        except:
            pass
        
        return "N/A"
    
    def start_automated_system(self):
        """Start the fully automated Claude AI trading system"""
        self.logger.info("🚀 ===== CLAUDE AI TRADING SYSTEM STARTING =====")
        self.logger.info(f"🤖 Claude AI: ENABLED")
        self.logger.info(f"🕐 Daily session: {self.config['trading']['daily_session_time']}")
        self.logger.info(f"👁️ Monitoring: Every {self.config['trading']['monitoring_interval']} minutes")
        self.logger.info(f"⏰ Trading hours: {self.config['trading']['trading_hours']['start']}-{self.config['trading']['trading_hours']['end']}")
        
        # Schedule sessions
        daily_time = self.config["trading"]["daily_session_time"]
        schedule.every().day.at(daily_time).do(self.daily_trading_session)
        
        monitor_interval = self.config["trading"]["monitoring_interval"]
        schedule.every(monitor_interval).minutes.do(self.monitoring_session)
        
        self.logger.info("")
        self.logger.info("🎯 MANUAL COMMANDS:")
        self.logger.info("   'test' - Run immediate Claude analysis")
        self.logger.info("   'status' - Check system status")
        self.logger.info("   'quit' - Exit system")
        self.logger.info("")
        self.logger.info("⚡ System is FULLY AUTOMATED with Claude AI!")
        self.logger.info("   Claude will analyze charts and make all decisions")
        self.logger.info("=" * 60)
        
        self.is_running = True
        
        # Interactive loop
        try:
            while self.is_running and not self.shutdown_requested:
                schedule.run_pending()
                
                try:
                    import select
                    import sys
                    
                    if select.select([sys.stdin], [], [], 1) == ([sys.stdin], [], []):
                        user_input = input().strip().lower()
                        
                        if user_input == 'test':
                            self.logger.info("🧪 Running manual Claude analysis...")
                            self.daily_trading_session()
                        elif user_input == 'status':
                            self._print_system_status()
                        elif user_input in ['quit', 'exit', 'stop']:
                            self.logger.info("🛑 Manual shutdown requested")
                            break
                    else:
                        time.sleep(1)
                        
                except (ImportError, OSError):
                    time.sleep(60)
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Keyboard interrupt received")
        finally:
            self._graceful_shutdown()
    
    def monitoring_session(self):
        """Monitoring session during trading hours"""
        if not self.current_trade:
            return
        
        try:
            self.logger.info(f"👁️ Monitoring session - {datetime.now().strftime('%H:%M:%S')}")
            
            if self.current_trade:
                trade_closed = self.monitor_active_trade()
                if trade_closed:
                    self.logger.info("✅ Trade closed during monitoring")
                    
        except Exception as e:
            self.logger.error(f"❌ Monitoring session error: {e}")
    
    def _print_system_status(self):
        """Print system status"""
        mt5_status = self.read_mt5_status()
        memory_stats = self.memory.get_memory_stats()
        
        self.logger.info("📊 ===== SYSTEM STATUS =====")
        self.logger.info(f"🕐 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⚡ System Running: {self.is_running}")
        self.logger.info(f"🤖 Claude AI: ACTIVE")
        self.logger.info(f"📈 Current Trade: {self.current_trade or 'None'}")
        self.logger.info(f"🔍 Session Active: {self.session_active}")
        self.logger.info(f"🤖 MT5 Status: {mt5_status.get('status', 'Unknown')}")
        self.logger.info(f"🧠 Memory Lessons: {memory_stats.get('total', 0)}")
        self.logger.info("==========================")
    
    def _graceful_shutdown(self):
        """Graceful system shutdown"""
        self.logger.info("🛑 ===== GRACEFUL SHUTDOWN =====")
        
        self.is_running = False
        self.session_active = False
        
        if self.current_trade:
            self.logger.info("🛑 Closing active trades...")
            self.send_command_to_mt5('4')
        
        # Final backup
        if self.config["automation"]["auto_backup"]:
            try:
                backup_path = self.memory.export_to_csv()
                self.logger.info(f"💾 Final backup: {backup_path}")
            except Exception as e:
                self.logger.error(f"❌ Backup error: {e}")
        
        self.logger.info("✅ Claude AI Trading System shutdown complete")

def main():
    """Main entry point"""
    print("🤖 SISTEMA TRADING IA + CLAUDE API")
    print("=" * 50)
    print("🎯 CARACTERÍSTICAS:")
    print("  • Análisis automático con Claude AI")
    print("  • Decisiones inteligentes basadas en IA")
    print("  • Ejecución automática en MT5")
    print("  • Sistema de memoria evolutivo")
    print("  • Monitoreo continuo de trades")
    print("=" * 50)
    
    try:
        system = SistemaTradingClaudeAI()
        system.start_automated_system()
        
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logging.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    main()
