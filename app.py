import shutil
import sqlite3
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


DB_NAME = "week_planner.db"
DB_PATH = Path(DB_NAME)
BACKUP_DIR = Path("backups")


DAY_TYPES = ["Ночная смена", "Дневная смена", "Отдых"]

DAY_THEME_PRESETS = {
    "Ночная смена": "Работа, заявки, журнал смены, сон, восстановление",
    "Дневная смена": "Работа, монтажи, заявки, отчёт смены, лёгкое обучение",
    "Отдых": "Сон, семья, личные дела, Python, спорт, финансы"
}

DAY_TYPE_COLORS = {
    "Ночная смена": "#141827",
    "Дневная смена": "#F4F8FB",
    "Отдых": "#F3FBF5"
}

DEFAULT_CATEGORIES = [
    "Работа",
    "Python",
    "Английский",
    "Спорт",
    "Дом",
    "Финансы",
    "Личное",
    "Здоровье",
    "Семья",
    "Машина",
    "Учёба",
    "Проекты",
    "Отдых",
    "КИПиА",
    "АСУ ТП"
]

STATUSES = ["Запланировано", "Выполнено", "Частично", "Пропущено"]
PRIORITIES = ["Низкий", "Средний", "Высокий", "Критичный"]

SKIP_REASONS = [
    "",
    "Усталость",
    "Не хватило времени",
    "Забыл",
    "Плохое самочувствие",
    "Работа задержала",
    "Не было настроения",
    "Семейные дела",
    "Другое"
]

WORK_TYPES = [
    "Вызов",
    "Заявка",
    "Монтаж",
    "Демонтаж",
    "Калибровка",
    "Проверка сигнала",
    "Проверка питания",
    "Проверка кабеля",
    "Замена датчика",
    "Настройка прибора",
    "Чистка датчика",
    "Осмотр",
    "Плановая работа",
    "Аварийная работа",
    "Совместно с механиками",
    "Совместно с электриками",
    "Другое"
]

WORK_STATUSES = [
    "Открыто",
    "В работе",
    "Завершено",
    "Передано следующей смене",
    "Ждём механиков",
    "Ждём электриков",
    "Ждём запчасть",
    "Неисправность не подтвердилась"
]

DEFAULT_INCOME_CATEGORIES = [
    "Зарплата",
    "Аванс",
    "Премия",
    "Такси / подработка",
    "Возврат долга",
    "Депозит / проценты",
    "Подарок",
    "Другое"
]

DEFAULT_EXPENSE_CATEGORIES = [
    "Ипотека",
    "Кредиты",
    "Продукты",
    "Кафе",
    "Бензин",
    "Машина",
    "Семья",
    "Связь / интернет",
    "Одежда",
    "Здоровье",
    "Спорт",
    "Обучение",
    "Развлечения",
    "Подарки",
    "Такси / транспорт",
    "Дорога на вахту",
    "Вахта",
    "Отдых",
    "Накопления",
    "Другое"
]

PAYMENT_METHODS = [
    "Kaspi",
    "Halyk",
    "Наличные",
    "Карта",
    "Перевод",
    "Депозит",
    "Другое"
]

STATUS_COLORS = {
    "Выполнено": "#2EAD4F",
    "Частично": "#F2C94C",
    "Пропущено": "#EB5757",
    "Запланировано": "#8E8E93"
}

PRIORITY_COLORS = {
    "Низкий": "#56CCF2",
    "Средний": "#2F80ED",
    "Высокий": "#F2994A",
    "Критичный": "#EB5757"
}

TIME_PERIOD_COLORS = {
    "Утро": "#56CCF2",
    "День": "#2F80ED",
    "Вечер": "#9B51E0",
    "Ночь": "#2D3436",
    "Неизвестно": "#8E8E93"
}

WEEKDAY_ORDER = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]

WEEKDAY_SHORT = {
    "Понедельник": "Пн",
    "Вторник": "Вт",
    "Среда": "Ср",
    "Четверг": "Чт",
    "Пятница": "Пт",
    "Суббота": "Сб",
    "Воскресенье": "Вс"
}

WEEKDAY_MAP = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
}

WEEKDAY_INDEX = {
    "Понедельник": 0,
    "Вторник": 1,
    "Среда": 2,
    "Четверг": 3,
    "Пятница": 4,
    "Суббота": 5,
    "Воскресенье": 6
}


# -----------------------------
# Database
# -----------------------------

def get_connection():
    return sqlite3.connect(DB_NAME)


def add_column_if_missing(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def create_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_date TEXT NOT NULL,
            start_time TEXT DEFAULT '09:00',
            duration_minutes INTEGER DEFAULT 30,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'Запланировано',
            priority TEXT DEFAULT 'Средний',
            weight INTEGER DEFAULT 1,
            skip_reason TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    for column_name, column_type in {
        "start_time": "TEXT DEFAULT '09:00'",
        "duration_minutes": "INTEGER DEFAULT 30",
        "status": "TEXT DEFAULT 'Запланировано'",
        "priority": "TEXT DEFAULT 'Средний'",
        "weight": "INTEGER DEFAULT 1",
        "skip_reason": "TEXT DEFAULT ''",
        "comment": "TEXT DEFAULT ''",
        "created_at": "TEXT DEFAULT ''"
    }.items():
        add_column_if_missing(cursor, "tasks", column_name, column_type)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS template_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT DEFAULT 'Основной',
            weekday TEXT NOT NULL,
            start_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT DEFAULT 'Средний',
            weight INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS year_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_date TEXT UNIQUE NOT NULL,
            day_type TEXT NOT NULL,
            theme TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_date TEXT NOT NULL,
            shift_type TEXT NOT NULL,
            area TEXT DEFAULT '',
            equipment TEXT DEFAULT '',
            tag TEXT DEFAULT '',
            work_type TEXT DEFAULT '',
            request_number TEXT DEFAULT '',
            problem TEXT DEFAULT '',
            action_taken TEXT DEFAULT '',
            result TEXT DEFAULT '',
            status TEXT DEFAULT '',
            handover_to TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(name, category_type)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budget_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_date TEXT NOT NULL,
            tx_type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_budget_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_month TEXT NOT NULL,
            category TEXT NOT NULL,
            planned_amount REAL NOT NULL,
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE(plan_month, category)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline TEXT DEFAULT '',
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for category in DEFAULT_INCOME_CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO budget_categories (name, category_type, created_at) VALUES (?, ?, ?)",
            (category, "Доход", now_text)
        )

    for category in DEFAULT_EXPENSE_CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO budget_categories (name, category_type, created_at) VALUES (?, ?, ?)",
            (category, "Расход", now_text)
        )

    cursor.execute("SELECT COUNT(*) FROM categories")
    category_count = cursor.fetchone()[0]

    if category_count == 0:
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for category in DEFAULT_CATEGORIES:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, created_at) VALUES (?, ?)",
                (category, now_text)
            )

    conn.commit()
    conn.close()


# -----------------------------
# Categories
# -----------------------------

def load_categories():
    conn = get_connection()
    df = pd.read_sql_query("SELECT name FROM categories ORDER BY name", conn)
    conn.close()

    if df.empty:
        return DEFAULT_CATEGORIES

    return df["name"].tolist()


