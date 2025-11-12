import os
import logging
import json
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
from config import Config
from database import Database
from datetime import datetime

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Konfiguratsiyani tekshirish
config_errors = Config.validate_config()
if config_errors:
    for error in config_errors:
        logger.error(f"❌ {error}")
    logger.error("❌ Bot ishga tushirish uchun konfiguratsiya to'liq emas!")
    exit(1)

# OpenRouter Service
class OpenRouterService:
    def __init__(self):
        self.api_url = Config.OPENROUTER_API_URL
        self.api_key = Config.OPENROUTER_API_KEY
        self.model = Config.MODEL
        self.db = Database()
    
    def get_response(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hasanai-bot.telegram",
            "X-Title": "HasanAI Bot"
        }
        
        # Knowledge bazasidan kontekst
        knowledge_base = self.db.get_knowledge_base()
        qa_pairs = knowledge_base.get('qa_pairs', {})
        
        # Knowledge bazasidan mos keladigan javobni qidirish
        for question, answer in qa_pairs.items():
            if question.lower() in prompt.lower():
                return answer
        
        # Agar knowledge bazada javob bo'lmasa, OpenRouter dan so'rash
        system_message = "Siz 2-maktab yordamchi assistanti sifatida javob berasiz. Faqat berilgan ma'lumotlar asosida javob bering. Agar savolga javob knowledge bazada bo'lmasa, 'Afsuski, men bu haqda maʼlumotga ega emasman' deb javob bering."
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": Config.MAX_TOKENS,
            "temperature": Config.TEMPERATURE
        }
        
        try:
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenRouter xatosi: {response.status_code} - {response.text}")
                return f"❌ Xatolik yuz berdi (Status: {response.status_code})"
                        
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter ulanish xatosi: {e}")
            return f"❌ Serverga ulanishda xatolik"
        except Exception as e:
            logger.error(f"OpenRouter kutilmagan xatolik: {e}")
            return f"❌ Kutilmagan xatolik"

# Bot Handlers
class BotHandlers:
    def __init__(self):
        self.db = Database()
        self.openai_service = OpenRouterService()
    
    def _is_admin(self, user_id: int) -> bool:
        return user_id == Config.ADMIN_ID
    
    # Start komandasi
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.update_user(user.id, user.username, user.first_name)
        
        welcome_text = """
👋 Salom! **HasanAI** - 2-maktab yordamchi botiga xush kelibsiz!

🎯 **Bot imkoniyatlari:**
• Savollaringizga javob olish
• 2-maktab haqida ma'lumot
• Tez va aniq javoblar

💡 **Foydalanish:** Faqat savolingizni yuboring!

👨‍💻 **Admin:** /admin
        """
        await update.message.reply_text(welcome_text)
        logger.info(f"Yangi foydalanuvchi: {user.id} - {user.first_name}")
    
    # Admin paneli
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            logger.warning(f"Admin panelga urinish: {user_id}")
            return
        
        admin_text = f"""
🛠️ **Admin Panel - HasanAI**

📊 **Statistika:**
/stats - Bot statistikasi

👥 **Foydalanuvchilar:**
/users - Foydalanuvchilar ro'yxati

📚 **Ma'lumotlar bazasi:**
/add_info - Yangi ma'lumot qo'shish
/view_knowledge - Ma'lumotlarni ko'rish

📢 **Reklama:**
/broadcast - Hammaga xabar yuborish

🆔 **Sizning ID:** {user_id}
        """
        await update.message.reply_text(admin_text)
        logger.info(f"Admin panel ochildi: {user_id}")
    
    # Asosiy message handler
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_message = update.message.text
        
        # Admin reklama tasdiqlash
        if user_message and user_message.lower() in ['ha', 'yo\'q'] and self._is_admin(user.id):
            await self._handle_broadcast_confirmation(update, context, user_message)
            return
        
        # Oddiy foydalanuvchi savoli
        self.db.update_user(user.id, user.username, user.first_name)
        
        # Kutish xabarini yuborish
        wait_msg = await update.message.reply_text("⏳ Javob tayyorlanmoqda...")
        
        try:
            # Endi bu sync funksiya, shuning uchun threadda ishlatamiz
            response = await context.application.run_async(
                self.openai_service.get_response, user_message
            )
            
            # Savollar sonini yangilash
            self.db.increment_questions(user.id)
            
            # Kutish xabarini o'chirish
            await wait_msg.delete()
            
            # Javobni yuborish
            await update.message.reply_text(response)
            logger.info(f"Foydalanuvchi savoli: {user.id} - {user_message[:50]}...")
            
        except Exception as e:
            await wait_msg.delete()
            await update.message.reply_text("❌ Javob olishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
            logger.error(f"Xatolik: {e}")
    
    # Statistika
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        stats = self.db.get_stats()
        
        stats_text = f"""
📊 **HasanAI Statistikasi**

👥 **Jami foydalanuvchilar:** {stats['total_users']}
❓ **Jami savollar:** {stats['total_questions']}
🔥 **Bugun faol:** {stats['active_today']}

🚀 **Bot faol va ishlayapti!**
        """
        await update.message.reply_text(stats_text)
    
    # Foydalanuvchilar ro'yxati
    async def show_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        users = self.db.load_json('users.json')
        
        if not users:
            await update.message.reply_text("📭 Hali foydalanuvchilar mavjud emas")
            return
        
        users_text = "👥 **Foydalanuvchilar ro'yxati:**\n\n"
        for i, (user_id, user_data) in enumerate(list(users.items())[:20], 1):
            users_text += f"{i}. **ID:** `{user_id}`\n"
            users_text += f"   **Ism:** {user_data.get('first_name', 'Noma lum')}\n"
            users_text += f"   **Username:** @{user_data.get('username', 'Noma lum')}\n"
            users_text += f"   **Savollar:** {user_data.get('questions_asked', 0)}\n"
            users_text += "   ──────────────\n"
        
        await update.message.reply_text(users_text)
    
    # Ma'lumot qo'shish
    async def add_knowledge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if not context.args:
            await update.message.reply_text("""
❌ **Iltimos, ma'lumotni quyidagi formatda yuboring:**
`/add_info Savol? - Javob`

**Misol:**
`/add_info Maktab qachon ochiladi? - Maktab 1-sentyabrda ochiladi`
            """)
            return
        
        text = ' '.join(context.args)
        if ' - ' not in text:
            await update.message.reply_text("❌ Noto'g'ri format. Iltimos: `Savol? - Javob`")
            return
        
        question, answer = text.split(' - ', 1)
        
        self.db.add_knowledge(question.strip(), answer.strip())
        await update.message.reply_text("✅ **Yangi ma'lumot muvaffaqiyatli qo'shildi!**")
    
    # Ma'lumotlar bazasini ko'rish
    async def view_knowledge(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        knowledge_base = self.db.get_knowledge_base()
        qa_pairs = knowledge_base.get('qa_pairs', {})
        
        if not qa_pairs:
            await update.message.reply_text("📭 **Ma'lumotlar bazasi bo'sh**")
            return
        
        knowledge_text = "📚 **Ma'lumotlar bazasi:**\n\n"
        for i, (question, answer) in enumerate(qa_pairs.items(), 1):
            knowledge_text += f"**{i}. ❓ {question}**\n"
            knowledge_text += f"   ✅ {answer}\n\n"
            
            if len(knowledge_text) > 3500:
                knowledge_text += "... (qolganlari kesib tashlandi)"
                break
        
        await update.message.reply_text(knowledge_text)
    
    # Reklama boshqaruvi
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Siz admin emassiz!")
            return
        
        if not context.args:
            await update.message.reply_text("""
📢 **Reklama yuborish**

Quyidagi buyruqlardan birini tanlang:

`/broadcast text` - Matnli reklama
`/broadcast photo` - Rasmli reklama  
`/broadcast video` - Videoli reklama
            """)
            return
        
        broadcast_type = context.args[0].lower()
        context.user_data['broadcast_type'] = broadcast_type
        
        if broadcast_type == 'text':
            await update.message.reply_text("📝 **Matnli reklama yuboring:**")
        elif broadcast_type == 'photo':
            await update.message.reply_text("🖼️ **Rasmli reklama yuboring (rasm + tag):**")
        elif broadcast_type == 'video':
            await update.message.reply_text("🎥 **Videoli reklama yuboring (video + tag):**")
        else:
            await update.message.reply_text("❌ Noto'g'ri tur. Faqat: text, photo, video")
    
    # Media handler (reklama uchun)
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_admin(update.effective_user.id):
            return
        
        if 'broadcast_type' not in context.user_data:
            return
        
        broadcast_type = context.user_data['broadcast_type']
        caption = update.message.caption or ""
        
        if broadcast_type == 'photo' and update.message.photo:
            context.user_data['broadcast_photo'] = update.message.photo[-1].file_id
            context.user_data['broadcast_caption'] = caption
            
            await update.message.reply_text(
                f"🖼️ **Rasm qabul qilindi!**\n\nTag: {caption}\n\n"
                f"Reklamani yuborishni tasdiqlaysizmi? (Ha / Yo'q)"
            )
            
        elif broadcast_type == 'video' and update.message.video:
            context.user_data['broadcast_video'] = update.message.video.file_id
            context.user_data['broadcast_caption'] = caption
            
            await update.message.reply_text(
                f"🎥 **Video qabul qilindi!**\n\nTag: {caption}\n\n"
                f"Reklamani yuborishni tasdiqlaysizmi? (Ha / Yo'q)"
            )
    
    # Reklama tasdiqlash
    async def _handle_broadcast_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, confirmation: str):
        if confirmation.lower() == 'ha':
            await update.message.reply_text("🔄 Reklama yuborilmoqda...")
            success_count = 0
            error_count = 0
            
            users = self.db.load_json('users.json')
            
            for user_id in users.keys():
                try:
                    if 'broadcast_photo' in context.user_data:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=context.user_data['broadcast_photo'],
                            caption=context.user_data.get('broadcast_caption', '')
                        )
                    elif 'broadcast_video' in context.user_data:
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=context.user_data['broadcast_video'],
                            caption=context.user_data.get('broadcast_caption', '')
                        )
                    else:
                        # Text reklama
                        broadcast_text = context.user_data.get('broadcast_text', '')
                        if broadcast_text:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=broadcast_text
                            )
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Reklama yuborishda xatolik {user_id}: {e}")
            
            # Tozalash
            context.user_data.clear()
            
            await update.message.reply_text(
                f"✅ Reklama yuborildi!\n\n"
                f"✅ Muvaffaqiyatli: {success_count}\n"
                f"❌ Xatolar: {error_count}"
            )
        else:
            context.user_data.clear()
            await update.message.reply_text("❌ Reklama bekor qilindi.")

