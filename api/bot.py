import os
import requests

from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://autoxabar.vercel.app")


def telegram_api(method, payload):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN Vercel Environment Variables ichida yo'q")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    response = requests.post(url, json=payload, timeout=15)

    try:
        data = response.json()
    except Exception:
        data = {"ok": False, "description": response.text}

    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))

    return data


def send_start_message(chat_id, first_name=""):
    text = f"""Salom {first_name}!

Telegram Auto Poster Bot ga xush kelibsiz.

Bu bot orqali:
✅ Telegram akkauntingizni ulaysiz
✅ Guruh yoki kanal tanlaysiz
✅ Xabar matnini yozasiz
✅ Har necha daqiqada yuborishni belgilaysiz

Boshlash uchun Web App tugmasini bosing."""

    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "🚀 Web App ni ochish",
                    "web_app": {
                        "url": WEBAPP_URL
                    }
                }
            ]
        ]
    }

    return telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup
    })


def send_help_message(chat_id):
    text = """Qo'llanma:

1. Web App ni oching
2. Telefon raqam bilan kiring
3. Telegram kodni kiriting
4. Guruhni tanlang
5. Xabar va vaqt oralig'ini belgilang
6. Jadvalga qo'shing

Eslatma: faqat o'zingiz ruxsatga ega bo'lgan guruh va kanallarda foydalaning."""

    return telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


@app.route("/api/bot", methods=["GET"])
def bot_health():
    return jsonify({
        "status": "bot ok" if BOT_TOKEN else "bot token missing",
        "webapp_url": WEBAPP_URL
    })


@app.route("/api/bot", methods=["POST"])
def telegram_webhook():
    data = request.get_json(silent=True) or {}

    try:
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            first_name = message.get("from", {}).get("first_name", "")

            if text.startswith("/start"):
                send_start_message(chat_id, first_name)
            elif text.startswith("/help"):
                send_help_message(chat_id)
            else:
                send_help_message(chat_id)

        elif "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            send_help_message(chat_id)

        return jsonify({"ok": True})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