def add_category(name):
    clean_name = name.strip()

    if not clean_name:
        return False, "Категория пустая"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO categories (name, created_at) VALUES (?, ?)",
            (clean_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, "Категория добавлена"
    except sqlite3.IntegrityError:
        return False, "Такая категория уже есть"
    finally:
        conn.close()


def delete_category_from_settings(name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE name = ?", (name,))
    conn.commit()
    conn.close()


def rename_category(old_name, new_name):
    old_name = old_name.strip()
    new_name = new_name.strip()

    if not old_name or not new_name:
        return False, "Название не должно быть пустым"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE categories SET name = ? WHERE name = ?", (new_name, old_name))

        for table_name in ["tasks", "template_tasks"]:
            cursor.execute(f"SELECT id, category FROM {table_name}")
            rows = cursor.fetchall()

            for row_id, category_text in rows:
                parts = [part.strip() for part in str(category_text).split(",") if part.strip()]
                updated_parts = [new_name if part == old_name else part for part in parts]
                cursor.execute(
                    f"UPDATE {table_name} SET category = ? WHERE id = ?",
                    (", ".join(updated_parts), row_id)
                )

        conn.commit()
        return True, "Категория переименована"
    except sqlite3.IntegrityError:
        return False, "Категория с таким именем уже есть"
    finally:
        conn.close()


# -----------------------------
# Year plan
# -----------------------------

def upsert_year_plan(plan_date, day_type, theme, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO year_plan (plan_date, day_type, theme, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(plan_date) DO UPDATE SET
            day_type = excluded.day_type,
            theme = excluded.theme,
            comment = excluded.comment
    """, (
        plan_date,
        day_type,
        theme,
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def delete_year_plan(plan_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM year_plan WHERE plan_date = ?", (plan_date,))
    conn.commit()
    conn.close()


def load_year_plan():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            id,
            plan_date AS 'Дата',
            day_type AS 'Тип_дня',
            theme AS 'Тема',
            comment AS 'Комментарий',
            created_at AS 'Создано'
        FROM year_plan
        ORDER BY plan_date
    """, conn)
    conn.close()
    return df


def get_day_plan(selected_date):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT day_type, theme, comment
        FROM year_plan
        WHERE plan_date = ?
    """, (str(selected_date),))

    row = cursor.fetchone()
    conn.close()

    if row:
        day_type, theme, comment = row
        return {
            "day_type": day_type,
            "theme": theme or DAY_THEME_PRESETS.get(day_type, ""),
            "comment": comment or ""
        }

    return {
        "day_type": "Не задано",
        "theme": "Тип дня не задан в годовом плане",
        "comment": ""
    }


def apply_theme_css(day_type):
    """
    Мягкие светлые темы по типу дня.
    Не делаем тёмный фон, чтобы глаза не уставали.
    """
    if day_type == "Ночная смена":
        background = "linear-gradient(135deg, #EEF4FF 0%, #E8EEF8 45%, #F8FAFC 100%)"
        text_color = "#111827"
        card_bg = "rgba(255, 255, 255, 0.88)"
        border = "rgba(99, 102, 241, 0.20)"
        accent = "#4F46E5"
        tab_bg = "rgba(238, 244, 255, 0.85)"

    elif day_type == "Дневная смена":
        background = "linear-gradient(135deg, #F8FBFF 0%, #EAF7FF 45%, #F9FAFB 100%)"
        text_color = "#111827"
        card_bg = "rgba(255, 255, 255, 0.90)"
        border = "rgba(14, 165, 233, 0.20)"
        accent = "#0284C7"
        tab_bg = "rgba(234, 247, 255, 0.85)"

    elif day_type == "Отдых":
        background = "linear-gradient(135deg, #F7FFF9 0%, #EAF8EF 45%, #FBFDFB 100%)"
        text_color = "#102A1D"
        card_bg = "rgba(255, 255, 255, 0.90)"
        border = "rgba(34, 197, 94, 0.20)"
        accent = "#16A34A"
        tab_bg = "rgba(234, 248, 239, 0.85)"

    else:
        background = "linear-gradient(135deg, #FFFFFF 0%, #F3F6FA 100%)"
        text_color = "#111827"
        card_bg = "rgba(255, 255, 255, 0.90)"
        border = "rgba(148, 163, 184, 0.20)"
        accent = "#64748B"
        tab_bg = "rgba(243, 246, 250, 0.85)"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {background};
            color: {text_color};
        }}

        [data-testid="stHeader"] {{
            background: rgba(0, 0, 0, 0);
        }}

        .block-container {{
            padding-top: 2rem;
        }}

        h1, h2, h3, h4, h5, h6, p, label, span {{
            color: {text_color};
        }}

        div[data-testid="stMetric"],
        div[data-testid="stExpander"],
        div[data-testid="stForm"] {{
            background: {card_bg};
            border: 1px solid {border};
            border-radius: 18px;
            padding: 12px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }}

        div[data-testid="stAlert"] {{
            border-radius: 16px;
            border: 1px solid {border};
        }}

        button[kind="primary"], .stButton > button {{
            border-radius: 12px;
            border: 1px solid {border};
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            background: {tab_bg};
            border-radius: 16px;
            padding: 6px;
        }}

        .stTabs [data-baseweb="tab"] {{
            border-radius: 12px;
            padding: 8px 12px;
        }}

        .stTabs [aria-selected="true"] {{
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid {border};
            color: {accent};
            font-weight: 700;
        }}

        section[data-testid="stSidebar"] {{
            background: {card_bg};
            border-right: 1px solid {border};
        }}

        div[data-testid="stDataFrame"] {{
            background: rgba(255, 255, 255, 0.82);
            border-radius: 16px;
        }}

        hr {{
            border-color: {border};
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# Tasks
# -----------------------------

def add_task(task_date, start_time, duration_minutes, title, categories, priority, weight):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tasks (
            task_date,
            start_time,
            duration_minutes,
            title,
            category,
            status,
            priority,
            weight,
            skip_reason,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        task_date,
        start_time,
        duration_minutes,
        title,
        categories,
        "Запланировано",
        priority,
        weight,
        "",
        "",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_tasks():
    conn = get_connection()

    df = pd.read_sql_query("""
        SELECT
            id,
            task_date AS 'Дата',
            start_time AS 'Время',
            duration_minutes AS 'Длительность_мин',
            title AS 'Задача',
            category AS 'Категории',
            status AS 'Статус',
            priority AS 'Приоритет',
            weight AS 'Вес',
            skip_reason AS 'Причина_пропуска',
            comment AS 'Комментарий',
            created_at AS 'Создано'
        FROM tasks
        ORDER BY task_date, start_time, id
    """, conn)

    conn.close()

    if not df.empty:
        df["Вес"] = pd.to_numeric(df["Вес"], errors="coerce").fillna(1).astype(int)
        df["Длительность_мин"] = pd.to_numeric(df["Длительность_мин"], errors="coerce").fillna(30).astype(int)
        df["Приоритет"] = df["Приоритет"].fillna("Средний")
        df["Причина_пропуска"] = df["Причина_пропуска"].fillna("")
        df["Комментарий"] = df["Комментарий"].fillna("")

    return df


def update_task_status(task_id, new_status, skip_reason, comment):
    conn = get_connection()
    cursor = conn.cursor()

    if new_status != "Пропущено":
        skip_reason = ""

    cursor.execute("""
        UPDATE tasks
        SET status = ?, skip_reason = ?, comment = ?
        WHERE id = ?
    """, (
        new_status,
        skip_reason,
        comment,
        task_id
    ))

    conn.commit()
    conn.close()


def update_task_details(task_id, task_date, start_time, duration_minutes, title, categories, status, priority, weight, skip_reason, comment):
    conn = get_connection()
    cursor = conn.cursor()

    if status != "Пропущено":
        skip_reason = ""

    cursor.execute("""
        UPDATE tasks
        SET
            task_date = ?,
            start_time = ?,
            duration_minutes = ?,
            title = ?,
            category = ?,
            status = ?,
            priority = ?,
            weight = ?,
            skip_reason = ?,
            comment = ?
        WHERE id = ?
    """, (
        task_date,
        start_time,
        duration_minutes,
        title,
        categories,
        status,
        priority,
        weight,
        skip_reason,
        comment,
        task_id
    ))

    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# -----------------------------
# Work logs
# -----------------------------

def add_work_log(work_date, shift_type, area, equipment, tag, work_type, request_number, problem, action_taken, result, status, handover_to, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO work_logs (
            work_date,
            shift_type,
            area,
            equipment,
            tag,
            work_type,
            request_number,
            problem,
            action_taken,
            result,
            status,
            handover_to,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        work_date,
        shift_type,
        area,
        equipment,
        tag,
        work_type,
        request_number,
        problem,
        action_taken,
        result,
        status,
        handover_to,
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_work_logs():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            id,
            work_date AS 'Дата',
            shift_type AS 'Смена',
            area AS 'Участок',
            equipment AS 'Оборудование',
            tag AS 'TAG',
            work_type AS 'Тип_работы',
            request_number AS 'Заявка',
            problem AS 'Проблема',
            action_taken AS 'Что_сделал',
            result AS 'Результат',
            status AS 'Статус',
            handover_to AS 'Кому_передано',
            comment AS 'Комментарий',
            created_at AS 'Создано'
        FROM work_logs
        ORDER BY work_date DESC, id DESC
    """, conn)
    conn.close()
    return df


def update_work_log(log_id, work_date, shift_type, area, equipment, tag, work_type, request_number, problem, action_taken, result, status, handover_to, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE work_logs
        SET
            work_date = ?,
            shift_type = ?,
            area = ?,
            equipment = ?,
            tag = ?,
            work_type = ?,
            request_number = ?,
            problem = ?,
            action_taken = ?,
            result = ?,
            status = ?,
            handover_to = ?,
            comment = ?
        WHERE id = ?
    """, (
        work_date,
        shift_type,
        area,
        equipment,
        tag,
        work_type,
        request_number,
        problem,
        action_taken,
        result,
        status,
        handover_to,
        comment,
        log_id
    ))

    conn.commit()
    conn.close()


def delete_work_log(log_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM work_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


# -----------------------------
# Budget
# -----------------------------

def load_budget_categories(category_type=None):
    conn = get_connection()

    if category_type:
        df = pd.read_sql_query(
            "SELECT id, name, category_type FROM budget_categories WHERE category_type = ? ORDER BY name",
            conn,
            params=(category_type,)
        )
    else:
        df = pd.read_sql_query(
            "SELECT id, name, category_type FROM budget_categories ORDER BY category_type, name",
            conn
        )

    conn.close()
    return df


def add_budget_category(name, category_type):
    clean_name = name.strip()

    if not clean_name:
        return False, "Название категории пустое"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO budget_categories (name, category_type, created_at) VALUES (?, ?, ?)",
            (clean_name, category_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, "Категория бюджета добавлена"
    except sqlite3.IntegrityError:
        return False, "Такая категория уже есть"
    finally:
        conn.close()


def delete_budget_category(category_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budget_categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()


def add_budget_transaction(tx_date, tx_type, category, amount, payment_method, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO budget_transactions (
            tx_date,
            tx_type,
            category,
            amount,
            payment_method,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        tx_date,
        tx_type,
        category,
        float(amount),
        payment_method,
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_budget_transactions():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            id,
            tx_date AS 'Дата',
            tx_type AS 'Тип',
            category AS 'Категория',
            amount AS 'Сумма',
            payment_method AS 'Способ_оплаты',
            comment AS 'Комментарий',
            created_at AS 'Создано'
        FROM budget_transactions
        ORDER BY tx_date DESC, id DESC
    """, conn)
    conn.close()

    if not df.empty:
        df["Сумма"] = pd.to_numeric(df["Сумма"], errors="coerce").fillna(0)
        df["Дата_dt"] = pd.to_datetime(df["Дата"], errors="coerce")
        df["Месяц"] = df["Дата_dt"].dt.to_period("M").astype(str)

        year_plan_df = load_year_plan()
        if not year_plan_df.empty:
            small_plan = year_plan_df[["Дата", "Тип_дня"]].copy()
            df = df.merge(small_plan, on="Дата", how="left")
        else:
            df["Тип_дня"] = "Не задано"

        df["Тип_дня"] = df["Тип_дня"].fillna("Не задано")

    return df


def delete_budget_transaction(tx_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budget_transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()


def upsert_monthly_plan(plan_month, category, planned_amount, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO monthly_budget_plan (plan_month, category, planned_amount, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(plan_month, category) DO UPDATE SET
            planned_amount = excluded.planned_amount,
            comment = excluded.comment
    """, (
        plan_month,
        category,
        float(planned_amount),
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_monthly_plan(plan_month=None):
    conn = get_connection()

    if plan_month:
        df = pd.read_sql_query("""
            SELECT
                id,
                plan_month AS 'Месяц',
                category AS 'Категория',
                planned_amount AS 'План',
                comment AS 'Комментарий',
                created_at AS 'Создано'
            FROM monthly_budget_plan
            WHERE plan_month = ?
            ORDER BY category
        """, conn, params=(plan_month,))
    else:
        df = pd.read_sql_query("""
            SELECT
                id,
                plan_month AS 'Месяц',
                category AS 'Категория',
                planned_amount AS 'План',
                comment AS 'Комментарий',
                created_at AS 'Создано'
            FROM monthly_budget_plan
            ORDER BY plan_month DESC, category
        """, conn)

    conn.close()

    if not df.empty:
        df["План"] = pd.to_numeric(df["План"], errors="coerce").fillna(0)

    return df


def delete_monthly_plan(plan_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monthly_budget_plan WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()


def add_savings_goal(name, target_amount, current_amount, deadline, comment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO savings_goals (
            name,
            target_amount,
            current_amount,
            deadline,
            comment,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        name,
        float(target_amount),
        float(current_amount),
        str(deadline) if deadline else "",
        comment,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_savings_goals():
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            id,
            name AS 'Цель',
            target_amount AS 'Цель_сумма',
            current_amount AS 'Сейчас',
            deadline AS 'Срок',
            comment AS 'Комментарий',
            created_at AS 'Создано'
        FROM savings_goals
        ORDER BY id DESC
    """, conn)
    conn.close()

    if not df.empty:
        df["Цель_сумма"] = pd.to_numeric(df["Цель_сумма"], errors="coerce").fillna(0)
        df["Сейчас"] = pd.to_numeric(df["Сейчас"], errors="coerce").fillna(0)
        df["Прогресс_%"] = df.apply(
            lambda row: row["Сейчас"] / row["Цель_сумма"] * 100 if row["Цель_сумма"] > 0 else 0,
            axis=1
        )

    return df


def update_savings_goal(goal_id, current_amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (float(current_amount), goal_id))
    conn.commit()
    conn.close()


def delete_savings_goal(goal_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()


def get_budget_month_summary(transactions_df, plan_month):
    if transactions_df.empty:
        return pd.DataFrame(), 0, 0, 0

    month_df = transactions_df[transactions_df["Месяц"] == plan_month].copy()

    income_total = month_df[month_df["Тип"] == "Доход"]["Сумма"].sum()
    expense_total = month_df[month_df["Тип"] == "Расход"]["Сумма"].sum()
    balance = income_total - expense_total

    expense_by_category = month_df[month_df["Тип"] == "Расход"].groupby("Категория")["Сумма"].sum().reset_index()
    expense_by_category = expense_by_category.rename(columns={"Сумма": "Факт"})

    plan_df = load_monthly_plan(plan_month)

    if plan_df.empty:
        summary_df = expense_by_category.copy()
        summary_df["План"] = 0
    else:
        summary_df = plan_df[["Категория", "План"]].merge(expense_by_category, on="Категория", how="outer")
        summary_df["План"] = summary_df["План"].fillna(0)
        summary_df["Факт"] = summary_df["Факт"].fillna(0)

    if not summary_df.empty:
        summary_df["Разница"] = summary_df["План"] - summary_df["Факт"]
        summary_df["Использовано_%"] = summary_df.apply(
            lambda row: row["Факт"] / row["План"] * 100 if row["План"] > 0 else 0,
            axis=1
        )
        summary_df = summary_df.sort_values("Факт", ascending=False)

    return summary_df, income_total, expense_total, balance


# -----------------------------
# Templates
# -----------------------------

def add_template_task(template_name, weekday, start_time, duration_minutes, title, categories, priority, weight):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO template_tasks (
            template_name,
            weekday,
            start_time,
            duration_minutes,
            title,
            category,
            priority,
            weight,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        template_name,
        weekday,
        start_time,
        duration_minutes,
        title,
        categories,
        priority,
        weight,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_template_tasks(template_name=None):
    conn = get_connection()

    if template_name:
        df = pd.read_sql_query("""
            SELECT
                id,
                template_name AS 'Шаблон',
                weekday AS 'День_недели',
                start_time AS 'Время',
                duration_minutes AS 'Длительность_мин',
                title AS 'Задача',
                category AS 'Категории',
                priority AS 'Приоритет',
                weight AS 'Вес',
                created_at AS 'Создано'
            FROM template_tasks
            WHERE template_name = ?
            ORDER BY id
        """, conn, params=(template_name,))
    else:
        df = pd.read_sql_query("""
            SELECT
                id,
                template_name AS 'Шаблон',
                weekday AS 'День_недели',
                start_time AS 'Время',
                duration_minutes AS 'Длительность_мин',
                title AS 'Задача',
                category AS 'Категории',
                priority AS 'Приоритет',
                weight AS 'Вес',
                created_at AS 'Создано'
            FROM template_tasks
            ORDER BY template_name, id
        """, conn)

    conn.close()

    if not df.empty:
        df["Вес"] = pd.to_numeric(df["Вес"], errors="coerce").fillna(1).astype(int)
        df["Длительность_мин"] = pd.to_numeric(df["Длительность_мин"], errors="coerce").fillna(30).astype(int)

    return df


def delete_template_task(template_task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM template_tasks WHERE id = ?", (template_task_id,))
    conn.commit()
    conn.close()


def load_template_names():
    df = load_template_tasks()

    if df.empty:
        return ["Основной"]

    names = sorted(df["Шаблон"].dropna().unique().tolist())
    return names if names else ["Основной"]


# -----------------------------
# Time helpers
# -----------------------------

def get_start_datetime(task_date, start_time):
    try:
        return datetime.strptime(f"{task_date} {start_time}", "%Y-%m-%d %H:%M")
    except Exception:
        return None


def get_task_interval(task_date, start_time, duration_minutes):
    start_datetime = get_start_datetime(task_date, start_time)

    if not start_datetime:
        return None, None

    end_datetime = start_datetime + timedelta(minutes=int(duration_minutes))
    return start_datetime, end_datetime


def find_time_conflict(task_date, start_time, duration_minutes, exclude_task_id=None):
    df = load_tasks()

    if df.empty:
        return None

    new_start, new_end = get_task_interval(task_date, start_time, duration_minutes)

    if not new_start or not new_end:
        return None

    same_day_tasks = df[df["Дата"] == str(task_date)]

    for _, row in same_day_tasks.iterrows():
        if exclude_task_id is not None and int(row["id"]) == int(exclude_task_id):
            continue

        existing_start, existing_end = get_task_interval(row["Дата"], row["Время"], row["Длительность_мин"])

        if not existing_start or not existing_end:
            continue

        if new_start < existing_end and new_end > existing_start:
            return row

    return None


def get_end_time(task_date, start_time, duration_minutes):
    try:
        _, end_datetime = get_task_interval(task_date, start_time, duration_minutes)

        if not end_datetime:
            return ""

        return end_datetime.strftime("%H:%M")
    except Exception:
        return ""


def get_time_state(task_date, start_time, duration_minutes):
    now = datetime.now()

    try:
        start_datetime, end_datetime = get_task_interval(task_date, start_time, duration_minutes)

        if not start_datetime or not end_datetime:
            return "Ошибка времени"

        if now < start_datetime:
            return "Ожидает"
        elif start_datetime <= now <= end_datetime:
            return "Идёт сейчас"
        return "Время прошло"
    except Exception:
        return "Ошибка времени"


def get_time_period(start_time):
    try:
        hour = int(str(start_time).split(":")[0])
    except Exception:
        return "Неизвестно"

    if 6 <= hour < 12:
        return "Утро"
    if 12 <= hour < 18:
        return "День"
    if 18 <= hour < 24:
        return "Вечер"
    return "Ночь"


def generate_dates_for_recurrence(start_date, end_date, repeat_type, selected_weekdays):
    result_dates = []
    current = start_date

    while current <= end_date:
        weekday_name = WEEKDAY_MAP[current.weekday()]

        if repeat_type == "Один раз":
            if current == start_date:
                result_dates.append(current)
            break

        if repeat_type == "Каждый день":
            result_dates.append(current)
        elif repeat_type == "Каждую неделю в этот день":
            if current.weekday() == start_date.weekday():
                result_dates.append(current)
        elif repeat_type == "Выбранные дни недели":
            if weekday_name in selected_weekdays:
                result_dates.append(current)

        current += timedelta(days=1)

    return result_dates


def get_default_time():
    now = datetime.now()
    minute = 0 if now.minute < 30 else 30
    return now.replace(minute=minute, second=0, microsecond=0).time()


# -----------------------------
# Statistics helpers
# -----------------------------

def calculate_score(status):
    if status == "Выполнено":
        return 1.0
    if status == "Частично":
        return 0.5
    return 0.0


def prepare_stats_dataframe(df):
    stats_df = df.copy()

    stats_df["Дата_dt"] = pd.to_datetime(stats_df["Дата"], errors="coerce")
    stats_df["score"] = stats_df["Статус"].apply(calculate_score)
    stats_df["Вес"] = pd.to_numeric(stats_df["Вес"], errors="coerce").fillna(1).astype(int)
    stats_df["weighted_score"] = stats_df["score"] * stats_df["Вес"]
    stats_df["День_недели"] = stats_df["Дата_dt"].dt.weekday.map(WEEKDAY_MAP)
    stats_df["Период_дня"] = stats_df["Время"].apply(get_time_period)

    year_plan_df = load_year_plan()

    if not year_plan_df.empty:
        year_plan_small = year_plan_df[["Дата", "Тип_дня", "Тема"]].copy()
        stats_df = stats_df.merge(year_plan_small, on="Дата", how="left")
    else:
        stats_df["Тип_дня"] = "Не задано"
        stats_df["Тема"] = ""

    stats_df["Тип_дня"] = stats_df["Тип_дня"].fillna("Не задано")
    stats_df["Тема"] = stats_df["Тема"].fillna("")

    now = datetime.now()

    def check_overdue(row):
        if row["Статус"] != "Запланировано":
            return False

        start_datetime = get_start_datetime(row["Дата"], row["Время"])

        if not start_datetime:
            return False

        return now > start_datetime

    stats_df["Просрочено"] = stats_df.apply(check_overdue, axis=1)
    return stats_df


def build_category_dataframe(df):
    category_rows = []

    for _, row in df.iterrows():
        categories = str(row["Категории"]).split(",")

        for category in categories:
            clean_category = category.strip()

            if clean_category:
                category_rows.append({
                    "Категория": clean_category,
                    "Статус": row["Статус"],
                    "score": calculate_score(row["Статус"]),
                    "Вес": int(row["Вес"]),
                    "weighted_score": calculate_score(row["Статус"]) * int(row["Вес"]),
                    "Дата": row["Дата"],
                    "Задача": row["Задача"],
                    "Длительность_мин": row["Длительность_мин"],
                    "Приоритет": row["Приоритет"],
                    "Причина_пропуска": row["Причина_пропуска"],
                    "Тип_дня": row.get("Тип_дня", "Не задано")
                })

    return pd.DataFrame(category_rows)


def get_week_range(selected_date):
    selected_datetime = pd.to_datetime(selected_date)
    week_start = selected_datetime - pd.Timedelta(days=selected_datetime.weekday())
    week_end = week_start + pd.Timedelta(days=6)
    return week_start.date(), week_end.date()


def filter_week(stats_df, selected_date):
    week_start, week_end = get_week_range(selected_date)

    week_df = stats_df[
        (stats_df["Дата_dt"] >= pd.to_datetime(week_start)) &
        (stats_df["Дата_dt"] <= pd.to_datetime(week_end))
    ].copy()

    return week_df, week_start, week_end


def get_completion_percent(df):
    if df.empty:
        return 0.0

    total_weight = pd.to_numeric(df["Вес"], errors="coerce").fillna(1).sum()

    if total_weight <= 0:
        return 0.0

    if "weighted_score" in df.columns:
        return df["weighted_score"].sum() / total_weight * 100

    score = df["Статус"].apply(calculate_score)
    return (score * df["Вес"]).sum() / total_weight * 100


def get_current_streak(stats_df):
    if stats_df.empty:
        return 0

    completed_dates = set(stats_df[stats_df["Статус"] == "Выполнено"]["Дата"].dropna().astype(str).tolist())
    streak = 0
    current_day = date.today()

    while str(current_day) in completed_dates:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def get_category_streak(stats_df, category_name):
    if stats_df.empty:
        return 0

    category_df = build_category_dataframe(stats_df)

    if category_df.empty:
        return 0

    category_df = category_df[
        (category_df["Категория"] == category_name) &
        (category_df["Статус"] == "Выполнено")
    ]

    completed_dates = set(category_df["Дата"].dropna().astype(str).tolist())
    streak = 0
    current_day = date.today()

    while str(current_day) in completed_dates:
        streak += 1
        current_day -= timedelta(days=1)

    return streak


def get_weighted_group_stats(df, group_column):
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby(group_column).agg(
        Количество_задач=("Задача", "count"),
        Вес_задач=("Вес", "sum"),
        Набрано_баллов=("weighted_score", "sum"),
        Минут_запланировано=("Длительность_мин", "sum")
    ).reset_index()

    grouped["Процент_выполнения"] = grouped.apply(
        lambda row: row["Набрано_баллов"] / row["Вес_задач"] * 100 if row["Вес_задач"] > 0 else 0,
        axis=1
    )

    return grouped


# -----------------------------
# Charts
# -----------------------------

def style_plotly_chart(fig, title, x_title, y_title):
    fig.update_layout(
        title={"text": title, "font": {"size": 26}, "x": 0.02},
        font={"size": 17},
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text="",
        height=520,
        margin={"l": 50, "r": 30, "t": 90, "b": 90},
        plot_bgcolor="rgba(0,0,0,0)"
    )
    fig.update_xaxes(tickfont={"size": 16}, title_font={"size": 18}, showgrid=False)
    fig.update_yaxes(tickfont={"size": 16}, title_font={"size": 18}, gridcolor="#E5E5E5")
    fig.update_traces(textposition="outside", textfont_size=18)
    return fig


def show_status_chart(week_df):
    status_count = week_df["Статус"].value_counts().reset_index()
    status_count.columns = ["Статус", "Количество"]

    fig = px.bar(
        status_count,
        x="Статус",
        y="Количество",
        color="Статус",
        text="Количество",
        color_discrete_map=STATUS_COLORS
    )

    fig = style_plotly_chart(fig, "Распределение задач по статусам", "Статус", "Количество задач")
    st.plotly_chart(fig, use_container_width=True)


def show_priority_chart(week_df):
    priority_count = week_df["Приоритет"].value_counts().reset_index()
    priority_count.columns = ["Приоритет", "Количество"]

    fig = px.bar(
        priority_count,
        x="Приоритет",
        y="Количество",
        color="Приоритет",
        text="Количество",
        color_discrete_map=PRIORITY_COLORS
    )

    fig = style_plotly_chart(fig, "Распределение задач по приоритету", "Приоритет", "Количество задач")
    st.plotly_chart(fig, use_container_width=True)


def show_percent_chart(df, x_column, y_column, title, x_title):
    if df.empty:
        st.info("Нет данных для графика")
        return

    chart_df = df.copy()
    chart_df["Подпись"] = chart_df[y_column].round(1).astype(str) + "%"

    fig = px.bar(
        chart_df,
        x=x_column,
        y=y_column,
        color=y_column,
        text="Подпись",
        color_continuous_scale=["#EB5757", "#F2C94C", "#2EAD4F"],
        range_color=[0, 100]
    )

    fig = style_plotly_chart(fig, title, x_title, "Процент выполнения")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_yaxes(range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)


def show_load_chart(df, x_column, y_column, title, x_title, y_title):
    if df.empty:
        st.info("Нет данных для графика")
        return

    fig = px.bar(df, x=x_column, y=y_column, text=y_column, color_discrete_sequence=["#2F80ED"])
    fig = style_plotly_chart(fig, title, x_title, y_title)
    st.plotly_chart(fig, use_container_width=True)


def show_skip_reason_chart(week_df):
    skip_df = week_df[
        (week_df["Статус"] == "Пропущено") &
        (week_df["Причина_пропуска"].astype(str).str.len() > 0)
    ]

    if skip_df.empty:
        st.success("Причин пропуска пока нет")
        return

    reason_count = skip_df["Причина_пропуска"].value_counts().reset_index()
    reason_count.columns = ["Причина", "Количество"]

    fig = px.bar(reason_count, x="Причина", y="Количество", text="Количество", color_discrete_sequence=["#EB5757"])
    fig = style_plotly_chart(fig, "Причины пропущенных задач", "Причина", "Количество")
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)


def show_week_compare_chart(compare_df):
    chart_df = compare_df.copy()
    chart_df["Подпись"] = chart_df["Процент"].round(1).astype(str) + "%"

    fig = px.bar(
        chart_df,
        x="Неделя",
        y="Процент",
        text="Подпись",
        color="Процент",
        color_continuous_scale=["#EB5757", "#F2C94C", "#2EAD4F"],
        range_color=[0, 100]
    )

    fig = style_plotly_chart(fig, "Сравнение с прошлой неделей", "Неделя", "Процент выполнения")
    fig.update_layout(coloraxis_showscale=False)
    fig.update_xaxes(tickangle=-10)
    fig.update_yaxes(range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)


def show_work_chart(work_df):
    if work_df.empty:
        st.info("Нет рабочих записей")
        return

    area_count = work_df["Участок"].replace("", "Не указан").value_counts().reset_index()
    area_count.columns = ["Участок", "Количество"]

    fig = px.bar(area_count, x="Участок", y="Количество", text="Количество", color_discrete_sequence=["#2F80ED"])
    fig = style_plotly_chart(fig, "Работы по участкам", "Участок", "Количество")
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Alarm and export
# -----------------------------

def play_alarm_sound():
    components.html(
        """
        <script>
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.type = "sine";
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
            gainNode.gain.setValueAtTime(0.15, audioCtx.currentTime);
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.5);
        } catch (error) {
            console.log(error);
        }
        </script>
        """,
        height=0
    )


def get_alarm_tasks(df):
    if df.empty:
        return df

    today = str(date.today())
    now = datetime.now()
    alarm_rows = []

    for _, row in df.iterrows():
        if row["Дата"] != today:
            continue
        if row["Статус"] != "Запланировано":
            continue

        start_datetime = get_start_datetime(row["Дата"], row["Время"])

        if start_datetime and now >= start_datetime:
            alarm_rows.append(row)

    return pd.DataFrame(alarm_rows)


def create_excel_report(stats_df, week_df, day_stats, category_stats, time_stats, day_type_stats, compare_df, month_stats, work_df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        week_df.to_excel(writer, sheet_name="Задачи недели", index=False)
        day_stats.to_excel(writer, sheet_name="По дням", index=False)
        category_stats.to_excel(writer, sheet_name="По категориям", index=False)
        time_stats.to_excel(writer, sheet_name="По времени суток", index=False)
        day_type_stats.to_excel(writer, sheet_name="По типу дня", index=False)
        compare_df.to_excel(writer, sheet_name="Сравнение недель", index=False)
        month_stats.to_excel(writer, sheet_name="По месяцам", index=False)
        work_df.to_excel(writer, sheet_name="Рабочий журнал", index=False)
        stats_df.to_excel(writer, sheet_name="Все задачи", index=False)

    output.seek(0)
    return output


def make_local_backup():
    BACKUP_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        return None

    backup_name = f"week_planner_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = BACKUP_DIR / backup_name
    shutil.copy(DB_PATH, backup_path)
    return backup_path


# -----------------------------
# AI analysis
# -----------------------------

def generate_ai_analysis(week_df, previous_week_df, work_week_df):
    if week_df.empty and work_week_df.empty:
        return ["На выбранную неделю нет личных задач и рабочих записей."]

    advice = []

    if not week_df.empty:
        done_tasks = len(week_df[week_df["Статус"] == "Выполнено"])
        partial_tasks = len(week_df[week_df["Статус"] == "Частично"])
        skipped_tasks = len(week_df[week_df["Статус"] == "Пропущено"])
        planned_tasks = len(week_df[week_df["Статус"] == "Запланировано"])
        overdue_tasks = len(week_df[week_df["Просрочено"] == True])

        percent = get_completion_percent(week_df)
        previous_percent = get_completion_percent(previous_week_df)

        if previous_week_df.empty:
            diff_text = "Нет данных за прошлую неделю для сравнения."
        else:
            diff = percent - previous_percent
            if diff > 0:
                diff_text = f"Прогресс лучше прошлой недели на {diff:.1f}%."
            elif diff < 0:
                diff_text = f"Результат ниже прошлой недели на {abs(diff):.1f}%."
            else:
                diff_text = "Результат примерно такой же, как на прошлой неделе."

        advice.append(f"📊 Личные задачи: {percent:.1f}% с учётом веса. {diff_text}")

        if percent >= 85:
            advice.append("🔥 Неделя сильная. Темп хороший, главное — не перегрузить следующую неделю.")
        elif percent >= 70:
            advice.append("✅ Хорошая неделя. Можно улучшить слабые дни и важные задачи.")
        elif percent >= 50:
            advice.append("⚠️ Средняя неделя. Посмотри, какие типы дней или категории проседают.")
        else:
            advice.append("🔧 Неделя слабая. Возможно, задачи плохо совпали с графиком смен или отдыхом.")

        critical_df = week_df[week_df["Приоритет"].isin(["Высокий", "Критичный"])]
        if not critical_df.empty:
            critical_percent = get_completion_percent(critical_df)
            advice.append(f"🎯 Важные задачи выполнены на {critical_percent:.1f}%.")

        if skipped_tasks >= 3:
            advice.append(f"❌ Пропущено задач: {skipped_tasks}. Проверь причины пропуска и типы дней.")

        if partial_tasks > done_tasks:
            advice.append("🟡 Много частичных задач. Возможно, задачи надо дробить на более конкретные действия.")

        if planned_tasks > 0:
            advice.append(f"⏳ Без отчёта осталось задач: {planned_tasks}. Лучше закрывать день вечером.")

        if overdue_tasks > 0:
            advice.append(f"⏰ Просроченных задач без отчёта: {overdue_tasks}.")

        day_type_stats = get_weighted_group_stats(week_df, "Тип_дня")
        if not day_type_stats.empty:
            weakest_type = day_type_stats.sort_values("Процент_выполнения", ascending=True).iloc[0]
            advice.append(f"🗓️ Самый слабый тип дня: {weakest_type['Тип_дня']} — {weakest_type['Процент_выполнения']:.1f}%.")

    if not work_week_df.empty:
        total_work = len(work_week_df)
        completed_work = len(work_week_df[work_week_df["Статус"] == "Завершено"])
        open_work = total_work - completed_work
        advice.append(f"🛠️ По рабочему журналу за неделю записей: {total_work}, завершено: {completed_work}, осталось/передано: {open_work}.")

        if "Участок" in work_week_df.columns and not work_week_df["Участок"].replace("", pd.NA).dropna().empty:
            top_area = work_week_df["Участок"].replace("", pd.NA).dropna().value_counts().idxmax()
            advice.append(f"📍 Самый частый участок по записям: {top_area}.")

        if "TAG" in work_week_df.columns and not work_week_df["TAG"].replace("", pd.NA).dropna().empty:
            tag_counts = work_week_df["TAG"].replace("", pd.NA).dropna().value_counts()
            if tag_counts.iloc[0] >= 2:
                advice.append(f"🔁 Повторяющийся TAG: {tag_counts.index[0]} — {tag_counts.iloc[0]} раз(а).")

        wait_statuses = ["Ждём механиков", "Ждём электриков", "Ждём запчасть", "Передано следующей смене"]
        waiting_count = len(work_week_df[work_week_df["Статус"].isin(wait_statuses)])
        if waiting_count > 0:
            advice.append(f"📌 Работ в ожидании/передаче: {waiting_count}. Их удобно вынести в передачу смены.")

    return advice


# -----------------------------
# Work report text
# -----------------------------

def build_shift_report(report_date, shift_type, logs_df):
    if logs_df.empty:
        return f"Отчёт за {shift_type.lower()} {report_date}\n\nРаботы за выбранную дату не добавлены."

    lines = []
    lines.append(f"Отчёт за {shift_type.lower()} {report_date}")
    lines.append("")
    lines.append("За смену выполнены/зарегистрированы работы:")
    lines.append("")

    for index, row in enumerate(logs_df.itertuples(index=False), start=1):
        area = getattr(row, "Участок") or "не указан"
        tag = getattr(row, "TAG") or "не указан"
        equipment = getattr(row, "Оборудование") or "не указано"
        work_type = getattr(row, "Тип_работы") or "не указано"
        request = getattr(row, "Заявка") or "-"
        problem = getattr(row, "Проблема") or "не указано"
        action = getattr(row, "Что_сделал") or "не указано"
        result = getattr(row, "Результат") or "не указано"
        status = getattr(row, "Статус") or "не указано"
        handover = getattr(row, "Кому_передано") or "-"
        comment = getattr(row, "Комментарий") or ""

        lines.append(f"{index}. Участок: {area}")
        lines.append(f"   Оборудование: {equipment}")
        lines.append(f"   TAG: {tag}")
        lines.append(f"   Тип работы: {work_type}")
        lines.append(f"   Заявка/вызов: {request}")
        lines.append(f"   Проблема: {problem}")
        lines.append(f"   Выполнено: {action}")
        lines.append(f"   Результат: {result}")
        lines.append(f"   Статус: {status}")

        if handover != "-":
            lines.append(f"   Передано: {handover}")

        if comment:
            lines.append(f"   Комментарий: {comment}")

        lines.append("")

    waiting_df = logs_df[logs_df["Статус"].isin(["Ждём механиков", "Ждём электриков", "Ждём запчасть", "Передано следующей смене"])]

    if not waiting_df.empty:
        lines.append("Работы для контроля/передачи:")
        for row in waiting_df.itertuples(index=False):
            lines.append(f"- {getattr(row, 'Участок')} / {getattr(row, 'TAG')} / {getattr(row, 'Статус')}")
        lines.append("")

    return "\n".join(lines)


# -----------------------------
# Render tabs
# -----------------------------

def render_dashboard_tab():
    st.header("🏠 Сегодня")

    today = date.today()
    today_text = str(today)
    day_plan = get_day_plan(today)

    tasks_df = load_tasks()
    work_df = load_work_logs()

    today_tasks = tasks_df[tasks_df["Дата"] == today_text].copy() if not tasks_df.empty else pd.DataFrame()
    today_work = work_df[work_df["Дата"] == today_text].copy() if not work_df.empty else pd.DataFrame()

    if day_plan["day_type"] == "Ночная смена":
        current_shift = "Ночь"
    elif day_plan["day_type"] == "Дневная смена":
        current_shift = "День"
    else:
        current_shift = "Отдых"

    if not today_work.empty:
        shift_work = today_work[today_work["Смена"] == current_shift].copy()
    else:
        shift_work = pd.DataFrame()

    unfinished_statuses = [
        "Открыто",
        "В работе",
        "Передано следующей смене",
        "Ждём механиков",
        "Ждём электриков",
        "Ждём запчасть"
    ]

    unfinished_work = work_df[work_df["Статус"].isin(unfinished_statuses)].copy() if not work_df.empty else pd.DataFrame()

    next_task_text = "Личных задач на сегодня нет"

    if not today_tasks.empty:
        planned_tasks = today_tasks[today_tasks["Статус"] == "Запланировано"].copy()

        if not planned_tasks.empty:
            planned_tasks["start_dt"] = planned_tasks.apply(
                lambda row: get_start_datetime(row["Дата"], row["Время"]),
                axis=1
            )

            now = datetime.now()
            future_tasks = planned_tasks[planned_tasks["start_dt"] >= now].copy()

            if not future_tasks.empty:
                next_row = future_tasks.sort_values("start_dt").iloc[0]
            else:
                next_row = planned_tasks.sort_values("Время").iloc[0]

            next_task_text = f"{next_row['Время']} — {next_row['Задача']}"

    st.markdown(
        f"""
        <div style="
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 22px;
            padding: 24px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            margin-bottom: 18px;
        ">
            <div style="font-size: 18px; opacity: 0.75; margin-bottom: 6px;">Сегодня: {day_plan['day_type']}</div>
            <div style="font-size: 30px; font-weight: 800; margin-bottom: 10px;">{today_text}</div>
            <div style="font-size: 20px;"><b>Тема:</b> {day_plan['theme']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Следующая личная задача",
            next_task_text
        )

    with col2:
        st.metric(
            "Рабочих записей за смену",
            len(shift_work)
        )

    with col3:
        st.metric(
            "Незавершённые рабочие заявки",
            len(unfinished_work)
        )

    if not unfinished_work.empty:
        st.subheader("Незавершённые работы")
        st.dataframe(
            unfinished_work[
                [
                    "Дата",
                    "Смена",
                    "Участок",
                    "Оборудование",
                    "TAG",
                    "Тип_работы",
                    "Заявка",
                    "Статус"
                ]
            ],
            use_container_width=True
        )


def render_year_plan_tab(): 
    st.header("📆 Годовой план смен")
    st.write("Здесь ты сам заранее отмечаешь: ночная смена, дневная смена или отдых. От этого меняется тема приложения.")

    st.subheader("Добавить / изменить один день")

    col1, col2 = st.columns(2)

    with col1:
        plan_date = st.date_input("Дата", value=date.today(), key="year_plan_single_date")

    with col2:
        day_type = st.selectbox("Тип дня", DAY_TYPES, key="year_plan_type")

    default_theme = DAY_THEME_PRESETS.get(day_type, "")
    theme = st.text_input("Тема дня", value=default_theme, key="year_plan_theme")
    comment = st.text_area("Комментарий", placeholder="Например: выезд, перелёт, закрыть отчёт, подготовка")

    col_save, col_delete = st.columns(2)

    with col_save:
        if st.button("Сохранить день"):
            upsert_year_plan(str(plan_date), day_type, theme, comment)
            st.success("День сохранён")
            st.rerun()

    with col_delete:
        if st.button("Удалить день из плана"):
            delete_year_plan(str(plan_date))
            st.warning("День удалён из годового плана")
            st.rerun()

    st.divider()
    st.subheader("Быстро заполнить диапазон")

    col3, col4, col5 = st.columns(3)

    with col3:
        range_start = st.date_input("Начало диапазона", value=date.today(), key="range_start")

    with col4:
        range_end = st.date_input("Конец диапазона", value=date.today() + timedelta(days=6), key="range_end")

    with col5:
        range_type = st.selectbox("Тип для диапазона", DAY_TYPES, key="range_type")

    range_theme = st.text_input("Тема для диапазона", value=DAY_THEME_PRESETS.get(range_type, ""), key="range_theme")
    range_comment = st.text_input("Комментарий для диапазона", key="range_comment")

    if st.button("Заполнить диапазон"):
        if range_end < range_start:
            st.warning("Конец диапазона не должен быть раньше начала")
        else:
            current = range_start
            count = 0

            while current <= range_end:
                upsert_year_plan(str(current), range_type, range_theme, range_comment)
                current += timedelta(days=1)
                count += 1

            st.success(f"Заполнено дней: {count}")
            st.rerun()

    st.divider()
    st.subheader("Текущий годовой план")

    plan_df = load_year_plan()

    if plan_df.empty:
        st.info("План пока пустой")
        return

    col_filter1, col_filter2 = st.columns(2)

    with col_filter1:
        year_filter = st.number_input("Год", min_value=2020, max_value=2100, value=date.today().year, step=1)

    with col_filter2:
        type_filter = st.multiselect("Типы дней", DAY_TYPES, default=DAY_TYPES)

    plan_df["Дата_dt"] = pd.to_datetime(plan_df["Дата"], errors="coerce")
    filtered_plan = plan_df[
        (plan_df["Дата_dt"].dt.year == int(year_filter)) &
        (plan_df["Тип_дня"].isin(type_filter))
    ].copy()

    st.dataframe(
        filtered_plan[["Дата", "Тип_дня", "Тема", "Комментарий"]],
        use_container_width=True
    )

    st.subheader("Статистика по типам дней")
    type_count = filtered_plan["Тип_дня"].value_counts().reset_index()
    type_count.columns = ["Тип_дня", "Количество"]
    st.dataframe(type_count, use_container_width=True)

    if not type_count.empty:
        fig = px.bar(type_count, x="Тип_дня", y="Количество", color="Тип_дня", text="Количество")
        fig = style_plotly_chart(fig, "Количество дней по типам", "Тип дня", "Количество дней")
        st.plotly_chart(fig, use_container_width=True)


def render_add_task_tab():
    st.header("➕ Добавить личную задачу")

    categories_list = load_categories()

    col_date, col_time, col_duration = st.columns(3)

    with col_date:
        task_date = st.date_input("Дата", value=date.today())

    with col_time:
        task_time = st.time_input("Время начала", value=get_default_time())

    with col_duration:
        duration_minutes = st.number_input("Продолжительность, минут", min_value=5, max_value=600, value=30, step=5)

    day_plan = get_day_plan(task_date)
    st.info(f"**Тип дня:** {day_plan['day_type']} | **Тема:** {day_plan['theme']}")

    title = st.text_input("Задача", placeholder="Например: Python 30 минут")

    col_cat, col_priority, col_weight = st.columns(3)

    with col_cat:
        categories = st.multiselect("Категории", categories_list)

    with col_priority:
        priority = st.selectbox("Приоритет", PRIORITIES, index=1)

    with col_weight:
        weight = st.slider("Вес задачи", min_value=1, max_value=5, value=1, help="1 — лёгкая, 5 — очень важная/сложная")

    repeat_type = st.selectbox("Повторение", ["Один раз", "Каждый день", "Каждую неделю в этот день", "Выбранные дни недели"])

    selected_weekdays = []
    repeat_end_date = task_date

    if repeat_type != "Один раз":
        repeat_end_date = st.date_input("Повторять до даты", value=task_date + timedelta(days=7))

    if repeat_type == "Выбранные дни недели":
        selected_weekdays = st.multiselect("Выбери дни недели", WEEKDAY_ORDER, default=[WEEKDAY_MAP[task_date.weekday()]])

    if st.button("Добавить задачу"):
        if title.strip() == "":
            st.warning("Напиши название задачи")
        elif not categories:
            st.warning("Выбери хотя бы одну категорию")
        elif repeat_type == "Выбранные дни недели" and not selected_weekdays:
            st.warning("Выбери хотя бы один день недели")
        elif repeat_end_date < task_date:
            st.warning("Дата окончания повтора не должна быть раньше даты начала")
        else:
            dates_to_add = generate_dates_for_recurrence(task_date, repeat_end_date, repeat_type, selected_weekdays)
            added_count = 0
            conflict_messages = []

            for current_date in dates_to_add:
                task_date_text = str(current_date)
                task_time_text = task_time.strftime("%H:%M")
                duration_value = int(duration_minutes)

                conflict_task = find_time_conflict(task_date_text, task_time_text, duration_value)

                if conflict_task is not None:
                    conflict_end_time = get_end_time(conflict_task["Дата"], conflict_task["Время"], conflict_task["Длительность_мин"])
                    conflict_messages.append(f"{task_date_text}: занято {conflict_task['Время']} - {conflict_end_time} | {conflict_task['Задача']}")
                    continue

                add_task(task_date_text, task_time_text, duration_value, title.strip(), ", ".join(categories), priority, int(weight))
                added_count += 1

            if added_count > 0:
                st.success(f"Добавлено задач: {added_count}")

            if conflict_messages:
                st.warning("Некоторые задачи не добавлены из-за конфликта времени:")
                for message in conflict_messages:
                    st.write(f"- {message}")

            if added_count > 0:
                st.rerun()


def render_work_log_tab():
    st.header("🛠️ Рабочий журнал КИПиА")
    st.write("Сюда записывай вызовы, заявки, монтажи, проверки, калибровки и передачу смены.")

    selected_date = st.date_input("Дата работы", value=date.today(), key="work_date")
    day_plan = get_day_plan(selected_date)

    default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Отдых"
    shift_options = ["День", "Ночь", "Отдых", "Другое"]
    shift_index = shift_options.index(default_shift) if default_shift in shift_options else 0

    st.info(f"По годовому плану: **{day_plan['day_type']}** | Тема: {day_plan['theme']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        shift_type = st.selectbox("Смена", shift_options, index=shift_index)

    with col2:
        area = st.text_input("Участок", placeholder="Например: FL-111, PU-332")

    with col3:
        equipment = st.text_input("Оборудование", placeholder="Например: конвейер, насос, клапан")

    col4, col5, col6 = st.columns(3)

    with col4:
        tag = st.text_input("TAG", placeholder="Например: 3445-LIT-0051")

    with col5:
        work_type = st.selectbox("Тип работы", WORK_TYPES)

    with col6:
        request_number = st.text_input("Заявка / вызов", placeholder="Номер заявки или кратко")

    problem = st.text_area("Проблема / причина вызова", placeholder="Что было не так?")
    action_taken = st.text_area("Что сделал", placeholder="Какие действия выполнил?")
    result = st.text_area("Результат", placeholder="Что получилось, в работе или нет?")

    col7, col8 = st.columns(2)

    with col7:
        status = st.selectbox("Статус", WORK_STATUSES, index=2)

    with col8:
        handover_to = st.text_input("Кому передано", placeholder="механикам, электрикам, следующей смене")

    comment = st.text_area("Комментарий", placeholder="Дополнительные детали")

    if st.button("Добавить запись в рабочий журнал"):
        if not area.strip() and not tag.strip() and not problem.strip():
            st.warning("Заполни хотя бы участок/TAG/проблему")
        else:
            add_work_log(
                str(selected_date),
                shift_type,
                area.strip(),
                equipment.strip(),
                tag.strip(),
                work_type,
                request_number.strip(),
                problem.strip(),
                action_taken.strip(),
                result.strip(),
                status,
                handover_to.strip(),
                comment.strip()
            )
            st.success("Запись добавлена")
            st.rerun()

    st.divider()
    st.subheader("Записи рабочего журнала")

    work_df = load_work_logs()

    if work_df.empty:
        st.info("Записей пока нет")
        return

    col_filter1, col_filter2, col_filter3 = st.columns(3)

    with col_filter1:
        date_from = st.date_input("Дата от", value=pd.to_datetime(work_df["Дата"].min()).date(), key="work_filter_from")

    with col_filter2:
        date_to = st.date_input("Дата до", value=pd.to_datetime(work_df["Дата"].max()).date(), key="work_filter_to")

    with col_filter3:
        status_filter = st.multiselect("Статус работы", WORK_STATUSES, default=[])

    search = st.text_input("Поиск по участку / TAG / проблеме", key="work_search")

    filtered = work_df.copy()
    filtered["Дата_dt"] = pd.to_datetime(filtered["Дата"], errors="coerce")
    filtered = filtered[(filtered["Дата_dt"] >= pd.to_datetime(date_from)) & (filtered["Дата_dt"] <= pd.to_datetime(date_to))]

    if status_filter:
        filtered = filtered[filtered["Статус"].isin(status_filter)]

    if search.strip():
        query = search.strip().lower()
        filtered = filtered[
            filtered.apply(
                lambda row: query in " ".join([
                    str(row["Участок"]),
                    str(row["TAG"]),
                    str(row["Проблема"]),
                    str(row["Что_сделал"]),
                    str(row["Результат"])
                ]).lower(),
                axis=1
            )
        ]

    st.dataframe(
        filtered[["id", "Дата", "Смена", "Участок", "Оборудование", "TAG", "Тип_работы", "Заявка", "Проблема", "Статус", "Кому_передано"]],
        use_container_width=True
    )

    st.subheader("Редактировать / удалить запись")

    if not filtered.empty:
        choices = (filtered["id"].astype(str) + " | " + filtered["Дата"] + " | " + filtered["Участок"].astype(str) + " | " + filtered["TAG"].astype(str)).tolist()
        selected = st.selectbox("Выбери запись", choices)
        selected_id = int(selected.split(" | ")[0])
        row = work_df[work_df["id"] == selected_id].iloc[0]

        with st.expander("Открыть редактирование записи"):
            edit_date = st.date_input("Дата", value=pd.to_datetime(row["Дата"]).date(), key=f"edit_work_date_{selected_id}")
            edit_shift = st.selectbox("Смена", shift_options, index=shift_options.index(row["Смена"]) if row["Смена"] in shift_options else 0, key=f"edit_shift_{selected_id}")
            edit_area = st.text_input("Участок", value=row["Участок"], key=f"edit_area_{selected_id}")
            edit_equipment = st.text_input("Оборудование", value=row["Оборудование"], key=f"edit_equipment_{selected_id}")
            edit_tag = st.text_input("TAG", value=row["TAG"], key=f"edit_tag_{selected_id}")
            edit_work_type = st.selectbox("Тип работы", WORK_TYPES, index=WORK_TYPES.index(row["Тип_работы"]) if row["Тип_работы"] in WORK_TYPES else 0, key=f"edit_type_{selected_id}")
            edit_request = st.text_input("Заявка / вызов", value=row["Заявка"], key=f"edit_request_{selected_id}")
            edit_problem = st.text_area("Проблема", value=row["Проблема"], key=f"edit_problem_{selected_id}")
            edit_action = st.text_area("Что сделал", value=row["Что_сделал"], key=f"edit_action_{selected_id}")
            edit_result = st.text_area("Результат", value=row["Результат"], key=f"edit_result_{selected_id}")
            edit_status = st.selectbox("Статус", WORK_STATUSES, index=WORK_STATUSES.index(row["Статус"]) if row["Статус"] in WORK_STATUSES else 0, key=f"edit_status_work_{selected_id}")
            edit_handover = st.text_input("Кому передано", value=row["Кому_передано"], key=f"edit_handover_{selected_id}")
            edit_comment = st.text_area("Комментарий", value=row["Комментарий"], key=f"edit_comment_work_{selected_id}")

            col_save, col_delete = st.columns(2)

            with col_save:
                if st.button("Сохранить рабочую запись", key=f"save_work_{selected_id}"):
                    update_work_log(
                        selected_id,
                        str(edit_date),
                        edit_shift,
                        edit_area,
                        edit_equipment,
                        edit_tag,
                        edit_work_type,
                        edit_request,
                        edit_problem,
                        edit_action,
                        edit_result,
                        edit_status,
                        edit_handover,
                        edit_comment
                    )
                    st.success("Рабочая запись обновлена")
                    st.rerun()

            with col_delete:
                if st.button("Удалить рабочую запись", key=f"delete_work_{selected_id}"):
                    delete_work_log(selected_id)
                    st.warning("Рабочая запись удалена")
                    st.rerun()


def render_shift_report_tab():
    st.header("📋 Отчёт смены")

    work_df = load_work_logs()

    if work_df.empty:
        st.info("Рабочих записей пока нет")
        return

    report_date = st.date_input("Дата отчёта", value=date.today(), key="shift_report_date")
    day_plan = get_day_plan(report_date)
    default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Другое"
    shift_options = ["День", "Ночь", "Отдых", "Другое"]
    shift_type = st.selectbox("Смена", shift_options, index=shift_options.index(default_shift) if default_shift in shift_options else 0, key="shift_report_shift")

    logs_for_report = work_df[(work_df["Дата"] == str(report_date)) & (work_df["Смена"] == shift_type)].copy()

    st.write(f"Найдено записей: **{len(logs_for_report)}**")

    if not logs_for_report.empty:
        st.dataframe(logs_for_report[["Участок", "Оборудование", "TAG", "Тип_работы", "Заявка", "Статус"]], use_container_width=True)

    report_text = build_shift_report(str(report_date), shift_type, logs_for_report)

    st.text_area("Готовый текст отчёта", value=report_text, height=500)

    st.download_button(
        "Скачать отчёт .txt",
        data=report_text.encode("utf-8"),
        file_name=f"shift_report_{report_date}_{shift_type}.txt",
        mime="text/plain"
    )


def render_work_stats_tab():
    st.header("📈 Статистика рабочего журнала")

    work_df = load_work_logs()

    if work_df.empty:
        st.info("Рабочих записей пока нет")
        return

    work_df["Дата_dt"] = pd.to_datetime(work_df["Дата"], errors="coerce")

    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("Дата от", value=work_df["Дата_dt"].min().date(), key="work_stats_from")
    with col2:
        date_to = st.date_input("Дата до", value=work_df["Дата_dt"].max().date(), key="work_stats_to")

    filtered = work_df[(work_df["Дата_dt"] >= pd.to_datetime(date_from)) & (work_df["Дата_dt"] <= pd.to_datetime(date_to))].copy()

    if filtered.empty:
        st.info("За выбранный период записей нет")
        return

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Всего записей", len(filtered))
    col_b.metric("Завершено", len(filtered[filtered["Статус"] == "Завершено"]))
    col_c.metric("Передано", len(filtered[filtered["Статус"] == "Передано следующей смене"]))
    col_d.metric("Ожидание", len(filtered[filtered["Статус"].isin(["Ждём механиков", "Ждём электриков", "Ждём запчасть"])]))

    st.divider()
    show_work_chart(filtered)

    st.subheader("По статусам")
    status_count = filtered["Статус"].value_counts().reset_index()
    status_count.columns = ["Статус", "Количество"]
    st.dataframe(status_count, use_container_width=True)

    fig = px.bar(status_count, x="Статус", y="Количество", text="Количество", color_discrete_sequence=["#2EAD4F"])
    fig = style_plotly_chart(fig, "Работы по статусам", "Статус", "Количество")
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Повторяющиеся TAG")
    tag_df = filtered[filtered["TAG"].astype(str).str.len() > 0]

    if tag_df.empty:
        st.info("TAG не заполнены")
    else:
        tag_count = tag_df["TAG"].value_counts().reset_index()
        tag_count.columns = ["TAG", "Количество"]
        st.dataframe(tag_count, use_container_width=True)


# Existing personal planning tabs

def render_task_list_tab():
    st.header("📋 Список личных задач")

    df = load_tasks()

    if df.empty:
        st.info("Пока задач нет")
        return

    categories_list = load_categories()
    st.subheader("Фильтры")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        date_from = st.date_input("Дата от", value=pd.to_datetime(df["Дата"].min()).date(), key="filter_from")
    with col2:
        date_to = st.date_input("Дата до", value=pd.to_datetime(df["Дата"].max()).date(), key="filter_to")
    with col3:
        status_filter = st.multiselect("Статус", STATUSES, default=[])
    with col4:
        priority_filter = st.multiselect("Приоритет", PRIORITIES, default=[])

    col5, col6 = st.columns(2)
    with col5:
        category_filter = st.multiselect("Категория", categories_list, default=[])
    with col6:
        search_text = st.text_input("Поиск по задаче", placeholder="Например: Python")

    display_df = df.copy()
    display_df["Дата_dt"] = pd.to_datetime(display_df["Дата"], errors="coerce")
    display_df = display_df[(display_df["Дата_dt"] >= pd.to_datetime(date_from)) & (display_df["Дата_dt"] <= pd.to_datetime(date_to))]

    if status_filter:
        display_df = display_df[display_df["Статус"].isin(status_filter)]
    if priority_filter:
        display_df = display_df[display_df["Приоритет"].isin(priority_filter)]
    if category_filter:
        display_df = display_df[display_df["Категории"].apply(lambda text: any(cat in [p.strip() for p in str(text).split(",")] for cat in category_filter))]
    if search_text.strip():
        display_df = display_df[display_df["Задача"].str.contains(search_text.strip(), case=False, na=False)]

    if display_df.empty:
        st.info("По фильтрам ничего не найдено")
        return

    display_df["Конец"] = display_df.apply(lambda row: get_end_time(row["Дата"], row["Время"], row["Длительность_мин"]), axis=1)
    display_df["Состояние_по_времени"] = display_df.apply(lambda row: get_time_state(row["Дата"], row["Время"], row["Длительность_мин"]), axis=1)

    display_df = display_df[["id", "Дата", "Время", "Конец", "Длительность_мин", "Задача", "Категории", "Приоритет", "Вес", "Статус", "Причина_пропуска", "Состояние_по_времени", "Комментарий"]]
    st.dataframe(display_df, use_container_width=True)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Найдено задач", len(display_df))
    col_b.metric("Всего минут", int(display_df["Длительность_мин"].sum()))
    col_c.metric("Суммарный вес", int(display_df["Вес"].sum()))


def render_daily_report_tab():
    st.header("✅ Отчёт по личным задачам")

    df = load_tasks()

    if df.empty:
        st.info("Пока задач нет")
        return

    selected_date = st.date_input("Выбери дату для отчёта", value=date.today(), key="report_date")
    day_tasks = df[df["Дата"] == str(selected_date)]

    if day_tasks.empty:
        st.info("На этот день задач нет")
        return

    for _, row in day_tasks.iterrows():
        end_time = get_end_time(row["Дата"], row["Время"], row["Длительность_мин"])
        st.subheader(row["Задача"])
        st.write(f"Время: {row['Время']} - {end_time}")
        st.write(f"Длительность: {row['Длительность_мин']} минут")
        st.write(f"Категории: {row['Категории']}")
        st.write(f"Приоритет: {row['Приоритет']} | Вес: {row['Вес']}")
        st.write(f"Текущий статус: {row['Статус']}")

        current_index = STATUSES.index(row["Статус"]) if row["Статус"] in STATUSES else 0
        new_status = st.selectbox("Новый статус", STATUSES, index=current_index, key=f"status_{row['id']}")

        default_reason = row["Причина_пропуска"] if row["Причина_пропуска"] in SKIP_REASONS else ""
        reason_index = SKIP_REASONS.index(default_reason) if default_reason in SKIP_REASONS else 0
        skip_reason = ""

        if new_status == "Пропущено":
            skip_reason = st.selectbox("Причина пропуска", SKIP_REASONS, index=reason_index, key=f"reason_{row['id']}")

        comment = st.text_area("Комментарий", value=row["Комментарий"] if row["Комментарий"] else "", key=f"comment_{row['id']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Сохранить отчёт", key=f"save_{row['id']}"):
                update_task_status(row["id"], new_status, skip_reason, comment)
                st.success("Отчёт сохранён")
                st.rerun()
        with col2:
            if st.button("Удалить задачу", key=f"delete_{row['id']}"):
                delete_task(row["id"])
                st.warning("Задача удалена")
                st.rerun()

        st.divider()


def render_edit_task_tab():
    st.header("✏️ Редактировать личную задачу")

    df = load_tasks()

    if df.empty:
        st.info("Пока задач нет")
        return

    categories_list = load_categories()
    df["Выбор"] = df["id"].astype(str) + " | " + df["Дата"] + " " + df["Время"] + " | " + df["Задача"]
    selected_task = st.selectbox("Выбери задачу", df["Выбор"].tolist())
    selected_id = int(selected_task.split(" | ")[0])
    task_row = df[df["id"] == selected_id].iloc[0]

    old_date = pd.to_datetime(task_row["Дата"]).date()
    old_time = datetime.strptime(task_row["Время"], "%H:%M").time() if task_row["Время"] else get_default_time()
    old_categories = [category.strip() for category in str(task_row["Категории"]).split(",") if category.strip()]

    col1, col2, col3 = st.columns(3)
    with col1:
        new_date = st.date_input("Дата", value=old_date, key=f"edit_date_{selected_id}")
    with col2:
        new_time = st.time_input("Время начала", value=old_time, key=f"edit_time_{selected_id}")
    with col3:
        new_duration = st.number_input("Продолжительность, минут", min_value=5, max_value=600, value=int(task_row["Длительность_мин"]), step=5, key=f"edit_duration_{selected_id}")

    day_plan = get_day_plan(new_date)
    st.info(f"Тип дня: **{day_plan['day_type']}** | Тема: {day_plan['theme']}")

    new_title = st.text_input("Название задачи", value=task_row["Задача"], key=f"edit_title_{selected_id}")

    col4, col5, col6 = st.columns(3)
    with col4:
        new_categories = st.multiselect("Категории", categories_list, default=[category for category in old_categories if category in categories_list], key=f"edit_categories_{selected_id}")
    with col5:
        priority_index = PRIORITIES.index(task_row["Приоритет"]) if task_row["Приоритет"] in PRIORITIES else 1
        new_priority = st.selectbox("Приоритет", PRIORITIES, index=priority_index, key=f"edit_priority_{selected_id}")
    with col6:
        new_weight = st.slider("Вес задачи", min_value=1, max_value=5, value=int(task_row["Вес"]), key=f"edit_weight_{selected_id}")

    status_index = STATUSES.index(task_row["Статус"]) if task_row["Статус"] in STATUSES else 0
    new_status = st.selectbox("Статус", STATUSES, index=status_index, key=f"edit_status_{selected_id}")

    skip_reason = ""
    if new_status == "Пропущено":
        default_reason = task_row["Причина_пропуска"] if task_row["Причина_пропуска"] in SKIP_REASONS else ""
        reason_index = SKIP_REASONS.index(default_reason) if default_reason in SKIP_REASONS else 0
        skip_reason = st.selectbox("Причина пропуска", SKIP_REASONS, index=reason_index, key=f"edit_skip_{selected_id}")

    new_comment = st.text_area("Комментарий", value=task_row["Комментарий"] if task_row["Комментарий"] else "", key=f"edit_comment_{selected_id}")

    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("💾 Сохранить изменения", key=f"update_task_{selected_id}"):
            if new_title.strip() == "":
                st.warning("Название задачи не должно быть пустым")
            elif not new_categories:
                st.warning("Выбери хотя бы одну категорию")
            else:
                new_date_text = str(new_date)
                new_time_text = new_time.strftime("%H:%M")
                new_duration_value = int(new_duration)
                conflict_task = find_time_conflict(new_date_text, new_time_text, new_duration_value, exclude_task_id=selected_id)

                if conflict_task is not None:
                    conflict_end_time = get_end_time(conflict_task["Дата"], conflict_task["Время"], conflict_task["Длительность_мин"])
                    st.error(f"Нельзя сохранить. На это время уже есть задача: {conflict_task['Время']} - {conflict_end_time} | {conflict_task['Задача']}")
                else:
                    update_task_details(selected_id, new_date_text, new_time_text, new_duration_value, new_title.strip(), ", ".join(new_categories), new_status, new_priority, int(new_weight), skip_reason, new_comment)
                    st.success("Задача обновлена")
                    st.rerun()

    with col_delete:
        if st.button("🗑️ Удалить эту задачу", key=f"delete_selected_task_{selected_id}"):
            delete_task(selected_id)
            st.warning("Задача удалена")
            st.rerun()


def render_calendar_tab():
    st.header("🗓️ Календарный вид недели")

    df = load_tasks()
    plan_df = load_year_plan()

    selected_week_date = st.date_input("Выбери любую дату недели", value=date.today(), key="calendar_week")
    week_start, week_end = get_week_range(selected_week_date)
    st.write(f"Неделя: **{week_start} — {week_end}**")

    if not df.empty:
        stats_df = prepare_stats_dataframe(df)
        week_df, _, _ = filter_week(stats_df, selected_week_date)
    else:
        week_df = pd.DataFrame()

    cols = st.columns(7)

    for day_index, weekday in enumerate(WEEKDAY_ORDER):
        current_date = week_start + timedelta(days=day_index)
        day_plan = get_day_plan(current_date)
        day_df = week_df[week_df["Дата"] == str(current_date)].sort_values("Время") if not week_df.empty else pd.DataFrame()

        with cols[day_index]:
            st.markdown(f"### {WEEKDAY_SHORT[weekday]}")
            st.caption(str(current_date))
            st.info(f"{day_plan['day_type']}\n\n{day_plan['theme']}")

            if day_df.empty:
                st.write("Личных задач нет")
            else:
                for _, row in day_df.iterrows():
                    end_time = get_end_time(row["Дата"], row["Время"], row["Длительность_мин"])
                    status_icon = {"Выполнено": "✅", "Частично": "🟡", "Пропущено": "❌", "Запланировано": "⏳"}.get(row["Статус"], "•")
                    st.markdown(f"**{status_icon} {row['Время']}-{end_time}**  \n{row['Задача']}  \n`{row['Приоритет']}` `Вес {row['Вес']}`")
                    st.divider()


def render_alarm_tab():
    st.header("⏰ Будильник и задачи на сегодня")
    df = load_tasks()

    if df.empty:
        st.info("Пока задач нет")
        return

    today = str(date.today())
    today_tasks = df[df["Дата"] == today].copy()

    if today_tasks.empty:
        st.info("На сегодня задач нет")
        return

    today_tasks["Конец"] = today_tasks.apply(lambda row: get_end_time(row["Дата"], row["Время"], row["Длительность_мин"]), axis=1)
    today_tasks["Состояние"] = today_tasks.apply(lambda row: get_time_state(row["Дата"], row["Время"], row["Длительность_мин"]), axis=1)

    active_tasks = today_tasks[
        (today_tasks["Статус"] == "Запланировано") &
        ((today_tasks["Состояние"] == "Идёт сейчас") | (today_tasks["Состояние"] == "Время прошло"))
    ]

    if not active_tasks.empty:
        st.error("⏰ Есть задачи, время которых уже наступило")
        for _, row in active_tasks.iterrows():
            st.write(f"**{row['Время']} - {row['Конец']}** | {row['Задача']} | {row['Категории']}")
        play_alarm_sound()
    else:
        st.success("Сейчас нет задач, время которых наступило")

    st.subheader("Задачи на сегодня")
    st.dataframe(today_tasks[["id", "Время", "Конец", "Длительность_мин", "Задача", "Категории", "Приоритет", "Вес", "Статус", "Состояние"]], use_container_width=True)


def render_template_tab():
    st.header("📦 Шаблон недели")
    categories_list = load_categories()
    template_names = load_template_names()

    st.subheader("Добавить задачу в шаблон")
    col1, col2 = st.columns(2)
    with col1:
        template_name = st.text_input("Название шаблона", value=template_names[0] if template_names else "Основной")
    with col2:
        weekday = st.selectbox("День недели", WEEKDAY_ORDER)

    col3, col4 = st.columns(2)
    with col3:
        start_time = st.time_input("Время", value=get_default_time(), key="template_time")
    with col4:
        duration = st.number_input("Длительность, минут", min_value=5, max_value=600, value=30, step=5, key="template_duration")

    title = st.text_input("Задача шаблона", placeholder="Например: Английский 20 минут")

    col5, col6, col7 = st.columns(3)
    with col5:
        categories = st.multiselect("Категории", categories_list, key="template_categories")
    with col6:
        priority = st.selectbox("Приоритет", PRIORITIES, index=1, key="template_priority")
    with col7:
        weight = st.slider("Вес", min_value=1, max_value=5, value=1, key="template_weight")

    if st.button("Добавить в шаблон"):
        if not template_name.strip():
            st.warning("Напиши название шаблона")
        elif not title.strip():
            st.warning("Напиши задачу")
        elif not categories:
            st.warning("Выбери категорию")
        else:
            add_template_task(template_name.strip(), weekday, start_time.strftime("%H:%M"), int(duration), title.strip(), ", ".join(categories), priority, int(weight))
            st.success("Задача добавлена в шаблон")
            st.rerun()

    st.divider()
    st.subheader("Список задач шаблона")
    template_df = load_template_tasks()

    if template_df.empty:
        st.info("Шаблон пока пустой")
    else:
        st.dataframe(template_df, use_container_width=True)
        delete_id = st.number_input("ID задачи шаблона для удаления", min_value=1, step=1)
        if st.button("Удалить задачу шаблона"):
            delete_template_task(int(delete_id))
            st.warning("Задача шаблона удалена")
            st.rerun()

    st.divider()
    st.subheader("Применить шаблон к неделе")
    template_names = load_template_names()
    selected_template = st.selectbox("Выбери шаблон", template_names)
    selected_week_date = st.date_input("Выбери любую дату нужной недели", value=date.today(), key="apply_template_date")
    week_start, week_end = get_week_range(selected_week_date)
    st.write(f"Будет применено к неделе: **{week_start} — {week_end}**")

    if st.button("Создать неделю по шаблону"):
        template_df = load_template_tasks(selected_template)

        if template_df.empty:
            st.warning("В этом шаблоне нет задач")
        else:
            added_count = 0
            conflicts = []

            for _, row in template_df.iterrows():
                weekday_index = WEEKDAY_INDEX.get(row["День_недели"], 0)
                task_date = week_start + timedelta(days=weekday_index)
                task_date_text = str(task_date)
                conflict = find_time_conflict(task_date_text, row["Время"], int(row["Длительность_мин"]))

                if conflict is not None:
                    conflict_end_time = get_end_time(conflict["Дата"], conflict["Время"], conflict["Длительность_мин"])
                    conflicts.append(f"{task_date_text}: занято {conflict['Время']} - {conflict_end_time} | {conflict['Задача']}")
                    continue

                add_task(task_date_text, row["Время"], int(row["Длительность_мин"]), row["Задача"], row["Категории"], row["Приоритет"], int(row["Вес"]))
                added_count += 1

            st.success(f"Создано задач из шаблона: {added_count}")

            if conflicts:
                st.warning("Некоторые задачи не добавлены из-за конфликта времени:")
                for conflict in conflicts:
                    st.write(f"- {conflict}")

            if added_count:
                st.rerun()


def render_autoplan_tab():
    st.header("🤖 Автопланирование недели")
    categories_list = load_categories()
    selected_week_date = st.date_input("Неделя для автоплана", value=date.today(), key="autoplan_week")
    week_start, week_end = get_week_range(selected_week_date)
    st.write(f"Неделя: **{week_start} — {week_end}**")

    title_prefix = st.text_input("Название задачи", placeholder="Например: Python практика")
    category = st.selectbox("Категория", categories_list)
    repetitions = st.number_input("Сколько раз за неделю", min_value=1, max_value=14, value=3, step=1)
    duration = st.number_input("Длительность, минут", min_value=5, max_value=300, value=30, step=5, key="auto_duration")
    priority = st.selectbox("Приоритет", PRIORITIES, index=1, key="auto_priority")
    weight = st.slider("Вес", min_value=1, max_value=5, value=1, key="auto_weight")
    preferred_days = st.multiselect("Предпочтительные дни", WEEKDAY_ORDER, default=["Понедельник", "Среда", "Пятница"])
    preferred_period = st.selectbox("Предпочтительное время", ["Утро", "День", "Вечер", "Ночь"])

    period_slots = {
        "Утро": ["07:00", "08:00", "09:00", "10:00"],
        "День": ["12:00", "13:00", "14:00", "15:00"],
        "Вечер": ["18:00", "19:00", "20:00", "21:00"],
        "Ночь": ["00:00", "01:00", "02:00", "03:00"]
    }

    if st.button("Сгенерировать план"):
        if not title_prefix.strip():
            st.warning("Напиши название задачи")
        elif not preferred_days:
            st.warning("Выбери хотя бы один день")
        else:
            added_count = 0
            attempts = []
            slots = period_slots[preferred_period]

            for weekday in preferred_days:
                current_date = week_start + timedelta(days=WEEKDAY_INDEX[weekday])
                for slot in slots:
                    attempts.append((current_date, slot))

            for weekday in WEEKDAY_ORDER:
                current_date = week_start + timedelta(days=WEEKDAY_INDEX[weekday])
                for slot in slots:
                    if (current_date, slot) not in attempts:
                        attempts.append((current_date, slot))

            conflicts = []

            for current_date, slot in attempts:
                if added_count >= repetitions:
                    break

                task_date_text = str(current_date)
                conflict = find_time_conflict(task_date_text, slot, int(duration))

                if conflict is not None:
                    conflicts.append(f"{task_date_text} {slot}: занято | {conflict['Задача']}")
                    continue

                add_task(task_date_text, slot, int(duration), title_prefix.strip(), category, priority, int(weight))
                added_count += 1

            if added_count:
                st.success(f"Автоплан добавил задач: {added_count}")
            if added_count < repetitions:
                st.warning(f"Не удалось добавить все задачи. Нужно было {repetitions}, добавлено {added_count}.")
            if conflicts:
                with st.expander("Конфликты времени"):
                    for conflict in conflicts[:20]:
                        st.write(f"- {conflict}")
            if added_count:
                st.rerun()


def render_budget_tab():
    st.header("💰 Бюджет")
    st.write("Доходы, расходы, план месяца, факт против плана, цели накоплений и анализ по вахте/отдыху.")

    budget_tab_add, budget_tab_plan, budget_tab_analysis, budget_tab_goals, budget_tab_categories = st.tabs([
        "➕ Доход / расход",
        "📅 План месяца",
        "📊 Анализ",
        "🎯 Накопления",
        "⚙️ Категории"
    ])

    with budget_tab_add:
        st.subheader("Добавить операцию")

        col1, col2, col3 = st.columns(3)

        with col1:
            tx_date = st.date_input("Дата", value=date.today(), key="budget_tx_date")

        with col2:
            tx_type = st.selectbox("Тип", ["Расход", "Доход"], key="budget_tx_type")

        with col3:
            payment_method = st.selectbox("Способ оплаты", PAYMENT_METHODS, key="budget_payment")

        category_df = load_budget_categories(tx_type)
        category_list = category_df["name"].tolist() if not category_df.empty else []

        col4, col5 = st.columns(2)

        with col4:
            category = st.selectbox("Категория", category_list, key="budget_category") if category_list else st.text_input("Категория")

        with col5:
            amount = st.number_input("Сумма, ₸", min_value=0.0, value=0.0, step=1000.0, key="budget_amount")

        comment = st.text_input("Комментарий", placeholder="Например: продукты, бензин, ипотека, аванс")

        day_plan = get_day_plan(tx_date)
        st.info(f"Тип дня по годовому плану: **{day_plan['day_type']}**")

        if st.button("Добавить операцию"):
            if not category:
                st.warning("Выбери категорию")
            elif amount <= 0:
                st.warning("Сумма должна быть больше 0")
            else:
                add_budget_transaction(str(tx_date), tx_type, category, amount, payment_method, comment.strip())
                st.success("Операция добавлена")
                st.rerun()

        st.divider()
        st.subheader("Последние операции")
        transactions_df = load_budget_transactions()

        if transactions_df.empty:
            st.info("Операций пока нет")
        else:
            st.dataframe(
                transactions_df[["id", "Дата", "Тип", "Категория", "Сумма", "Способ_оплаты", "Тип_дня", "Комментарий"]].head(50),
                use_container_width=True
            )

            delete_tx_id = st.number_input("ID операции для удаления", min_value=1, step=1, key="delete_budget_tx")
            if st.button("Удалить операцию"):
                delete_budget_transaction(int(delete_tx_id))
                st.warning("Операция удалена")
                st.rerun()

    with budget_tab_plan:
        st.subheader("План месяца")

        selected_month_date = st.date_input("Месяц планирования", value=date.today(), key="budget_plan_month")
        plan_month = pd.to_datetime(selected_month_date).to_period("M").strftime("%Y-%m")
        st.write(f"Месяц: **{plan_month}**")

        expense_categories = load_budget_categories("Расход")
        expense_category_list = expense_categories["name"].tolist() if not expense_categories.empty else DEFAULT_EXPENSE_CATEGORIES

        col1, col2 = st.columns(2)

        with col1:
            plan_category = st.selectbox("Категория расхода", expense_category_list, key="plan_category")

        with col2:
            planned_amount = st.number_input("План, ₸", min_value=0.0, value=0.0, step=5000.0, key="plan_amount")

        plan_comment = st.text_input("Комментарий к плану", key="plan_comment")

        if st.button("Сохранить план по категории"):
            if planned_amount <= 0:
                st.warning("План должен быть больше 0")
            else:
                upsert_monthly_plan(plan_month, plan_category, planned_amount, plan_comment.strip())
                st.success("План сохранён")
                st.rerun()

        st.divider()
        plan_df = load_monthly_plan(plan_month)

        if plan_df.empty:
            st.info("План на этот месяц пока не заполнен")
        else:
            st.dataframe(plan_df[["id", "Месяц", "Категория", "План", "Комментарий"]], use_container_width=True)
            st.metric("План расходов на месяц", f"{plan_df['План'].sum():,.0f} ₸".replace(",", " "))

            delete_plan_id = st.number_input("ID строки плана для удаления", min_value=1, step=1, key="delete_plan_id")
            if st.button("Удалить строку плана"):
                delete_monthly_plan(int(delete_plan_id))
                st.warning("Строка плана удалена")
                st.rerun()

    with budget_tab_analysis:
        st.subheader("Анализ бюджета")

        transactions_df = load_budget_transactions()

        if transactions_df.empty:
            st.info("Операций пока нет")
        else:
            selected_month_date = st.date_input("Месяц анализа", value=date.today(), key="budget_analysis_month")
            analysis_month = pd.to_datetime(selected_month_date).to_period("M").strftime("%Y-%m")

            summary_df, income_total, expense_total, balance = get_budget_month_summary(transactions_df, analysis_month)
            month_df = transactions_df[transactions_df["Месяц"] == analysis_month].copy()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Доход", f"{income_total:,.0f} ₸".replace(",", " "))
            col2.metric("Расход", f"{expense_total:,.0f} ₸".replace(",", " "))
            col3.metric("Остаток", f"{balance:,.0f} ₸".replace(",", " "))
            col4.metric("Операций", len(month_df))

            st.divider()
            st.subheader("Факт против плана")

            if summary_df.empty:
                st.info("Нет расходов или плана за этот месяц")
            else:
                st.dataframe(summary_df, use_container_width=True)

                chart_df = summary_df.melt(
                    id_vars="Категория",
                    value_vars=["План", "Факт"],
                    var_name="Тип",
                    value_name="Сумма"
                )

                fig = px.bar(
                    chart_df,
                    x="Категория",
                    y="Сумма",
                    color="Тип",
                    barmode="group",
                    text="Сумма"
                )
                fig = style_plotly_chart(fig, "План против факта", "Категория", "Сумма, ₸")
                fig.update_xaxes(tickangle=-35)
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Расходы по категориям")

            expense_df = month_df[month_df["Тип"] == "Расход"].copy()

            if expense_df.empty:
                st.info("Расходов за этот месяц нет")
            else:
                expense_by_category = expense_df.groupby("Категория")["Сумма"].sum().reset_index().sort_values("Сумма", ascending=False)
                st.dataframe(expense_by_category, use_container_width=True)

                fig = px.pie(expense_by_category, names="Категория", values="Сумма", title="Структура расходов")
                fig.update_layout(font={"size": 16}, height=520)
                st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Вахта / отдых")

            if "Тип_дня" in month_df.columns and not month_df.empty:
                day_type_expenses = month_df[month_df["Тип"] == "Расход"].groupby("Тип_дня")["Сумма"].sum().reset_index().sort_values("Сумма", ascending=False)

                if day_type_expenses.empty:
                    st.info("Нет расходов для анализа по типу дня")
                else:
                    st.dataframe(day_type_expenses, use_container_width=True)
                    fig = px.bar(day_type_expenses, x="Тип_дня", y="Сумма", text="Сумма", color="Тип_дня")
                    fig = style_plotly_chart(fig, "Расходы по типу дня", "Тип дня", "Сумма, ₸")
                    st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("Все операции за месяц")
            st.dataframe(
                month_df[["id", "Дата", "Тип", "Категория", "Сумма", "Способ_оплаты", "Тип_дня", "Комментарий"]],
                use_container_width=True
            )

    with budget_tab_goals:
        st.subheader("Накопления и цели")

        col1, col2, col3 = st.columns(3)

        with col1:
            goal_name = st.text_input("Название цели", placeholder="Например: резерв, досрочное погашение")

        with col2:
            target_amount = st.number_input("Целевая сумма, ₸", min_value=0.0, value=0.0, step=10000.0, key="goal_target")

        with col3:
            current_amount = st.number_input("Сейчас накоплено, ₸", min_value=0.0, value=0.0, step=10000.0, key="goal_current")

        goal_deadline = st.date_input("Срок", value=date.today(), key="goal_deadline")
        goal_comment = st.text_input("Комментарий к цели", key="goal_comment")

        if st.button("Добавить цель"):
            if not goal_name.strip():
                st.warning("Напиши название цели")
            elif target_amount <= 0:
                st.warning("Целевая сумма должна быть больше 0")
            else:
                add_savings_goal(goal_name.strip(), target_amount, current_amount, goal_deadline, goal_comment.strip())
                st.success("Цель добавлена")
                st.rerun()

        st.divider()
        goals_df = load_savings_goals()

        if goals_df.empty:
            st.info("Целей пока нет")
        else:
            st.dataframe(goals_df, use_container_width=True)

            for _, row in goals_df.iterrows():
                st.write(f"**{row['Цель']}** — {row['Сейчас']:,.0f} / {row['Цель_сумма']:,.0f} ₸".replace(",", " "))
                st.progress(min(row["Прогресс_%"] / 100, 1.0))

            st.divider()
            goal_ids = goals_df["id"].tolist()
            selected_goal_id = st.selectbox("Выбери цель для обновления/удаления", goal_ids, key="selected_goal")
            selected_goal = goals_df[goals_df["id"] == selected_goal_id].iloc[0]
            new_current = st.number_input(
                "Новая сумма накопления, ₸",
                min_value=0.0,
                value=float(selected_goal["Сейчас"]),
                step=10000.0,
                key="update_goal_current"
            )

            col_update, col_delete = st.columns(2)

            with col_update:
                if st.button("Обновить сумму цели"):
                    update_savings_goal(int(selected_goal_id), new_current)
                    st.success("Цель обновлена")
                    st.rerun()

            with col_delete:
                if st.button("Удалить цель"):
                    delete_savings_goal(int(selected_goal_id))
                    st.warning("Цель удалена")
                    st.rerun()

    with budget_tab_categories:
        st.subheader("Категории бюджета")

        col1, col2 = st.columns(2)

        with col1:
            new_budget_category = st.text_input("Новая категория бюджета")

        with col2:
            new_budget_type = st.selectbox("Тип категории", ["Расход", "Доход"], key="new_budget_type")

        if st.button("Добавить категорию бюджета"):
            ok, message = add_budget_category(new_budget_category, new_budget_type)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)

        categories_df = load_budget_categories()

        if categories_df.empty:
            st.info("Категорий бюджета нет")
        else:
            st.dataframe(categories_df, use_container_width=True)
            delete_category_id = st.number_input("ID категории для удаления", min_value=1, step=1, key="delete_budget_category")

            if st.button("Удалить категорию бюджета"):
                delete_budget_category(int(delete_category_id))
                st.warning("Категория бюджета удалена")
                st.rerun()


def render_settings_tab():
    st.header("⚙️ Настройки")
    st.subheader("Категории")
    categories = load_categories()
    st.write(", ".join(categories))

    col1, col2 = st.columns(2)
    with col1:
        new_category = st.text_input("Новая категория")
        if st.button("Добавить категорию"):
            ok, message = add_category(new_category)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.warning(message)
    with col2:
        category_to_delete = st.selectbox("Удалить категорию из списка", categories)
        if st.button("Удалить категорию"):
            delete_category_from_settings(category_to_delete)
            st.warning("Категория удалена из списка. В старых задачах история останется.")
            st.rerun()

    st.divider()
    st.subheader("Переименовать категорию")
    old_category = st.selectbox("Старая категория", categories, key="rename_old")
    renamed_category = st.text_input("Новое название")
    if st.button("Переименовать"):
        ok, message = rename_category(old_category, renamed_category)
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.warning(message)

    st.divider()
    st.subheader("Бэкап базы")
    if DB_PATH.exists():
        with open(DB_PATH, "rb") as file:
            db_bytes = file.read()
        st.download_button("Скачать базу данных", data=db_bytes, file_name=f"week_planner_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db", mime="application/octet-stream")
    if st.button("Создать локальный бэкап в папке backups"):
        backup_path = make_local_backup()
        if backup_path:
            st.success(f"Бэкап создан: {backup_path}")
        else:
            st.warning("База ещё не создана")



def render_metrics_for_week(week_df, previous_week_df):
    total_tasks = len(week_df)
    done_tasks = len(week_df[week_df["Статус"] == "Выполнено"])
    partial_tasks = len(week_df[week_df["Статус"] == "Частично"])
    skipped_tasks = len(week_df[week_df["Статус"] == "Пропущено"])
    planned_tasks = len(week_df[week_df["Статус"] == "Запланировано"])
    overdue_tasks = len(week_df[week_df["Просрочено"] == True])

    percent = get_completion_percent(week_df)
    previous_percent = get_completion_percent(previous_week_df)

    if previous_week_df.empty:
        delta_text = None
    else:
        delta_text = f"{percent - previous_percent:.1f}%"

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    col1.metric("Всего", total_tasks)
    col2.metric("Выполнено", done_tasks)
    col3.metric("Частично", partial_tasks)
    col4.metric("Пропущено", skipped_tasks)
    col5.metric("Без отчёта", planned_tasks)
    col6.metric("Просрочено", overdue_tasks)

    st.metric(
        "Общий процент выполнения с учётом веса",
        f"{percent:.1f}%",
        delta=delta_text
    )


def render_advanced_stats_tab():
    st.header("📊 Статистика + ИИ")
    df = load_tasks()
    work_df = load_work_logs()

    if df.empty and work_df.empty:
        st.info("Пока нет данных")
        return

    selected_week_date = st.date_input("Выбери любую дату нужной недели", value=date.today(), key="stats_week_date")
    week_start, week_end = get_week_range(selected_week_date)
    st.write(f"Период анализа: **{week_start} — {week_end}**")

    if not df.empty:
        stats_df = prepare_stats_dataframe(df)
        week_df, _, _ = filter_week(stats_df, selected_week_date)
        previous_week_date = pd.to_datetime(selected_week_date).date() - timedelta(days=7)
        previous_week_df, previous_week_start, previous_week_end = filter_week(stats_df, previous_week_date)
    else:
        stats_df = pd.DataFrame()
        week_df = pd.DataFrame()
        previous_week_df = pd.DataFrame()
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_end - timedelta(days=7)

    if not work_df.empty:
        work_df["Дата_dt"] = pd.to_datetime(work_df["Дата"], errors="coerce")
        work_week_df = work_df[(work_df["Дата_dt"] >= pd.to_datetime(week_start)) & (work_df["Дата_dt"] <= pd.to_datetime(week_end))].copy()
    else:
        work_week_df = pd.DataFrame()

    if not week_df.empty:
        render_metrics_for_week(week_df, previous_week_df)
        st.divider()
        st.subheader("📌 Распределение по статусам")
        show_status_chart(week_df)
        st.divider()
        st.subheader("🔥 Распределение по приоритету")
        show_priority_chart(week_df)
        st.divider()
        st.subheader("📅 Выполнение по дням недели")
        day_stats = get_weighted_group_stats(week_df, "День_недели")
        day_stats["День_недели"] = pd.Categorical(day_stats["День_недели"], categories=WEEKDAY_ORDER, ordered=True)
        day_stats = day_stats.sort_values("День_недели")
        st.dataframe(day_stats, use_container_width=True)
        show_percent_chart(day_stats, "День_недели", "Процент_выполнения", "Процент выполнения по дням недели", "День недели")
        st.divider()
        st.subheader("🗓️ Выполнение по типу дня")
        day_type_stats = get_weighted_group_stats(week_df, "Тип_дня")
        st.dataframe(day_type_stats, use_container_width=True)
        show_percent_chart(day_type_stats, "Тип_дня", "Процент_выполнения", "Процент выполнения по типу дня", "Тип дня")
        st.divider()
        st.subheader("⏱️ Плановая нагрузка по дням")
        show_load_chart(day_stats, "День_недели", "Минут_запланировано", "Плановая нагрузка по дням", "День недели", "Минут запланировано")
        st.divider()
        st.subheader("🧩 Выполнение по категориям")
        category_df = build_category_dataframe(week_df)
        if category_df.empty:
            category_stats = pd.DataFrame()
            st.info("Нет данных по категориям")
        else:
            category_stats = get_weighted_group_stats(category_df, "Категория")
            category_stats = category_stats.sort_values("Процент_выполнения", ascending=False)
            st.dataframe(category_stats, use_container_width=True)
            show_percent_chart(category_stats, "Категория", "Процент_выполнения", "Процент выполнения по категориям", "Категория")
        st.divider()
        st.subheader("🕒 Анализ по времени суток")
        time_stats = get_weighted_group_stats(week_df, "Период_дня")
        time_order = ["Утро", "День", "Вечер", "Ночь", "Неизвестно"]
        time_stats["Период_дня"] = pd.Categorical(time_stats["Период_дня"], categories=time_order, ordered=True)
        time_stats = time_stats.sort_values("Период_дня")
        st.dataframe(time_stats, use_container_width=True)
        show_percent_chart(time_stats, "Период_дня", "Процент_выполнения", "Выполнение по времени суток", "Период дня")
        st.divider()
        st.subheader("❌ Причины пропуска")
        show_skip_reason_chart(week_df)
        st.divider()
        st.subheader("🔥 Серия выполнения")
        col1, col2, col3 = st.columns(3)
        col1.metric("Дней подряд с выполненными задачами", get_current_streak(stats_df))
        col2.metric("Python streak", get_category_streak(stats_df, "Python"))
        col3.metric("Спорт streak", get_category_streak(stats_df, "Спорт"))
        st.divider()
        st.subheader("📈 Сравнение с прошлой неделей")
        current_percent = get_completion_percent(week_df)
        previous_percent = get_completion_percent(previous_week_df)
        compare_df = pd.DataFrame([
            {"Неделя": f"{previous_week_start} — {previous_week_end}", "Процент": previous_percent},
            {"Неделя": f"{week_start} — {week_end}", "Процент": current_percent}
        ])
        st.dataframe(compare_df, use_container_width=True)
        show_week_compare_chart(compare_df)
        st.divider()
        st.subheader("📆 Статистика по месяцам")
        month_df = stats_df.copy()
        month_df["Месяц"] = month_df["Дата_dt"].dt.to_period("M").astype(str)
        month_stats = get_weighted_group_stats(month_df, "Месяц")
        st.dataframe(month_stats, use_container_width=True)
        show_percent_chart(month_stats, "Месяц", "Процент_выполнения", "Статистика выполнения по месяцам", "Месяц")
    else:
        day_stats = pd.DataFrame()
        category_stats = pd.DataFrame()
        time_stats = pd.DataFrame()
        day_type_stats = pd.DataFrame()
        compare_df = pd.DataFrame()
        month_stats = pd.DataFrame()

    st.divider()
    st.subheader("🛠️ Рабочая статистика за неделю")
    if work_week_df.empty:
        st.info("Рабочих записей за выбранную неделю нет")
    else:
        show_work_chart(work_week_df)
        st.dataframe(work_week_df[["Дата", "Смена", "Участок", "Оборудование", "TAG", "Тип_работы", "Заявка", "Статус"]], use_container_width=True)

    st.divider()
    st.subheader("📤 Экспорт отчёта")
    if not week_df.empty or not work_week_df.empty:
        excel_file = create_excel_report(stats_df, week_df, day_stats, category_stats, time_stats, day_type_stats, compare_df, month_stats, work_week_df)
        st.download_button("Скачать Excel-отчёт недели", data=excel_file, file_name=f"week_report_{week_start}_{week_end}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.divider()
    st.subheader("🤖 ИИ-анализ недели")
    for advice in generate_ai_analysis(week_df, previous_week_df, work_week_df):
        st.info(advice)


def main():
    st.set_page_config(page_title="Week Planner Pro", layout="wide")
    create_database()

    today_plan = get_day_plan(date.today())
    apply_theme_css(today_plan["day_type"])

    if st_autorefresh:
        st_autorefresh(interval=30 * 1000, key="auto_refresh")
    else:
        st.warning("Для автообновления установи: pip install streamlit-autorefresh")

    st.title("📅 Week Planner Pro + КИПиА журнал")
    st.write("Годовой план смен, личные задачи, рабочий журнал, отчёт смены и аналитика.")

    df = load_tasks()
    alarm_tasks = get_alarm_tasks(df)

    st.sidebar.header("Сегодня")
    st.sidebar.write(f"Дата: **{date.today()}**")
    st.sidebar.write(f"Тип дня: **{today_plan['day_type']}**")
    st.sidebar.write(f"Тема: {today_plan['theme']}")
    st.sidebar.divider()
    st.sidebar.header("⏰ Будильник")
    st.sidebar.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if not alarm_tasks.empty:
        st.sidebar.error("Есть задачи по времени!")
        for _, row in alarm_tasks.iterrows():
            st.sidebar.write(f"⏰ {row['Время']} — {row['Задача']}")
        play_alarm_sound()
    else:
        st.sidebar.success("Активных будильников нет")

    menu_items = [
        "🏠 Главная",
        "📆 Годовой план",
        "➕ Личная задача",
        "🛠️ Рабочий журнал",
        "📋 Отчёт смены",
        "📈 Рабочая статистика",
        "💰 Бюджет",
        "📋 Список задач",
        "✅ Отчёт задач",
        "✏️ Редактировать",
        "🗓️ Календарь",
        "📦 Шаблон",
        "🤖 Автоплан",
        "⏰ Будильник",
        "📊 Статистика + ИИ",
        "⚙️ Настройки"
    ]

    st.sidebar.divider()
    st.sidebar.header("📌 Меню")

    selected_page = st.sidebar.selectbox(
        "Открыть раздел",
        menu_items,
        index=0
    )

    if selected_page == "🏠 Главная":
        render_dashboard_tab()
    elif selected_page == "📆 Годовой план":
        render_year_plan_tab()
    elif selected_page == "➕ Личная задача":
        render_add_task_tab()
    elif selected_page == "🛠️ Рабочий журнал":
        render_work_log_tab()
    elif selected_page == "📋 Отчёт смены":
        render_shift_report_tab()
    elif selected_page == "📈 Рабочая статистика":
        render_work_stats_tab()
    elif selected_page == "💰 Бюджет":
        render_budget_tab()
    elif selected_page == "📋 Список задач":
        render_task_list_tab()
    elif selected_page == "✅ Отчёт задач":
        render_daily_report_tab()
    elif selected_page == "✏️ Редактировать":
        render_edit_task_tab()
    elif selected_page == "🗓️ Календарь":
        render_calendar_tab()
    elif selected_page == "📦 Шаблон":
        render_template_tab()
    elif selected_page == "🤖 Автоплан":
        render_autoplan_tab()
    elif selected_page == "⏰ Будильник":
        render_alarm_tab()
    elif selected_page == "📊 Статистика + ИИ":
        render_advanced_stats_tab()
    elif selected_page == "⚙️ Настройки":
        render_settings_tab()


if __name__ == "__main__":
    main()
