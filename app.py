import streamlit as st
import pandas as pd
import requests

# Настройка страницы
st.set_page_config(page_title="Предиктивный мониторинг рынка труда", layout="wide")

st.title("🔮 Система предиктивного прогнозирования индекса нужности профессий")
st.subheader("Инструмент стратегического планирования квот с учетом ИИ-трансформации и горизонтов выпуска")
st.markdown("---")

# Справочники ID регионов по стандарту HeadHunter
REGIONS = {
    "Москва": "1",
    "Санкт-Петербург": "2",
    "Новосибирск": "4",
    "Казань": "88",
    "Екатеринбург": "3"
}

# Бэкап-данные на случай сбоев сети
FALLBACK_DATA = {
    "noExperience": {"Юрист": 45, "Тестировщик": 80, "Копирайтер": 60, "Информационная безопасность": 210, "Data Scientist": 110},
    "between1And3": {"Юрист": 320, "Тестировщик": 450, "Копирайтер": 280, "Информационная безопасность": 540, "Data Scientist": 410}
}

PROFEESION_TRENDS = {
    "Юрист (Правоведение)": {"ai_impact": 0.15, "market_growth": 0.02},
    "Тестировщик ПО": {"ai_impact": 0.12, "market_growth": 0.05},
    "Копирайтер / Маркетолог": {"ai_impact": 0.22, "market_growth": 0.03},
    "Специалист по Информ. Безопасности": {"ai_impact": 0.02, "market_growth": 0.18},
    "AI Engineer / Data Scientist": {"ai_impact": 0.01, "market_growth": 0.25},
    "Дефолт": {"ai_impact": 0.08, "market_growth": 0.05}
}

