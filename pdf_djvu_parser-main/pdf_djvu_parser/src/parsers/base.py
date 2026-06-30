"""Базовый модуль для парсеров документов."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров документов."""

    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        """Извлекает текст из файла.
        
        Args:
            file_path: Путь к файлу для парсинга.
            
        Returns:
            Извлеченный текст в виде строки.
        """
        pass