"""Парсер для PDF файлов."""

from pathlib import Path
import fitz  # PyMuPDF
from .base import BaseParser


class PdfParser(BaseParser):
    """Парсер для извлечения текста из PDF файлов."""

    def extract_text(self, file_path):
        """Извлекает текст из PDF документа."""
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(
                f"Ожидался файл PDF, получен: {file_path.suffix}"
            )

        text_parts = []
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text_parts.append(page.get_text())
        except Exception as e:
            raise ValueError(f"Ошибка чтения PDF: {e}")

        return "\n".join(text_parts)