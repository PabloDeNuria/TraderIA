#!/usr/bin/env python3
"""
Claude Trader - Integración API de Anthropic para Trading Automático
Conecta el sistema de trading con Claude API para análisis automático
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

try:
    import anthropic
except ImportError:
    print("❌ Error: pip3 install anthropic")
    exit(1)

class ClaudeTrader:
    def __init__(self, api_key: str = None):
        """Initialize Claude Trader with API key"""
        self.api_key = api_key or "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"
        
        # Initialize Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Setup logging
        self.logger = logging.getLogger("ClaudeTrader")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Claude API"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
        except Exception as e:
            self.logger.error(f"❌ Error encoding image {image_path}: {e}")
            return None
    
    def create_trading_prompt(self, memory_context: str) -> str:
        """Create comprehensive trading prompt for Claude"""
        return f"""Eres un trader profesional experto analizando el mercado EURUSD. 

ANÁLISIS REQUERIDO:
Analiza las 3 capturas de pantalla proporcionadas (H4, H1, M15) siguiendo esta metodología:

1. H4 (4 horas): Identifica la estructura principal
   - ¿Hay tendencia bullish (HH/HL) o bearish (LH/LL)?
   - ¿Está lateral sin dirección clara?
   - ¿Hay niveles de soporte/resistencia importantes?

2. H1 (1 hora): Confirmación de estructura
   - ¿Hay break de estructura que confirme la dirección?
   - ¿Respeta los niveles del H4?
   - ¿Hay momentum claro?

3. M15 (15 minutos): Timing de entrada
   - ¿Hay order blocks o zonas de valor?
   - ¿Es buen momento para entrar o esperar retroceso?
   - ¿Hay confluencia con niveles superiores?

MEMORIA DE LECCIONES APRENDIDAS:
{memory_context}

REGLAS ESTRICTAS:
- NO operar sin estructura clara en H4
- NO comprar techos ni vender suelos sin retroceso
- Esperar confluencia entre timeframes
- Respetar niveles históricos de soporte/resistencia

DECISIONES DISPONIBLES:
1 = WAIT (Esperar mejores condiciones)
2 = LONG (Entrada compradora)
3 = SHORT (Entrada vendedora)
4 = CLOSE (Cerrar posiciones)

FORMATO DE RESPUESTA REQUERIDO:
Responde EXACTAMENTE en este formato JSON:
{{
    "decision": "X",
    "reasoning": "Explica tu análisis detallado aquí",
    "confidence": X,
    "h4_analysis": "Tu análisis del H4",
    "h1_analysis": "Tu análisis del H1", 
    "m15_analysis": "Tu análisis del M15",
    "risk_assessment": "Evaluación de riesgo"
}}

Donde:
- decision: Solo el número 1, 2, 3 o 4
- confidence: Nivel de confianza del 1-10
- reasoning: Explicación completa de tu decisión

