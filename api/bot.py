import os
import sys
import json
import asyncio

from flask import Flask, request, jsonify
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.database import Database

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://autoxabar.vercel.app")
DATABASE_URL = os.getenv("DATABASE_URL")

db = Database(DATABASE_URL)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable topilmadi")

application = Application.builder().token(BOT_TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton(
                text="Web App ni ochish",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ],
        [
            InlineKeyboardButton(
                text="Qo'llanma",
                callback_data="help"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = f"""
Salom {user.first_name}!

Telegram Auto Poster Bot ga xush kelibsiz.

Bu bot orqali siz:
✅ Guruhlarga avtomatik xabar yuborishingiz
✅ Vaqt oralig'ini belgilashingiz
✅ Bir nechta guruhlarni boshqarishingiz mumkin

Boshlash uchun quyidagi tugma orqali Web App ni oching.
"""

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Qo'llanma:

1. Web App ni oching
2. Telefon raqam bilan kiring
3. Telegram kodni kiriting
4. Guruhni tanlang
5. Xabar va vaqt oralig'ini belgilang
6. Jadvalga qo'shing
"""

    await update.message.reply_text(help_text)


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        user_id = str(update.effective_user.id)

        if data.get("action") == "schedule":
            db.save_task(
                user_id=user_id,
                group_id=data["group_id"],
                message=data["message"],
                interval_seconds=data["interval"]
            )

            await update.message.reply_text("✅ Xabar jadvali muvaffaqiyatli qo'shildi!")

    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")


application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route("/api/bot", methods=["GET"])
def bot_health():
    return jsonify({"status": "bot ok"})


@app.route("/api/bot", methods=["POST"])
def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        run_async(application.process_update(update))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
