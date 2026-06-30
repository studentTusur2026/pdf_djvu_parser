"""Вспомогательные функции для парсера."""

import logging
from pathlib import Path


def setup_logger(log_file=Path("data/parser.log")):
    """Настраивает и возвращает объект логгера.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("document_parser")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(
            log_file,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger