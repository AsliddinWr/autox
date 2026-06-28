import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneCodeInvalidError
from telethon.tl.types import Channel
import asyncio
from datetime import datetime
import json
from utils.database import Database

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# API ma'lumotlari
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Database
db = Database(os.getenv('DATABASE_URL'))

# Vaqtinchalik sessiyalar (production da Redis ishlatish kerak)
temp_sessions = {}

def get_client_from_session(user_id):
    """Sessiyadan client olish"""
    session_data = db.get_session(user_id)
    if session_data:
        client = TelegramClient(
            StringSession(session_data['session_string']), 
            API_ID, 
            API_HASH
        )
        return client
    return None

async def send_scheduled_message(user_id, group_id, message):
    """Rejalashtirilgan xabar yuborish"""
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
                print(f"Xabar yuborildi: {group_id}")
                await client.disconnect()
                return True
    except Exception as e:
        print(f"Xabar yuborishda xatolik: {e}")
    return False

@app.route('/')
def index():
    user_id = session.get('user_id')
    if user_id and db.get_session(user_id):
        return render_template('dashboard.html')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({'error': 'Telefon raqam kiritilishi shart'}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        loop.run_until_complete(client.connect())
        
        result = loop.run_until_complete(client.send_code_request(phone))
        
        session['phone'] = phone
        session['phone_code_hash'] = result.phone_code_hash
        
        # Vaqtinchalik saqlash
        temp_sessions[phone] = {
            'session_string': client.session.save(),
            'phone_code_hash': result.phone_code_hash
        }
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        loop.close()

@app.route('/verify', methods=['POST'])
def verify():
    code = request.form.get('code')
    phone = session.get('phone')
    
    if not phone or not code:
        return jsonify({'error': 'Ma\'lumotlar yetarli emas'}), 400
    
    temp_data = temp_sessions.get(phone)
    if not temp_data:
        return jsonify({'error': 'Sessiya topilmadi'}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        client = TelegramClient(
            StringSession(temp_data['session_string']),
            API_ID,
            API_HASH
        )
        loop.run_until_complete(client.connect())
        
        await client.sign_in(
            phone, 
            code, 
            phone_code_hash=temp_data['phone_code_hash']
        )
        
        # Sessiyani saqlash
        session_string = client.session.save()
        db.save_session(phone, session_string)
        
        session['user_id'] = phone
        del temp_sessions[phone]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        loop.close()

@app.route('/api/groups')
def get_groups():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Avtorizatsiya qilinmagan'}), 401
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        client = get_client_from_session(user_id)
        if not client:
            return jsonify({'error': 'Sessiya topilmadi'}), 401
        
        loop.run_until_complete(client.connect())
        
        if not loop.run_until_complete(client.is_user_authorized()):
            return jsonify({'error': 'Avtorizatsiya qilinmagan'}), 401
        
        dialogs = loop.run_until_complete(client.get_dialogs())
        groups = []
        
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                entity = dialog.entity
                groups.append({
                    'id': str(dialog.id),
                    'title': dialog.name,
                    'type': 'channel' if isinstance(entity, Channel) else 'group'
                })
        
        return jsonify({'groups': groups})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        loop.close()

@app.route('/api/schedule', methods=['POST'])
def schedule_message():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Avtorizatsiya qilinmagan'}), 401
    
    data = request.json
    group_id = data.get('group_id')
    message = data.get('message')
    interval = int(data.get('interval', 60))
    interval_type = data.get('interval_type', 'minutes')
    
    if interval_type == 'minutes':
        interval *= 60
    elif interval_type == 'hours':
        interval *= 3600
    
    # Ma'lumotlar bazasiga saqlash
    task_id = db.save_task(user_id, group_id, message, interval)
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': 'Jadval qo\'shildi'
    })

@app.route('/api/tasks')
def get_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Avtorizatsiya qilinmagan'}), 401
    
    tasks = db.get_tasks(user_id)
    return jsonify({'tasks': tasks})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Avtorizatsiya qilinmagan'}), 401
    
    db.delete_task(task_id)
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        db.delete_session(user_id)
    session.clear()
    return redirect(url_for('index'))

# Vercel uchun handler
def handler(request, context):
    return app(request.environ, start_response)