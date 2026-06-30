"""Консольный интерфейс парсера документов."""

import argparse
import sys
from pathlib import Path

from database import DatabaseManager
from parsers.djvu_parser import DjvuParser
from parsers.pdf_parser import PdfParser
from utils import setup_logger

# поддерживаемые форматы файлов
SUPPORTED_EXTENSIONS = {".pdf", ".djvu"}


def process_file(file_path, db, logger):
    """Обрабатывает один файл: парсит и сохраняет в БД."""
    suffix = file_path.suffix.lower()
    logger.info(f"Начало обработки файла: {file_path.name}")
    print(f"[*] Обработка: {file_path.name}")

    try:
        if suffix == ".pdf":
            parser = PdfParser()
        elif suffix == ".djvu":
            parser = DjvuParser()
        else:
            logger.warning(f"Неподдерживаемый формат: {suffix}")
            return

        text = parser.extract_text(file_path)
        file_size = file_path.stat().st_size

        record_id = db.save_document(
            file_name=file_path.name,
            file_format=suffix[1:],
            file_size=file_size,
            text_content=text,
        )
        logger.info(f"Файл сохранён в БД. ID: {record_id}")
        print(f"[+] Сохранено в БД (ID: {record_id})")

    except EnvironmentError as error:
        logger.warning(f"Пропущен {file_path.name}: {error}")
        print(f"[!] Пропущен: {file_path.name} — {error}")
    except FileNotFoundError as error:
        logger.error(f"Файл не найден: {error}")
        print(f"[✗] {error}")
    except Exception as error:
        logger.error(f"Ошибка при обработке {file_path.name}: {error}")
        print(f"[] Ошибка в {file_path.name}: {error}")


def main():
    """Точка входа в приложение."""
    # разбираем аргументы командной строки
    arg_parser = argparse.ArgumentParser(
        description="Парсер текстовых данных из PDF и DJVU файлов.",
    )
    arg_parser.add_argument(
        "path",
        type=str,
        help="Путь к файлу или папке с документами.",
    )
    args = arg_parser.parse_args()

    logger = setup_logger()
    db = DatabaseManager()
    target_path = Path(args.path)

    print("\n=== Парсер документов ===")
    print(f"Цель: {target_path}")
    print(f"DjVu поддерживается: {'да' if DjvuParser().is_available else 'нет'}\n")

    try:
        if target_path.is_file():
            process_file(target_path, db, logger)
        elif target_path.is_dir():
            # ищем все подходящие файлы в папке
            files = [
                f for f in target_path.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
            ]
            if not files:
                print("[!] В папке не найдено поддерживаемых файлов.")
                return
            for file in files:
                process_file(file, db, logger)
        else:
            logger.error("Указанный путь не существует.")
            print("[✗] Путь не существует.")
            sys.exit(1)
    finally:
        db.close()
        print("\n=== Готово ===")


if __name__ == "__main__":
    main()