import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import json
from utils.database import Database

# Database
db = Database(os.getenv('DATABASE_URL'))

# Web App URL
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-app.vercel.app')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    user = update.effective_user
    
    # Web App tugmasi
    keyboard = [
        [
            InlineKeyboardButton(
                text="🚀 Web App ni ochish", 
                web_app=WebAppInfo(url=f"{WEBAPP_URL}/?user_id={user.id}")
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Qo'llanma", 
                callback_data="help"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
👋 Salom {user.first_name}!

🤖 **Telegram Auto Poster Bot** ga xush kelibsiz!

Bu bot orqali siz:
✅ Guruhlarga avtomatik xabar yuborishingiz
✅ Vaqt oralig'ini belgilashingiz
✅ Bir nechta guruhlarni boshqarishingiz mumkin

Quyidagi tugma orqali Web App ni oching va boshlang!
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
📚 **Qo'llanma:**

1️⃣ **Web App ni oching**
   - "Web App ni ochish" tugmasini bosing
   
2️⃣ **Telefon raqam bilan kiring**
   - Telegram akkauntingiz raqamini kiriting
   - Tasdiqlash kodini kiriting
   
3️⃣ **Guruhni tanlang**
   - Guruhlaringiz ro'yxati chiqadi
   - Kerakli guruhni tanlang
   
4️⃣ **Xabar va vaqtni belgilang**
   - Xabar matnini yozing
   - Yuborish oralig'ini belgilang
   
5️⃣ **Jadvalni ishga tushiring**
   - "Jadvalga qo'shish" tugmasini bosing

❗️ **Muhim:**
- Akkauntingiz xavfsizligi ta'minlanadi
- Sessiya ma'lumotlari shifrlangan holda saqlanadi
- 24/7 ishlaydi

📞 Yordam kerak bo'lsa: @support
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Web App dan kelgan ma'lumot"""
    data = json.loads(update.effective_message.web_app_data.data)
    user_id = str(update.effective_user.id)
    
    if data.get('action') == 'schedule':
        db.save_task(
            user_id,
            data['group_id'],
            data['message'],
            data['interval']
        )
        
        await update.message.reply_text(
            "✅ Xabar jadvali muvaffaqiyatli qo'shildi!"
        )

# Botni sozlash
application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

# Handlerlar
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))

# Vercel uchun handler
async def handler(request, context):
    """Vercel serverless function handler"""
    if request.method == "POST":
        await application.update_queue.put(
            Update.de_json(json.loads(await request.body()), application.bot)
        )
    return {"statusCode": 200}