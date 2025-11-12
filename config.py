import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    ADMIN_ID = int(os.getenv('ADMIN_ID'))
    OPENROUTER_API_URL = os.getenv('OPENROUTER_API_URL')
    
    # OpenRouter model sozlamalari
    MODEL = "google/gemini-pro-1.5"  # Siz o'zgartirishingiz mumkin
    MAX_TOKENS = 1000
    TEMPERATURE = 0.7