# Text reklama uchun handler
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not BotHandlers()._is_admin(update.effective_user.id):
        return
    
    if 'broadcast_type' in context.user_data and context.user_data['broadcast_type'] == 'text':
        context.user_data['broadcast_text'] = update.message.text
        await update.message.reply_text(
            f"📝 **Matn qabul qilindi!**\n\n{update.message.text}\n\n"
            f"Reklamani yuborishni tasdiqlaysizmi? (Ha / Yo'q)"
        )

# Asosiy bot
def main():
    # Konfiguratsiyani tekshirish
    config_errors = Config.validate_config()
    if config_errors:
        for error in config_errors:
            logger.error(f"❌ {error}")
        logger.error("❌ Bot ishga tushirish uchun konfiguratsiya to'liq emas!")
        return
    
    # Botni yaratish
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Handlers
    handlers = BotHandlers()
    
    # Command handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("admin", handlers.admin_panel))
    application.add_handler(CommandHandler("stats", handlers.show_stats))
    application.add_handler(CommandHandler("users", handlers.show_users))
    application.add_handler(CommandHandler("add_info", handlers.add_knowledge))
    application.add_handler(CommandHandler("view_knowledge", handlers.view_knowledge))
    application.add_handler(CommandHandler("broadcast", handlers.broadcast_start))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handlers.handle_media))
    
    # Text reklama handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'^(?!(Ha|Yo\'q)$).*'), 
        handle_broadcast_text
    ))
    
    # Botni ishga tushirish
    logger.info("HasanAI bot ishga tushdi...")
    logger.info(f"Admin ID: {Config.ADMIN_ID}")
    application.run_polling()

if __name__ == '__main__':
    main()
