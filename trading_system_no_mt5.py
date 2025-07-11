#!/usr/bin/env python3
"""
Sistema Trading IA - VERSIÓN SIN MT5
Solo análisis y memoria, sin comunicación MT5 hasta resolver encoding
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
from contextlib import contextmanager

# Import our enhanced components
try:
    from local_memory_system import LocalTradingMemory
except ImportError:
    print("❌ Error: local_memory_system.py no encontrado")
    sys.exit(1)

class SistemaTradingSinMT5:
    def __init__(self, config_file: str = "trading_system_config.json"):
        """Initialize trading system without MT5 communication"""
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.memory = LocalTradingMemory()
        self.screenshots_dir = Path(self.config["directories"]["screenshots"])
        
        # Trading state
        self.current_trade = None
        self.waiting_for_setup = False
        self.is_running = False
        self.shutdown_requested = False
        
        # Track decisions for logging
        self.decisions_log = []
        
        self.logger.info("Sistema de Trading IA inicializado (SIN MT5)")
        self.logger.info("🚫 MT5 communication disabled - Analysis only mode")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        default_config = {
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
                
                self._merge_config(default_config, loaded_config)
                return default_config
            else:
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
        """Setup logging system"""
        log_dir = Path(self.config["directories"]["logs"])
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("TradingSystemNoMT5")
        self.logger.setLevel(getattr(logging, self.config["notifications"]["log_level"]))
        
        self.logger.handlers.clear()
        
        if self.config["notifications"]["file_logging"]:
            log_file = log_dir / f"trading_system_no_mt5_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
        if self.config["notifications"]["console_logging"]:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        if self.config["notifications"]["file_logging"]:
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        if self.config["notifications"]["console_logging"]:
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
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
                self.logger.error("Could not import trading automation")
                yield None
        except Exception as e:
            self.logger.error(f"Error in automation context: {e}")
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
                automation_class = getattr(module, class_name)
                self.logger.info(f"Successfully imported {module_name}.{class_name}")
                return automation_class
            except (ImportError, AttributeError) as e:
                self.logger.debug(f"Failed to import {module_name}.{class_name}: {e}")
                continue
        
        self.logger.error("All automation import attempts failed")
        return None
    
    def take_screenshots(self) -> Optional[Dict[str, str]]:
        """Take screenshots using automation"""
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
                    return screenshots
                else:
                    self.logger.error("❌ Error en capturas automáticas")
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ Error tomando capturas: {e}")
            return None
    
    def get_memory_for_analysis(self) -> str:
        """Get recent memory for AI analysis"""
        try:
            recent_lessons = self.memory.get_recent_lessons(limit=10, min_relevance=4)
            memory_text = self.memory.format_memory_for_ai(recent_lessons)
            
            context_info = [
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                f"Estado actual: {self.current_trade or 'Sin trades activos'}",
                f"Modo: ANÁLISIS SOLAMENTE (Sin MT5)"
            ]
            
            full_context = "\n".join(context_info) + "\n\n" + memory_text
            return full_context
            
        except Exception as e:
            self.logger.error(f"Error getting memory: {e}")
            return "MEMORIA: [Error cargando memoria]"
    
    def manual_analysis_prompt(self, screenshots: Dict[str, str], memory_text: str) -> str:
        """Enhanced manual analysis prompt"""
        print("\n" + "="*70)
        print("🤖 ANÁLISIS TRADING IA - MODO SIN MT5")
        print("="*70)
        
        print(f"\n📊 CAPTURAS DISPONIBLES ({len(screenshots)}):")
        if screenshots:
            for tf, path in screenshots.items():
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
        
        print(f"\n🚫 NOTA: Modo análisis solamente - No se enviarán comandos a MT5")
        
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
                return '1'
            except Exception as e:
                self.logger.error(f"Error en input: {e}")
                attempt += 1
        
        print(f"❌ Máximo de intentos alcanzado. Defaulting a WAIT por seguridad.")
        return '1'
    
    def log_trading_decision(self, decision: str) -> bool:
        """Log trading decision instead of sending to MT5"""
        try:
            decision_map = {
                '1': 'WAIT',
                '2': 'LONG', 
                '3': 'SHORT',
                '4': 'CLOSE'
            }
            
            if decision not in decision_map:
                self.logger.error(f"Decisión inválida: {decision}")
                return False
            
            action_name = decision_map[decision]
            timestamp = datetime.now().isoformat()
            
            # Log decision
            decision_entry = {
                'timestamp': timestamp,
                'decision': action_name,
                'decision_code': decision
            }
            
            self.decisions_log.append(decision_entry)
            
            # Save to file
            decisions_file = Path("trading_decisions_log.json")
            try:
                if decisions_file.exists():
                    with open(decisions_file, 'r') as f:
                        all_decisions = json.load(f)
                else:
                    all_decisions = []
                
                all_decisions.append(decision_entry)
                
                with open(decisions_file, 'w') as f:
                    json.dump(all_decisions, f, indent=2)
                    
            except Exception as e:
                self.logger.error(f"Error saving decision log: {e}")
            
            if decision in ['2', '3']:
                self.current_trade = action_name
                self.logger.info(f"📝 DECISIÓN REGISTRADA: {action_name}")
                print(f"🎯 Tu decisión de {action_name} ha sido registrada")
                print("💡 En modo real, esto sería enviado a MT5")
            elif decision == '1':
                self.logger.info(f"⏳ DECISIÓN: Esperando mejores condiciones")
                print("⏳ Esperando mejores condiciones - Registrado")
            elif decision == '4':
                self.current_trade = None
                self.logger.info(f"🛑 DECISIÓN: Cerrar posiciones")
                print("🛑 Decisión de cerrar posiciones - Registrada")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error registrando decisión: {e}")
            return False
    
    def daily_trading_session(self):
        """Daily trading session without MT5"""
        session_start = datetime.now()
        self.logger.info(f"\n🚀 SESIÓN DE TRADING DIARIA (SIN MT5) - {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*60)
        
        try:
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
            
            # Step 4: Log decision (instead of sending to MT5)
            self.logger.info(f"Paso 4: Registrando decisión: {decision}")
            success = self.log_trading_decision(decision)
            
            # Session summary
            session_duration = (datetime.now() - session_start).total_seconds()
            self.logger.info(f"\n📊 RESUMEN DE SESIÓN:")
            self.logger.info(f"Duración: {session_duration:.1f} segundos")
            self.logger.info(f"Screenshots: {len(screenshots)}")
            self.logger.info(f"Decisión: {decision}")
            self.logger.info(f"Registro: {'✅ Exitoso' if success else '❌ Falló'}")
            
            print(f"\n✅ Sesión completada - Decisión registrada en trading_decisions_log.json")
            
        except Exception as e:
            self.logger.error(f"Error en sesión de trading: {e}")
            self.logger.exception("Stack trace:")
    
    def start_scheduler(self):
        """Start the scheduler"""
        self.logger.info("⏰ Iniciando scheduler de trading (SIN MT5)...")
        
        daily_time = self.config["trading"]["daily_session_time"]
        schedule.every().day.at(daily_time).do(self.daily_trading_session)
        
        self.logger.info("📅 Sesiones programadas:")
        self.logger.info(f"  - Análisis principal: {daily_time}")
        self.logger.info(f"  - Modo: ANÁLISIS SOLAMENTE")
        
        # Test run
        if input("\n🧪 ¿Ejecutar sesión de prueba? (y/N): ").lower().strip() == 'y':
            self.daily_trading_session()
        
        self.logger.info("\n⏰ Scheduler activo - Presiona Ctrl+C para detener")
        self.is_running = True
        
        try:
            while self.is_running and not self.shutdown_requested:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received")
        finally:
            self._graceful_shutdown()
    
    def _graceful_shutdown(self):
        """Perform graceful shutdown"""
        self.logger.info("🛑 Iniciando apagado graceful del sistema...")
        self.is_running = False
        
        if self.config["automation"]["auto_backup"]:
            try:
                self.memory.export_to_csv()
                self.logger.info("✅ Backup final creado")
            except Exception as e:
                self.logger.error(f"Error creando backup final: {e}")
        
        self.logger.info("✅ Sistema apagado correctamente")

def main():
    """Main function"""
    print("🤖 SISTEMA DE TRADING IA - MODO SIN MT5")
    print("="*60)
    print("🚫 MT5 communication disabled")
    print("📝 Decisions will be logged to file")
    print("="*60)
    
    try:
        system = SistemaTradingSinMT5()
        system.start_scheduler()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n\n❌ Error crítico en sistema: {e}")
        logging.error(f"Fatal error in main: {e}", exc_info=True)

if __name__ == "__main__":
    main()
