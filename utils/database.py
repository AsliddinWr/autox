import os
import sqlite3
from datetime import datetime


class Database:
    def __init__(self, database_url=None):
        self.database_url = database_url
        self.use_postgres = bool(database_url and database_url.startswith("postgres"))

        if self.use_postgres:
            import psycopg2
            self.conn = psycopg2.connect(database_url)
        else:
            db_path = os.getenv("SQLITE_PATH", "/tmp/database.db")
            self.conn = sqlite3.connect(db_path, check_same_thread=False)

        self.create_tables()

    def placeholder(self):
        return "%s" if self.use_postgres else "?"

    def create_tables(self):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_logins (
                    phone TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    phone_code_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
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
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_logins (
                    phone TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    phone_code_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP
                )
            """)

        self.conn.commit()

    def save_session(self, user_id, session_string):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                INSERT INTO sessions (user_id, session_string)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET session_string = EXCLUDED.session_string
            """, (user_id, session_string))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (user_id, session_string)
                VALUES (?, ?)
            """, (user_id, session_string))

        self.conn.commit()

    def get_session(self, user_id):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(f"SELECT session_string FROM sessions WHERE user_id = {ph}", (user_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return {"session_string": row[0]}

    def delete_session(self, user_id):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(f"DELETE FROM sessions WHERE user_id = {ph}", (user_id,))
        self.conn.commit()

    def save_temp_login(self, phone, session_string, phone_code_hash):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                INSERT INTO temp_logins (phone, session_string, phone_code_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (phone)
                DO UPDATE SET
                    session_string = EXCLUDED.session_string,
                    phone_code_hash = EXCLUDED.phone_code_hash,
                    created_at = CURRENT_TIMESTAMP
            """, (phone, session_string, phone_code_hash))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO temp_logins (phone, session_string, phone_code_hash)
                VALUES (?, ?, ?)
            """, (phone, session_string, phone_code_hash))

        self.conn.commit()

    def get_temp_login(self, phone):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(
            f"SELECT session_string, phone_code_hash FROM temp_logins WHERE phone = {ph}",
            (phone,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "session_string": row[0],
            "phone_code_hash": row[1]
        }

    def delete_temp_login(self, phone):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(f"DELETE FROM temp_logins WHERE phone = {ph}", (phone,))
        self.conn.commit()

    def save_task(self, user_id, group_id, message, interval_seconds):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                INSERT INTO tasks (user_id, group_id, message, interval_seconds)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (user_id, group_id, message, interval_seconds))

            task_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO tasks (user_id, group_id, message, interval_seconds)
                VALUES (?, ?, ?, ?)
            """, (user_id, group_id, message, interval_seconds))

            task_id = cursor.lastrowid

        self.conn.commit()
        return str(task_id)

    def get_tasks(self, user_id):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        if self.use_postgres:
            cursor.execute(f"""
                SELECT id, group_id, message, interval_seconds, is_active, created_at
                FROM tasks
                WHERE user_id = {ph} AND is_active = TRUE
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute(f"""
                SELECT id, group_id, message, interval_seconds, is_active, created_at
                FROM tasks
                WHERE user_id = {ph} AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))

        tasks = []

        for row in cursor.fetchall():
            tasks.append({
                "task_id": str(row[0]),
                "group_id": row[1],
                "message": row[2],
                "interval": row[3],
                "is_active": bool(row[4]),
                "created_at": str(row[5])
            })

        return tasks

    def get_all_active_tasks(self):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                SELECT id, user_id, group_id, message, interval_seconds
                FROM tasks
                WHERE is_active = TRUE
            """)
        else:
            cursor.execute("""
                SELECT id, user_id, group_id, message, interval_seconds
                FROM tasks
                WHERE is_active = 1
            """)

        return cursor.fetchall()

    def update_task_run(self, task_id):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(f"""
            UPDATE tasks
            SET last_run = CURRENT_TIMESTAMP
            WHERE id = {ph}
        """, (task_id,))

        self.conn.commit()

    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        ph = self.placeholder()

        cursor.execute(f"""
            UPDATE tasks
            SET is_active = {True if self.use_postgres else 0}
            WHERE id = {ph}
        """, (task_id,))

        self.conn.commit()

    def close(self):
        self.conn.close()
