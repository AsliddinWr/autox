import sqlite3
import json
from datetime import datetime
import os

class Database:
    def __init__(self, database_url=None):
        # Vercel uchun PostgreSQL, lokal uchun SQLite
        if database_url and database_url.startswith('postgres'):
            import psycopg2
            self.conn = psycopg2.connect(database_url)
            self.use_postgres = True
        else:
            self.conn = sqlite3.connect('database.db', check_same_thread=False)
            self.use_postgres = False
        
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Sessiyalar jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                user_id TEXT PRIMARY KEY,
                session_string TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasklar jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                message TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_session(self, user_id, session_string):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (user_id, session_string) 
            VALUES (%s, %s) 
            ON CONFLICT (user_id) 
            DO UPDATE SET session_string = %s
        ''', (user_id, session_string, session_string))
        self.conn.commit()
    
    def get_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT session_string FROM sessions WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        return {'session_string': row[0]} if row else None
    
    def delete_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE user_id = %s', (user_id,))
        self.conn.commit()
    
    def save_task(self, user_id, group_id, message, interval_seconds):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (user_id, group_id, message, interval_seconds)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (user_id, group_id, message, interval_seconds))
        task_id = cursor.fetchone()[0]
        self.conn.commit()
        return task_id
    
    def get_tasks(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, group_id, message, interval_seconds, is_active, created_at
            FROM tasks 
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY created_at DESC
        ''', (user_id,))
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'task_id': str(row[0]),
                'group_id': row[1],
                'message': row[2],
                'interval': row[3],
                'is_active': row[4],
                'created_at': str(row[5])
            })
        return tasks
    
    def get_all_active_tasks(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, user_id, group_id, message, interval_seconds
            FROM tasks 
            WHERE is_active = TRUE
        ''')
        return cursor.fetchall()
    
    def update_task_run(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tasks 
            SET last_run = CURRENT_TIMESTAMP 
            WHERE id = %s
        ''', (task_id,))
        self.conn.commit()
    
    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE tasks SET is_active = FALSE WHERE id = %s', (task_id,))
        self.conn.commit()
    
    def close(self):
        self.conn.close()