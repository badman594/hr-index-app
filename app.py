import streamlit as st
import pandas as pd
import requests

# Настройка страницы
st.set_page_config(page_title="Мониторинг рынка труда", layout="wide")

st.title("📊 Система динамического прогнозирования индекса нужности профессий")
st.subheader("Инструмент предиктивной аналитики для Вузов (Интеграция с Живым API HH.ru)")
st.markdown("---")

# Справочники ID регионов по стандарту HeadHunter
REGIONS = {
    "Москва": "1",
    "Санкт-Петербург": "2",
    "Новосибирск": "4",
    "Казань": "88",
    "Екатеринбург": "3"
}

# Функция запроса к реальному API HeadHunter
def get_hh_vacancies_count(keyword, area_id, experience):
    url = "https://hh.ru"
    
    # Строгое требование документации HH: указать User-Agent вашего приложения
    headers = {
        "User-Agent": "PredictiveEduApp/1.0 (study-index-project@example.com)"
    }
    
    # Параметры запроса
    params = {
        "text": keyword,
        "area": area_id,
        "experience": experience,
        "per_page": 1 # Нам нужно только поле 'found', всю базу качать не нужно
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("found", 0) # Поле 'found' возвращает точное число вакансий на HH
        else:
            return 0
    except Exception:
        return 0

# Функция расчета статуса индекса
def get_status_logic(vacancies, resumes, students):
    if vacancies == 0:
        return float('inf'), "🔴 КРИТИЧЕСКИЙ ДЕФИЦИТ ВАКАНСИЙ! Набор закрыт.", "danger"
    
    idx_val = round((resumes + students) / vacancies, 2)
    if idx_val < 2.0:
        return idx_val, "🟢 Дефицит кадров. Рекомендуется УВЕЛИЧИТЬ набор.", "success"
    elif 2.0 <= idx_val <= 5.0:
        return idx_val, "🟡 Баланс. Рынок стабилен. Корректировка не требуется.", "warning"
    else:
        return idx_val, "🔴 Перепроизводство! Рекомендуется СОКРАТИТЬ квоты.", "error"

# --- ИНТЕРФЕЙС НАСТРОЕК ---
st.sidebar.header("🌐 Глобальные фильтры рынка")

selected_city = st.sidebar.selectbox("Выберите регион анализа:", list(REGIONS.keys()))
selected_area_id = REGIONS[selected_city]

selected_exp = st.sidebar.selectbox("Уровень опыта (Грейд):", {
    "Без опыта (Junior)": "noExperience",
    "От 1 до 3 лет (Middle)": "between1And3",
    "От 3 до 6 лет (Senior)": "between3And6"
}.keys())

exp_api_value = {
    "Без опыта (Junior)": "noExperience",
    "От 1 до 3 лет (Middle)": "between1And3",
    "От 3 до 6 лет (Senior)": "between3And6"
}[selected_exp]

st.sidebar.markdown("---")
st.sidebar.markdown("**Формула:** `(Резюме + Студенты) / Живые Вакансии`")

# --- ГЕНЕРАЦИЯ ДИНАМИЧЕСКИХ ДАННЫХ ---
st.header(f"📈 Аналитика для региона: {selected_city} ({selected_exp})")

# Базовый набор профессий и поисковых запросов для API
professions_config = [
    {"name": "Юрист (Правоведение)", "query": "Юрист", "resumes_est": 850, "students": 300},
    {"name": "Тестировщик ПО", "query": "QA Automation OR Тестировщик", "resumes_est": 1200, "students": 150},
    {"name": "Копирайтер / Маркетолог", "query": "Копирайтер OR Маркетолог", "resumes_est": 900, "students": 250},
    {"name": "Специалист по Информ. Безопасности", "query": "Информационная безопасность", "resumes_est": 150, "students": 120},
    {"name": "AI Engineer / Data Scientist", "query": "Data Scientist OR Machine Learning", "resumes_est": 90, "students": 60}
]

dynamic_results = []

# Запускаем живой сбор через API для каждой строчки
with st.spinner('Связываюсь с серверами HeadHunter для обновления данных...'):
    for prof in professions_config:
        # Тянем вакансии из API HH
        live_vacancies = get_hh_vacancies_count(prof["query"], selected_area_id, exp_api_value)
        
        # Считаем индекс
        val, status, _ = get_status_logic(live_vacancies, prof["resumes_est"], prof["students"])
        
        dynamic_results.append({
            "Направление обучения": prof["name"],
            "Живые вакансии на HH": live_vacancies,
            "Индекс Нужности": val,
            "Рекомендация системе образования": status
        })

df_dynamic = pd.DataFrame(dynamic_results)
st.table(df_dynamic)

st.markdown("---")

# --- СИМУЛЯТОР ---
st.header("🎛️ Персональный симулятор квот факультета")
st.caption("Используйте этот блок на созвоне с деканом, чтобы рассчитать параметры под его конкретную кафедру.")

col1, col2 = st.columns(2)
with col1:
    prof_keyword = st.text_input("Введите ключевое слово для поиска вакансий (например: Бухгалтер, Дизайнер):", "Дизайнер")
with col2:
    v_students = st.slider("Сколько студентов планирует набрать/выпустить вуз?", 10, 500, 80)

# Живой расчет для симулятора
sim_vacancies = get_hh_vacancies_count(prof_keyword, selected_area_id, exp_api_value)
# Эмуляция соискателей на базе средних трендов (пропорционально вакансиям)
sim_resumes = sim_vacancies * 4 if sim_vacancies > 0 else 100 

sim_index, sim_status, alert_type = get_status_logic(sim_vacancies, sim_resumes, v_students)

st.subheader(f"Результаты экспресс-анализа рынка для запроса '{prof_keyword}':")
st.markdown(f"* Найдено активных вакансий в регионе {selected_city}: **{sim_vacancies}**")
st.markdown(f"* Текущий расчетный индекс нужности: **{sim_index}**")

if alert_type == "success":
    st.success(sim_status)
elif alert_type == "warning":
    st.warning(sim_status)
else:
    st.error(sim_status)
