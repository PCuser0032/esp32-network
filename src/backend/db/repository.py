import json
import sqlite3
from datetime import datetime
from abc import ABC, abstractmethod

# ==========================================
# 1. Интерфейс (Абстракция)
# ==========================================


class TelemetryRepository(ABC):
    @abstractmethod
    def init_db(self):
        """Создает таблицы, если их нет"""
        pass

    @abstractmethod
    def save_telemetry(self, device_id: str, payload: dict):
        """Сохраняет запись телеметрии"""
        pass

# ==========================================
# 2. Реализация для SQLite (Для MVP)
# ==========================================


class SQLiteRepository(TelemetryRepository):
    def __init__(self, db_path="iot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    status TEXT DEFAULT 'offline',
                    last_seen_at TEXT
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    ts TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
            """)
        print(f"[DB] SQLite initialized successfully ({self.db_path}).")

    def save_telemetry(self, device_id: str, payload: dict):
        now_str = datetime.now().isoformat()
        payload_str = json.dumps(payload)  # В SQLite храним JSON как TEXT

        with self.conn:
            # Обновляем или добавляем устройство
            self.conn.execute("""
                INSERT OR REPLACE INTO devices (device_id, status, last_seen_at) 
                VALUES (?, 'online', ?)
            """, (device_id, now_str))

            # Записываем телеметрию
            self.conn.execute("""
                INSERT INTO telemetry (device_id, ts, payload) 
                VALUES (?, ?, ?)
            """, (device_id, now_str, payload_str))

# ==========================================
# 3. Заготовка для PostgreSQL (На будущее)
# ==========================================
# import psycopg
# class PostgresRepository(TelemetryRepository):
#     def __init__(self, dsn):
#         self.dsn = dsn
#     def init_db(self):
#         pass
#     def save_telemetry(self, device_id, payload):
#         pass

# ==========================================
# 4. Фабрика (Выбор БД по конфигу)
# ==========================================


def get_repository(db_type="sqlite", **kwargs):
    if db_type == "sqlite":
        return SQLiteRepository(**kwargs)
    elif db_type == "postgres":
        raise NotImplementedError("PostgreSQL adapter not implemented yet")
    else:
        raise ValueError(f"Unknown DB type: {db_type}")
