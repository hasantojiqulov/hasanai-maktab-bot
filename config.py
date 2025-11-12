import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '').strip()
    
    # ADMIN_ID ni xatoliksiz o'qish
    admin_id_str = os.getenv('ADMIN_ID', '').strip()
    try:
        ADMIN_ID = int(admin_id_str) if admin_id_str else 0
    except (ValueError, TypeError):
        ADMIN_ID = 0
    
    OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions').strip()
    MODEL = "google/gemini-pro-1.5"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.7
    
    @classmethod
    def validate_config(cls):
        """Konfiguratsiyani tekshirish"""
        errors = []
        
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN topilmadi. .env faylini tekshiring.")
        
        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY topilmadi. .env faylini tekshiring.")
        
        if not cls.ADMIN_ID:
            errors.append("ADMIN_ID topilmadi yoki noto'g'ri formatda. .env faylini tekshiring.")
        
        return errors
