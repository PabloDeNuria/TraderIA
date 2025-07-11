#!/usr/bin/env python3
"""
Local Memory System for Trading AI - VERSIÓN MEJORADA
Manages lessons in local JSON file with enhanced error handling and features
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import shutil

class LocalTradingMemory:
    def __init__(self, memory_file: str = "trading_memory.json", backup_enabled: bool = True):
        """Initialize local memory system with enhanced features"""
        self.memory_file = memory_file
        self.backup_enabled = backup_enabled
        
        # ✅ IMPROVED: Flexible storage location
        self.memory_path = self._get_memory_path()
        self.backup_dir = self.memory_path.parent / "backups"
        
        # Setup logging
        self._setup_logging()
        
        # Initialize memory
        self.ensure_memory_file()
        
        # Create backup if enabled
        if self.backup_enabled:
            self._create_backup()
    
    def _get_memory_path(self) -> Path:
        """Get appropriate memory file path based on environment"""
        # Try current directory first, then Desktop as fallback
        current_dir = Path.cwd() / self.memory_file
        desktop_dir = Path.home() / "Desktop" / self.memory_file
        
        # If file exists in current directory, use it
        if current_dir.exists():
            return current_dir
        
        # If current directory is writable, use it
        try:
            test_file = Path.cwd() / ".test_write"
            test_file.touch()
            test_file.unlink()
            return current_dir
        except (PermissionError, OSError):
            self.logger.warning("Current directory not writable, using Desktop")
            return desktop_dir
    
    def _setup_logging(self):
        """Setup logging for memory operations"""
        self.logger = logging.getLogger("TradingMemory")
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _create_backup(self):
        """Create automatic backup of memory file"""
        if not self.memory_path.exists():
            return
        
        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"trading_memory_backup_{timestamp}.json"
            
            shutil.copy2(self.memory_path, backup_file)
            
            # Keep only last 10 backups
            self._cleanup_old_backups()
            
            self.logger.info(f"Backup created: {backup_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Keep only the most recent backups"""
        try:
            backup_files = list(self.backup_dir.glob("trading_memory_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove old backups
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                self.logger.info(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup backups: {e}")
    
    def ensure_memory_file(self):
        """Create memory file if it doesn't exist with improved initial data"""
        if not self.memory_path.exists():
            # ✅ IMPROVED: Better initial lessons with timestamps
            initial_lessons = [
                {
                    "id": "L001",
                    "date": "2024-12-15",
                    "pair": "EURUSD",
                    "type": "Estructura",
                    "context": "H4 lateral sin dirección clara, sin HH/HL definidos",
                    "rule": "No operar si H4 no muestra estructura cristalina - evitar rangos",
                    "result": "WAIT",
                    "relevance": 5,
                    "tags": ["estructura", "h4", "lateral"]
                },
                {
                    "id": "L002", 
                    "date": "2024-12-16",
                    "pair": "EURUSD",
                    "type": "Timing",
                    "context": "Estructura bullish OK pero precio en resistencia histórica",
                    "rule": "No comprar techos sin zona de demanda clara - esperar retroceso",
                    "result": "WAIT",
                    "relevance": 4,
                    "tags": ["timing", "resistencia", "entry"]
                },
                {
                    "id": "L003",
                    "date": "2024-12-17",
                    "pair": "EURUSD",
                    "type": "Setup Completo",
                    "context": "H4 bullish + H1 break estructura + M15 order block",
                    "rule": "Cascada completa = alta probabilidad de éxito",
                    "result": "+22 pips",
                    "relevance": 5,
                    "tags": ["cascada", "order_block", "win"]
                },
                {
                    "id": "L004",
                    "date": "2024-12-18",
                    "pair": "EURUSD",
                    "type": "Risk Management",
                    "context": "Trade ganador, movió SL a BE prematuramente",
                    "rule": "Dejar correr winners - SL a BE solo después de 1:1 RR",
                    "result": "BE (podría haber sido +30)",
                    "relevance": 4,
                    "tags": ["risk_management", "sl", "be"]
                },
                {
                    "id": "L005",
                    "date": "2024-12-19",
                    "pair": "EURUSD",
                    "type": "Zona Rota",
                    "context": "Order block identificado pero precio lo rompió violentamente",
                    "rule": "No forzar trades cuando zona falla - respetar el mercado",
                    "result": "WAIT",
                    "relevance": 5,
                    "tags": ["order_block", "zona_rota", "discipline"]
                },
                {
                    "id": "L006",
                    "date": "2024-12-20",
                    "pair": "EURUSD",
                    "type": "Sistema",
                    "context": "Memoria evitó repetir error de timing en resistencia",
                    "rule": "Sistema de memoria funciona para evitar errores recurrentes",
                    "result": "No Loss",
                    "relevance": 5,
                    "tags": ["memoria", "sistema", "avoided_loss"]
                }
            ]
            
            initial_data = {
                "lessons": initial_lessons,
                "last_lesson_id": 6,
                "metadata": {
                    "created": datetime.now().isoformat(),
                    "version": "2.0",
                    "total_lessons": len(initial_lessons)
                }
            }
            
            self.save_memory(initial_data)
            self.logger.info(f"Memory file created: {self.memory_path}")
    
    def load_memory(self) -> Dict[str, Any]:
        """Load memory from JSON file with enhanced error handling"""
        try:
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # ✅ IMPROVED: Validate data structure
            if not isinstance(data, dict):
                raise ValueError("Invalid memory format: not a dictionary")
            
            if "lessons" not in data:
                data["lessons"] = []
            
            if "last_lesson_id" not in data:
                data["last_lesson_id"] = 0
                
            # Add metadata if missing
            if "metadata" not in data:
                data["metadata"] = {
                    "created": datetime.now().isoformat(),
                    "version": "2.0",
                    "total_lessons": len(data["lessons"])
                }
            
            return data
            
        except FileNotFoundError:
            self.logger.warning("Memory file not found, creating new one")
            self.ensure_memory_file()
            return self.load_memory()
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in memory file: {e}")
            # Try to restore from backup
            return self._restore_from_backup()
        
        except Exception as e:
            self.logger.error(f"Error loading memory: {e}")
            return {"lessons": [], "last_lesson_id": 0, "metadata": {}}
    
    def _restore_from_backup(self) -> Dict[str, Any]:
        """Restore memory from most recent backup"""
        try:
            if not self.backup_dir.exists():
                raise FileNotFoundError("No backup directory")
            
            backup_files = list(self.backup_dir.glob("trading_memory_backup_*.json"))
            if not backup_files:
                raise FileNotFoundError("No backup files found")
            
            # Get most recent backup
            latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            self.logger.info(f"Restoring from backup: {latest_backup}")
            
            with open(latest_backup, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Save restored data as current memory
            self.save_memory(data)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            return {"lessons": [], "last_lesson_id": 0, "metadata": {}}
    
    def save_memory(self, memory_data: Dict[str, Any]):
        """Save memory to JSON file with enhanced safety"""
        try:
            # ✅ IMPROVED: Atomic write with temporary file
            temp_path = self.memory_path.with_suffix('.tmp')
            
            # Update metadata
            if "metadata" in memory_data:
                memory_data["metadata"]["last_updated"] = datetime.now().isoformat()
                memory_data["metadata"]["total_lessons"] = len(memory_data.get("lessons", []))
            
            # Write to temporary file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename (safer than direct write)
            temp_path.replace(self.memory_path)
            
            self.logger.debug("Memory saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving memory: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def get_recent_lessons(self, limit: int = 10, min_relevance: int = 4, 
                          lesson_type: Optional[str] = None, 
                          tags: Optional[List[str]] = None) -> List[Dict]:
        """Get recent relevant lessons with advanced filtering"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        # ✅ IMPROVED: Advanced filtering
        filtered_lessons = []
        
        for lesson in lessons:
            # Relevance filter
            if lesson.get("relevance", 0) < min_relevance:
                continue
            
            # Type filter
            if lesson_type and lesson.get("type") != lesson_type:
                continue
            
            # Tags filter
            if tags:
                lesson_tags = lesson.get("tags", [])
                if not any(tag in lesson_tags for tag in tags):
                    continue
            
            filtered_lessons.append(lesson)
        
        # Sort by date (most recent first)
        filtered_lessons.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return filtered_lessons[:limit]
    
    def add_lesson(self, pair: str, lesson_type: str, context: str, 
                   rule: str, result: str, relevance: int,
                   tags: Optional[List[str]] = None) -> str:
        """Add new lesson to memory with enhanced validation"""
        # ✅ IMPROVED: Input validation
        if not all([pair, lesson_type, context, rule, result]):
            raise ValueError("All lesson fields are required")
        
        if not 1 <= relevance <= 5:
            raise ValueError("Relevance must be between 1 and 5")
        
        memory = self.load_memory()
        
        # Generate new lesson ID
        last_id = memory.get("last_lesson_id", 0)
        new_id = f"L{last_id + 1:03d}"
        
        new_lesson = {
            "id": new_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pair": pair.upper(),
            "type": lesson_type,
            "context": context.strip(),
            "rule": rule.strip(),
            "result": result,
            "relevance": relevance,
            "tags": tags or [],
            "created_timestamp": datetime.now().isoformat()
        }
        
        # Add to memory
        memory["lessons"].append(new_lesson)
        memory["last_lesson_id"] = last_id + 1
        
        # Save updated memory
        self.save_memory(memory)
        
        self.logger.info(f"New lesson {new_id} added: {lesson_type} - {result}")
        return new_id
    
    def update_lesson(self, lesson_id: str, **updates) -> bool:
        """Update existing lesson"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        for lesson in lessons:
            if lesson.get("id") == lesson_id:
                # Update allowed fields
                allowed_updates = ["context", "rule", "result", "relevance", "tags"]
                for key, value in updates.items():
                    if key in allowed_updates:
                        lesson[key] = value
                
                lesson["last_updated"] = datetime.now().isoformat()
                
                self.save_memory(memory)
                self.logger.info(f"Lesson {lesson_id} updated")
                return True
        
        self.logger.warning(f"Lesson {lesson_id} not found")
        return False
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """Delete lesson by ID"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        original_count = len(lessons)
        memory["lessons"] = [l for l in lessons if l.get("id") != lesson_id]
        
        if len(memory["lessons"]) < original_count:
            self.save_memory(memory)
            self.logger.info(f"Lesson {lesson_id} deleted")
            return True
        
        self.logger.warning(f"Lesson {lesson_id} not found")
        return False
    
    def search_lessons(self, query: str, search_fields: List[str] = None) -> List[Dict]:
        """Search lessons by text query"""
        if search_fields is None:
            search_fields = ["context", "rule", "type", "tags"]
        
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        query_lower = query.lower()
        matching_lessons = []
        
        for lesson in lessons:
            for field in search_fields:
                field_value = lesson.get(field, "")
                
                # Handle different field types
                if isinstance(field_value, list):  # tags
                    field_text = " ".join(field_value).lower()
                else:
                    field_text = str(field_value).lower()
                
                if query_lower in field_text:
                    matching_lessons.append(lesson)
                    break
        
        return matching_lessons
    
    def format_memory_for_ai(self, lessons: List[Dict]) -> str:
        """Format lessons for AI analysis with enhanced details"""
        if not lessons:
            return "MEMORIA: [Vacía - Sin lecciones relevantes]"
        
        formatted_lessons = []
        formatted_lessons.append("=== MEMORIA TRADING ===")
        
        for lesson in lessons:
            # Enhanced formatting with more context
            tags_str = ", ".join(lesson.get("tags", []))
            formatted = (
                f"{lesson['id']}: [{lesson['pair']}] {lesson['type']}\n"
                f"  📝 Contexto: {lesson['context']}\n"
                f"  📋 Regla: {lesson['rule']}\n"
                f"  📊 Resultado: {lesson['result']} | Relevancia: {lesson['relevance']}/5\n"
                f"  🏷️ Tags: {tags_str}\n"
            )
            formatted_lessons.append(formatted)
        
        return "\n".join(formatted_lessons)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        if not lessons:
            return {"total": 0, "by_type": {}, "by_relevance": {}, "by_result": {}}
        
        # Enhanced statistics
        by_type = {}
        by_relevance = {}
        by_result = {}
        by_tags = {}
        
        win_count = 0
        loss_count = 0
        total_pips = 0
        
        for lesson in lessons:
            # Count by type
            lesson_type = lesson.get("type", "Unknown")
            by_type[lesson_type] = by_type.get(lesson_type, 0) + 1
            
            # Count by relevance
            relevance = lesson.get("relevance", 0)
            by_relevance[relevance] = by_relevance.get(relevance, 0) + 1
            
            # Count by result
            result = lesson.get("result", "Unknown")
            by_result[result] = by_result.get(result, 0) + 1
            
            # Count tags
            for tag in lesson.get("tags", []):
                by_tags[tag] = by_tags.get(tag, 0) + 1
            
            # Analyze wins/losses
            if "+" in result and "pip" in result:
                win_count += 1
                try:
                    pips = float(result.split("+")[1].split(" ")[0])
                    total_pips += pips
                except:
                    pass
            elif "-" in result and "pip" in result:
                loss_count += 1
                try:
                    pips = float(result.split("-")[1].split(" ")[0])
                    total_pips -= pips
                except:
                    pass
        
        return {
            "total": len(lessons),
            "by_type": by_type,
            "by_relevance": by_relevance,
            "by_result": by_result,
            "by_tags": by_tags,
            "performance": {
                "wins": win_count,
                "losses": loss_count,
                "total_pips": total_pips,
                "win_rate": win_count / (win_count + loss_count) * 100 if (win_count + loss_count) > 0 else 0
            },
            "last_lesson_id": memory.get("last_lesson_id", 0),
            "metadata": memory.get("metadata", {})
        }
    
    def export_to_csv(self, output_file: str = None, include_tags: bool = True):
        """Export memory to CSV with enhanced format"""
        import csv
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"trading_memory_export_{timestamp}.csv"
        
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        output_path = Path.home() / "Desktop" / output_file
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            if lessons:
                # Prepare fieldnames
                fieldnames = ["id", "date", "pair", "type", "context", "rule", "result", "relevance"]
                if include_tags:
                    fieldnames.append("tags")
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for lesson in lessons:
                    row = {k: lesson.get(k, "") for k in fieldnames}
                    if include_tags and "tags" in lesson:
                        row["tags"] = "; ".join(lesson["tags"])
                    writer.writerow(row)
        
        self.logger.info(f"Memory exported to: {output_path}")
        return output_path

# Example usage and testing
if __name__ == "__main__":
    # Initialize memory system
    memory = LocalTradingMemory()
    
    # Test: Get recent lessons
    recent = memory.get_recent_lessons(limit=5)
    print("\n=== RECENT LESSONS ===")
    print(memory.format_memory_for_ai(recent))
    
    # Test: Search functionality
    print("\n=== SEARCH TEST ===")
    search_results = memory.search_lessons("estructura")
    print(f"Found {len(search_results)} lessons containing 'estructura'")
    
    # Test: Get comprehensive stats
    print("\n=== MEMORY STATS ===")
    stats = memory.get_memory_stats()
    print(f"Total lessons: {stats['total']}")
    print(f"Performance: {stats['performance']}")
    print(f"By type: {stats['by_type']}")
    
    # Test: Add new lesson with tags
    print("\n=== ADDING NEW LESSON ===")
    new_id = memory.add_lesson(
        pair="EURUSD",
        lesson_type="Test Enhanced",
        context="Testing improved memory system with tags and validation",
        rule="Enhanced local storage with backup and search works perfectly",
        result="Success",
        relevance=5,
        tags=["test", "enhanced", "backup", "search"]
    )
    
    print(f"\n✅ Enhanced local memory system working perfectly!")
    print(f"Memory file: {memory.memory_path}")
    print(f"Backup directory: {memory.backup_dir}")
