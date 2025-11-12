import os
from dotenv import load_dotenv

# .env faylini yuklash
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

class Config:
    # To'g'ridan-to'g'ri fayldan o'qish
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
    except FileNotFoundError:
        env_content = ""
    
    def _get_env_value(self, key):
        for line in self.env_content.split('\n'):
            if line.startswith(key + '='):
                return line.split('=', 1)[1].strip()
        return None
    
    BOT_TOKEN = os.getenv('BOT_TOKEN') or _get_env_value('BOT_TOKEN') or ''
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY') or _get_env_value('OPENROUTER_API_KEY') or ''
    
    # ADMIN_ID ni xatoliksiz o'qish
    admin_id_str = os.getenv('ADMIN_ID') or _get_env_value('ADMIN_ID') or ''
    try:
        ADMIN_ID = int(admin_id_str) if admin_id_str else 0
    except (ValueError, TypeError):
        ADMIN_ID = 0
    
    OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL') or _get_env_value('OPENROUTER_API_URL') or 'https://openrouter.ai/api/v1/chat/completions'
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

# Test
if __name__ == '__main__':
    config = Config()
    print("BOT_TOKEN:", config.BOT_TOKEN)
    print("OPENROUTER_API_KEY:", config.OPENROUTER_API_KEY)
    print("ADMIN_ID:", config.ADMIN_ID)
