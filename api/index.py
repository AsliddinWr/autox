import os
import sys
import asyncio
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError, SessionPasswordNeededError
from telethon.tl.types import Channel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.database import Database

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)

app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

API_ID_RAW = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
DATABASE_URL = os.getenv("DATABASE_URL")

if not API_ID_RAW:
    raise RuntimeError("API_ID environment variable topilmadi")

if not API_HASH:
    raise RuntimeError("API_HASH environment variable topilmadi")

API_ID = int(API_ID_RAW)

db = Database(DATABASE_URL)


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def create_client(session_string=None):
    client = TelegramClient(
        StringSession(session_string) if session_string else StringSession(),
        API_ID,
        API_HASH
    )
    await client.connect()
    return client


async def get_authorized_client(user_id):
    session_data = db.get_session(user_id)
    if not session_data:
        return None

    client = await create_client(session_data["session_string"])

    if not await client.is_user_authorized():
        await client.disconnect()
        return None

    return client


@app.route("/")
def index():
    user_id = session.get("user_id")

    if user_id and db.get_session(user_id):
        return render_template("dashboard.html")

    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    phone = request.form.get("phone", "").strip()

    if not phone:
        return jsonify({"error": "Telefon raqam kiritilishi shart"}), 400

    async def _login():
        client = await create_client()

        try:
            result = await client.send_code_request(phone)
            session_string = client.session.save()

            db.save_temp_login(
                phone=phone,
                session_string=session_string,
                phone_code_hash=result.phone_code_hash
            )

            session["phone"] = phone

            return jsonify({"success": True, "message": "Kod Telegram ilovangizga yuborildi"})
        finally:
            await client.disconnect()

    try:
        return run_async(_login())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/verify", methods=["POST"])
def verify():
    code = request.form.get("code", "").strip()
    phone = session.get("phone")

    if not phone or not code:
        return jsonify({"error": "Ma'lumotlar yetarli emas"}), 400

    temp_data = db.get_temp_login(phone)

    if not temp_data:
        return jsonify({"error": "Vaqtinchalik login sessiya topilmadi. Qaytadan kod oling."}), 400

    async def _verify():
        client = await create_client(temp_data["session_string"])

        try:
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=temp_data["phone_code_hash"]
            )

            session_string = client.session.save()

            db.save_session(phone, session_string)
            db.delete_temp_login(phone)

            session["user_id"] = phone

            return jsonify({"success": True})
        finally:
            await client.disconnect()

    try:
        return run_async(_verify())

    except PhoneCodeInvalidError:
        return jsonify({"error": "Kod noto'g'ri kiritildi"}), 400

    except SessionPasswordNeededError:
        return jsonify({
            "error": "Bu akkauntda 2 bosqichli parol yoqilgan. Hozircha bu funksiya qo'llab-quvvatlanmaydi."
        }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/groups")
def get_groups():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Avtorizatsiya qilinmagan"}), 401

    async def _get_groups():
        client = await get_authorized_client(user_id)

        if not client:
            return jsonify({"error": "Sessiya topilmadi yoki avtorizatsiya tugagan"}), 401

        try:
            dialogs = await client.get_dialogs()
            groups = []

            for dialog in dialogs:
                if dialog.is_group or dialog.is_channel:
                    entity = dialog.entity

                    groups.append({
                        "id": str(dialog.id),
                        "title": dialog.name,
                        "type": "channel" if isinstance(entity, Channel) else "group"
                    })

            return jsonify({"groups": groups})
        finally:
            await client.disconnect()

    try:
        return run_async(_get_groups())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/schedule", methods=["POST"])
def schedule_message():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Avtorizatsiya qilinmagan"}), 401

    data = request.get_json(silent=True) or {}

    group_id = data.get("group_id")
    message = data.get("message")
    interval = int(data.get("interval", 60))
    interval_type = data.get("interval_type", "minutes")

    if not group_id or not message:
        return jsonify({"error": "Guruh va xabar kiritilishi shart"}), 400

    if interval_type == "seconds":
        interval_seconds = interval
    elif interval_type == "minutes":
        interval_seconds = interval * 60
    elif interval_type == "hours":
        interval_seconds = interval * 3600
    else:
        interval_seconds = interval * 60

    task_id = db.save_task(user_id, group_id, message, interval_seconds)

    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Jadval qo'shildi"
    })


@app.route("/api/tasks")
def get_tasks():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Avtorizatsiya qilinmagan"}), 401

    tasks = db.get_tasks(user_id)
    return jsonify({"tasks": tasks})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "Avtorizatsiya qilinmagan"}), 401

    db.delete_task(task_id)
    return jsonify({"success": True})


@app.route("/logout")
def logout():
    user_id = session.get("user_id")

    if user_id:
        db.delete_session(user_id)

    session.clear()
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
