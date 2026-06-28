import os
import sys
import asyncio

from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.database import Database

app = Flask(__name__)
db = Database(os.getenv("DATABASE_URL"))


def get_api_config():
    api_id_raw = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    if not api_id_raw or not api_hash:
        raise RuntimeError("API_ID yoki API_HASH env sozlanmagan")

    return int(api_id_raw), api_hash


def check_secret():
    expected = os.getenv("CRON_SECRET")

    if not expected:
        return False

    provided = request.args.get("secret") or request.headers.get("x-cron-secret")
    return provided == expected


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def send_task(task):
    api_id, api_hash = get_api_config()

    session_data = db.get_session(task["user_id"])

    if not session_data:
        raise RuntimeError("User session topilmadi")

    client = TelegramClient(
        StringSession(session_data["session_string"]),
        api_id,
        api_hash
    )

    await client.connect()

    try:
        if not await client.is_user_authorized():
            raise RuntimeError("User Telegram sessiyasi avtorizatsiyadan chiqqan")

        await client.send_message(int(task["group_id"]), task["message"])
    finally:
        await client.disconnect()


@app.route("/api/cron", methods=["GET"])
def cron_runner():
    if not check_secret():
        return jsonify({
            "success": False,
            "error": "CRON_SECRET noto'g'ri yoki sozlanmagan"
        }), 401

    tasks = db.get_due_tasks(limit=10)

    results = []

    for task in tasks:
        try:
            run_async(send_task(task))
            db.mark_task_success(task["task_id"])

            results.append({
                "task_id": task["task_id"],
                "status": "sent",
                "group": task["group_title"]
            })
        except Exception as e:
            db.mark_task_error(task["task_id"], str(e))

            results.append({
                "task_id": task["task_id"],
                "status": "error",
                "error": str(e)
            })

    return jsonify({
        "success": True,
        "processed": len(results),
        "results": results
    })


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "cron ok"})
