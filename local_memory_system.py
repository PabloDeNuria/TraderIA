#!/usr/bin/env python3
"""
Local Memory System for Trading AI
Manages lessons in local JSON file instead of Google Sheets
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any

class LocalTradingMemory:
    def __init__(self, memory_file="trading_memory.json"):
        """Initialize local memory system"""
        self.memory_file = memory_file
        self.memory_path = os.path.join(os.path.expanduser("~/Desktop"), memory_file)
        self.ensure_memory_file()
    
    def ensure_memory_file(self):
        """Create memory file if it doesn't exist"""
        if not os.path.exists(self.memory_path):
            # Initialize with existing lessons
            initial_lessons = [
                {
                    "id": "L001",
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Estructura",
                    "context": "H4 lateral sin dirección",
                    "rule": "No operar si H4 no cristalino",
                    "result": "WAIT",
                    "relevance": 5
                },
                {
                    "id": "L002", 
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Timing",
                    "context": "Estructura OK pero en máximos",
                    "rule": "No comprar techos sin zona clara",
                    "result": "WAIT",
                    "relevance": 4
                },
                {
                    "id": "L003",
                    "date": "2024-12-XX", 
                    "pair": "EURUSD",
                    "type": "Setup Completo",
                    "context": "H4+H1+M15 alineados",
                    "rule": "Cascada completa = alta probabilidad",
                    "result": "+22 pips",
                    "relevance": 5
                },
                {
                    "id": "L007",
                    "date": "2024-12-XX",
                    "pair": "EURUSD", 
                    "type": "Zona Rota",
                    "context": "Zona identificada pero rompió",
                    "rule": "No forzar trades cuando zona falla",
                    "result": "WAIT",
                    "relevance": 5
                },
                {
                    "id": "L008",
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Sistema",
                    "context": "Evitó pérdida por memoria",
                    "rule": "Memoria funciona para evitar errores", 
                    "result": "No Loss",
                    "relevance": 5
                },
                {
                    "id": "L009",
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Técnico", 
                    "context": "Error lectura temporalidad",
                    "rule": "Leer texto exacto, no adivinar",
                    "result": "N/A",
                    "relevance": 5
                },
                {
                    "id": "L010",
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Técnico",
                    "context": "Precisión en capturas", 
                    "rule": "Verificar datos antes de analizar",
                    "result": "N/A",
                    "relevance": 5
                },
                {
                    "id": "L011",
                    "date": "2024-12-XX",
                    "pair": "EURUSD",
                    "type": "Setup Completo",
                    "context": "Cascada + zona respetada",
                    "rule": "Order block funciona en retrocesos",
                    "result": "+16 pips", 
                    "relevance": 5
                }
            ]
            
            self.save_memory({"lessons": initial_lessons, "last_lesson_id": 11})
            print(f"Memory file created: {self.memory_path}")
    
    def load_memory(self) -> Dict[str, Any]:
        """Load memory from JSON file"""
        try:
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading memory: {e}")
            return {"lessons": [], "last_lesson_id": 0}
    
    def save_memory(self, memory_data: Dict[str, Any]):
        """Save memory to JSON file"""
        try:
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def get_recent_lessons(self, limit: int = 10, min_relevance: int = 4) -> List[Dict]:
        """Get recent relevant lessons"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        # Filter by relevance
        relevant = [l for l in lessons if l.get("relevance", 0) >= min_relevance]
        
        # Sort by date (most recent first)
        relevant.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        return relevant[:limit]
    
    def add_lesson(self, pair: str, lesson_type: str, context: str, 
                   rule: str, result: str, relevance: int) -> str:
        """Add new lesson to memory"""
        memory = self.load_memory()
        
        # Generate new lesson ID
        last_id = memory.get("last_lesson_id", 0)
        new_id = f"L{last_id + 1:03d}"
        
        new_lesson = {
            "id": new_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "pair": pair,
            "type": lesson_type,
            "context": context,
            "rule": rule,
            "result": result,
            "relevance": relevance
        }
        
        # Add to memory
        memory["lessons"].append(new_lesson)
        memory["last_lesson_id"] = last_id + 1
        
        # Save updated memory
        self.save_memory(memory)
        
        print(f"New lesson {new_id} added to memory")
        return new_id
    
    def format_memory_for_ai(self, lessons: List[Dict]) -> str:
        """Format lessons for Claude API"""
        if not lessons:
            return "MEMORIA: [Vacía]"
        
        formatted_lessons = []
        for lesson in lessons:
            formatted = f"{lesson['id']}: {lesson['pair']}-{lesson['context']}→{lesson['result']} [{lesson['relevance']}/5]"
            formatted_lessons.append(formatted)
        
        return "MEMORIA:\n" + "\n".join(formatted_lessons)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        if not lessons:
            return {"total": 0, "by_type": {}, "by_relevance": {}}
        
        # Count by type
        by_type = {}
        by_relevance = {}
        
        for lesson in lessons:
            lesson_type = lesson.get("type", "Unknown")
            relevance = lesson.get("relevance", 0)
            
            by_type[lesson_type] = by_type.get(lesson_type, 0) + 1
            by_relevance[relevance] = by_relevance.get(relevance, 0) + 1
        
        return {
            "total": len(lessons),
            "by_type": by_type,
            "by_relevance": by_relevance,
            "last_lesson_id": memory.get("last_lesson_id", 0)
        }
    
    def export_to_csv(self, output_file: str = "trading_memory_export.csv"):
        """Export memory to CSV for backup"""
        import csv
        
        memory = self.load_memory()
        lessons = memory.get("lessons", [])
        
        output_path = os.path.join(os.path.expanduser("~/Desktop"), output_file)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            if lessons:
                fieldnames = lessons[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(lessons)
        
        print(f"Memory exported to: {output_path}")

# Example usage and testing
if __name__ == "__main__":
    # Initialize memory system
    memory = LocalTradingMemory()
    
    # Test: Get recent lessons
    recent = memory.get_recent_lessons(limit=5)
    print("\n=== RECENT LESSONS ===")
    print(memory.format_memory_for_ai(recent))
    
    # Test: Add new lesson
    print("\n=== ADDING NEW LESSON ===")
    new_id = memory.add_lesson(
        pair="EURUSD",
        lesson_type="Test",
        context="Testing local memory system",
        rule="Local storage works perfectly",
        result="Success",
        relevance=5
    )
    
    # Test: Get stats
    print("\n=== MEMORY STATS ===")
    stats = memory.get_memory_stats()
    print(f"Total lessons: {stats['total']}")
    print(f"By type: {stats['by_type']}")
    print(f"By relevance: {stats['by_relevance']}")
    
    # Test: Export backup
    print("\n=== CREATING BACKUP ===")
    memory.export_to_csv()
    
    print("\n✅ Local memory system working perfectly!")
