import os
import sqlite3


class Database:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.use_postgres = bool(
            self.database_url and self.database_url.startswith(("postgres://", "postgresql://"))
        )

        if self.use_postgres:
            import psycopg2
            self.conn = psycopg2.connect(self.database_url)
        else:
            db_path = os.getenv("SQLITE_PATH", "/tmp/autox_database.db")
            self.conn = sqlite3.connect(db_path, check_same_thread=False)

        self.create_tables()
        self.migrate_tables()

    def ph(self):
        return "%s" if self.use_postgres else "?"

    def create_tables(self):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS temp_logins (
                    phone TEXT PRIMARY KEY,
                    session_string TEXT NOT NULL,
                    phone_code_hash TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    group_title TEXT,
                    message TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_run TIMESTAMP WITH TIME ZONE,
                    next_run TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_error TEXT
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
                    group_title TEXT,
                    message TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_error TEXT
                )
            """)

        self.conn.commit()

    def migrate_tables(self):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS group_title TEXT")
            cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS next_run TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
            cursor.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_error TEXT")
        else:
            cursor.execute("PRAGMA table_info(tasks)")
            columns = {row[1] for row in cursor.fetchall()}

            if "group_title" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN group_title TEXT")
            if "next_run" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN next_run TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            if "last_error" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN last_error TEXT")

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
        cursor.execute(
            f"SELECT session_string FROM sessions WHERE user_id = {self.ph()}",
            (user_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        return {"session_string": row[0]}

    def delete_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            f"DELETE FROM sessions WHERE user_id = {self.ph()}",
            (user_id,)
        )
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
                    created_at = NOW()
            """, (phone, session_string, phone_code_hash))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO temp_logins (phone, session_string, phone_code_hash)
                VALUES (?, ?, ?)
            """, (phone, session_string, phone_code_hash))

        self.conn.commit()

    def get_temp_login(self, phone):
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT session_string, phone_code_hash
            FROM temp_logins
            WHERE phone = {self.ph()}
            """,
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
        cursor.execute(
            f"DELETE FROM temp_logins WHERE phone = {self.ph()}",
            (phone,)
        )
        self.conn.commit()

    def save_task(self, user_id, group_id, group_title, message, interval_seconds):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                INSERT INTO tasks (
                    user_id, group_id, group_title, message, interval_seconds, next_run
                )
                VALUES (%s, %s, %s, %s, %s, NOW() + (%s * INTERVAL '1 second'))
                RETURNING id
            """, (user_id, group_id, group_title, message, interval_seconds, interval_seconds))
            task_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO tasks (
                    user_id, group_id, group_title, message, interval_seconds, next_run
                )
                VALUES (?, ?, ?, ?, ?, datetime('now', '+' || ? || ' seconds'))
            """, (user_id, group_id, group_title, message, interval_seconds, interval_seconds))
            task_id = cursor.lastrowid

        self.conn.commit()
        return str(task_id)

    def get_tasks(self, user_id):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                SELECT id, group_id, group_title, message, interval_seconds,
                       is_active, created_at, last_run, next_run, last_error
                FROM tasks
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT id, group_id, group_title, message, interval_seconds,
                       is_active, created_at, last_run, next_run, last_error
                FROM tasks
                WHERE user_id = ? AND is_active = 1
                ORDER BY created_at DESC
            """, (user_id,))

        tasks = []

        for row in cursor.fetchall():
            tasks.append({
                "task_id": str(row[0]),
                "group_id": row[1],
                "group_title": row[2] or row[1],
                "message": row[3],
                "interval_seconds": row[4],
                "is_active": bool(row[5]),
                "created_at": str(row[6]),
                "last_run": str(row[7]) if row[7] else None,
                "next_run": str(row[8]) if row[8] else None,
                "last_error": row[9]
            })

        return tasks

    def get_due_tasks(self, limit=10):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                SELECT id, user_id, group_id, group_title, message, interval_seconds
                FROM tasks
                WHERE is_active = TRUE AND next_run <= NOW()
                ORDER BY next_run ASC
                LIMIT %s
            """, (limit,))
        else:
            cursor.execute("""
                SELECT id, user_id, group_id, group_title, message, interval_seconds
                FROM tasks
                WHERE is_active = 1 AND next_run <= CURRENT_TIMESTAMP
                ORDER BY next_run ASC
                LIMIT ?
            """, (limit,))

        tasks = []

        for row in cursor.fetchall():
            tasks.append({
                "task_id": str(row[0]),
                "user_id": row[1],
                "group_id": row[2],
                "group_title": row[3] or row[2],
                "message": row[4],
                "interval_seconds": int(row[5])
            })

        return tasks

    def mark_task_success(self, task_id):
        cursor = self.conn.cursor()

        if self.use_postgres:
            cursor.execute("""
                UPDATE tasks
                SET last_run = NOW(),
                    next_run = NOW() + (interval_seconds * INTERVAL '1 second'),
                    last_error = NULL
                WHERE id = %s
            """, (task_id,))
        else:
            cursor.execute("""
                UPDATE tasks
                SET last_run = CURRENT_TIMESTAMP,
                    next_run = datetime('now', '+' || interval_seconds || ' seconds'),
                    last_error = NULL
                WHERE id = ?
            """, (task_id,))

        self.conn.commit()

    def mark_task_error(self, task_id, error):
        cursor = self.conn.cursor()
        error = str(error)[:500]

        if self.use_postgres:
            cursor.execute("""
                UPDATE tasks
                SET last_run = NOW(),
                    next_run = NOW() + (interval_seconds * INTERVAL '1 second'),
                    last_error = %s
                WHERE id = %s
            """, (error, task_id))
        else:
            cursor.execute("""
                UPDATE tasks
                SET last_run = CURRENT_TIMESTAMP,
                    next_run = datetime('now', '+' || interval_seconds || ' seconds'),
                    last_error = ?
                WHERE id = ?
            """, (error, task_id))

        self.conn.commit()

    def delete_task(self, task_id, user_id=None):
        cursor = self.conn.cursor()

        if user_id:
            if self.use_postgres:
                cursor.execute("""
                    UPDATE tasks SET is_active = FALSE
                    WHERE id = %s AND user_id = %s
                """, (task_id, user_id))
            else:
                cursor.execute("""
                    UPDATE tasks SET is_active = 0
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id))
        else:
            if self.use_postgres:
                cursor.execute("UPDATE tasks SET is_active = FALSE WHERE id = %s", (task_id,))
            else:
                cursor.execute("UPDATE tasks SET is_active = 0 WHERE id = ?", (task_id,))

        self.conn.commit()

    def close(self):
        self.conn.close()
