from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import os

WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-app.vercel.app')

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi uchun handler"""
    user = update.effective_user
    
    keyboard = [
        [InlineKeyboardButton(
            "🚀 Web App ni ochish", 
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/?user_id={user.id}")
        )],
        [InlineKeyboardButton("📋 Yordam", callback_data="help")],
    ]
    
    await update.message.reply_text(
        f"Assalomu alaykum {user.first_name}! 👋\n\n"
        "Telegram Auto Poster botiga xush kelibsiz!\n"
        "Guruhlarga avtomatik xabar yuborish uchun Web App ni oching.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
📚 **Yordam:**

1. Web App ni oching
2. Telefon raqamingizni kiriting
3. Kodni tasdiqlang
4. Guruh va xabarni tanlang
5. Vaqt oralig'ini belgilang
6. Avtomatik yuborishni boshlang
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
