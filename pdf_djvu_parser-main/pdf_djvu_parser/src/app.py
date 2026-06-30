"""Веб-интерфейс парсера документов на Streamlit."""

import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from database import DatabaseManager
from parsers.djvu_parser import DjvuParser
from parsers.pdf_parser import PdfParser

# настройки страницы
st.set_page_config(
    page_title="Парсер PDF/DJVU",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# константы
DB_PATH = Path("data/parser_database.db")


# вспомогательные функции для работы с БД
def get_db_connection() -> sqlite3.Connection:
    """Создаёт новое соединение с базой данных."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def get_db_stats():
    """Получает статистику из базы данных."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(word_count), 0), "
            "COALESCE(SUM(file_size_bytes), 0) FROM documents"
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_all_documents():
    """Получает список всех документов из БД."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT id, file_name, file_format, file_size_bytes, "
            "parsed_date, word_count FROM documents ORDER BY id DESC"
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_document_text(doc_id: int) -> str:
    """Получает текст документа по ID."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT text_content FROM documents WHERE id = ?",
            (doc_id,),
        )
        result = cursor.fetchone()
        return result[0] if result else ""
    finally:
        conn.close()


def get_format_stats():
    """Получает статистику по форматам файлов."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT file_format, COUNT(*), SUM(word_count), "
            "SUM(file_size_bytes) FROM documents GROUP BY file_format"
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_top_documents(limit: int = 10):
    """Получает топ документов по количеству слов."""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT file_name, word_count, file_size_bytes "
            "FROM documents ORDER BY word_count DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


# инициализация парсеров
@st.cache_resource
def get_parsers() -> tuple[PdfParser, DjvuParser]:
    """Создаёт экземпляры парсеров."""
    return PdfParser(), DjvuParser()


# инициализация БД (только создание таблиц)
def init_database() -> None:
    """Инициализирует базу данных (создаёт таблицы)."""
    db = DatabaseManager(DB_PATH)
    db.close()


# боковая панель
def render_sidebar(djvu_available: bool) -> None:
    """Отрисовывает боковую панель со статистикой."""
    with st.sidebar:
        st.title("📄 Парсер документов")
        st.markdown("---")

        st.subheader("Статистика")
        stats = get_db_stats()
        count, total_words, total_size = stats if stats else (0, 0, 0)

        col1, col2 = st.columns(2)
        col1.metric("Файлов", count)
        col2.metric("Всего слов", f"{total_words:,}".replace(",", " "))

        st.metric("Общий размер", f"{total_size / 1024:.1f} КБ")

        st.markdown("---")
        st.subheader("⚙️ Возможности")
        st.success("✅ PDF — поддерживается")
        if djvu_available:
            st.success("✅ DJVU — поддерживается")
        else:
            st.warning("⚠️ DJVU — не установлено (djvutxt)")

        st.markdown("---")
        st.caption("Итоговый проект курса Python • ТУСУР • 2026")


# главная страница: загрузка файлов
def render_upload_page(
    pdf_parser: PdfParser,
    djvu_parser: DjvuParser,
) -> None:
    """Отрисовывает страницу загрузки и обработки файлов."""
    st.title("📤 Загрузка документов")
    st.markdown(
        "Загрузите PDF или DJVU файлы. Текст будет извлечён "
        "и сохранён в базу данных SQLite."
    )

    # инициализация session_state для результатов
    if "processing_results" not in st.session_state:
        st.session_state.processing_results = None

    uploaded_files = st.file_uploader(
        "Выберите файлы",
        type=["pdf", "djvu"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        if st.button("🚀 Обработать все файлы", type="primary"):
            progress_bar = st.progress(0, text="Обработка...")
            status_container = st.container()

            processed_files = []
            skipped_files = []
            error_files = []

            for i, uploaded_file in enumerate(uploaded_files):
                progress_bar.progress(
                    (i) / len(uploaded_files),
                    text=(
                        f"Обработка {i + 1}/{len(uploaded_files)}: "
                        f"{uploaded_file.name}"
                    ),
                )

                suffix = Path(uploaded_file.name).suffix.lower()

                # проверяем, можно ли обработать этот файл
                if suffix == ".djvu" and not djvu_parser.is_available:
                    skipped_files.append({
                        "name": uploaded_file.name,
                        "reason": "Требуется утилита djvutxt (не установлена)",
                    })
                    continue

                try:
                    # сохраняем во временный файл
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=suffix,
                    ) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = Path(tmp.name)

                    # выбираем парсер
                    if suffix == ".pdf":
                        text = pdf_parser.extract_text(tmp_path)
                    elif suffix == ".djvu":
                        text = djvu_parser.extract_text(tmp_path)
                    else:
                        raise ValueError(
                            f"Неподдерживаемый формат: {suffix}"
                        )

                    # сохраняем в БД
                    db = DatabaseManager(DB_PATH)
                    try:
                        record_id = db.save_document(
                            file_name=uploaded_file.name,
                            file_format=suffix[1:],
                            file_size=uploaded_file.size,
                            text_content=text,
                        )
                    finally:
                        db.close()

                    processed_files.append({
                        "name": uploaded_file.name,
                        "id": record_id,
                    })

                    # удаляем временный файл
                    tmp_path.unlink()

                except Exception as error:
                    error_files.append({
                        "name": uploaded_file.name,
                        "error": str(error),
                    })

            progress_bar.progress(1.0, text="Готово!")

            # сохраняем результаты в session_state
            st.session_state.processing_results = {
                "processed": processed_files,
                "skipped": skipped_files,
                "errors": error_files,
            }

    # показываем результаты из session_state (если есть)
    if st.session_state.processing_results:
        results = st.session_state.processing_results

        st.markdown("---")
        st.subheader("📊 Результаты обработки")

        # успешно обработанные
        if results["processed"]:
            success_msg = (
                f"✅ **Успешно обработано: "
                f"{len(results['processed'])} файл(ов)**\n\n"
            )
            for f in results["processed"]:
                success_msg += f"  • {f['name']} (ID: {f['id']})\n"
            st.success(success_msg)

        # пропущенные
        if results["skipped"]:
            skip_msg = (
                f"⏭️ **Пропущено: "
                f"{len(results['skipped'])} файл(ов)**\n\n"
            )
            for f in results["skipped"]:
                skip_msg += f"  • {f['name']} — {f['reason']}\n"
            st.warning(skip_msg)

        # с ошибками
        if results["errors"]:
            error_msg = (
                f"❌ **С ошибками: "
                f"{len(results['errors'])} файл(ов)**\n\n"
            )
            for f in results["errors"]:
                error_msg += f"  • {f['name']} — {f['error']}\n"
            st.error(error_msg)

        # итоговая статистика
        total = (
            len(results["processed"])
            + len(results["skipped"])
            + len(results["errors"])
        )
        st.markdown(
            f"**Итого:** {total} файл(ов) → "
            f"✅ {len(results['processed'])} обработано, "
            f"⏭️ {len(results['skipped'])} пропущено, "
            f"❌ {len(results['errors'])} с ошибками"
        )

        # кнопка для очистки результатов
        if st.button("🔄 Очистить результаты", key="clear_results"):
            st.session_state.processing_results = None
            st.rerun()


# страница: база данных
def render_database_page() -> None:
    """Отрисовывает страницу с таблицей документов."""
    st.title("🗄️ База данных")

    rows = get_all_documents()

    if not rows:
        st.info("База данных пуста. Загрузите файлы на предыдущей вкладке.")
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "ID", "Файл", "Формат",
            "Размер (байт)", "Дата", "Слов",
        ],
    )
    df["Размер (КБ)"] = (df["Размер (байт)"] / 1024).round(2)

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # управление базой данных
    st.subheader("⚙️ Управление")

    st.markdown("**Удалить запись:**")
    file_options = {
        f"{row[1]} (ID: {row[0]})": row[0] for row in rows
    }
    selected_name = st.selectbox(
        "Выберите документ",
        list(file_options.keys()),
        key="delete_single_select",
    )
    selected_id = file_options[selected_name]

    if st.button(
        "️ Удалить выбранный файл",
        type="secondary",
        key="btn_delete_single",
    ):
        try:
            conn = get_db_connection()
            conn.execute(
                "DELETE FROM documents WHERE id = ?",
                (selected_id,),
            )
            conn.commit()
            conn.close()
            st.success(f"✅ Файл '{selected_name}' удалён из базы данных")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Ошибка при удалении: {e}")

    st.markdown("---")

    # просмотр содержимого
    st.subheader("🔍 Просмотр содержимого документа")

    if rows:
        file_options = {
            f"{row[1]} (ID: {row[0]})": row[0] for row in rows
        }
        selected_name = st.selectbox(
            "Выберите документ",
            list(file_options.keys()),
            key="view_text_select",
        )
        selected_id = file_options[selected_name]

        text = get_document_text(selected_id)

        st.text_area(
            "Извлечённый текст",
            value=text,
            height=400,
            label_visibility="collapsed",
        )

        # кнопка скачивания в формате TXT
        st.markdown("---")
        st.subheader("📥 Скачивание")

        original_name = selected_name.split(" (ID:")[0]
        txt_filename = Path(original_name).stem + ".txt"

        st.download_button(
            label=f"📥 Скачать '{txt_filename}'",
            data=text,
            file_name=txt_filename,
            mime="text/plain",
            type="primary",
        )

        st.caption(f"Файл будет сохранён как: {txt_filename}")


# страница: аналитика
def render_analytics_page() -> None:
    """Отрисовывает страницу со статистикой."""
    st.title("📈 Аналитика")

    # общая статистика
    stats = get_db_stats()
    count, total_words, total_size = stats if stats else (0, 0, 0)

    st.subheader("📊 Общая статистика")
    col1, col2, col3 = st.columns(3)
    col1.metric("Всего документов", count)
    col2.metric(
        "Всего слов",
        f"{total_words:,}".replace(",", " "),
    )
    col3.metric("Общий размер", f"{total_size / 1024:.1f} КБ")

    st.markdown("---")

    # статистика по форматам
    st.subheader("📋 Статистика по форматам")
    format_stats = get_format_stats()

    if format_stats:
        df_formats = pd.DataFrame(
            format_stats,
            columns=[
                "Формат", "Количество файлов",
                "Всего слов", "Размер (байт)",
            ],
        )
        df_formats["Размер (КБ)"] = (
            df_formats["Размер (байт)"] / 1024
        ).round(2)
        st.dataframe(df_formats, use_container_width=True, hide_index=True)
    else:
        st.info("Нет данных для отображения")

    st.markdown("---")

    # топ документов
    st.subheader("🏆 Топ-10 документов по количеству слов")
    top_docs = get_top_documents(10)

    if top_docs:
        df_top = pd.DataFrame(
            top_docs,
            columns=["Файл", "Количество слов", "Размер (байт)"],
        )
        df_top["Размер (КБ)"] = (
            df_top["Размер (байт)"] / 1024
        ).round(2)
        st.dataframe(df_top, use_container_width=True, hide_index=True)
    else:
        st.info("Нет данных для отображения")


# главная функция
def main() -> None:
    """Точка входа Streamlit-приложения."""
    init_database()

    pdf_parser, djvu_parser = get_parsers()
    djvu_available = djvu_parser.is_available

    render_sidebar(djvu_available)

    tab1, tab2, tab3 = st.tabs([
        "📤 Загрузка",
        "🗄️ База данных",
        "📈 Аналитика",
    ])

    with tab1:
        render_upload_page(pdf_parser, djvu_parser)
    with tab2:
        render_database_page()
    with tab3:
        render_analytics_page()


if __name__ == "__main__":
    main()