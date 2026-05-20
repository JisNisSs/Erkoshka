import hmac
import random
from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


# =============================
# App config
# =============================

st.set_page_config(
    page_title="Erkoshka Planner",
    layout="wide"
)


DAY_TYPES = ["Ночная смена", "Дневная смена", "Отдых"]

DAY_THEME_PRESETS = {
    "Ночная смена": "Работа, заявки, журнал смены, сон, восстановление",
    "Дневная смена": "Работа, монтажи, заявки, отчёт смены, лёгкое обучение",
    "Отдых": "Сон, семья, личные дела, Python, спорт, финансы"
}

TASK_STATUSES = ["Запланировано", "Выполнено", "Частично", "Пропущено"]
TASK_PRIORITIES = ["Низкий", "Средний", "Высокий", "Критичный"]

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

PAYMENT_METHODS = [
    "Kaspi",
    "Halyk",
    "Наличные",
    "Карта",
    "Перевод",
    "Депозит",
    "Другое"
]

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

WEEKDAY_MAP = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье"
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


# =============================
# Supabase connection
# =============================

@st.cache_resource
def get_supabase_client():
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    return create_client(supabase_url, supabase_key)


def supabase_select(table_name, order_column=None, desc=False):
    client = get_supabase_client()
    query = client.table(table_name).select("*")

    if order_column:
        query = query.order(order_column, desc=desc)

    response = query.execute()
    return response.data or []


def supabase_insert(table_name, data):
    client = get_supabase_client()
    return client.table(table_name).insert(data).execute()


def supabase_update(table_name, row_id, data):
    client = get_supabase_client()
    return client.table(table_name).update(data).eq("id", row_id).execute()


def supabase_delete(table_name, row_id):
    client = get_supabase_client()
    return client.table(table_name).delete().eq("id", row_id).execute()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =============================
# Style
# =============================

def get_day_plan(selected_date):
    client = get_supabase_client()
    response = (
        client
        .table("year_plan")
        .select("*")
        .eq("plan_date", str(selected_date))
        .limit(1)
        .execute()
    )

    data = response.data or []

    if data:
        row = data[0]
        day_type = row.get("day_type", "Не задано")
        theme = row.get("theme") or DAY_THEME_PRESETS.get(day_type, "")
        comment = row.get("comment") or ""
        return {"day_type": day_type, "theme": theme, "comment": comment}

    return {
        "day_type": "Не задано",
        "theme": "Тип дня не задан в годовом плане",
        "comment": ""
    }


