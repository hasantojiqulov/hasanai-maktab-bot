import json
import os
from datetime import datetime
from typing import Dict, Any

class Database:
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
        
    def _get_file_path(self, filename: str) -> str:
        return os.path.join(self.data_dir, filename)
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        file_path = self._get_file_path(filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_json(self, filename: str, data: Dict[str, Any]):
        file_path = self._get_file_path(filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def update_user(self, user_id: int, username: str, first_name: str):
        users = self.load_json('users.json')
        
        if str(user_id) not in users:
            users[str(user_id)] = {
                'username': username,
                'first_name': first_name,
                'join_date': datetime.now().isoformat(),
                'questions_asked': 0,
                'last_active': datetime.now().isoformat()
            }
        else:
            users[str(user_id)].update({
                'username': username,
                'first_name': first_name,
                'last_active': datetime.now().isoformat()
            })
        
        self.save_json('users.json', users)
    
    def increment_questions(self, user_id: int):
        users = self.load_json('users.json')
        stats = self.load_json('stats.json')
        
        if str(user_id) in users:
            users[str(user_id)]['questions_asked'] = users[str(user_id)].get('questions_asked', 0) + 1
        
        stats['total_questions'] = stats.get('total_questions', 0) + 1
        stats['last_question_time'] = datetime.now().isoformat()
        
        self.save_json('users.json', users)
        self.save_json('stats.json', stats)
    
    def get_stats(self) -> Dict[str, Any]:
        users = self.load_json('users.json')
        stats = self.load_json('stats.json')
        
        return {
            'total_users': len(users),
            'total_questions': stats.get('total_questions', 0),
            'active_today': self._count_active_today(users)
        }
    
    def _count_active_today(self, users: Dict[str, Any]) -> int:
        today = datetime.now().date()
        count = 0
        
        for user_data in users.values():
            last_active = user_data.get('last_active')
            if last_active:
                try:
                    active_date = datetime.fromisoformat(last_active).date()
                    if active_date == today:
                        count += 1
                except ValueError:
                    continue
        
        return count

    def add_knowledge(self, question: str, answer: str):
        knowledge_base = self.load_json('knowledge_base.json')
        if 'qa_pairs' not in knowledge_base:
            knowledge_base['qa_pairs'] = {}
        
        knowledge_base['qa_pairs'][question.strip()] = answer.strip()
        self.save_json('knowledge_base.json', knowledge_base)
    
    def get_knowledge_base(self):
        return self.load_json('knowledge_base.json')
