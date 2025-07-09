#!/usr/bin/env python3
"""
Sistema Trading IA Completo - VERSIÓN MEJORADA
Integra: Capturas + Memoria + Análisis + MT5 EA con manejo robusto de errores
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

# Import our enhanced components
try:
    from local_memory_system import LocalTradingMemory
except ImportError:
    print("❌ Error: local_memory_system.py no encontrado")
    sys.exit(1)

class SistemaTradingCompleto:
    def __init__(self, config_file: str = "trading_system_config.json"):
        """Initialize complete trading system with enhanced configuration"""
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.memory = LocalTradingMemory()
        self.screenshots_dir = Path(self.config["directories"]["screenshots"])
        
        # Setup MT5 communication
        self.setup_mt5_paths()
        
        # Trading state
        self.current_trade = None
        self.waiting_for_setup = False
        self.is_running = False
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        self.logger.info("Sistema de Trading IA inicializado (versión mejorada)")
        self.logger.info(f"Comandos MT5: {self.mt5_commands_file}")
        self.logger.info(f"Estado MT5: {self.mt5_status_file}")
        
        # Ensure MT5 files exist
        self.ensure_mt5_files_exist()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with comprehensive defaults"""
        default_config = {
            "trading": {
                "pairs": ["EURUSD"],
                "timeframes": ["H4", "H1", "M15"],
                "daily_session_time": "13:00",
                "monitoring_interval": 15,  # minutes
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
                "command_timeout": 30,  # seconds
                "status_check_interval": 5  # seconds
            },
            "automation": {
                "screenshot_validation": True,
                "auto_backup": True,
                "error_recovery": True,
                "headless_mode": False
            },
            "notifications": {
                "log_level": "INFO",
                "file_logging": True,
                "console_logging": True
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with defaults (recursive merge)
                self._merge_config(default_config, loaded_config)
                return default_config
            else:
                # Save default config
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return default_config
    
    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge loaded config with defaults"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
    
    def _setup_logging(self):
        """Setup comprehensive logging system"""
        # Create logs directory
        log_dir = Path(self.config["directories"]["logs"])
        log_dir.mkdir(exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger("TradingSystem")
        self.logger.setLevel(getattr(logging, self.config["notifications"]["log_level"]))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation
        if self.config["notifications"]["file_logging"]:
            log_file = log_dir / f"trading_system_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler
        if self.config["notifications"]["console_logging"]:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        if self.config["notifications"]["file_logging"]:
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        if self.config["notifications"]["console_logging"]:
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def setup_mt5_paths(self):
        """Setup MT5 paths with enhanced detection"""
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
        """Auto-detect MT5 paths based on OS and common installations"""
        home = Path.home()
        
        possible_paths = []
        
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
        
        # Find existing path or use first as default
        mt5_dir = None
        for path in possible_paths:
            if path.exists():
                mt5_dir = path
                self.logger.info(f"Found existing MT5 directory: {mt5_dir}")
                break
        
        if not mt5_dir:
            mt5_dir = possible_paths[0]
            self.logger.warning(f"MT5 directory not found, will create: {mt5_dir}")
        
        self.mt5_commands_file = mt5_dir / "trading_commands.txt"
        self.mt5_status_file = mt5_dir / "trade_status.txt"
    
    def ensure_mt5_files_exist(self):
        """Ensure MT5 communication files exist with validation"""
        try:
            # Create directories
            self.mt5_commands_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create command file
            if not self.mt5_commands_file.exists():
                self.mt5_commands_file.write_text("", encoding='utf-8')
                self.logger.info(f"Created MT5 commands file: {self.mt5_commands_file}")
            
            # Create status file with default status
            if not self.mt5_status_file.exists():
                default_status = f"WAITING|0|0|0|0|{datetime.now().isoformat()}|System starting"
                self.mt5_status_file.write_text(default_status, encoding='utf-8')
                self.logger.info(f"Created MT5 status file: {self.mt5_status_file}")
            
            # Validate file permissions
            self._validate_mt5_files()
            
        except Exception as e:
            self.logger.error(f"Error creating MT5 files: {e}")
            raise
    
    def _validate_mt5_files(self):
        """Validate MT5 files are readable and writable"""
        try:
            # Test write to command file
            test_content = "TEST"
            self.mt5_commands_file.write_text(test_content, encoding='utf-8')
            
            # Test read from command file
            read_content = self.mt5_commands_file.read_text(encoding='utf-8')
            if read_content != test_content:
                raise ValueError("MT5 command file read/write validation failed")
            
            # Clear test content
            self.mt5_commands_file.write_text("", encoding='utf-8')
            
            # Test read from status file
            self.mt5_status_file.read_text(encoding='utf-8')
            
            self.logger.debug("MT5 file validation successful")
            
        except Exception as e:
            self.logger.error(f"MT5 file validation failed: {e}")
            raise
    
    @contextmanager
    def automation_context(self):
        """Context manager for trading automation"""
        automation = None
        try:
            # Import with multiple fallbacks
            automation_class = self._import_trading_automation()
            if automation_class:
                automation = automation_class(
                    headless=self.config["automation"]["headless_mode"],
                    max_retries=self.config["trading"]["max_retries"]
                )
                yield automation
            else:
                self.logger.error("Could not import trading automation")
                yield None
        except Exception as e:
            self.logger.error(f"Error in automation context: {e}")
            yield None
        finally:
            if automation and hasattr(automation, 'cleanup_driver'):
                automation.cleanup_driver()
    
    def _import_trading_automation(self):
        """Import TradingView automation with multiple fallbacks"""
        import_attempts = [
            ('trading_bot', 'TradingViewAutomation'),
            ('Trading_bot', 'TradingViewAutomation'),
            ('tradingview_automation', 'TradingViewAutomation')
        ]
        
        for module_name, class_name in import_attempts:
            try:
                module = __import__(module_name, fromlist=[class_name])
                automation_class = getattr(module, class_name)
                self.logger.info(f"Successfully imported {module_name}.{class_name}")
                return automation_class
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Failed to import {module_name}.{class_name}: {e}")
                continue
        
        self.logger.error("All automation import attempts failed")
        return None
    
    def take_screenshots(self) -> Optional[Dict[str, str]]:
        """Take screenshots using automation with enhanced error handling"""
        self.logger.info("📸 Iniciando capturas automáticas...")
        
        try:
            with self.automation_context() as automation:
                if not automation:
                    self.logger.error("Automation not available")
                    return None
                
                screenshots = automation.capture_all_timeframes(
                    pairs=self.config["trading"]["pairs"]
                )
                
                if screenshots:
                    self.logger.info("✅ Capturas completadas:")
                    for tf, path in screenshots.items():
                        self.logger.info(f"  {tf}: {path}")
                    
                    # Validate screenshots if enabled
                    if self.config["automation"]["screenshot_validation"]:
                        screenshots = self._validate_screenshots(screenshots)
                    
                    return screenshots
                else:
                    self.logger.error("❌ Error en capturas automáticas")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Error tomando capturas: {e}")
            return None
    
    def _validate_screenshots(self, screenshots: Dict[str, str]) -> Dict[str, str]:
        """Validate screenshot files exist and have reasonable size"""
        validated = {}
        min_size = 50 * 1024  # 50KB minimum
        
        for key, filepath in screenshots.items():
            try:
                path = Path(filepath)
                if path.exists():
                    size = path.stat().st_size
                    if size >= min_size:
                        validated[key] = filepath
                        self.logger.debug(f"Screenshot validated: {key} ({size} bytes)")
                    else:
                        self.logger.warning(f"Screenshot too small: {key} ({size} bytes)")
                else:
                    self.logger.warning(f"Screenshot file not found: {filepath}")
            except Exception as e:
                self.logger.error(f"Error validating screenshot {key}: {e}")
        
        return validated
    
    def get_memory_for_analysis(self) -> str:
        """Get recent memory for AI analysis with enhanced formatting"""
        try:
            recent_lessons = self.memory.get_recent_lessons(limit=10, min_relevance=4)
            memory_text = self.memory.format_memory_for_ai(recent_lessons)
            
            # Add current trading context
            context_info = [
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Estado actual: {self.current_trade or 'Sin trades activos'}",
                f"Esperando setup: {'Sí' if self.waiting_for_setup else 'No'}"
            ]
            
            full_context = "\n".join(context_info) + "\n\n" + memory_text
            return full_context
            
        except Exception as e:
            self.logger.error(f"Error getting memory: {e}")
            return "MEMORIA: [Error cargando memoria]"
    
    def manual_analysis_prompt(self, screenshots: Dict[str, str], memory_text: str) -> str:
        """Enhanced manual analysis prompt with better UX"""
        print("\n" + "="*70)
        print("🤖 ANÁLISIS TRADING IA - MANUAL INPUT")
        print("="*70)
        
        print(f"\n📊 CAPTURAS DISPONIBLES ({len(screenshots)}):")
        if screenshots:
            for tf, path in screenshots.items():
                # Show file size for validation
                try:
                    size_kb = Path(path).stat().st_size / 1024
                    print(f"  ✅ {tf}: {Path(path).name} ({size_kb:.1f} KB)")
                except:
                    print(f"  ❌ {tf}: {path} (Error)")
        
        print(f"\n🧠 MEMORIA ACTIVA:")
        print(memory_text)
        
        print(f"\n📋 METODOLOGÍA DE ANÁLISIS:")
        print("1. 📊 H4: Estructura principal (HH/HL para bull, LH/LL para bear)")
        print("2. 📈 H1: Confirmación de break de estructura")
        print("3. ⏰ M15: Entry preciso en order block/zona de valor")
        print("4. 🧠 Consultar memoria para evitar errores previos")
        
        print(f"\n🎯 OPCIONES DE DECISIÓN:")
        print("1️⃣  WAIT - Esperar mejores condiciones")
        print("2️⃣  LONG - Entrada compradora")
        print("3️⃣  SHORT - Entrada vendedora") 
        print("4️⃣  CLOSE - Cerrar todas las posiciones")
        
        print(f"\n💡 RECORDATORIOS:")
        print("• No operar sin estructura clara en H4")
        print("• No comprar techos ni vender suelos sin retroceso")
        print("• Esperar confluencia entre timeframes")
        
        # Enhanced input validation with timeout
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                decision = input(f"\n🔥 TU DECISIÓN (1-4) [Intento {attempt + 1}/{max_attempts}]: ").strip()
                
                if decision in ['1', '2', '3', '4']:
                    decision_names = {'1': 'WAIT', '2': 'LONG', '3': 'SHORT', '4': 'CLOSE'}
                    print(f"✅ Decisión confirmada: {decision_names[decision]}")
                    return decision
                else:
                    print("❌ Por favor ingresa solo: 1 (WAIT), 2 (LONG), 3 (SHORT), o 4 (CLOSE)")
                    attempt += 1
                    
            except KeyboardInterrupt:
                print("\n🛑 Cancelado por usuario")
                return '1'  # Default to WAIT
            except Exception as e:
                self.logger.error(f"Error en input: {e}")
                attempt += 1
        
        print(f"❌ Máximo de intentos alcanzado. Defaulting a WAIT por seguridad.")
        return '1'
    
    def send_command_to_mt5(self, command: str) -> bool:
        """Send command to MT5 EA with enhanced error handling and validation"""
        try:
            # Validate command
            valid_commands = ['1', '2', '3', '4']
            if command not in valid_commands:
                self.logger.error(f"Invalid command: {command}")
                return False
            
            # Add timestamp to command for tracking
            timestamp = datetime.now().isoformat()
            command_with_timestamp = f"{command}|{timestamp}"
            
            # Write command atomically
            temp_file = self.mt5_commands_file.with_suffix('.tmp')
            temp_file.write_text(command_with_timestamp, encoding='utf-8')
            temp_file.replace(self.mt5_commands_file)
            
            command_names = {'1': 'WAIT', '2': 'LONG', '3': 'SHORT', '4': 'CLOSE'}
            self.logger.info(f"📤 Comando enviado a MT5: {command_names.get(command, command)}")
            
            # Wait briefly and verify command was written
            time.sleep(0.5)
            written_content = self.mt5_commands_file.read_text(encoding='utf-8')
            
            if command in written_content:
                return True
            else:
                self.logger.error("Command verification failed")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error enviando comando a MT5: {e}")
            return False
    
    def read_mt5_status(self) -> Dict[str, Any]:
        """Read current status from MT5 EA with enhanced parsing"""
        try:
            if not self.mt5_status_file.exists():
                return {'status': 'FILE_NOT_FOUND', 'message': 'Status file does not exist'}
            
            status_line = self.mt5_status_file.read_text(encoding='utf-8').strip()
            
            if not status_line:
                return {'status': 'EMPTY', 'message': 'Status file is empty'}
            
            # Enhanced parsing with better error handling
            parts = status_line.split('|')
            
            if len(parts) < 6:
                self.logger.warning(f"Invalid status format: {status_line}")
                return {'status': 'PARSE_ERROR', 'message': f'Invalid format: {status_line}'}
            
            try:
                status_data = {
                    'status': parts[0],
                    'ticket': int(parts[1]) if parts[1].isdigit() else 0,
                    'entry': self._safe_float_parse(parts[2]),
                    'sl': self._safe_float_parse(parts[3]),
                    'tp': self._safe_float_parse(parts[4]),
                    'timestamp': parts[5],
                    'message': parts[6] if len(parts) > 6 else "",
                    'raw_data': status_line
                }
                
                # Add derived information
                if status_data['status'] in ['LONG_ACTIVE', 'SHORT_ACTIVE']:
                    status_data['is_active'] = True
                    status_data['direction'] = 'LONG' if 'LONG' in status_data['status'] else 'SHORT'
                else:
                    status_data['is_active'] = False
                    status_data['direction'] = None
                
                return status_data
                
            except (ValueError, IndexError) as e:
                self.logger.error(f"Error parsing MT5 status: {e}")
                return {'status': 'PARSE_ERROR', 'message': f'Parse error: {e}', 'raw_data': status_line}
            
        except Exception as e:
            self.logger.error(f"❌ Error leyendo estado MT5: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def _safe_float_parse(self, value: str) -> float:
        """Safely parse float value"""
        try:
            if value and value != '0' and value != '':
                return float(value)
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def monitor_trade(self) -> bool:
        """Monitor active trade with enhanced status handling"""
        status = self.read_mt5_status()
        
        if status['status'] in ['TP_HIT', 'SL_HIT', 'CLOSED', 'MANUAL_CLOSE']:
            self.logger.info(f"\n🚨 TRADE CERRADO: {status['status']}")
            self.logger.info(f"📊 Detalles: {status['message']}")
            
            # Log trade summary
            if status.get('entry') and status.get('entry') > 0:
                self.logger.info(f"📈 Entrada: {status['entry']}")
                if status.get('sl'):
                    self.logger.info(f"🛑 SL: {status['sl']}")
                if status.get('tp'):
                    self.logger.info(f"🎯 TP: {status['tp']}")
            
            # Take post-trade screenshot for analysis
            self.logger.info("📸 Tomando captura post-trade...")
            post_screenshots = self.take_screenshots()
            
            if post_screenshots:
                # Generate post-trade lesson
                self.generate_post_trade_lesson(status, post_screenshots)
            else:
                self.logger.warning("No se pudieron tomar capturas post-trade")
            
            # Reset trade monitoring
            self.current_trade = None
            return True
        
        elif status['status'] in ['LONG_ACTIVE', 'SHORT_ACTIVE']:
            # Enhanced active trade monitoring
            direction = status.get('direction', 'UNKNOWN')
            entry = status.get('entry', 0)
            message = status.get('message', '')
            
            self.logger.info(f"📈 Trade activo: {direction} @ {entry} - {message}")
            return False
        
        elif status['status'] == 'ERROR':
            self.logger.error(f"Error en MT5: {status['message']}")
            return False
        
        return False
    
    def generate_post_trade_lesson(self, trade_result: Dict[str, Any], post_screenshots: Dict[str, str]):
        """Generate lesson from trade result with enhanced data collection"""
        self.logger.info("\n🧠 GENERANDO LECCIÓN POST-TRADE...")
        
        # Automatic lesson data extraction
        lesson_data = {
            'result_type': trade_result['status'],
            'entry_price': trade_result.get('entry', 0),
            'sl_price': trade_result.get('sl', 0),
            'tp_price': trade_result.get('tp', 0),
            'direction': trade_result.get('direction', 'UNKNOWN'),
            'timestamp': trade_result.get('timestamp', ''),
            'message': trade_result.get('message', '')
        }
        
        # Calculate pips if possible
        pips_result = "N/A"
        if lesson_data['entry_price'] > 0:
            if lesson_data['result_type'] == 'TP_HIT' and lesson_data['tp_price'] > 0:
                if lesson_data['direction'] == 'LONG':
                    pips = (lesson_data['tp_price'] - lesson_data['entry_price']) * 10000
                else:
                    pips = (lesson_data['entry_price'] - lesson_data['tp_price']) * 10000
                pips_result = f"+{pips:.1f} pips"
            elif lesson_data['result_type'] == 'SL_HIT' and lesson_data['sl_price'] > 0:
                if lesson_data['direction'] == 'LONG':
                    pips = (lesson_data['sl_price'] - lesson_data['entry_price']) * 10000
                else:
                    pips = (lesson_data['entry_price'] - lesson_data['sl_price']) * 10000
                pips_result = f"{pips:.1f} pips"
        
        print("📋 INFORMACIÓN AUTOMÁTICA:")
        print(f"Resultado: {lesson_data['result_type']}")
        print(f"Dirección: {lesson_data['direction']}")
        print(f"Entrada: {lesson_data['entry_price']}")
        print(f"Resultado en pips: {pips_result}")
        print("Capturas post-trade disponibles para análisis")
        
        print("\n🎯 ANÁLISIS REQUERIDO:")
        print("1. ¿Cómo se comportó el precio después de entrada?")
        print("2. ¿Fue movimiento gradual o brusco?")
        print("3. ¿Respetó las zonas como esperado?")
        print("4. ¿Qué se puede mejorar para el próximo trade?")
        
        try:
            # Manual input for lesson details
            lesson_context = input("\n📝 Contexto de la lección (ej: H4 bull + order block M15): ")
            lesson_rule = input("📋 Regla aprendida (ej: Order blocks funcionan en retrocesos): ")
            
            while True:
                try:
                    relevance = int(input("🎯 Relevancia (1-5): "))
                    if 1 <= relevance <= 5:
                        break
                    else:
                        print("Por favor ingresa un número entre 1 y 5")
                except ValueError:
                    print("Por favor ingresa un número válido")
            
            # Generate tags automatically
            auto_tags = []
            if lesson_data['direction']:
                auto_tags.append(lesson_data['direction'].lower())
            if 'TP_HIT' in lesson_data['result_type']:
                auto_tags.append('win')
            elif 'SL_HIT' in lesson_data['result_type']:
                auto_tags.append('loss')
            auto_tags.append('post_trade')
            
            # Add lesson to memory
            lesson_id = self.memory.add_lesson(
                pair="EURUSD",
                lesson_type="Post-Trade",
                context=lesson_context,
                rule=lesson_rule,
                result=pips_result,
                relevance=relevance,
                tags=auto_tags
            )
            
            self.logger.info(f"✅ Lección {lesson_id} guardada en memoria")
            
        except KeyboardInterrupt:
            self.logger.info("\n⏭️ Generación de lección omitida por usuario")
        except Exception as e:
            self.logger.error(f"Error generando lección: {e}")
    
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        try:
            now = datetime.now().time()
            start_time = dt_time.fromisoformat(self.config["trading"]["trading_hours"]["start"])
            end_time = dt_time.fromisoformat(self.config["trading"]["trading_hours"]["end"])
            
            return start_time <= now <= end_time
        except Exception as e:
            self.logger.error(f"Error checking trading hours: {e}")
            return False
    
    def daily_trading_session(self):
        """Enhanced daily trading session with comprehensive error handling"""
        session_start = datetime.now()
        self.logger.info(f"\n🚀 SESIÓN DE TRADING DIARIA - {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*60)
        
        try:
            # Pre-session checks
            if not self._pre_session_checks():
                self.logger.error("Pre-session checks failed, aborting session")
                return
            
            # Step 1: Take screenshots
            self.logger.info("Paso 1: Capturando screenshots...")
            screenshots = self.take_screenshots()
            
            if not screenshots:
                self.logger.error("❌ No se pudieron tomar capturas - cancelando sesión")
                return
            
            # Step 2: Get memory context
            self.logger.info("Paso 2: Cargando memoria...")
            memory_text = self.get_memory_for_analysis()
            
            # Step 3: Manual analysis
            self.logger.info("Paso 3: Análisis manual...")
            decision = self.manual_analysis_prompt(screenshots, memory_text)
            
            # Step 4: Process decision
            self.logger.info(f"Paso 4: Procesando decisión: {decision}")
            success = self._process_trading_decision(decision)
            
            # Session summary
            session_duration = (datetime.now() - session_start).total_seconds()
            self.logger.info(f"\n📊 RESUMEN DE SESIÓN:")
            self.logger.info(f"Duración: {session_duration:.1f} segundos")
            self.logger.info(f"Screenshots: {len(screenshots)}")
            self.logger.info(f"Decisión: {decision}")
            self.logger.info(f"Ejecución: {'✅ Exitosa' if success else '❌ Falló'}")
            
        except Exception as e:
            self.logger.error(f"Error en sesión de trading: {e}")
            self.logger.exception("Stack trace:")
    
    def _pre_session_checks(self) -> bool:
        """Perform pre-session system checks"""
        checks = [
            ("MT5 Files", self._check_mt5_files),
            ("Memory System", self._check_memory_system),
            ("Screenshot Directory", self._check_screenshot_directory)
        ]
        
        all_passed = True
        
        for check_name, check_func in checks:
            try:
                if check_func():
                    self.logger.info(f"✅ {check_name}: OK")
                else:
                    self.logger.error(f"❌ {check_name}: FAILED")
                    all_passed = False
            except Exception as e:
                self.logger.error(f"❌ {check_name}: ERROR - {e}")
                all_passed = False
        
        return all_passed
    
    def _check_mt5_files(self) -> bool:
        """Check MT5 communication files"""
        return (self.mt5_commands_file.exists() and 
                self.mt5_status_file.exists() and
                os.access(self.mt5_commands_file, os.W_OK))
    
    def _check_memory_system(self) -> bool:
        """Check memory system functionality"""
        try:
            test_lessons = self.memory.get_recent_lessons(limit=1)
            return True
        except:
            return False
    
    def _check_screenshot_directory(self) -> bool:
        """Check screenshot directory exists and is writable"""
        try:
            self.screenshots_dir.mkdir(exist_ok=True)
            return os.access(self.screenshots_dir, os.W_OK)
        except:
            return False
    
    def _process_trading_decision(self, decision: str) -> bool:
        """Process trading decision with enhanced validation"""
        decision_map = {
            '1': ('WAIT', 'Esperando mejores condiciones'),
            '2': ('LONG', 'Entrada compradora ejecutada'),
            '3': ('SHORT', 'Entrada vendedora ejecutada'),
            '4': ('CLOSE', 'Cerrando todas las posiciones')
        }
        
        if decision not in decision_map:
            self.logger.error(f"Decisión inválida: {decision}")
            return False
        
        action_name, success_message = decision_map[decision]
        
        if self.send_command_to_mt5(decision):
            if decision in ['2', '3']:
                self.current_trade = action_name
                self.logger.info(f"✅ {success_message}")
            elif decision == '1':
                self.logger.info(f"⏳ {success_message}")
            elif decision == '4':
                self.current_trade = None
                self.logger.info(f"🛑 {success_message}")
            return True
        else:
            self.logger.error(f"❌ Error enviando comando {action_name}")
            return False
    
    def monitoring_session(self):
        """Enhanced monitoring session with better logic"""
        # Only monitor during trading hours
        if not self.is_trading_hours():
            return
        
        # Skip if no active monitoring needed
        if not self.waiting_for_setup and not self.current_trade:
            return
        
        try:
            self.logger.info(f"\n👁️ MONITOREO - {datetime.now().strftime('%H:%M:%S')}")
            
            # Check if we have an active trade to monitor
            if self.current_trade:
                trade_closed = self.monitor_trade()
                if trade_closed:
                    self.logger.info("✅ Monitoreo de trade completado")
                    return
            
            # If waiting for setup, check for new opportunities
            if self.waiting_for_setup:
                self._monitor_for_setup()
                
        except Exception as e:
            self.logger.error(f"Error en sesión de monitoreo: {e}")
    
    def _monitor_for_setup(self):
        """Monitor for trading setup when waiting"""
        self.logger.info("📸 Tomando capturas de monitoreo...")
        screenshots = self.take_screenshots()
        
        if screenshots:
            memory_text = self.get_memory_for_analysis()
            decision = self.manual_analysis_prompt(screenshots, memory_text)
            
            success = self._process_trading_decision(decision)
            
            if decision in ['2', '3'] and success:
                self.waiting_for_setup = False
                self.logger.info("✅ Setup encontrado - Trade ejecutado")
            elif decision == '1':
                self.waiting_for_setup = False
                self.logger.info("⏳ Terminando monitoreo - Continuar esperando")
    
    def start_scheduler(self):
        """Start the enhanced automated scheduler"""
        self.logger.info("⏰ Iniciando scheduler de trading avanzado...")
        
        # Daily session
        daily_time = self.config["trading"]["daily_session_time"]
        schedule.every().day.at(daily_time).do(self.daily_trading_session)
        
        # Monitoring during trading hours
        monitor_interval = self.config["trading"]["monitoring_interval"]
        schedule.every(monitor_interval).minutes.do(self.monitoring_session)
        
        # System health check (every hour)
        schedule.every().hour.do(self._system_health_check)
        
        self.logger.info("📅 Sesiones programadas:")
        self.logger.info(f"  - Análisis principal: {daily_time}")
        self.logger.info(f"  - Monitoreo: cada {monitor_interval} minutos")
        self.logger.info(f"  - Horario activo: {self.config['trading']['trading_hours']['start']}-{self.config['trading']['trading_hours']['end']}")
        self.logger.info(f"  - Chequeo de salud: cada hora")
        
        # Test run
        if input("\n🧪 ¿Ejecutar sesión de prueba? (y/N): ").lower().strip() == 'y':
            self.daily_trading_session()
        
        self.logger.info("\n⏰ Scheduler activo - Presiona Ctrl+C para detener")
        self.is_running = True
        
        try:
            while self.is_running and not self.shutdown_requested:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        finally:
            self._graceful_shutdown()
    
    def _system_health_check(self):
        """Periodic system health check"""
        self.logger.info("🔍 Ejecutando chequeo de salud del sistema...")
        
        health_status = {
            'mt5_files': self._check_mt5_files(),
            'memory_system': self._check_memory_system(),
            'screenshot_dir': self._check_screenshot_directory()
        }
        
        issues = [k for k, v in health_status.items() if not v]
        
        if issues:
            self.logger.warning(f"⚠️ Problemas detectados: {', '.join(issues)}")
            # Attempt auto-repair
            self._attempt_auto_repair(issues)
        else:
            self.logger.info("✅ Sistema saludable")
    
    def _attempt_auto_repair(self, issues: List[str]):
        """Attempt to automatically repair system issues"""
        for issue in issues:
            try:
                if issue == 'mt5_files':
                    self.ensure_mt5_files_exist()
                    self.logger.info(f"🔧 Auto-reparación MT5 files: completada")
                elif issue == 'screenshot_dir':
                    self.screenshots_dir.mkdir(exist_ok=True)
                    self.logger.info(f"🔧 Auto-reparación screenshot directory: completada")
            except Exception as e:
                self.logger.error(f"🔧 Auto-reparación {issue} falló: {e}")
    
    def _graceful_shutdown(self):
        """Perform graceful shutdown"""
        self.logger.info("🛑 Iniciando apagado graceful del sistema...")
        
        self.is_running = False
        
        # Close any active trades if configured
        if self.current_trade and self.config.get("shutdown", {}).get("close_trades", False):
            self.logger.info("Cerrando trades activos antes del shutdown...")
            self.send_command_to_mt5('4')
        
        # Create final backup if enabled
        if self.config["automation"]["auto_backup"]:
            try:
                self.memory.export_to_csv()
                self.logger.info("✅ Backup final creado")
            except Exception as e:
                self.logger.error(f"Error creando backup final: {e}")
        
        self.logger.info("✅ Sistema apagado correctamente")

def main():
    """Enhanced main function with better error handling"""
    print("🤖 SISTEMA DE TRADING IA - VERSIÓN COMPLETA MEJORADA")
    print("="*60)
    
    try:
        system = SistemaTradingCompleto()
        system.start_scheduler()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n\n❌ Error crítico en sistema: {e}")
        logging.error(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()
