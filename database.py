import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_name="messages.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Структура: id, datetime, atm_id, chat_title, user_info, comment"""
        with self.conn:
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS messages
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  datetime
                                  DATETIME
                                  DEFAULT
                                  CURRENT_TIMESTAMP,
                                  atm_id
                                  TEXT
                                  NOT
                                  NULL,
                                  chat_title
                                  TEXT
                                  NOT
                                  NULL,
                                  user_info
                                  TEXT
                                  NOT
                                  NULL,
                                  comment
                                  TEXT
                              )
                              """)
            self.conn.execute("""
                              CREATE INDEX IF NOT EXISTS idx_atm_datetime ON messages (atm_id, datetime)
                              """)

    def insert_message(self, atm_id, user_info, chat_title, comment=""):
        """Обычная вставка с проверкой на дубликат (2 часа)"""
        cursor = self.conn.execute("""
                                   SELECT 1
                                   FROM messages
                                   WHERE atm_id = ?
                                     AND datetime > datetime('now', '-2 hours') LIMIT 1
                                   """, (atm_id,))

        if cursor.fetchone() is not None:
            return False

        with self.conn:
            self.conn.execute("""
                              INSERT INTO messages (atm_id, chat_title, user_info, comment)
                              VALUES (?, ?, ?, ?)
                              """, (atm_id, chat_title, user_info, comment))
        return True

    def insert_history_message(self, atm_id, user_info, chat_title, comment, dt_string):
        """Метод для импорта (без проверок на дубликаты по времени)"""
        with self.conn:
            # ВАЖНО: порядок полей должен строго соответствовать VALUES
            self.conn.execute("""
                              INSERT INTO messages (atm_id, chat_title, user_info, comment, datetime)
                              VALUES (?, ?, ?, ?, ?)
                              """, (atm_id, chat_title, user_info, comment, dt_string))

    def get_stats_by_chat(self, date_from, date_to):
        """Статистика для отчетов по количеству"""
        query = """
                SELECT chat_title, COUNT(*) as count
                FROM messages
                WHERE datetime >= ? AND datetime <= ?
                GROUP BY chat_title
                ORDER BY count DESC \
                """
        cursor = self.conn.execute(query, [date_from, date_to])
        return cursor.fetchall()

    def count_messages(self, atm_id=None, chat_title=None, date_from=None):
        query = "SELECT COUNT(*) FROM messages WHERE 1=1"
        params = []
        if atm_id:
            query += " AND atm_id = ?";
            params.append(atm_id)
        if chat_title:
            query += " AND chat_title LIKE ?";
            params.append(f"%{chat_title}%")
        if date_from:
            query += " AND datetime >= ?";
            params.append(date_from)

        cursor = self.conn.execute(query, params)
        return cursor.fetchone()[0]

    def search_messages(self, atm_id=None, chat_title=None, date_from=None):
        query = "SELECT id, datetime, atm_id, user_info, chat_title, comment FROM messages WHERE 1=1"
        params = []

        if atm_id:
            query += " AND atm_id = ?"
            params.append(atm_id)
        if chat_title:
            query += " AND chat_title LIKE ?"
            params.append(f"%{chat_title}%")
        if date_from:
            query += " AND datetime >= ?"
            params.append(date_from)

        query += " ORDER BY datetime DESC"
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_messages_in_last_hours(self, hours=24):
        time_threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        query = "SELECT * FROM messages WHERE datetime > ? ORDER BY datetime DESC"
        cursor = self.conn.execute(query, (time_threshold,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()