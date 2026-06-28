import os
import sys
import asyncio
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, SessionPasswordNeededError
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

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

db = Database(os.getenv("DATABASE_URL"))


def get_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def get_api_config():
    api_id_raw = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    if not api_id_raw:
        raise RuntimeError("API_ID Vercel Environment Variables ichida yo'q")

    if not api_hash:
        raise RuntimeError("API_HASH Vercel Environment Variables ichida yo'q")

    try:
        api_id = int(api_id_raw)
    except ValueError:
        raise RuntimeError("API_ID faqat raqam bo'lishi kerak")

    return api_id, api_hash


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def create_client(session_string=None):
    api_id, api_hash = get_api_config()

    client = TelegramClient(
        StringSession(session_string) if session_string else StringSession(),
        api_id,
        api_hash
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


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "database": "postgres" if db.use_postgres else "sqlite",
        "api_id_set": bool(os.getenv("API_ID")),
        "api_hash_set": bool(os.getenv("API_HASH")),
        "bot_token_set": bool(os.getenv("BOT_TOKEN"))
    })


@app.route("/login", methods=["POST"])
def login():
    data = get_payload()
    phone = (data.get("phone") or "").strip().replace(" ", "")

    if not phone:
        return jsonify({"success": False, "error": "Telefon raqam kiritilishi shart"}), 400

    if not phone.startswith("+"):
        return jsonify({"success": False, "error": "Raqam + bilan boshlanishi kerak. Masalan: +998901234567"}), 400

    async def _login():
        client = await create_client()

        try:
            result = await client.send_code_request(phone)

            db.save_temp_login(
                phone=phone,
                session_string=client.session.save(),
                phone_code_hash=result.phone_code_hash
            )

            session["phone"] = phone
            session.modified = True

            return jsonify({
                "success": True,
                "message": "Kod Telegram ilovangizga yuborildi"
            })
        finally:
            await client.disconnect()

    try:
        return run_async(_login())

    except PhoneNumberInvalidError:
        return jsonify({"success": False, "error": "Telefon raqam noto'g'ri"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/verify", methods=["POST"])
def verify():
    data = get_payload()
    code = (data.get("code") or "").strip()
    phone = session.get("phone")

    if not phone or not code:
        return jsonify({"success": False, "error": "Kod yoki telefon raqam topilmadi"}), 400

    temp_data = db.get_temp_login(phone)

    if not temp_data:
        return jsonify({"success": False, "error": "Login sessiya topilmadi. Kodni qaytadan oling."}), 400

    async def _verify():
        client = await create_client(temp_data["session_string"])

        try:
            try:
                await client.sign_in(
                    phone=phone,
                    code=code,
                    phone_code_hash=temp_data["phone_code_hash"]
                )
            except SessionPasswordNeededError:
                db.save_temp_login(
                    phone=phone,
                    session_string=client.session.save(),
                    phone_code_hash=temp_data["phone_code_hash"]
                )
                return jsonify({
                    "success": False,
                    "password_required": True,
                    "message": "2 bosqichli parol kerak"
                })

            db.save_session(phone, client.session.save())
            db.delete_temp_login(phone)

            session["user_id"] = phone
            session.modified = True

            return jsonify({"success": True})
        finally:
            await client.disconnect()

    try:
        return run_async(_verify())

    except PhoneCodeInvalidError:
        return jsonify({"success": False, "error": "Kod noto'g'ri kiritildi"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/verify-password", methods=["POST"])
def verify_password():
    data = get_payload()
    password = data.get("password") or ""
    phone = session.get("phone")

    if not phone or not password:
        return jsonify({"success": False, "error": "Parol kiritilishi shart"}), 400

    temp_data = db.get_temp_login(phone)

    if not temp_data:
        return jsonify({"success": False, "error": "Login sessiya topilmadi. Qaytadan kod oling."}), 400

    async def _verify_password():
        client = await create_client(temp_data["session_string"])

        try:
            await client.sign_in(password=password)

            db.save_session(phone, client.session.save())
            db.delete_temp_login(phone)

            session["user_id"] = phone
            session.modified = True

            return jsonify({"success": True})
        finally:
            await client.disconnect()

    try:
        return run_async(_verify_password())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/groups")
def get_groups():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "error": "Avtorizatsiya qilinmagan"}), 401

    async def _get_groups():
        client = await get_authorized_client(user_id)

        if not client:
            return jsonify({"success": False, "error": "Telegram sessiya topilmadi. Qaytadan kiring."}), 401

        try:
            dialogs = await client.get_dialogs(limit=200)
            groups = []

            for dialog in dialogs:
                if dialog.is_group or dialog.is_channel:
                    entity = dialog.entity

                    groups.append({
                        "id": str(dialog.id),
                        "title": dialog.name or "Nomsiz guruh",
                        "type": "channel" if isinstance(entity, Channel) else "group"
                    })

            return jsonify({"success": True, "groups": groups})
        finally:
            await client.disconnect()

    try:
        return run_async(_get_groups())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/schedule", methods=["POST"])
def schedule_message():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "error": "Avtorizatsiya qilinmagan"}), 401

    data = get_payload()

    group_id = str(data.get("group_id") or "").strip()
    group_title = str(data.get("group_title") or "").strip()
    message = str(data.get("message") or "").strip()
    interval = data.get("interval") or 1
    interval_type = data.get("interval_type") or "minutes"

    if not group_id:
        return jsonify({"success": False, "error": "Guruh tanlanishi shart"}), 400

    if not message:
        return jsonify({"success": False, "error": "Xabar matni kiritilishi shart"}), 400

    try:
        interval = int(interval)
    except ValueError:
        interval = 1

    interval = max(interval, 1)

    if interval_type == "hours":
        interval_seconds = interval * 3600
    else:
        interval_seconds = interval * 60

    task_id = db.save_task(
        user_id=user_id,
        group_id=group_id,
        group_title=group_title,
        message=message,
        interval_seconds=interval_seconds
    )

    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Jadval qo'shildi"
    })


@app.route("/api/tasks")
def get_tasks():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "error": "Avtorizatsiya qilinmagan"}), 401

    return jsonify({
        "success": True,
        "tasks": db.get_tasks(user_id)
    })


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"success": False, "error": "Avtorizatsiya qilinmagan"}), 401

    db.delete_task(task_id, user_id=user_id)

    return jsonify({"success": True})


@app.route("/logout")
def logout():
    user_id = session.get("user_id")

    if user_id:
        db.delete_session(user_id)

    session.clear()
    return redirect(url_for("index"))


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Server xatosi",
        "detail": str(error)
    }), 500
