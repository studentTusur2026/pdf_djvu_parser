"""Модуль для работы с базой данных SQLite."""

import sqlite3
from datetime import datetime
from pathlib import Path


class DatabaseManager:
    """Менеджер для работы с базой данных SQLite."""

    def __init__(
        self,
        db_path: Path = Path("data/parser_database.db"),
    ) -> None:
        """Инициализирует подключение к БД и создает таблицы."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
        )
        self._create_tables()

    def _create_tables(self) -> None:
        """Создает необходимые таблицы в БД, если их нет."""
        query = """
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_format TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            parsed_date DATETIME NOT NULL,
            word_count INTEGER NOT NULL,
            text_content TEXT NOT NULL
        );
        """
        with self.conn:
            self.conn.execute(query)

    def save_document(
        self,
        file_name: str,
        file_format: str,
        file_size: int,
        text_content: str,
    ) -> int:
        """Сохраняет метаданные и текст документа в БД"""
        
        word_count = len(text_content.split())
        parsed_date = datetime.now().isoformat()

        query = """
        INSERT INTO documents
        (file_name, file_format, file_size_bytes,
         parsed_date, word_count, text_content)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.conn:
            cursor = self.conn.execute(
                query,
                (
                    file_name,
                    file_format,
                    file_size,
                    parsed_date,
                    word_count,
                    text_content,
                ),
            )
        return cursor.lastrowid

    def close(self) -> None:
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()