def apply_theme_css(day_type):
    if day_type == "Ночная смена":
        background = "linear-gradient(135deg, #EEF4FF 0%, #E8EEF8 45%, #F8FAFC 100%)"
        text_color = "#111827"
        card_bg = "rgba(255, 255, 255, 0.90)"
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
        div[data-testid="stMetric"], div[data-testid="stExpander"], div[data-testid="stForm"] {{
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
        .stButton > button {{
            border-radius: 12px;
            border: 1px solid {border};
        }}
        section[data-testid="stSidebar"] {{
            background: {card_bg};
            border-right: 1px solid {border};
        }}
        div[data-testid="stDataFrame"] {{
            background: rgba(255, 255, 255, 0.82);
            border-radius: 16px;
        }}
        @keyframes fadeUp {{
            from {{
                opacity: 0;
                transform: translateY(12px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        @keyframes slideInLeft {{
            from {{
                opacity: 0;
                transform: translateX(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateX(0);
            }}
        }}

        @keyframes softGlow {{
            0% {{
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
            }}
            50% {{
                box-shadow: 0 14px 34px rgba(15, 23, 42, 0.11);
            }}
            100% {{
                box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
            }}
        }}

        .custom-card {{
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid {border};
            border-radius: 22px;
            padding: 24px;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
            margin-bottom: 18px;
            animation: fadeUp 0.45s ease-out, softGlow 4s ease-in-out infinite;
        }}

        div[data-testid="stMetric"] {{
            animation: fadeUp 0.42s ease-out;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }}

        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.10);
        }}

        .stButton > button {{
            transition: transform 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
        }}

        .stButton > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.10);
        }}

        section[data-testid="stSidebar"] {{
            animation: slideInLeft 0.35s ease-out;
        }}

        div[data-testid="stAlert"] {{
            animation: fadeUp 0.35s ease-out;
        }}

        @keyframes gradientMove {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        @keyframes buttonPulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.025); }}
            100% {{ transform: scale(1); }}
        }}

        @keyframes borderGlow {{
            0% {{ border-color: {border}; }}
            50% {{ border-color: {accent}; }}
            100% {{ border-color: {border}; }}
        }}

        .custom-card {{
            background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(238,244,255,0.92), rgba(255,255,255,0.96));
            background-size: 220% 220%;
            animation: fadeUp 0.5s ease-out, gradientMove 7s ease infinite, borderGlow 4s ease-in-out infinite;
            border: 2px solid {border};
            transform-origin: center;
        }}

        .custom-card:hover {{
            transform: translateY(-3px) scale(1.01);
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.14);
        }}

        .stButton > button:first-child {{
            animation: buttonPulse 3.2s ease-in-out infinite;
        }}

        div[data-testid="stMetric"] {{
            border-left: 4px solid {accent};
        }}

        div[data-testid="stMetric"]:hover {{
            transform: translateY(-4px) scale(1.015);
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.14);
        }}

        .element-container {{
            animation: fadeUp 0.35s ease-out;
        }}

        @media (prefers-reduced-motion: reduce) {{
            * {{
                animation: none !important;
                transition: none !important;
            }}
        }}

        .accent-text {{
            color: {accent};
            font-weight: 800;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


# =============================
# Data loading helpers
# =============================

def df_from_table(table_name, order_column=None, desc=False):
    data = supabase_select(table_name, order_column=order_column, desc=desc)
    return pd.DataFrame(data)


def load_categories():
    df = df_from_table("categories", order_column="name")
    if df.empty:
        return DEFAULT_CATEGORIES
    return df["name"].tolist()


def load_budget_categories(category_type=None):
    df = df_from_table("budget_categories", order_column="name")
    if df.empty:
        if category_type == "Доход":
            return DEFAULT_INCOME_CATEGORIES
        if category_type == "Расход":
            return DEFAULT_EXPENSE_CATEGORIES
        return DEFAULT_INCOME_CATEGORIES + DEFAULT_EXPENSE_CATEGORIES

    if category_type:
        df = df[df["category_type"] == category_type]

    return df["name"].tolist()


def load_tasks():
    df = df_from_table("tasks", order_column="task_date")

    if df.empty:
        return pd.DataFrame(columns=[
            "id", "Дата", "Время", "Длительность_мин", "Задача", "Категории",
            "Статус", "Приоритет", "Вес", "Причина_пропуска", "Комментарий", "Создано"
        ])

    df = df.rename(columns={
        "task_date": "Дата",
        "start_time": "Время",
        "duration_minutes": "Длительность_мин",
        "title": "Задача",
        "category": "Категории",
        "status": "Статус",
        "priority": "Приоритет",
        "weight": "Вес",
        "skip_reason": "Причина_пропуска",
        "comment": "Комментарий",
        "created_at": "Создано"
    })

    df["Длительность_мин"] = pd.to_numeric(df["Длительность_мин"], errors="coerce").fillna(30).astype(int)
    df["Вес"] = pd.to_numeric(df["Вес"], errors="coerce").fillna(1).astype(int)
    df["Статус"] = df["Статус"].fillna("Запланировано")
    df["Приоритет"] = df["Приоритет"].fillna("Средний")
    df["Причина_пропуска"] = df["Причина_пропуска"].fillna("")
    df["Комментарий"] = df["Комментарий"].fillna("")

    return df.sort_values(["Дата", "Время", "id"])


def load_year_plan():
    df = df_from_table("year_plan", order_column="plan_date")

    if df.empty:
        return pd.DataFrame(columns=["id", "Дата", "Тип_дня", "Тема", "Комментарий", "Создано"])

    return df.rename(columns={
        "plan_date": "Дата",
        "day_type": "Тип_дня",
        "theme": "Тема",
        "comment": "Комментарий",
        "created_at": "Создано"
    })


def load_work_logs():
    df = df_from_table("work_logs", order_column="work_date", desc=True)

    if df.empty:
        return pd.DataFrame(columns=[
            "id", "Дата", "Смена", "Участок", "Оборудование", "TAG", "Тип_работы",
            "Заявка", "Проблема", "Что_сделал", "Результат", "Статус",
            "Кому_передано", "Комментарий", "Создано"
        ])

    return df.rename(columns={
        "work_date": "Дата",
        "shift_type": "Смена",
        "area": "Участок",
        "equipment": "Оборудование",
        "tag": "TAG",
        "work_type": "Тип_работы",
        "request_number": "Заявка",
        "problem": "Проблема",
        "action_taken": "Что_сделал",
        "result": "Результат",
        "status": "Статус",
        "handover_to": "Кому_передано",
        "comment": "Комментарий",
        "created_at": "Создано"
    })


def load_budget_transactions():
    df = df_from_table("budget_transactions", order_column="tx_date", desc=True)

    if df.empty:
        return pd.DataFrame(columns=[
            "id", "Дата", "Тип", "Категория", "Сумма", "Способ_оплаты",
            "Комментарий", "Создано", "Дата_dt", "Месяц", "Тип_дня"
        ])

    df = df.rename(columns={
        "tx_date": "Дата",
        "tx_type": "Тип",
        "category": "Категория",
        "amount": "Сумма",
        "payment_method": "Способ_оплаты",
        "comment": "Комментарий",
        "created_at": "Создано"
    })

    df["Сумма"] = pd.to_numeric(df["Сумма"], errors="coerce").fillna(0)
    df["Дата_dt"] = pd.to_datetime(df["Дата"], errors="coerce")
    df["Месяц"] = df["Дата_dt"].dt.to_period("M").astype(str)

    plan_df = load_year_plan()
    if not plan_df.empty:
        df = df.merge(plan_df[["Дата", "Тип_дня"]], on="Дата", how="left")
    else:
        df["Тип_дня"] = "Не задано"

    df["Тип_дня"] = df["Тип_дня"].fillna("Не задано")
    return df


def load_monthly_plan(plan_month=None):
    df = df_from_table("monthly_budget_plan", order_column="plan_month", desc=True)

    if df.empty:
        return pd.DataFrame(columns=["id", "Месяц", "Категория", "План", "Комментарий", "Создано"])

    df = df.rename(columns={
        "plan_month": "Месяц",
        "category": "Категория",
        "planned_amount": "План",
        "comment": "Комментарий",
        "created_at": "Создано"
    })
    df["План"] = pd.to_numeric(df["План"], errors="coerce").fillna(0)

    if plan_month:
        df = df[df["Месяц"] == plan_month]

    return df


def load_savings_goals():
    df = df_from_table("savings_goals", order_column="id", desc=True)

    if df.empty:
        return pd.DataFrame(columns=[
            "id", "Цель", "Цель_сумма", "Сейчас", "Срок", "Комментарий", "Создано", "Прогресс_%"
        ])

    df = df.rename(columns={
        "name": "Цель",
        "target_amount": "Цель_сумма",
        "current_amount": "Сейчас",
        "deadline": "Срок",
        "comment": "Комментарий",
        "created_at": "Создано"
    })
    df["Цель_сумма"] = pd.to_numeric(df["Цель_сумма"], errors="coerce").fillna(0)
    df["Сейчас"] = pd.to_numeric(df["Сейчас"], errors="coerce").fillna(0)
    df["Прогресс_%"] = df.apply(
        lambda row: row["Сейчас"] / row["Цель_сумма"] * 100 if row["Цель_сумма"] > 0 else 0,
        axis=1
    )
    return df


# =============================
# Time and stats helpers
# =============================

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


def get_end_time(task_date, start_time, duration_minutes):
    _, end_datetime = get_task_interval(task_date, start_time, duration_minutes)
    if not end_datetime:
        return ""
    return end_datetime.strftime("%H:%M")


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

        existing_start, existing_end = get_task_interval(
            row["Дата"], row["Время"], row["Длительность_мин"]
        )
        if not existing_start or not existing_end:
            continue

        if new_start < existing_end and new_end > existing_start:
            return row

    return None


def get_default_time():
    now = datetime.now()
    minute = 0 if now.minute < 30 else 30
    return now.replace(minute=minute, second=0, microsecond=0).time()


def calculate_score(status):
    if status == "Выполнено":
        return 1.0
    if status == "Частично":
        return 0.5
    return 0.0


def prepare_stats_dataframe(df):
    stats_df = df.copy()
    if stats_df.empty:
        return stats_df

    stats_df["Дата_dt"] = pd.to_datetime(stats_df["Дата"], errors="coerce")
    stats_df["score"] = stats_df["Статус"].apply(calculate_score)
    stats_df["weighted_score"] = stats_df["score"] * stats_df["Вес"]
    stats_df["День_недели"] = stats_df["Дата_dt"].dt.weekday.map(WEEKDAY_MAP)

    plan_df = load_year_plan()
    if not plan_df.empty:
        stats_df = stats_df.merge(plan_df[["Дата", "Тип_дня", "Тема"]], on="Дата", how="left")
    else:
        stats_df["Тип_дня"] = "Не задано"
        stats_df["Тема"] = ""

    stats_df["Тип_дня"] = stats_df["Тип_дня"].fillna("Не задано")
    stats_df["Тема"] = stats_df["Тема"].fillna("")
    return stats_df


def get_completion_percent(df):
    if df.empty:
        return 0.0
    total_weight = df["Вес"].sum()
    if total_weight <= 0:
        return 0.0
    weighted = df["Статус"].apply(calculate_score) * df["Вес"]
    return weighted.sum() / total_weight * 100


def get_week_range(selected_date):
    selected_datetime = pd.to_datetime(selected_date)
    week_start = selected_datetime - pd.Timedelta(days=selected_datetime.weekday())
    week_end = week_start + pd.Timedelta(days=6)
    return week_start.date(), week_end.date()


def filter_week(stats_df, selected_date):
    week_start, week_end = get_week_range(selected_date)
    if stats_df.empty:
        return stats_df, week_start, week_end
    week_df = stats_df[
        (stats_df["Дата_dt"] >= pd.to_datetime(week_start)) &
        (stats_df["Дата_dt"] <= pd.to_datetime(week_end))
    ].copy()
    return week_df, week_start, week_end


def build_shift_report(report_date, shift_type, logs_df):
    if logs_df.empty:
        return f"Отчёт за {shift_type.lower()} {report_date}\n\nРаботы за выбранную дату не добавлены."

    lines = []
    lines.append(f"Отчёт за {shift_type.lower()} {report_date}")
    lines.append("")
    lines.append("За смену выполнены/зарегистрированы работы:")
    lines.append("")

    for index, row in enumerate(logs_df.itertuples(index=False), start=1):
        lines.append(f"{index}. Участок: {getattr(row, 'Участок') or 'не указан'}")
        lines.append(f"   Оборудование: {getattr(row, 'Оборудование') or 'не указано'}")
        lines.append(f"   TAG: {getattr(row, 'TAG') or 'не указан'}")
        lines.append(f"   Тип работы: {getattr(row, 'Тип_работы') or 'не указано'}")
        lines.append(f"   Заявка/вызов: {getattr(row, 'Заявка') or '-'}")
        lines.append(f"   Проблема: {getattr(row, 'Проблема') or 'не указано'}")
        lines.append(f"   Выполнено: {getattr(row, 'Что_сделал') or 'не указано'}")
        lines.append(f"   Результат: {getattr(row, 'Результат') or 'не указано'}")
        lines.append(f"   Статус: {getattr(row, 'Статус') or 'не указано'}")

        handover = getattr(row, "Кому_передано") or ""
        if handover:
            lines.append(f"   Передано: {handover}")

        comment = getattr(row, "Комментарий") or ""
        if comment:
            lines.append(f"   Комментарий: {comment}")

        lines.append("")

    waiting_statuses = ["Ждём механиков", "Ждём электриков", "Ждём запчасть", "Передано следующей смене"]
    waiting_df = logs_df[logs_df["Статус"].isin(waiting_statuses)]

    if not waiting_df.empty:
        lines.append("Работы для контроля/передачи:")
        for row in waiting_df.itertuples(index=False):
            lines.append(f"- {getattr(row, 'Участок')} / {getattr(row, 'TAG')} / {getattr(row, 'Статус')}")
        lines.append("")

    return "\n".join(lines)


def style_plotly_chart(fig, title, x_title, y_title):
    fig.update_layout(
        title={"text": title, "font": {"size": 24}, "x": 0.02},
        font={"size": 15},
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text="",
        height=480,
        margin={"l": 45, "r": 25, "t": 80, "b": 80},
        plot_bgcolor="rgba(0,0,0,0)"
    )
    fig.update_xaxes(tickfont={"size": 14}, title_font={"size": 16}, showgrid=False)
    fig.update_yaxes(tickfont={"size": 14}, title_font={"size": 16}, gridcolor="#E5E5E5")
    fig.update_traces(textposition="outside", textfont_size=14)
    return fig


# =============================
# Pages
# =============================

def render_dashboard_page():
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

    shift_work = today_work[today_work["Смена"] == current_shift].copy() if not today_work.empty else pd.DataFrame()

    unfinished_statuses = [
        "Открыто", "В работе", "Передано следующей смене",
        "Ждём механиков", "Ждём электриков", "Ждём запчасть"
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
            next_row = future_tasks.sort_values("start_dt").iloc[0] if not future_tasks.empty else planned_tasks.sort_values("Время").iloc[0]
            next_task_text = f"{next_row['Время']} — {next_row['Задача']}"

    st.markdown(
        f"""
        <div class="custom-card">
            <div style="font-size: 18px; opacity: 0.75; margin-bottom: 6px;">Сегодня: {day_plan['day_type']}</div>
            <div style="font-size: 30px; font-weight: 800; margin-bottom: 10px;">{today_text}</div>
            <div style="font-size: 20px;"><b>Тема:</b> {day_plan['theme']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Следующая личная задача", next_task_text)
    col2.metric("Рабочих записей за смену", len(shift_work))
    col3.metric("Незавершённые рабочие заявки", len(unfinished_work))

    if not unfinished_work.empty:
        st.subheader("Незавершённые работы")
        st.dataframe(
            unfinished_work[["Дата", "Смена", "Участок", "Оборудование", "TAG", "Тип_работы", "Заявка", "Статус"]],
            use_container_width=True
        )


def render_year_plan_page():
    st.header("📆 Годовой план смен")

    st.subheader("Добавить / изменить один день")
    col1, col2 = st.columns(2)
    with col1:
        plan_date = st.date_input("Дата", value=date.today(), key="year_plan_single_date")
    with col2:
        day_type = st.selectbox("Тип дня", DAY_TYPES, key="year_plan_type")

    theme = st.text_input("Тема дня", value=DAY_THEME_PRESETS.get(day_type, ""), key="year_plan_theme")
    comment = st.text_area("Комментарий", placeholder="Например: выезд, закрыть отчёт, подготовка")

    col_save, col_delete = st.columns(2)
    with col_save:
        if st.button("Сохранить день"):
            client = get_supabase_client()
            client.table("year_plan").upsert({
                "plan_date": str(plan_date),
                "day_type": day_type,
                "theme": theme,
                "comment": comment,
                "created_at": now_text()
            }, on_conflict="plan_date").execute()
            st.success("День сохранён")
            st.rerun()

    with col_delete:
        if st.button("Удалить день из плана"):
            client = get_supabase_client()
            client.table("year_plan").delete().eq("plan_date", str(plan_date)).execute()
            st.warning("День удалён")
            st.rerun()

    st.divider()
    st.subheader("Быстро заполнить диапазон")
    col3, col4, col5 = st.columns(3)
    with col3:
        range_start = st.date_input("Начало", value=date.today(), key="range_start")
    with col4:
        range_end = st.date_input("Конец", value=date.today() + timedelta(days=6), key="range_end")
    with col5:
        range_type = st.selectbox("Тип", DAY_TYPES, key="range_type")

    range_theme = st.text_input("Тема для диапазона", value=DAY_THEME_PRESETS.get(range_type, ""), key="range_theme")
    range_comment = st.text_input("Комментарий для диапазона", key="range_comment")

    if st.button("Заполнить диапазон"):
        if range_end < range_start:
            st.warning("Конец диапазона не должен быть раньше начала")
        else:
            client = get_supabase_client()
            rows = []
            current = range_start
            while current <= range_end:
                rows.append({
                    "plan_date": str(current),
                    "day_type": range_type,
                    "theme": range_theme,
                    "comment": range_comment,
                    "created_at": now_text()
                })
                current += timedelta(days=1)
            client.table("year_plan").upsert(rows, on_conflict="plan_date").execute()
            st.success(f"Заполнено дней: {len(rows)}")
            st.rerun()

    st.divider()
    st.subheader("Текущий план")
    plan_df = load_year_plan()
    if plan_df.empty:
        st.info("План пока пустой")
        return

    plan_df["Дата_dt"] = pd.to_datetime(plan_df["Дата"], errors="coerce")
    selected_year = st.number_input("Год", min_value=2020, max_value=2100, value=date.today().year, step=1)
    filtered = plan_df[plan_df["Дата_dt"].dt.year == int(selected_year)].copy()
    st.dataframe(filtered[["Дата", "Тип_дня", "Тема", "Комментарий"]], use_container_width=True)

    type_count = filtered["Тип_дня"].value_counts().reset_index()
    type_count.columns = ["Тип_дня", "Количество"]
    if not type_count.empty:
        fig = px.bar(type_count, x="Тип_дня", y="Количество", color="Тип_дня", text="Количество")
        fig = style_plotly_chart(fig, "Количество дней по типам", "Тип дня", "Количество")
        st.plotly_chart(fig, use_container_width=True)


def render_add_task_page():
    st.header("➕ Личная задача")

    categories = load_categories()
    col1, col2, col3 = st.columns(3)
    with col1:
        task_date = st.date_input("Дата", value=date.today())
    with col2:
        task_time = st.time_input("Время начала", value=get_default_time())
    with col3:
        duration = st.number_input("Продолжительность, минут", min_value=5, max_value=600, value=30, step=5)

    day_plan = get_day_plan(task_date)
    st.info(f"Тип дня: **{day_plan['day_type']}** | Тема: {day_plan['theme']}")

    title = st.text_input("Задача", placeholder="Например: Python 30 минут")

    col4, col5, col6 = st.columns(3)
    with col4:
        selected_categories = st.multiselect("Категории", categories)
    with col5:
        priority = st.selectbox("Приоритет", TASK_PRIORITIES, index=1)
    with col6:
        weight = st.slider("Вес задачи", 1, 5, 1)

    if st.button("Добавить задачу"):
        if not title.strip():
            st.warning("Напиши задачу")
        elif not selected_categories:
            st.warning("Выбери категорию")
        else:
            conflict = find_time_conflict(str(task_date), task_time.strftime("%H:%M"), int(duration))
            if conflict is not None:
                conflict_end = get_end_time(conflict["Дата"], conflict["Время"], conflict["Длительность_мин"])
                st.error(f"На это время уже есть задача: {conflict['Время']} - {conflict_end} | {conflict['Задача']}")
            else:
                supabase_insert("tasks", {
                    "task_date": str(task_date),
                    "start_time": task_time.strftime("%H:%M"),
                    "duration_minutes": int(duration),
                    "title": title.strip(),
                    "category": ", ".join(selected_categories),
                    "status": "Запланировано",
                    "priority": priority,
                    "weight": int(weight),
                    "skip_reason": "",
                    "comment": "",
                    "created_at": now_text()
                })
                st.success("Задача добавлена")
                st.rerun()


def render_task_list_page():
    st.header("📋 Список задач")
    df = load_tasks()
    if df.empty:
        st.info("Задач пока нет")
        return

    df["Конец"] = df.apply(lambda row: get_end_time(row["Дата"], row["Время"], row["Длительность_мин"]), axis=1)
    st.dataframe(
        df[["id", "Дата", "Время", "Конец", "Длительность_мин", "Задача", "Категории", "Приоритет", "Вес", "Статус", "Комментарий"]],
        use_container_width=True
    )


def render_task_report_page():
    st.header("✅ Отчёт задач")
    df = load_tasks()
    if df.empty:
        st.info("Задач пока нет")
        return

    selected_date = st.date_input("Дата отчёта", value=date.today())
    day_tasks = df[df["Дата"] == str(selected_date)].copy()
    if day_tasks.empty:
        st.info("На этот день задач нет")
        return

    for _, row in day_tasks.iterrows():
        st.subheader(row["Задача"])
        st.write(f"Время: {row['Время']} - {get_end_time(row['Дата'], row['Время'], row['Длительность_мин'])}")
        st.write(f"Категории: {row['Категории']} | Приоритет: {row['Приоритет']} | Вес: {row['Вес']}")

        status_index = TASK_STATUSES.index(row["Статус"]) if row["Статус"] in TASK_STATUSES else 0
        new_status = st.selectbox("Статус", TASK_STATUSES, index=status_index, key=f"task_status_{row['id']}")

        skip_reason = ""
        if new_status == "Пропущено":
            skip_reason = st.selectbox("Причина пропуска", SKIP_REASONS, key=f"skip_{row['id']}")

        comment = st.text_area("Комментарий", value=row["Комментарий"] or "", key=f"task_comment_{row['id']}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Сохранить", key=f"save_task_{row['id']}"):
                supabase_update("tasks", int(row["id"]), {
                    "status": new_status,
                    "skip_reason": skip_reason if new_status == "Пропущено" else "",
                    "comment": comment
                })
                st.success("Сохранено")
                st.rerun()
        with col2:
            if st.button("Удалить", key=f"delete_task_{row['id']}"):
                supabase_delete("tasks", int(row["id"]))
                st.warning("Удалено")
                st.rerun()
        st.divider()


def render_work_log_page():
    st.header("🛠️ Рабочий журнал КИПиА")

    selected_date = st.date_input("Дата", value=date.today(), key="work_date")
    day_plan = get_day_plan(selected_date)
    default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Отдых"
    shift_options = ["День", "Ночь", "Отдых", "Другое"]
    shift_index = shift_options.index(default_shift) if default_shift in shift_options else 0
    st.info(f"По годовому плану: **{day_plan['day_type']}** | Тема: {day_plan['theme']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        shift_type = st.selectbox("Смена", shift_options, index=shift_index)
    with col2:
        area = st.text_input("Участок", placeholder="FL-111, PU-332")
    with col3:
        equipment = st.text_input("Оборудование", placeholder="конвейер, насос, клапан")

    col4, col5, col6 = st.columns(3)
    with col4:
        tag = st.text_input("TAG", placeholder="3445-LIT-0051")
    with col5:
        work_type = st.selectbox("Тип работы", WORK_TYPES)
    with col6:
        request_number = st.text_input("Заявка / вызов")

    problem = st.text_area("Проблема / причина вызова")
    action_taken = st.text_area("Что сделал")
    result = st.text_area("Результат")

    col7, col8 = st.columns(2)
    with col7:
        status = st.selectbox("Статус", WORK_STATUSES, index=2)
    with col8:
        handover_to = st.text_input("Кому передано")

    comment = st.text_area("Комментарий")

    if st.button("Добавить запись"):
        if not area.strip() and not tag.strip() and not problem.strip():
            st.warning("Заполни хотя бы участок, TAG или проблему")
        else:
            supabase_insert("work_logs", {
                "work_date": str(selected_date),
                "shift_type": shift_type,
                "area": area.strip(),
                "equipment": equipment.strip(),
                "tag": tag.strip(),
                "work_type": work_type,
                "request_number": request_number.strip(),
                "problem": problem.strip(),
                "action_taken": action_taken.strip(),
                "result": result.strip(),
                "status": status,
                "handover_to": handover_to.strip(),
                "comment": comment.strip(),
                "created_at": now_text()
            })
            st.success("Запись добавлена")
            st.rerun()

    st.divider()
    logs_df = load_work_logs()
    if logs_df.empty:
        st.info("Рабочих записей пока нет")
    else:
        st.dataframe(
            logs_df[["id", "Дата", "Смена", "Участок", "Оборудование", "TAG", "Тип_работы", "Заявка", "Статус", "Кому_передано"]].head(100),
            use_container_width=True
        )
        delete_id = st.number_input("ID записи для удаления", min_value=1, step=1)
        if st.button("Удалить рабочую запись"):
            supabase_delete("work_logs", int(delete_id))
            st.warning("Запись удалена")
            st.rerun()


def render_shift_report_page():
    st.header("📋 Отчёт смены")
    work_df = load_work_logs()
    if work_df.empty:
        st.info("Рабочих записей пока нет")
        return

    report_date = st.date_input("Дата отчёта", value=date.today())
    day_plan = get_day_plan(report_date)
    default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Другое"
    shift_options = ["День", "Ночь", "Отдых", "Другое"]
    shift_type = st.selectbox("Смена", shift_options, index=shift_options.index(default_shift) if default_shift in shift_options else 0)

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


def render_work_stats_page():
    st.header("📈 Рабочая статистика")
    work_df = load_work_logs()
    if work_df.empty:
        st.info("Рабочих записей пока нет")
        return

    work_df["Дата_dt"] = pd.to_datetime(work_df["Дата"], errors="coerce")
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("Дата от", value=work_df["Дата_dt"].min().date())
    with col2:
        date_to = st.date_input("Дата до", value=work_df["Дата_dt"].max().date())

    filtered = work_df[(work_df["Дата_dt"] >= pd.to_datetime(date_from)) & (work_df["Дата_dt"] <= pd.to_datetime(date_to))].copy()
    if filtered.empty:
        st.info("Нет записей за период")
        return

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Всего", len(filtered))
    col_b.metric("Завершено", len(filtered[filtered["Статус"] == "Завершено"]))
    col_c.metric("Передано", len(filtered[filtered["Статус"] == "Передано следующей смене"]))
    col_d.metric("Ожидание", len(filtered[filtered["Статус"].isin(["Ждём механиков", "Ждём электриков", "Ждём запчасть"])]))

    area_count = filtered["Участок"].replace("", "Не указан").value_counts().reset_index()
    area_count.columns = ["Участок", "Количество"]
    fig = px.bar(area_count, x="Участок", y="Количество", text="Количество")
    fig = style_plotly_chart(fig, "Работы по участкам", "Участок", "Количество")
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

    status_count = filtered["Статус"].value_counts().reset_index()
    status_count.columns = ["Статус", "Количество"]
    st.dataframe(status_count, use_container_width=True)


def render_budget_page():
    st.header("💰 Бюджет")

    tab_add, tab_plan, tab_analysis, tab_goals, tab_categories = st.tabs([
        "➕ Доход / расход", "📅 План месяца", "📊 Анализ", "🎯 Накопления", "⚙️ Категории"
    ])

    with tab_add:
        col1, col2, col3 = st.columns(3)
        with col1:
            tx_date = st.date_input("Дата", value=date.today(), key="tx_date")
        with col2:
            tx_type = st.selectbox("Тип", ["Расход", "Доход"], key="tx_type")
        with col3:
            payment_method = st.selectbox("Способ оплаты", PAYMENT_METHODS)

        categories = load_budget_categories(tx_type)
        col4, col5 = st.columns(2)
        with col4:
            category = st.selectbox("Категория", categories)
        with col5:
            amount = st.number_input("Сумма, ₸", min_value=0.0, value=0.0, step=1000.0)

        comment = st.text_input("Комментарий")
        day_plan = get_day_plan(tx_date)
        st.info(f"Тип дня: **{day_plan['day_type']}**")

        if st.button("Добавить операцию"):
            if amount <= 0:
                st.warning("Сумма должна быть больше 0")
            else:
                supabase_insert("budget_transactions", {
                    "tx_date": str(tx_date),
                    "tx_type": tx_type,
                    "category": category,
                    "amount": float(amount),
                    "payment_method": payment_method,
                    "comment": comment.strip(),
                    "created_at": now_text()
                })
                st.success("Операция добавлена")
                st.rerun()

        transactions_df = load_budget_transactions()
        if not transactions_df.empty:
            st.subheader("Последние операции")
            st.dataframe(transactions_df[["id", "Дата", "Тип", "Категория", "Сумма", "Способ_оплаты", "Тип_дня", "Комментарий"]].head(50), use_container_width=True)
            delete_id = st.number_input("ID операции для удаления", min_value=1, step=1)
            if st.button("Удалить операцию"):
                supabase_delete("budget_transactions", int(delete_id))
                st.warning("Операция удалена")
                st.rerun()

    with tab_plan:
        selected_month_date = st.date_input("Месяц", value=date.today(), key="plan_month_date")
        plan_month = pd.to_datetime(selected_month_date).to_period("M").strftime("%Y-%m")
        st.write(f"Месяц: **{plan_month}**")

        expense_categories = load_budget_categories("Расход")
        col1, col2 = st.columns(2)
        with col1:
            plan_category = st.selectbox("Категория", expense_categories)
        with col2:
            planned_amount = st.number_input("План, ₸", min_value=0.0, value=0.0, step=5000.0)
        plan_comment = st.text_input("Комментарий к плану")

        if st.button("Сохранить план"):
            if planned_amount <= 0:
                st.warning("План должен быть больше 0")
            else:
                client = get_supabase_client()
                client.table("monthly_budget_plan").upsert({
                    "plan_month": plan_month,
                    "category": plan_category,
                    "planned_amount": float(planned_amount),
                    "comment": plan_comment.strip(),
                    "created_at": now_text()
                }, on_conflict="plan_month,category").execute()
                st.success("План сохранён")
                st.rerun()

        plan_df = load_monthly_plan(plan_month)
        if plan_df.empty:
            st.info("План пока пустой")
        else:
            st.dataframe(plan_df[["id", "Месяц", "Категория", "План", "Комментарий"]], use_container_width=True)
            st.metric("План расходов", f"{plan_df['План'].sum():,.0f} ₸".replace(",", " "))

    with tab_analysis:
        transactions_df = load_budget_transactions()
        if transactions_df.empty:
            st.info("Операций пока нет")
        else:
            selected_month_date = st.date_input("Месяц анализа", value=date.today(), key="analysis_month_date")
            analysis_month = pd.to_datetime(selected_month_date).to_period("M").strftime("%Y-%m")
            month_df = transactions_df[transactions_df["Месяц"] == analysis_month].copy()

            income_total = month_df[month_df["Тип"] == "Доход"]["Сумма"].sum()
            expense_total = month_df[month_df["Тип"] == "Расход"]["Сумма"].sum()
            balance = income_total - expense_total

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Доход", f"{income_total:,.0f} ₸".replace(",", " "))
            col2.metric("Расход", f"{expense_total:,.0f} ₸".replace(",", " "))
            col3.metric("Остаток", f"{balance:,.0f} ₸".replace(",", " "))
            col4.metric("Операций", len(month_df))

            expense_df = month_df[month_df["Тип"] == "Расход"].copy()
            if not expense_df.empty:
                expense_by_category = expense_df.groupby("Категория")["Сумма"].sum().reset_index().sort_values("Сумма", ascending=False)
                st.dataframe(expense_by_category, use_container_width=True)
                fig = px.pie(expense_by_category, names="Категория", values="Сумма", title="Структура расходов")
                st.plotly_chart(fig, use_container_width=True)

                by_day_type = expense_df.groupby("Тип_дня")["Сумма"].sum().reset_index().sort_values("Сумма", ascending=False)
                fig2 = px.bar(by_day_type, x="Тип_дня", y="Сумма", text="Сумма", color="Тип_дня")
                fig2 = style_plotly_chart(fig2, "Расходы по типу дня", "Тип дня", "Сумма, ₸")
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Все операции месяца")
            st.dataframe(month_df[["id", "Дата", "Тип", "Категория", "Сумма", "Способ_оплаты", "Тип_дня", "Комментарий"]], use_container_width=True)

    with tab_goals:
        col1, col2, col3 = st.columns(3)
        with col1:
            goal_name = st.text_input("Название цели")
        with col2:
            target_amount = st.number_input("Целевая сумма, ₸", min_value=0.0, value=0.0, step=10000.0)
        with col3:
            current_amount = st.number_input("Сейчас накоплено, ₸", min_value=0.0, value=0.0, step=10000.0)
        deadline = st.date_input("Срок", value=date.today())
        goal_comment = st.text_input("Комментарий к цели")

        if st.button("Добавить цель"):
            if not goal_name.strip():
                st.warning("Напиши цель")
            elif target_amount <= 0:
                st.warning("Цель должна быть больше 0")
            else:
                supabase_insert("savings_goals", {
                    "name": goal_name.strip(),
                    "target_amount": float(target_amount),
                    "current_amount": float(current_amount),
                    "deadline": str(deadline),
                    "comment": goal_comment.strip(),
                    "created_at": now_text()
                })
                st.success("Цель добавлена")
                st.rerun()

        goals_df = load_savings_goals()
        if not goals_df.empty:
            st.dataframe(goals_df, use_container_width=True)
            for _, row in goals_df.iterrows():
                st.write(f"**{row['Цель']}** — {row['Сейчас']:,.0f} / {row['Цель_сумма']:,.0f} ₸".replace(",", " "))
                st.progress(min(row["Прогресс_%"] / 100, 1.0))

    with tab_categories:
        col1, col2 = st.columns(2)
        with col1:
            new_category = st.text_input("Новая категория бюджета")
        with col2:
            new_type = st.selectbox("Тип", ["Расход", "Доход"])
        if st.button("Добавить категорию"):
            if not new_category.strip():
                st.warning("Название пустое")
            else:
                supabase_insert("budget_categories", {
                    "name": new_category.strip(),
                    "category_type": new_type,
                    "created_at": now_text()
                })
                st.success("Категория добавлена")
                st.rerun()

        categories_df = df_from_table("budget_categories", order_column="name")
        if not categories_df.empty:
            st.dataframe(categories_df, use_container_width=True)


def render_stats_page():
    st.header("📊 Статистика + ИИ")
    tasks_df = load_tasks()
    work_df = load_work_logs()

    if tasks_df.empty and work_df.empty:
        st.info("Пока нет данных")
        return

    selected_week_date = st.date_input("Выбери любую дату недели", value=date.today())
    week_start, week_end = get_week_range(selected_week_date)
    st.write(f"Период: **{week_start} — {week_end}**")

    if not tasks_df.empty:
        stats_df = prepare_stats_dataframe(tasks_df)
        week_df, _, _ = filter_week(stats_df, selected_week_date)

        if not week_df.empty:
            percent = get_completion_percent(week_df)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Всего задач", len(week_df))
            col2.metric("Выполнено", len(week_df[week_df["Статус"] == "Выполнено"]))
            col3.metric("Пропущено", len(week_df[week_df["Статус"] == "Пропущено"]))
            col4.metric("Процент", f"{percent:.1f}%")

            status_count = week_df["Статус"].value_counts().reset_index()
            status_count.columns = ["Статус", "Количество"]
            fig = px.bar(status_count, x="Статус", y="Количество", color="Статус", text="Количество", color_discrete_map=STATUS_COLORS)
            fig = style_plotly_chart(fig, "Задачи по статусам", "Статус", "Количество")
            st.plotly_chart(fig, use_container_width=True)

            if "Тип_дня" in week_df.columns:
                day_type_stats = week_df.groupby("Тип_дня").agg(
                    Количество=("Задача", "count")
                ).reset_index()
                fig2 = px.bar(day_type_stats, x="Тип_дня", y="Количество", text="Количество", color="Тип_дня")
                fig2 = style_plotly_chart(fig2, "Задачи по типу дня", "Тип дня", "Количество")
                st.plotly_chart(fig2, use_container_width=True)

    if not work_df.empty:
        st.divider()
        st.subheader("Рабочий журнал")
        work_df["Дата_dt"] = pd.to_datetime(work_df["Дата"], errors="coerce")
        work_week_df = work_df[(work_df["Дата_dt"] >= pd.to_datetime(week_start)) & (work_df["Дата_dt"] <= pd.to_datetime(week_end))].copy()
        if not work_week_df.empty:
            st.metric("Рабочих записей за неделю", len(work_week_df))
            area_count = work_week_df["Участок"].replace("", "Не указан").value_counts().reset_index()
            area_count.columns = ["Участок", "Количество"]
            fig3 = px.bar(area_count, x="Участок", y="Количество", text="Количество")
            fig3 = style_plotly_chart(fig3, "Работы по участкам", "Участок", "Количество")
            st.plotly_chart(fig3, use_container_width=True)


def render_settings_page():
    st.header("⚙️ Настройки")
    st.subheader("Категории личных задач")

    categories_df = df_from_table("categories", order_column="name")
    if not categories_df.empty:
        st.dataframe(categories_df, use_container_width=True)

    new_category = st.text_input("Новая категория")
    if st.button("Добавить категорию"):
        if not new_category.strip():
            st.warning("Название пустое")
        else:
            supabase_insert("categories", {
                "name": new_category.strip(),
                "created_at": now_text()
            })
            st.success("Категория добавлена")
            st.rerun()


# =============================
# Password protection
# =============================

def check_password():
    """
    Простая защита приложения паролем.
    Пароль хранится в Streamlit Secrets:
    APP_PASSWORD = "твой_пароль"
    """
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown("# 🔒 Erkoshka Planner")
    st.write("Введите пароль, чтобы открыть приложение.")

    password = st.text_input("Пароль", type="password")

    if st.button("Войти", use_container_width=True):
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error("APP_PASSWORD не задан в Streamlit Secrets.")
            st.stop()

        if hmac.compare_digest(password, correct_password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Неверный пароль")

    return False


def logout_button():
    if st.sidebar.button("🚪 Выйти", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()


# =============================
# Voice input
# =============================

def render_browser_voice_box():
    components.html(
        """
        <div style="font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;">
            <div style="
                background:#F8FAFC;
                border:1px solid #CBD5E1;
                border-radius:16px;
                padding:12px;
                margin-bottom:12px;
                color:#334155;
                font-size:15px;
                line-height:1.45;
            ">
                <b>Как пользоваться:</b><br>
                1) Нажми <b>Старт</b> и говори.<br>
                2) Нажми <b>Стоп</b>, когда закончил.<br>
                3) Нажми <b>Скопировать</b> и вставь текст в поле ниже.<br>
                <span style="color:#64748B;">На iPhone можно проще: нажми микрофон на клавиатуре прямо в поле ввода ниже.</span>
            </div>

            <div id="statusBox" style="
                padding:12px;
                border-radius:14px;
                background:#EEF4FF;
                border:1px solid #C7D2FE;
                color:#1E293B;
                font-weight:700;
                margin-bottom:10px;
                text-align:center;
            ">Готов к записи</div>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">
                <button id="startBtn" style="
                    padding:14px 16px;
                    border-radius:14px;
                    border:1px solid #86EFAC;
                    background:#DCFCE7;
                    font-size:17px;
                    font-weight:800;
                    cursor:pointer;
                ">▶️ Старт</button>

                <button id="stopBtn" style="
                    padding:14px 16px;
                    border-radius:14px;
                    border:1px solid #FCA5A5;
                    background:#FEE2E2;
                    font-size:17px;
                    font-weight:800;
                    cursor:pointer;
                ">⏹️ Стоп</button>
            </div>

            <textarea id="voiceText" placeholder="После записи здесь появится текст..." style="
                width:100%;
                min-height:150px;
                margin-top:8px;
                padding:12px;
                border-radius:14px;
                border:1px solid #CBD5E1;
                font-size:16px;
                box-sizing:border-box;
            "></textarea>

            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
                <button id="copyBtn" style="
                    padding:12px 16px;
                    border-radius:14px;
                    border:1px solid #93C5FD;
                    background:#DBEAFE;
                    font-size:16px;
                    font-weight:800;
                    cursor:pointer;
                ">📋 Скопировать</button>

                <button id="clearBtn" style="
                    padding:12px 16px;
                    border-radius:14px;
                    border:1px solid #CBD5E1;
                    background:#F1F5F9;
                    font-size:16px;
                    font-weight:800;
                    cursor:pointer;
                ">🧹 Очистить</button>
            </div>

            <div id="hint" style="margin-top:8px;color:#64748B;font-size:14px;text-align:center;"></div>
        </div>

        <script>
        const startBtn = document.getElementById("startBtn");
        const stopBtn = document.getElementById("stopBtn");
        const copyBtn = document.getElementById("copyBtn");
        const clearBtn = document.getElementById("clearBtn");
        const voiceText = document.getElementById("voiceText");
        const statusBox = document.getElementById("statusBox");
        const hint = document.getElementById("hint");

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        let finalText = "";
        let isListening = false;

        function setStatus(text, bg, border) {
            statusBox.innerText = text;
            statusBox.style.background = bg;
            statusBox.style.borderColor = border;
        }

        if (!SpeechRecognition) {
            setStatus("Голосовой ввод браузером не поддерживается", "#FEF3C7", "#FCD34D");
            hint.innerText = "Используй микрофон на клавиатуре iPhone в поле ниже.";
            startBtn.disabled = true;
            stopBtn.disabled = true;
            startBtn.style.opacity = "0.55";
            stopBtn.style.opacity = "0.55";
        } else {
            recognition = new SpeechRecognition();
            recognition.lang = "ru-RU";
            recognition.interimResults = true;
            recognition.continuous = true;

            recognition.onstart = () => {
                isListening = true;
                setStatus("🎙️ Слушаю... говори", "#DCFCE7", "#86EFAC");
                hint.innerText = "Когда закончишь, нажми Стоп.";
            };

            recognition.onresult = (event) => {
                let interimText = "";
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalText += transcript + " ";
                    } else {
                        interimText += transcript;
                    }
                }
                voiceText.value = (finalText + interimText).trim();
            };

            recognition.onerror = (event) => {
                isListening = false;
                setStatus("Ошибка: " + event.error, "#FEE2E2", "#FCA5A5");
                hint.innerText = "Попробуй ещё раз или используй микрофон на клавиатуре телефона.";
            };

            recognition.onend = () => {
                isListening = false;
                setStatus("⏹️ Запись остановлена", "#E0F2FE", "#7DD3FC");
                hint.innerText = "Теперь нажми Скопировать и вставь текст в поле ниже.";
            };
        }

        startBtn.onclick = () => {
            if (!recognition) return;
            if (isListening) return;
            finalText = voiceText.value ? voiceText.value + " " : "";
            try {
                recognition.start();
            } catch (e) {
                setStatus("Уже записывает", "#DCFCE7", "#86EFAC");
            }
        };

        stopBtn.onclick = () => {
            if (!recognition) return;
            if (isListening) {
                recognition.stop();
            } else {
                setStatus("Запись уже остановлена", "#E0F2FE", "#7DD3FC");
            }
        };

        copyBtn.onclick = async () => {
            try {
                await navigator.clipboard.writeText(voiceText.value);
                setStatus("✅ Текст скопирован", "#DCFCE7", "#86EFAC");
                hint.innerText = "Вставь его в поле ниже.";
            } catch (e) {
                voiceText.select();
                document.execCommand("copy");
                setStatus("✅ Текст скопирован", "#DCFCE7", "#86EFAC");
            }
        };

        clearBtn.onclick = () => {
            finalText = "";
            voiceText.value = "";
            setStatus("Готов к новой записи", "#EEF4FF", "#C7D2FE");
            hint.innerText = "Нажми Старт, чтобы начать заново.";
        };
        </script>
        """,
        height=440
    )


def clean_voice_text(text):
    return " ".join(str(text).strip().split())


def extract_area(text):
    for token in clean_voice_text(text).upper().replace("/", " ").split():
        token = token.strip(".,;:()[]")
        if "-" in token:
            left, right = token.split("-", 1)
            if left.isalpha() and right.isdigit() and 2 <= len(left) <= 4:
                return token
    return ""


def extract_tag(text):
    tokens = [token.strip(".,;:()[]").upper() for token in clean_voice_text(text).replace("/", " ").split()]
    for token in tokens:
        parts = token.split("-")
        if len(parts) >= 3 and parts[0].isdigit() and parts[1].isalpha() and parts[2].isdigit():
            return token
    for token in tokens:
        if "-" in token:
            parts = token.split("-")
            if len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit() and len(parts[0]) >= 2:
                return token
    return ""


def detect_work_type(text):
    lower = clean_voice_text(text).lower()
    checks = [
        ("монтаж", "Монтаж"),
        ("демонтаж", "Демонтаж"),
        ("калибр", "Калибровка"),
        ("питани", "Проверка питания"),
        ("кабель", "Проверка кабеля"),
        ("сигнал", "Проверка сигнала"),
        ("замен", "Замена датчика"),
        ("настро", "Настройка прибора"),
        ("чист", "Чистка датчика"),
        ("осмотр", "Осмотр"),
        ("авар", "Аварийная работа"),
        ("заяв", "Заявка"),
        ("вызов", "Вызов")
    ]
    for key, value in checks:
        if key in lower:
            return value
    return "Вызов"


def detect_work_status(text):
    lower = clean_voice_text(text).lower()
    if "механ" in lower and ("жд" in lower or "перед" in lower):
        return "Ждём механиков"
    if "элект" in lower and ("жд" in lower or "перед" in lower):
        return "Ждём электриков"
    if "запчаст" in lower or "зип" in lower:
        return "Ждём запчасть"
    if "следующ" in lower or "передал" in lower or "передано" in lower:
        return "Передано следующей смене"
    if "в работе" in lower:
        return "В работе"
    if "откры" in lower:
        return "Открыто"
    if "не подтверд" in lower:
        return "Неисправность не подтвердилась"
    if "норм" in lower or "работает" in lower or "восстанов" in lower or "заверш" in lower or "готов" in lower:
        return "Завершено"
    return "Завершено"


def split_problem_and_action(text):
    source = clean_voice_text(text)
    lower = source.lower()
    action_words = ["проверил", "проверили", "заменил", "заменили", "почистил", "почистили", "настроил", "настроили", "сделал", "сделали", "выполнил", "выполнили", "устранил", "устранили"]
    positions = []
    for word in action_words:
        pos = lower.find(word)
        if pos >= 0:
            positions.append(pos)
    if not positions:
        return source, ""
    pos = min(positions)
    return source[:pos].strip(" ,.;"), source[pos:].strip(" ,.;")


def parse_amount_from_voice(text):
    digits = ""
    last_number = ""
    for char in str(text):
        if char.isdigit():
            digits += char
        else:
            if digits:
                last_number = digits
                digits = ""
    if digits:
        last_number = digits
    if not last_number:
        return 0.0
    try:
        return float(last_number)
    except Exception:
        return 0.0


def render_voice_assistant_page():
    st.header("🎙️ Голосовой ввод")
    st.write("Скажи фразу, скопируй распознанный текст и вставь ниже. На iPhone можно нажать микрофон на клавиатуре прямо в поле ввода.")

    render_browser_voice_box()
    st.divider()

    voice_mode = st.selectbox("Куда сохранить голосовую запись", ["🛠️ Рабочий журнал", "➕ Личная задача", "💰 Расход / доход"])
    voice_text = st.text_area("Вставь сюда распознанный текст", placeholder="Например: FL-111 3445-LIT-0051 нестабильный сигнал проверил питание почистил датчик сигнал восстановился", height=130)
    clean_text = clean_voice_text(voice_text)

    if not clean_text:
        st.info("Сначала продиктуй или вставь текст.")
        return

    if voice_mode == "🛠️ Рабочий журнал":
        work_date = st.date_input("Дата", value=date.today(), key="voice_work_date")
        day_plan = get_day_plan(work_date)
        default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Другое"
        shift_options = ["День", "Ночь", "Другое"]
        shift_index = shift_options.index(default_shift) if default_shift in shift_options else 0

        parsed_problem, parsed_action = split_problem_and_action(clean_text)
        parsed_type = detect_work_type(clean_text)
        parsed_status = detect_work_status(clean_text)

        st.subheader("Проверь поля перед сохранением")
        shift_type = st.selectbox("Смена", shift_options, index=shift_index, key="voice_shift")
        area = st.text_input("Участок", value=extract_area(clean_text), key="voice_area")
        tag = st.text_input("TAG", value=extract_tag(clean_text), key="voice_tag")
        work_type = st.selectbox("Тип работы", WORK_TYPES, index=WORK_TYPES.index(parsed_type) if parsed_type in WORK_TYPES else 0, key="voice_work_type")
        problem = st.text_area("Проблема", value=parsed_problem, key="voice_problem")
        action_taken = st.text_area("Что сделал", value=parsed_action, key="voice_action")
        result = st.text_area("Результат", value="", key="voice_result")
        status = st.selectbox("Статус", WORK_STATUSES, index=WORK_STATUSES.index(parsed_status) if parsed_status in WORK_STATUSES else 2, key="voice_status")

        if st.button("Сохранить в рабочий журнал", use_container_width=True):
            supabase_insert("work_logs", {
                "work_date": str(work_date),
                "shift_type": shift_type,
                "area": area.strip(),
                "equipment": "",
                "tag": tag.strip(),
                "work_type": work_type,
                "request_number": "",
                "problem": problem.strip(),
                "action_taken": action_taken.strip(),
                "result": result.strip(),
                "status": status,
                "handover_to": "",
                "comment": clean_text,
                "created_at": now_text()
            })
            st.success("Голосовая запись сохранена в рабочий журнал")
            st.rerun()

    elif voice_mode == "➕ Личная задача":
        task_date = st.date_input("Дата", value=date.today(), key="voice_task_date")
        task_time = st.time_input("Время", value=get_default_time(), key="voice_task_time")
        duration = st.number_input("Минут", min_value=5, max_value=300, value=30, step=5, key="voice_task_duration")
        category = st.selectbox("Категория", load_categories(), key="voice_task_category")
        priority = st.selectbox("Приоритет", TASK_PRIORITIES, index=1, key="voice_task_priority")
        title = st.text_input("Название задачи", value=clean_text, key="voice_task_title")

        if st.button("Сохранить задачу", use_container_width=True):
            conflict = find_time_conflict(str(task_date), task_time.strftime("%H:%M"), int(duration))
            if conflict is not None:
                conflict_end = get_end_time(conflict["Дата"], conflict["Время"], conflict["Длительность_мин"])
                st.error(f"На это время уже есть: {conflict['Время']} - {conflict_end} | {conflict['Задача']}")
            else:
                supabase_insert("tasks", {
                    "task_date": str(task_date),
                    "start_time": task_time.strftime("%H:%M"),
                    "duration_minutes": int(duration),
                    "title": title.strip(),
                    "category": category,
                    "status": "Запланировано",
                    "priority": priority,
                    "weight": 1,
                    "skip_reason": "",
                    "comment": "Голосовой ввод",
                    "created_at": now_text()
                })
                st.success("Задача сохранена")
                st.rerun()

    elif voice_mode == "💰 Расход / доход":
        tx_date = st.date_input("Дата", value=date.today(), key="voice_tx_date")
        tx_type = st.selectbox("Тип", ["Расход", "Доход"], key="voice_tx_type")
        category = st.selectbox("Категория", load_budget_categories(tx_type), key="voice_tx_category")
        amount = st.number_input("Сумма, ₸", min_value=0.0, value=parse_amount_from_voice(clean_text), step=1000.0, key="voice_tx_amount")
        payment_method = st.selectbox("Оплата", PAYMENT_METHODS, key="voice_tx_payment")
        comment = st.text_input("Комментарий", value=clean_text, key="voice_tx_comment")

        if st.button("Сохранить операцию", use_container_width=True):
            if amount <= 0:
                st.warning("Сумма должна быть больше 0")
            else:
                supabase_insert("budget_transactions", {
                    "tx_date": str(tx_date),
                    "tx_type": tx_type,
                    "category": category,
                    "amount": float(amount),
                    "payment_method": payment_method,
                    "comment": comment.strip(),
                    "created_at": now_text()
                })
                st.success("Операция сохранена")
                st.rerun()


# =============================
# Mobile / Desktop mode
# =============================

def detect_device_mode():
    """
    Автоопределение телефона через ширину экрана.
    Streamlit сам напрямую не даёт user-agent, поэтому используем маленький JS.
    Если автоопределение не успело сработать, по умолчанию будет desktop.
    """
    device_param = st.query_params.get("device", None)

    if isinstance(device_param, list):
        device_param = device_param[0] if device_param else None

    if device_param in ["mobile", "desktop"]:
        return device_param

    components.html(
        """
        <script>
        const width = window.parent.innerWidth || window.innerWidth;
        const device = width <= 768 ? "mobile" : "desktop";
        const url = new URL(window.parent.location.href);
        if (!url.searchParams.get("device")) {
            url.searchParams.set("device", device);
            window.parent.location.replace(url.toString());
        }
        </script>
        """,
        height=0
    )

    return "desktop"


def render_mobile_quick_task():
    st.header("➕ Быстрая личная задача")

    categories = load_categories()

    task_date = st.date_input("Дата", value=date.today(), key="mobile_task_date")
    day_plan = get_day_plan(task_date)
    st.info(f"{day_plan['day_type']} | {day_plan['theme']}")

    title = st.text_input("Задача", placeholder="Например: Английский 15 минут", key="mobile_task_title")

    col1, col2 = st.columns(2)
    with col1:
        task_time = st.time_input("Время", value=get_default_time(), key="mobile_task_time")
    with col2:
        duration = st.number_input("Минут", min_value=5, max_value=300, value=30, step=5, key="mobile_task_duration")

    category = st.selectbox("Категория", categories, key="mobile_task_category")
    priority = st.selectbox("Приоритет", TASK_PRIORITIES, index=1, key="mobile_task_priority")

    if st.button("Сохранить задачу", use_container_width=True):
        if not title.strip():
            st.warning("Напиши задачу")
        else:
            conflict = find_time_conflict(str(task_date), task_time.strftime("%H:%M"), int(duration))
            if conflict is not None:
                conflict_end = get_end_time(conflict["Дата"], conflict["Время"], conflict["Длительность_мин"])
                st.error(f"На это время уже есть: {conflict['Время']} - {conflict_end} | {conflict['Задача']}")
            else:
                supabase_insert("tasks", {
                    "task_date": str(task_date),
                    "start_time": task_time.strftime("%H:%M"),
                    "duration_minutes": int(duration),
                    "title": title.strip(),
                    "category": category,
                    "status": "Запланировано",
                    "priority": priority,
                    "weight": 1,
                    "skip_reason": "",
                    "comment": "",
                    "created_at": now_text()
                })
                st.success("Задача сохранена")
                st.rerun()


def render_mobile_quick_work():
    st.header("🛠️ Быстрый рабочий вызов")

    work_date = st.date_input("Дата", value=date.today(), key="mobile_work_date")
    day_plan = get_day_plan(work_date)

    default_shift = "Ночь" if day_plan["day_type"] == "Ночная смена" else "День" if day_plan["day_type"] == "Дневная смена" else "Другое"
    shift_options = ["День", "Ночь", "Другое"]
    shift_index = shift_options.index(default_shift) if default_shift in shift_options else 0

    st.info(f"{day_plan['day_type']} | {day_plan['theme']}")

    shift_type = st.selectbox("Смена", shift_options, index=shift_index, key="mobile_work_shift")
    area = st.text_input("Участок", placeholder="FL-111", key="mobile_work_area")
    tag = st.text_input("TAG", placeholder="3445-LIT-0051", key="mobile_work_tag")
    problem = st.text_area("Проблема", placeholder="Что случилось?", key="mobile_work_problem")
    action_taken = st.text_area("Что сделал", placeholder="Кратко что проверил/сделал", key="mobile_work_action")

    col1, col2 = st.columns(2)
    with col1:
        work_type = st.selectbox("Тип", WORK_TYPES, key="mobile_work_type")
    with col2:
        status = st.selectbox("Статус", WORK_STATUSES, index=2, key="mobile_work_status")

    if st.button("Сохранить рабочую запись", use_container_width=True):
        if not area.strip() and not tag.strip() and not problem.strip():
            st.warning("Заполни участок, TAG или проблему")
        else:
            supabase_insert("work_logs", {
                "work_date": str(work_date),
                "shift_type": shift_type,
                "area": area.strip(),
                "equipment": "",
                "tag": tag.strip(),
                "work_type": work_type,
                "request_number": "",
                "problem": problem.strip(),
                "action_taken": action_taken.strip(),
                "result": "",
                "status": status,
                "handover_to": "",
                "comment": "",
                "created_at": now_text()
            })
            st.success("Рабочая запись сохранена")
            st.rerun()


def render_mobile_quick_expense():
    st.header("💰 Быстрый расход / доход")

    tx_date = st.date_input("Дата", value=date.today(), key="mobile_tx_date")
    tx_type = st.selectbox("Тип", ["Расход", "Доход"], key="mobile_tx_type")
    categories = load_budget_categories(tx_type)

    category = st.selectbox("Категория", categories, key="mobile_tx_category")
    amount = st.number_input("Сумма, ₸", min_value=0.0, value=0.0, step=1000.0, key="mobile_tx_amount")
    payment_method = st.selectbox("Оплата", PAYMENT_METHODS, key="mobile_tx_payment")
    comment = st.text_input("Комментарий", key="mobile_tx_comment")

    if st.button("Сохранить операцию", use_container_width=True):
        if amount <= 0:
            st.warning("Сумма должна быть больше 0")
        else:
            supabase_insert("budget_transactions", {
                "tx_date": str(tx_date),
                "tx_type": tx_type,
                "category": category,
                "amount": float(amount),
                "payment_method": payment_method,
                "comment": comment.strip(),
                "created_at": now_text()
            })
            st.success("Операция сохранена")
            st.rerun()


def render_mobile_day_plan():
    st.header("📆 Тип дня")

    plan_date = st.date_input("Дата", value=date.today(), key="mobile_plan_date")
    day_type = st.selectbox("Тип дня", DAY_TYPES, key="mobile_plan_type")
    theme = st.text_input("Тема", value=DAY_THEME_PRESETS.get(day_type, ""), key="mobile_plan_theme")

    if st.button("Сохранить тип дня", use_container_width=True):
        client = get_supabase_client()
        client.table("year_plan").upsert({
            "plan_date": str(plan_date),
            "day_type": day_type,
            "theme": theme,
            "comment": "",
            "created_at": now_text()
        }, on_conflict="plan_date").execute()
        st.success("Тип дня сохранён")
        st.rerun()


def render_mobile_app():
    st.sidebar.header("📱 Мобильное меню")

    mobile_pages = [
        "🏠 Сегодня",
        "🎙️ Голосовой ввод",
        "➕ Личная задача",
        "🛠️ Рабочий вызов",
        "💰 Расход / доход",
        "📋 Отчёт смены",
        "📆 Тип дня"
    ]

    selected_mobile_page = st.sidebar.selectbox("Раздел", mobile_pages)

    if selected_mobile_page == "🏠 Сегодня":
        render_dashboard_page()
    elif selected_mobile_page == "🎙️ Голосовой ввод":
        render_voice_assistant_page()
    elif selected_mobile_page == "➕ Личная задача":
        render_mobile_quick_task()
    elif selected_mobile_page == "🛠️ Рабочий вызов":
        render_mobile_quick_work()
    elif selected_mobile_page == "💰 Расход / доход":
        render_mobile_quick_expense()
    elif selected_mobile_page == "📋 Отчёт смены":
        render_shift_report_page()
    elif selected_mobile_page == "📆 Тип дня":
        render_mobile_day_plan()


def render_desktop_app():
    st.sidebar.header("📌 Меню")

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
        "📊 Статистика + ИИ",
        "⚙️ Настройки"
    ]

    selected_page = st.sidebar.selectbox("Открыть раздел", menu_items)

    if selected_page == "🏠 Главная":
        render_dashboard_page()
    elif selected_page == "📆 Годовой план":
        render_year_plan_page()
    elif selected_page == "➕ Личная задача":
        render_add_task_page()
    elif selected_page == "🛠️ Рабочий журнал":
        render_work_log_page()
    elif selected_page == "📋 Отчёт смены":
        render_shift_report_page()
    elif selected_page == "📈 Рабочая статистика":
        render_work_stats_page()
    elif selected_page == "💰 Бюджет":
        render_budget_page()
    elif selected_page == "📋 Список задач":
        render_task_list_page()
    elif selected_page == "✅ Отчёт задач":
        render_task_report_page()
    elif selected_page == "📊 Статистика + ИИ":
        render_stats_page()
    elif selected_page == "⚙️ Настройки":
        render_settings_page()


# =============================
# Fun live animations
# =============================

def render_live_fun_mode(day_type):
    """
    Видимая живая анимация прямо на странице.
    Плюс цитата дня и смайлик настроения в карточке Erkoshka Live.
    """
    quotes = [
        ("Ақырын жүріп, анық бас.", "Абай Құнанбайұлы"),
        ("Еңбек етсең ерінбей, тояды қарның тіленбей.", "Абай Құнанбайұлы"),
        ("Пайда ойлама, ар ойла.", "Абай Құнанбайұлы"),
        ("Болмасаң да ұқсап бақ.", "Абай Құнанбайұлы"),
        ("Ғылым таппай мақтанба.", "Абай Құнанбайұлы"),
        ("Сен де бір кірпіш дүниеге, кетігін тап та бар қалан.", "Абай Құнанбайұлы"),
        ("Адам болам десеңіз, оған қайғы жесеңіз.", "Абай Құнанбайұлы"),
        ("Талап, еңбек, терең ой — адамның асыл ісі.", "Абай Құнанбайұлы"),
        ("Ақыл, қайрат, жүректі бірдей ұста.", "Абай Құнанбайұлы"),
        ("Жүректе қайрат болмаса, ұйықтаған ойды кім түртпек?", "Абай Құнанбайұлы"),
        ("Тәрбиесіз берілген білім — адамзаттың қас жауы.", "Әл-Фараби"),
        ("Білімді болу — белгісіз нәрсені аша білу.", "Әл-Фараби"),
        ("Қайырымды адам — қоғамның тірегі.", "Әл-Фараби"),
        ("Ақыл мен мінез қосылса, адам толық болады.", "Әл-Фараби"),
        ("Бақытқа жеткізетін жол — ізгілік пен білім.", "Әл-Фараби"),
        ("Адал еңбек, ақ жүрек, таза ақыл — адамға керек үш қасиет.", "Шәкәрім Құдайбердіұлы"),
        ("Ар ілімі — адамдықтың негізі.", "Шәкәрім Құдайбердіұлы"),
        ("Ұждан жоғалса, адамдық та әлсірейді.", "Шәкәрім Құдайбердіұлы"),
        ("Таза ақыл адамды тура жолға бастайды.", "Шәкәрім Құдайбердіұлы"),
        ("Еңбек пен ақыл біріксе, жол ашылады.", "Шәкәрім Құдайбердіұлы"),
        ("Кел, балалар, оқылық.", "Ыбырай Алтынсарин"),
        ("Оқысаңыз, балалар, шамнан шырақ жағылар.", "Ыбырай Алтынсарин"),
        ("Білім — өмірге жарық түсіретін шам.", "Ыбырай Алтынсарин"),
        ("Өнер-білім бар жұрттар алға қарай барады.", "Ыбырай Алтынсарин"),
        ("Еңбекпен табылған нан тәтті.", "Ыбырай Алтынсарин"),
        ("Ел бүгіншіл, менікі ертең үшін.", "Ахмет Байтұрсынұлы"),
        ("Білімді болуға оқу керек.", "Ахмет Байтұрсынұлы"),
        ("Ұлттың сақталуына тіл керек.", "Ахмет Байтұрсынұлы"),
        ("Оқусыз халық қанша бай болса да, біраз жылда кедей болады.", "Ахмет Байтұрсынұлы"),
        ("Тіл — адамның адамдық белгісінің зоры.", "Ахмет Байтұрсынұлы"),
        ("Оян, қазақ!", "Міржақып Дулатов"),
        ("Елдің ертеңі білімді ұрпақтың қолында.", "Міржақып Дулатов"),
        ("Ұлтқа қызмет ету білімнен басталады.", "Міржақып Дулатов"),
        ("Жастардың міндеті — елге пайда келтіру.", "Міржақып Дулатов"),
        ("Ой оянса, ел оянады.", "Міржақып Дулатов"),
        ("Мен жастарға сенемін.", "Мағжан Жұмабаев"),
        ("Жас қырандар — елдің ертеңгі күші.", "Мағжан Жұмабаев"),
        ("Жүректе от болмаса, істе қуат болмайды.", "Мағжан Жұмабаев"),
        ("Рухы биік елдің жолы ұзақ.", "Мағжан Жұмабаев"),
        ("Арман адамды алға жетелейді.", "Мағжан Жұмабаев"),
        ("Білім — халықтың болашағы.", "Жүсіпбек Аймауытов"),
        ("Тәрбие мен білім қатар жүрсе, адам түзеледі.", "Жүсіпбек Аймауытов"),
        ("Өзін таныған адам елін де таниды.", "Жүсіпбек Аймауытов"),
        ("Жақсы мұғалім — жақсы қоғамның бастауы.", "Жүсіпбек Аймауытов"),
        ("Еңбекке үйренген адам өмірден өз орнын табады.", "Жүсіпбек Аймауытов"),
        ("Қараңғы қазақ көгіне өрмелеп шығып күн болам.", "Сұлтанмахмұт Торайғыров"),
        ("Білімсіз елдің күні қараң.", "Сұлтанмахмұт Торайғыров"),
        ("Жастардың күші — халықтың үміті.", "Сұлтанмахмұт Торайғыров"),
        ("Армансыз адам алысқа бармайды.", "Сұлтанмахмұт Торайғыров"),
        ("Елге қызмет — ерге міндет.", "Сұлтанмахмұт Торайғыров"),
        ("You have power over your mind, not outside events.", "Marcus Aurelius"),
        ("The happiness of your life depends upon your thoughts.", "Marcus Aurelius"),
        ("Waste no more time arguing what a good person should be. Be one.", "Marcus Aurelius"),
        ("The obstacle is the way.", "Marcus Aurelius"),
        ("If it is not right, do not do it.", "Marcus Aurelius"),
        ("He who fears death will never do anything worthy of life.", "Seneca"),
        ("Luck is what happens when preparation meets opportunity.", "Seneca"),
        ("Difficulties strengthen the mind.", "Seneca"),
        ("We suffer more often in imagination than in reality.", "Seneca"),
        ("No wind is favorable to one who has no destination.", "Seneca"),
        ("It is not things that disturb us, but our judgments about them.", "Epictetus"),
        ("First say to yourself what you would be, then do what you have to do.", "Epictetus"),
        ("No person is free who is not master of himself.", "Epictetus"),
        ("Do not explain your philosophy. Embody it.", "Epictetus"),
        ("The key is to keep company only with people who uplift you.", "Epictetus"),
        ("A journey of a thousand miles begins with a single step.", "Lao Tzu"),
        ("Knowing others is wisdom; knowing yourself is enlightenment.", "Lao Tzu"),
        ("Mastering others is strength; mastering yourself is true power.", "Lao Tzu"),
        ("Nature does not hurry, yet everything is accomplished.", "Lao Tzu"),
        ("The wise person does not hoard.", "Lao Tzu"),
        ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
        ("Our greatest glory is not in never falling, but in rising every time.", "Confucius"),
        ("To know what you know and what you do not know, that is knowledge.", "Confucius"),
        ("The person who moves a mountain begins by carrying small stones.", "Confucius"),
        ("Study the past if you would define the future.", "Confucius"),
        ("Knowing yourself is the beginning of all wisdom.", "Aristotle"),
        ("We are what we repeatedly do.", "Aristotle"),
        ("Quality is not an act, it is a habit.", "Aristotle"),
        ("The roots of education are bitter, but the fruit is sweet.", "Aristotle"),
        ("Patience is bitter, but its fruit is sweet.", "Aristotle"),
        ("An unexamined life is not worth living.", "Socrates"),
        ("I know that I know nothing.", "Socrates"),
        ("The secret of change is to focus energy on building the new.", "Socrates"),
        ("Strong minds discuss ideas.", "Socrates"),
        ("To find yourself, think for yourself.", "Socrates"),
        ("What we think, we become.", "Buddha"),
        ("Peace comes from within.", "Buddha"),
        ("No one saves us but ourselves.", "Buddha"),
        ("The mind is everything.", "Buddha"),
        ("Drop by drop is the water pot filled.", "Buddha"),
        ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison"),
        ("I have not failed. I have found ways that do not work.", "Thomas Edison"),
        ("Opportunity is missed because it is dressed in overalls.", "Thomas Edison"),
        ("There is no substitute for hard work.", "Thomas Edison"),
        ("If we did all we are capable of, we would amaze ourselves.", "Thomas Edison"),
        ("Life is like riding a bicycle. To keep balance, you must keep moving.", "Albert Einstein"),
        ("Imagination is more important than knowledge.", "Albert Einstein"),
        ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
        ("A person who never made a mistake never tried anything new.", "Albert Einstein"),
        ("Try not to become successful, but valuable.", "Albert Einstein"),
    ]

    mood_emojis = ["🧠", "🔥", "🚀", "⚡", "💪", "🌿", "☕", "🛠️", "📚", "✅", "🦅", "🌙", "☀️", "💎", "🧭"]

    current_bucket = int(datetime.now().timestamp() // 120)

    if (
        "erk_quote_order" not in st.session_state
        or len(st.session_state.get("erk_quote_order", [])) != len(quotes)
    ):
        quote_order = list(range(len(quotes)))
        random.shuffle(quote_order)
        st.session_state["erk_quote_order"] = quote_order
        st.session_state["erk_quote_position"] = 0
        st.session_state["erk_quote_bucket"] = current_bucket

    if st.session_state.get("erk_quote_bucket") != current_bucket:
        st.session_state["erk_quote_bucket"] = current_bucket
        st.session_state["erk_quote_position"] += 1

        if st.session_state["erk_quote_position"] >= len(st.session_state["erk_quote_order"]):
            quote_order = list(range(len(quotes)))
            random.shuffle(quote_order)
            st.session_state["erk_quote_order"] = quote_order
            st.session_state["erk_quote_position"] = 0

    quote_index = st.session_state["erk_quote_order"][st.session_state["erk_quote_position"]]
    mood_index = quote_index % len(mood_emojis)

    quote_text, quote_author = quotes[quote_index]
    quote_of_day = f"{quote_text}<br><span class='erk-live-author'>— {quote_author}</span>"
    mood_emoji = mood_emojis[mood_index]

    if day_type == "Ночная смена":
        emojis = ["🌙", "🛠️", "⚡", "📟", "🔧", "💤"]
        mascot = mood_emoji
        phrase = "Ночная смена"
        bg_1 = "rgba(99, 102, 241, 0.16)"
        bg_2 = "rgba(14, 165, 233, 0.12)"
        border_color = "rgba(99, 102, 241, 0.45)"
    elif day_type == "Дневная смена":
        emojis = ["☀️", "🛠️", "⚙️", "📋", "🔌", "✅"]
        mascot = mood_emoji
        phrase = "Дневная смена"
        bg_1 = "rgba(14, 165, 233, 0.16)"
        bg_2 = "rgba(34, 197, 94, 0.12)"
        border_color = "rgba(14, 165, 233, 0.45)"
    elif day_type == "Отдых":
        emojis = ["🌿", "☕", "🏃", "📚", "💰", "😎"]
        mascot = mood_emoji
        phrase = "Отдых"
        bg_1 = "rgba(34, 197, 94, 0.16)"
        bg_2 = "rgba(250, 204, 21, 0.14)"
        border_color = "rgba(34, 197, 94, 0.45)"
    else:
        emojis = ["📅", "✅", "📝", "💡", "⚙️", "🚀"]
        mascot = mood_emoji
        phrase = "День не задан"
        bg_1 = "rgba(148, 163, 184, 0.16)"
        bg_2 = "rgba(99, 102, 241, 0.12)"
        border_color = "rgba(100, 116, 139, 0.45)"

    left_positions = [7, 19, 33, 51, 67, 84]
    delays = [0, 1.5, 3, 0.8, 2.3, 4]
    durations = [8, 10, 9, 11, 8.5, 10.5]

    emoji_html = ""
    for index, emoji in enumerate(emojis):
        emoji_html += f"""
        <div class="erk-floating-emoji" style="
            left:{left_positions[index]}%;
            animation-delay:{delays[index]}s;
            animation-duration:{durations[index]}s;
        ">{emoji}</div>
        """

    st.markdown(
        f"""
        <style>
        @keyframes erkFloatEmoji {{
            0% {{
                transform: translateY(0) rotate(0deg) scale(0.8);
                opacity: 0;
            }}
            10% {{ opacity: 0.85; }}
            50% {{
                transform: translateY(-45vh) rotate(14deg) scale(1.15);
                opacity: 0.95;
            }}
            90% {{ opacity: 0.75; }}
            100% {{
                transform: translateY(-92vh) rotate(-12deg) scale(0.85);
                opacity: 0;
            }}
        }}

        @keyframes erkMascotBounce {{
            0%, 100% {{ transform: translateY(0) rotate(-2deg); }}
            50% {{ transform: translateY(-9px) rotate(2deg); }}
        }}

        @keyframes erkShine {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        @keyframes erkPulseRing {{
            0% {{ box-shadow: 0 0 0 0 {border_color}; }}
            70% {{ box-shadow: 0 0 0 12px rgba(255, 255, 255, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }}
        }}

        .erk-live-layer {{
            position: fixed;
            inset: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 999999;
        }}

        .erk-floating-emoji {{
            position: absolute;
            bottom: -60px;
            font-size: 34px;
            animation-name: erkFloatEmoji;
            animation-timing-function: linear;
            animation-iteration-count: infinite;
            filter: drop-shadow(0 8px 12px rgba(15, 23, 42, 0.22));
        }}

        .erk-live-mascot {{
            position: fixed;
            right: 20px;
            bottom: 20px;
            z-index: 1000000;
            width: 250px;
            max-width: calc(100vw - 34px);
            pointer-events: none;
            background: linear-gradient(135deg, rgba(255,255,255,0.96), {bg_1}, {bg_2}, rgba(255,255,255,0.96));
            background-size: 240% 240%;
            border: 2px solid {border_color};
            border-radius: 24px;
            padding: 13px 15px;
            box-shadow: 0 16px 42px rgba(15, 23, 42, 0.20);
            animation: erkMascotBounce 3s ease-in-out infinite, erkShine 6s ease infinite, erkPulseRing 3.5s ease-out infinite;
        }}

        .erk-live-top {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}

        .erk-live-icon {{
            font-size: 36px;
            line-height: 1;
        }}

        .erk-live-title {{
            font-size: 15px;
            font-weight: 900;
            color: #0F172A;
        }}

        .erk-live-text {{
            font-size: 13px;
            color: #334155;
            line-height: 1.35;
            font-weight: 600;
            margin-bottom: 6px;
        }}

        .erk-live-quote {{
            font-size: 12.5px;
            color: #0F172A;
            line-height: 1.35;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.62);
            border-radius: 14px;
            padding: 8px 9px;
            border: 1px solid rgba(148, 163, 184, 0.24);
        }}

        .erk-live-author {{
            display: inline-block;
            margin-top: 5px;
            color: #475569;
            font-size: 12px;
            font-weight: 800;
        }}

        @media (max-width: 768px) {{
            .erk-floating-emoji {{
                font-size: 28px;
            }}
            .erk-live-mascot {{
                right: 10px;
                bottom: 10px;
                width: 215px;
                padding: 10px 12px;
            }}
            .erk-live-icon {{
                font-size: 30px;
            }}
            .erk-live-text {{
                font-size: 12px;
            }}
            .erk-live-quote {{
                font-size: 11.5px;
            }}
        }}
        </style>

        <div class="erk-live-layer">
            {emoji_html}
        </div>

        <div class="erk-live-mascot">
            <div class="erk-live-top">
                <div class="erk-live-icon">{mascot}</div>
                <div class="erk-live-title">Erkoshka Live</div>
            </div>
            <div class="erk-live-text"><b>{phrase}</b></div>
            <div class="erk-live-quote">💬 {quote_of_day}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =============================
# Main
# =============================

def main():
    if not check_password():
        return

    try:
        today_plan = get_day_plan(date.today())
        apply_theme_css(today_plan["day_type"])
        st.sidebar.success("Supabase подключен ✅")
        live_mode = st.sidebar.toggle("🎬 Живой режим", value=True)
        if live_mode:
            if st_autorefresh:
                st_autorefresh(interval=120000, key="quote_refresh")
            render_live_fun_mode(today_plan["day_type"])
    except Exception as error:
        st.error("Ошибка подключения к Supabase")
        st.exception(error)
        return

    st.title("📅 Erkoshka Planner")
    st.write("Облачный планировщик: смены, личные задачи, КИПиА журнал и бюджет.")

    logout_button()
    st.sidebar.divider()

    st.sidebar.header("Сегодня")
    st.sidebar.write(f"Дата: **{date.today()}**")
    st.sidebar.write(f"Тип дня: **{today_plan['day_type']}**")
    st.sidebar.write(f"Тема: {today_plan['theme']}")

    st.sidebar.divider()

    detected_mode = detect_device_mode()
    default_index = 0 if detected_mode == "mobile" else 1

    interface_mode = st.sidebar.radio(
        "Режим интерфейса",
        ["📱 Телефон", "💻 Компьютер"],
        index=default_index
    )

    st.sidebar.caption(
        "Автоопределение: телефон" if detected_mode == "mobile" else "Автоопределение: компьютер"
    )

    if interface_mode == "📱 Телефон":
        render_mobile_app()
    else:
        render_desktop_app()


if __name__ == "__main__":
    main()
