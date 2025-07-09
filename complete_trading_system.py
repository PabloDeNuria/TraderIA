#!/usr/bin/env python3
"""
Sistema Trading IA Completo
Integra: Capturas + Memoria + Análisis Manual + MT5 EA
"""

import time
import schedule
from datetime import datetime
import os
import sys

# Import our existing components
from local_memory_system import LocalTradingMemory

# Import TradingView automation (assuming it's the previous script)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SistemaTradingCompleto:
    def __init__(self):
        """Initialize complete trading system"""
        self.memory = LocalTradingMemory()
        self.screenshots_dir = "trading_screenshots"
        
        # Correct MT5 paths for Mac with Wine
        self.mt5_commands_file = "/Users/pablodenuria/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files/trading_commands.txt"
        self.mt5_status_file = "/Users/pablodenuria/Library/Application Support/net.metaquotes.wine.metatrader5/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files/trade_status.txt"
        
        self.current_trade = None
        self.waiting_for_setup = False
        
        print("Sistema de Trading IA inicializado")
        print(f"Comandos MT5: {self.mt5_commands_file}")
        print(f"Estado MT5: {self.mt5_status_file}")
        
        # Ensure MT5 files exist
        self.ensure_mt5_files_exist()
    
    def ensure_mt5_files_exist(self):
        """Ensure MT5 communication files exist"""
        # Create directories if they don't exist
        os.makedirs(os.path.dirname(self.mt5_commands_file), exist_ok=True)
        
        # Create empty files if they don't exist
        if not os.path.exists(self.mt5_commands_file):
            with open(self.mt5_commands_file, 'w') as f:
                f.write("")
        
        if not os.path.exists(self.mt5_status_file):
            with open(self.mt5_status_file, 'w') as f:
                f.write("WAITING|0|0|0|0|System starting")
    
    def take_screenshots(self):
        """Take H4, H1, M15 screenshots using existing automation"""
        print("📸 Tomando capturas automáticas...")
        
        try:
            # Import and use existing TradingView automation
            import sys
            import os
            
            # Add current directory to path
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            
            # Try importing the TradingView script with different names
            try:
                from trading_bot import TradingViewAutomation
            except ImportError:
                try:
                    from Trading_bot import TradingViewAutomation
                except ImportError:
                    try:
                        from tradingview_automation import TradingViewAutomation
                    except ImportError:
                        # Last resort: execute script directly
                        import subprocess
                        import glob
                        
                        # Find the trading bot script
                        possible_names = ['trading_bot.py', 'Trading_bot.py', 'tradingview_automation.py']
                        script_path = None
                        
                        for name in possible_names:
                            if os.path.exists(name):
                                script_path = name
                                break
                        
                        if script_path:
                            print(f"Ejecutando {script_path}...")
                            result = subprocess.run([sys.executable, script_path],
                                                  capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                # Find the screenshots
                                today = datetime.now().strftime("%Y-%m-%d")
                                screenshots_dir = os.path.join("trading_screenshots", today)
                                
                                if os.path.exists(screenshots_dir):
                                    screenshots = {}
                                    for filename in os.listdir(screenshots_dir):
                                        if "H4" in filename:
                                            screenshots["H4"] = os.path.join(screenshots_dir, filename)
                                        elif "H1" in filename:
                                            screenshots["H1"] = os.path.join(screenshots_dir, filename)
                                        elif "M15" in filename:
                                            screenshots["M15"] = os.path.join(screenshots_dir, filename)
                                    
                                    if len(screenshots) == 3:
                                        print("✅ Capturas completadas:")
                                        for tf, path in screenshots.items():
                                            print(f"  {tf}: {path}")
                                        return screenshots
                            
                            print(f"Error ejecutando {script_path}: {result.stderr}")
                        
                        print("❌ No se encontró script de capturas")
                        return None
            
            automation = TradingViewAutomation()
            screenshots = automation.capture_all_timeframes()
            
            if screenshots:
                print("✅ Capturas completadas:")
                for tf, path in screenshots.items():
                    print(f"  {tf}: {path}")
                return screenshots
            else:
                print("❌ Error en capturas automáticas")
                return None
                
        except Exception as e:
            print(f"❌ Error tomando capturas: {e}")
            return None
    
    def get_memory_for_analysis(self):
        """Get recent memory for AI analysis"""
        recent_lessons = self.memory.get_recent_lessons(limit=10, min_relevance=4)
        memory_text = self.memory.format_memory_for_ai(recent_lessons)
        return memory_text
    
    def manual_analysis_prompt(self, screenshots, memory_text):
        """Display analysis prompt for manual input"""
        print("\n" + "="*60)
        print("🤖 ANÁLISIS TRADING IA - MANUAL INPUT")
        print("="*60)
        
        print(f"\n📊 CAPTURAS DISPONIBLES:")
        if screenshots:
            for tf, path in screenshots.items():
                print(f"  {tf}: {path}")
        
        print(f"\n🧠 MEMORIA ACTIVA:")
        print(memory_text)
        
        print(f"\n📋 INSTRUCCIONES:")
        print("1. Analiza las capturas con metodología ICT/SMC")
        print("2. Consulta la memoria para evitar errores previos")
        print("3. Decide: ENTRADA específica o WAIT")
        
        print(f"\n🎯 FORMATOS DE RESPUESTA:")
        print("ENTRADA LONG: 2")
        print("ENTRADA SHORT: 3")
        print("ESPERAR: 1")
        print("CERRAR TRADES: 4")
        
        decision = input("\n🔥 TU DECISIÓN (1-4): ").strip()
        return decision
    
    def send_command_to_mt5(self, command):
        """Send command to MT5 EA using direct file write"""
        try:
            # Simple UTF-8 write without encoding issues
            with open(self.mt5_commands_file, 'w', encoding='utf-8', newline='') as f:
                f.write(str(command))
            print(f"📤 Comando enviado a MT5: {command}")
            return True
        except Exception as e:
            print(f"❌ Error enviando comando a MT5: {e}")
            return False
    
    def read_mt5_status(self):
        """Read current status from MT5 EA"""
        try:
            if os.path.exists(self.mt5_status_file):
                with open(self.mt5_status_file, 'r') as f:
                    status_line = f.read().strip()
                
                if status_line:
                    # Parse: STATUS|TICKET|ENTRY|SL|TP|TIMESTAMP|MESSAGE
                    parts = status_line.split('|')
                    if len(parts) >= 6:
                        return {
                            'status': parts[0],
                            'ticket': int(parts[1]) if parts[1].isdigit() else 0,
                            'entry': float(parts[2]) if parts[2] else 0,
                            'sl': float(parts[3]) if parts[3] else 0,
                            'tp': float(parts[4]) if parts[4] else 0,
                            'timestamp': parts[5],
                            'message': parts[6] if len(parts) > 6 else ""
                        }
            
            return {'status': 'UNKNOWN', 'message': 'No status available'}
            
        except Exception as e:
            print(f"❌ Error leyendo estado MT5: {e}")
            return {'status': 'ERROR', 'message': str(e)}
    
    def monitor_trade(self):
        """Monitor active trade and handle TP/SL hits"""
        status = self.read_mt5_status()
        
        if status['status'] in ['TP_HIT', 'SL_HIT', 'CLOSED']:
            print(f"\n🚨 TRADE CERRADO: {status['status']}")
            print(f"📊 Detalles: {status['message']}")
            
            # Take post-trade screenshot for analysis
            print("📸 Tomando captura post-trade...")
            post_screenshots = self.take_screenshots()
            
            if post_screenshots:
                # Generate post-trade lesson
                self.generate_post_trade_lesson(status, post_screenshots)
            
            # Reset trade monitoring
            self.current_trade = None
            return True
        
        elif status['status'] in ['LONG_ACTIVE', 'SHORT_ACTIVE']:
            print(f"📈 Trade activo: {status['status']} - {status['message']}")
            return False
        
        return False
    
    def generate_post_trade_lesson(self, trade_result, post_screenshots):
        """Generate lesson from trade result"""
        print("\n🧠 GENERANDO LECCIÓN POST-TRADE...")
        
        # Manual lesson generation for now
        print("📋 INFORMACIÓN PARA LECCIÓN:")
        print(f"Resultado: {trade_result['status']}")
        print(f"Detalles: {trade_result['message']}")
        print("Capturas post-trade disponibles para análisis")
        
        print("\n🎯 ANÁLISIS REQUERIDO:")
        print("1. ¿Cómo se comportó el precio después de entrada?")
        print("2. ¿Fue movimiento gradual o brusco?")
        print("3. ¿Respetó las zonas como esperado?")
        print("4. ¿Qué se puede mejorar?")
        
        lesson_context = input("\nContexto de la lección: ")
        lesson_rule = input("Regla aprendida: ")
        relevance = int(input("Relevancia (1-5): "))
        
        # Add lesson to memory
        lesson_id = self.memory.add_lesson(
            pair="EURUSD",
            lesson_type="Post-Trade",
            context=lesson_context,
            rule=lesson_rule,
            result=trade_result['status'],
            relevance=relevance
        )
        
        print(f"✅ Lección {lesson_id} guardada en memoria")
    
    def daily_trading_session(self):
        """Main daily trading session at 13:00 UTC+8"""
        print(f"\n🚀 SESIÓN DE TRADING - {datetime.now()}")
        print("="*50)
        
        # Ensure MT5 communication files exist
        self.ensure_mt5_files_exist()
        
        # Step 1: Take screenshots
        screenshots = self.take_screenshots()
        if not screenshots:
            print("❌ No se pudieron tomar capturas - cancelando sesión")
            return
        
        # Step 2: Get memory
        memory_text = self.get_memory_for_analysis()
        
        # Step 3: Manual analysis (until API is ready)
        decision = self.manual_analysis_prompt(screenshots, memory_text)
        
        # Step 4: Process decision
        if decision == '2':  # LONG
            if self.send_command_to_mt5('2'):
                self.current_trade = 'LONG'
                print("✅ Comando LONG enviado")
            else:
                print("❌ Error enviando comando")
        
        elif decision == '3':  # SHORT
            if self.send_command_to_mt5('3'):
                self.current_trade = 'SHORT'
                print("✅ Comando SHORT enviado")
            else:
                print("❌ Error enviando comando")
        
        elif decision == '1':  # WAIT
            self.send_command_to_mt5('1')
            print("⏳ Esperando mejores condiciones")
        
        elif decision == '4':  # CLOSE
            self.send_command_to_mt5('4')
            print("🛑 Cerrando todas las posiciones")
            self.current_trade = None
        
        else:
            print("❌ Decisión no válida (usa 1, 2, 3 o 4)")
    
    def monitoring_session(self):
        """Periodic monitoring session"""
        if not self.waiting_for_setup and not self.current_trade:
            return
        
        print(f"\n👁️ MONITOREO - {datetime.now().strftime('%H:%M:%S')}")
        
        # Check if we have an active trade to monitor
        if self.current_trade:
            trade_closed = self.monitor_trade()
            if trade_closed:
                print("✅ Monitoreo de trade completado")
                return
        
        # If waiting for setup, take new screenshots and analyze
        if self.waiting_for_setup:
            print("📸 Tomando capturas de monitoreo...")
            screenshots = self.take_screenshots()
            
            if screenshots:
                memory_text = self.get_memory_for_analysis()
                decision = self.manual_analysis_prompt(screenshots, memory_text)
                
                if decision.startswith('LONG') or decision.startswith('SHORT'):
                    if self.send_command_to_mt5(decision):
                        self.current_trade = decision
                        self.waiting_for_setup = False
                        print("✅ Setup encontrado - Trade ejecutado")
                elif decision == 'WAIT':
                    self.waiting_for_setup = False
                    print("⏳ Terminando monitoreo - WAIT")
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        print("⏰ Iniciando scheduler de trading...")
        
        # Daily session at 13:00 UTC+8
        schedule.every().day.at("13:00").do(self.daily_trading_session)
        
        # Monitoring every 15 minutes during trading hours (14:00-17:00 UTC+8)
        schedule.every(15).minutes.do(self.monitoring_session)
        
        print("📅 Sesiones programadas:")
        print("  - Análisis principal: 13:00 UTC+8")
        print("  - Monitoreo: cada 15 minutos")
        print("  - Horario activo: 14:00-17:00 UTC+8")
        
        # For testing - run immediately
        print("\n🧪 EJECUTANDO SESIÓN DE PRUEBA...")
        self.daily_trading_session()
        
        print("\n⏰ Scheduler activo - Presiona Ctrl+C para detener")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    """Main function"""
    print("🤖 SISTEMA DE TRADING IA - VERSIÓN COMPLETA")
    print("="*50)
    
    try:
        system = SistemaTradingCompleto()
        system.start_scheduler()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n\n❌ Error en sistema: {e}")

if __name__ == "__main__":
    main()
