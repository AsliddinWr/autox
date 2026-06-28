import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
import os
from utils.database import Database

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
db = Database(os.getenv('DATABASE_URL'))

async def check_and_send_messages():
    """Faol tasklarni tekshirish va xabar yuborish"""
    while True:
        try:
            tasks = db.get_all_active_tasks()
            
            for task in tasks:
                task_id, user_id, group_id, message, interval = task
                
                # Oxirgi yuborilgan vaqtni tekshirish
                # Bu yerda last_run vaqtini tekshirish logikasi
                
                try:
                    session_data = db.get_session(user_id)
                    if session_data:
                        client = TelegramClient(
                            StringSession(session_data['session_string']),
                            API_ID,
                            API_HASH
                        )
                        await client.connect()
                        
                        if await client.is_user_authorized():
                            await client.send_message(int(group_id), message)
                            db.update_task_run(task_id)
                            print(f"[{datetime.now()}] Xabar yuborildi: Task {task_id}")
                        
                        await client.disconnect()
                except Exception as e:
                    print(f"Task {task_id} uchun xatolik: {e}")
            
            await asyncio.sleep(60)  # Har 60 sekundda tekshirish
            
        except Exception as e:
            print(f"Scheduler xatolik: {e}")
            await asyncio.sleep(60)

# Bu funksiyani alohida processda ishga tushirish kerak