"""Парсер для DJVU файлов."""

import shutil
import subprocess
from pathlib import Path

from .base import BaseParser


class DjvuParser(BaseParser):
    """Парсер для извлечения текста из DJVU файлов.
    Использует системную утилиту djvutxt из пакета DjVuLibre.
    """

    def __init__(self):
        """Проверяет доступность утилиты djvutxt в системе."""
        self._djvutxt_available = shutil.which("djvutxt") is not None

    @property
    def is_available(self):
        """Возвращает True, если djvutxt доступен в системе."""
        return self._djvutxt_available

    def extract_text(self, file_path):
        """Извлекает текст из DJVU документа."""
        if not self._djvutxt_available:
            raise EnvironmentError(
                "Утилита 'djvutxt' не найдена в системе. "
                "Для поддержки DJVU установите DjVuLibre."
            )

        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        try:
            result = subprocess.run(
                ["djvutxt", str(file_path)],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
            )
            return result.stdout
        except subprocess.CalledProcessError as error:
            raise ValueError(f"Ошибка обработки DJVU: {error.stderr}")