IMPORTANTE: Responde SOLO con el JSON, sin texto adicional."""

    def analyze_market(self, screenshots: Dict[str, str], memory_context: str) -> Dict[str, Any]:
        """Send analysis request to Claude API"""
        try:
            self.logger.info("🤖 Sending analysis to Claude API...")
            
            # Prepare images for Claude
            images = []
            timeframe_order = ["H4", "H1", "M15"]
            
            for tf in timeframe_order:
                if tf in screenshots:
                    image_path = screenshots[tf]
                    encoded_image = self.encode_image(image_path)
                    
                    if encoded_image:
                        images.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": encoded_image
                            }
                        })
                        self.logger.info(f"📸 Added {tf} screenshot to analysis")
                    else:
                        self.logger.error(f"❌ Failed to encode {tf} screenshot")
            
            if not images:
                self.logger.error("❌ No valid screenshots for analysis")
                return self._fallback_decision("No screenshots available")
            
            # Create prompt
            trading_prompt = self.create_trading_prompt(memory_context)
            
            # Prepare message content
            message_content = []
            
            # Add all images first
            message_content.extend(images)
            
            # Add text prompt
            message_content.append({
                "type": "text",
                "text": trading_prompt
            })
            
            # Send to Claude API
            self.logger.info(f"📤 Sending request to Claude with {len(images)} images...")
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.1,  # Low temperature for consistent trading decisions
                messages=[{
                    "role": "user",
                    "content": message_content
                }]
            )
            
            # Parse response
            response_text = response.content[0].text.strip()
            self.logger.info("✅ Received response from Claude")
            
            # Try to parse JSON response
            try:
                # Clean response if it has markdown formatting
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].strip()
                
                decision_data = json.loads(response_text)
                
                # Validate decision format
                if not self._validate_decision(decision_data):
                    return self._fallback_decision("Invalid decision format from Claude")
                
                self.logger.info(f"🎯 Claude decision: {decision_data.get('decision')} (confidence: {decision_data.get('confidence', 0)}/10)")
                return decision_data
                
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ JSON parse error: {e}")
                self.logger.error(f"Raw response: {response_text}")
                return self._fallback_decision("Invalid JSON response from Claude")
                
        except Exception as e:
            self.logger.error(f"❌ Claude API error: {e}")
            return self._fallback_decision(f"API error: {str(e)}")
    
    def _validate_decision(self, decision_data: Dict) -> bool:
        """Validate Claude's decision format"""
        required_fields = ["decision", "reasoning", "confidence"]
        
        for field in required_fields:
            if field not in decision_data:
                self.logger.error(f"❌ Missing field: {field}")
                return False
        
        # Validate decision value
        if decision_data["decision"] not in ["1", "2", "3", "4"]:
            self.logger.error(f"❌ Invalid decision: {decision_data['decision']}")
            return False
        
        # Validate confidence
        try:
            confidence = int(decision_data["confidence"])
            if not 1 <= confidence <= 10:
                self.logger.error(f"❌ Invalid confidence: {confidence}")
                return False
        except (ValueError, TypeError):
            self.logger.error("❌ Invalid confidence format")
            return False
        
        return True
    
    def _fallback_decision(self, reason: str) -> Dict[str, Any]:
        """Generate fallback WAIT decision"""
        return {
            "decision": "1",
            "reasoning": f"FALLBACK: {reason} - Defaulting to WAIT for safety",
            "confidence": 1,
            "h4_analysis": "Error in analysis",
            "h1_analysis": "Error in analysis", 
            "m15_analysis": "Error in analysis",
            "risk_assessment": "High risk due to analysis failure",
            "source": "fallback"
        }
    
    def save_analysis_log(self, screenshots: Dict[str, str], decision_data: Dict[str, Any]):
        """Save analysis log for review"""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "screenshots": screenshots,
                "claude_analysis": decision_data,
                "api_usage": {
                    "model": "claude-3-5-sonnet-20241022",
                    "tokens_estimated": len(str(decision_data)) * 4  # Rough estimate
                }
            }
            
            log_file = Path("claude_trading_log.json")
            
            # Load existing logs
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new log
            logs.append(log_data)
            
            # Keep only last 100 analyses
            logs = logs[-100:]
            
            # Save updated logs
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📝 Analysis log saved ({len(logs)} total)")
            
        except Exception as e:
            self.logger.error(f"❌ Error saving analysis log: {e}")

def test_claude_connection():
    """Test Claude API connection"""
    trader = ClaudeTrader()
    
    try:
        # Simple test message
        response = trader.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": "Respond with exactly: 'Claude API connection successful'"
            }]
        )
        
        result = response.content[0].text.strip()
        print(f"✅ API Test Result: {result}")
        return True
        
    except Exception as e:
        print(f"❌ API Test Failed: {e}")
        return False

if __name__ == "__main__":
    print("🤖 Claude Trader API Integration")
    print("=" * 40)
    
    # Test API connection
    if test_claude_connection():
        print("✅ Claude API ready for trading!")
    else:
        print("❌ Claude API connection failed!")
        print("Check your API key and internet connection.")