# Умная функция запроса к API, которая сама убирает фильтры, если вакансий нет
def get_hh_vacancies_smart(keyword, area_id, experience=None):
    url = "https://hh.ru"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Попытка 1: Запрос с учетом выбранного опыта
    params = {"text": keyword, "area": area_id, "per_page": 1}
    if experience:
        params["experience"] = experience
        
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            found = response.json().get("found", 0)
            if found > 0:
                return found
                
        # Попытка 2: Если с опытом выдало 0 (как со сварщиком), пробуем искать без фильтра опыта
        if experience:
            params.pop("experience", None)
            response = requests.get(url, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                return response.json().get("found", 0)
    except Exception:
        pass
    return 0

def get_status_logic(vacancies, resumes, students):
    if vacancies <= 0:
        return float('inf'), "🔴 КРИТИЧЕСКИЙ ДЕФИЦИТ ВАКАНСИЙ! Рынок перегружен.", "danger"
    
    idx_val = round((resumes + students) / vacancies, 2)
    if idx_val < 2.0:
        return idx_val, "🟢 Высокая нужность. Рекомендуется УВЕЛИЧИТЬ набор.", "success"
    elif 2.0 <= idx_val <= 5.0:
        return idx_val, "🟡 Баланс. Рынок стабилен. Корректировка не требуется.", "warning"
    else:
        return idx_val, "🔴 Риск безработицы! Срочно СОКРАТИТЬ квоты или внедрить ИИ-навыки.", "error"

# --- НАСТРОЙКИ В БОКОВОЙ ПАНЕЛИ ---
st.sidebar.header("🌐 Параметры моделирования")
selected_city = st.sidebar.selectbox("Регион анализа:", list(REGIONS.keys()))
selected_area_id = REGIONS[selected_city]

selected_exp = st.sidebar.selectbox("Текущий уровень выпускника:", ["Без опыта (Junior)", "От 1 до 3 лет (Middle)"])
exp_api_value = "noExperience" if selected_exp == "Без опыта (Junior)" else "between1And3"

st.sidebar.markdown("---")
st.sidebar.header("⏳ Временной горизонт")
horizon = st.sidebar.slider("Горизонт планирования (лет до выпуска):", min_value=0, max_value=4, value=0)

# --- ТАБЛИЦА ГОТОВЫХ НАПРАВЛЕНИЙ ---
st.header(f"📊 Прогноз востребованности через {horizon} л. ({selected_city})")

professions_config = [
    {"name": "Юрист (Правоведение)", "query": "Юрист", "fb_key": "Юрист", "resumes_est": 850, "students": 300},
    {"name": "Тестировщик ПО", "query": "Тестировщик", "fb_key": "Тестировщик", "resumes_est": 1200, "students": 150},
    {"name": "Копирайтер / Маркетолог", "query": "Копирайтер OR Маркетолог", "fb_key": "Копирайтер", "resumes_est": 900, "students": 250},
    {"name": "Специалист по Информ. Безопасности", "query": "Информационная безопасность", "fb_key": "Информационная безопасность", "resumes_est": 150, "students": 120},
    {"name": "AI Engineer / Data Scientist", "query": "Data Scientist OR Machine Learning", "fb_key": "Data Scientist", "resumes_est": 90, "students": 60}
]

dynamic_results = []

with st.spinner('Расчет прогностических моделей...'):
    for prof in professions_config:
        base_vacancies = get_hh_vacancies_smart(prof["query"], selected_area_id, exp_api_value)
        if base_vacancies == 0:
            base_vacancies = FALLBACK_DATA.get(exp_api_value, {}).get(prof["fb_key"], 100)
            
        trends = PROFEESION_TRENDS.get(prof["name"], PROFEESION_TRENDS["Дефолт"])
        yearly_factor = 1.0 - trends["ai_impact"] + trends["market_growth"]
        predicted_vacancies = int(base_vacancies * (yearly_factor ** horizon))
        if predicted_vacancies < 1:
            predicted_vacancies = 1
            
        regional_coef = 0.4 if selected_city != "Москва" else 1.0
        current_resumes = int(prof["resumes_est"] * regional_coef)
        current_students = int(prof["students"] * regional_coef)
        
        if horizon > 0:
            current_resumes = int(current_resumes * (1.1 ** horizon))
        
        val, status, _ = get_status_logic(predicted_vacancies, current_resumes, current_students)
        
        dynamic_results.append({
            "Направление обучения": prof["name"],
            "Текущие вакансии": base_vacancies,
            f"Вакансии через {horizon} л.": predicted_vacancies,
            "Прогнозный Индекс": val,
            "Стратегическое решение для Вуза": status
        })

df_dynamic = pd.DataFrame(dynamic_results)
st.table(df_dynamic)

st.markdown("---")

# --- СИМУЛЯТОР С ГАРАНТИРОВАННЫМ ПОИСКОМ ---
st.header("🎛️ Симулятор влияния ИИ на специальность")
st.caption("Проверьте любую профессию на устойчивость к искусственному интеллекту.")

col1, col2, col3 = st.columns(3)
with col1:
    prof_keyword = st.text_input("Профессия для теста (например: Бухгалтер, Дизайнер):", value="")
with col2:
    ai_risk = st.slider("Уровень угрозы со стороны ИИ (% замещения задач в год):", 0, 50, 15)
with col3:
    v_students = st.slider("План набора студентов на 1 курс:", 10, 300, 60)

btn_calc = st.button("🚀 Рассчитать прогноз по ИИ")

if btn_calc:
    clean_keyword = prof_keyword.strip()
    
    if len(clean_keyword) < 3:
        st.warning("⚠️ Пожалуйста, введите название профессии (минимум 3 символа).")
    else:
        with st.spinner(f'Выполняю сквозной поиск для "{clean_keyword}"...'):
            # Запрашиваем общий объем рынка по этой профессии вообще БЕЗ жестких фильтров опыта
            sim_base_vacancies = get_hh_vacancies_smart(clean_keyword, selected_area_id, experience=None)

            if sim_base_vacancies == 0:
                st.error(f"❌ Профессия '{clean_keyword}' не найдена на рынке труда региона {selected_city}. Проверьте написание.")
            else:
                # Берем условную долю вакансий, доступную новичкам
                junior_vacancies = int(sim_base_vacancies * 0.20) if sim_base_vacancies > 10 else sim_base_vacancies
                if junior_vacancies < 1:
                    junior_vacancies = 1

                # Расчет будущего
                sim_future_vacancies = int(junior_vacancies * ((1.0 - (ai_risk/100)) ** horizon))
                if sim_future_vacancies < 1:
                    sim_future_vacancies = 1

                sim_resumes = int(junior_vacancies * 4)
                if horizon > 0:
                    sim_resumes = int(sim_resumes * (1.1 ** horizon))

                sim_index, sim_status, alert_type = get_status_logic(sim_future_vacancies, sim_resumes, v_students)

                st.subheader(f"Результат симуляции для '{clean_keyword}':")
                st.markdown(f"* Всего активных вакансий в регионе: **{sim_base_vacancies}**")
                st.markdown(f"* Прогнозный Индекс Нужности: **{sim_index}**")

                if alert_type == "success":
                    st.success(sim_status)
                elif alert_type == "warning":
                    st.warning(sim_status)
                else:
                    st.error(sim_status)
else:
    st.info("💡 Введите название профессии и нажмите кнопку для расчета прогноза.")
