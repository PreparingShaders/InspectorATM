import sqlite3
from datetime import datetime, timedelta


class Database:
    def __init__(self, db_name="messages.db"):
        """Инициализирует подключение к базе данных"""
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Создает таблицы в базе данных, если их еще нет"""
        with self.conn:
            self.conn.execute("""
                              CREATE TABLE IF NOT EXISTS messages
                              (
                                  id
                                  INTEGER
                                  PRIMARY
                                  KEY
                                  AUTOINCREMENT,
                                  date_time
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
                              CREATE INDEX IF NOT EXISTS idx_atm_datetime
                                  ON messages (atm_id, date_time)
                              """)

    def insert_message(self, atm_id, chat_title, user_info, comment=""):
        """
        Сохраняет сообщение в базу данных с проверкой на дубликаты

        Возвращает True, если сообщение сохранено, False - если дубликат
        """
        # Проверяем, есть ли такое же сообщение в течение последних 2 часов
        two_hours_ago = datetime.now() - timedelta(hours=2)

        cursor = self.conn.execute("""
                                   SELECT 1
                                   FROM messages
                                   WHERE atm_id = ?
                                     AND chat_title = ?
                                     AND user_info = ?
                                     AND comment = ?
                                     AND date_time > ?
                                   """, (atm_id, chat_title, user_info, comment, two_hours_ago))

        if cursor.fetchone() is not None:
            return False  # Дубликат найден

        # Сохраняем сообщение
        with self.conn:
            self.conn.execute("""
                              INSERT INTO messages (atm_id, chat_title, user_info, comment)
                              VALUES (?, ?, ?, ?)
                              """, (atm_id, chat_title, user_info, comment))

        return True

    def get_all_messages(self):
        """Возвращает все сообщения из базы данных"""
        cursor = self.conn.execute("""
                                   SELECT id, date_time, atm_id, chat_title, user_info, comment
                                   FROM messages
                                   ORDER BY date_time DESC
                                   """)
        return cursor.fetchall()

    def get_messages_by_atm(self, atm_id):
        """Возвращает сообщения по ID банкомата"""
        cursor = self.conn.execute("""
                                   SELECT id, date_time, atm_id, chat_title, user_info, comment
                                   FROM messages
                                   WHERE atm_id = ?
                                   ORDER BY date_time DESC
                                   """, (atm_id,))
        return cursor.fetchall()

    def get_messages_by_chat(self, chat_title):
        """Возвращает сообщения по названию чата"""
        cursor = self.conn.execute("""
                                   SELECT id, date_time, atm_id, chat_title, user_info, comment
                                   FROM messages
                                   WHERE chat_title LIKE ?
                                   ORDER BY date_time DESC
                                   """, (f'%{chat_title}%',))
        return cursor.fetchall()

    def get_messages_by_user(self, user_info):
        """Возвращает сообщения по пользователю"""
        cursor = self.conn.execute("""
                                   SELECT id, date_time, atm_id, chat_title, user_info, comment
                                   FROM messages
                                   WHERE user_info LIKE ?
                                   ORDER BY date_time DESC
                                   """, (f'%{user_info}%',))
        return cursor.fetchall()

    def get_messages_in_last_hours(self, hours=24):
        """Возвращает сообщения за последние N часов"""
        time_threshold = datetime.now() - timedelta(hours=hours)
        cursor = self.conn.execute("""
                                   SELECT id, date_time, atm_id, chat_title, user_info, comment
                                   FROM messages
                                   WHERE date_time > ?
                                   ORDER BY date_time DESC
                                   """, (time_threshold,))
        return cursor.fetchall()

    def close(self):
        """Закрывает подключение к базе данных"""
        self.conn.close()