import streamlit as st
import pandas as pd
import requests

# ==========================================
# ЧАСТЬ 1: НАСТРОЙКИ СТРАНИЦЫ И СПРАВОЧНИКИ
# ==========================================
st.set_page_config(page_title="Предиктивный мониторинг рынка труда", layout="wide")

st.title("🔮 Система предиктивного прогнозирования индекса нужности профессий")
st.subheader("Инструмент стратегического планирования квот с учетом ИИ-трансформации и горизонтов выпуска")
st.markdown("---")

REGIONS = {
    "Москва": "1",
    "Санкт-Петербург": "2",
    "Новосибирск": "4",
    "Казань": "88",
    "Екатеринбург": "3"
}

FALLBACK_DATA = {
    "noExperience": {
        "Юрист (Правоведение)": 45, 
        "Тестировщик ПО": 80, 
        "Копирайтер / Маркетолог": 60, 
        "Специалист по Информ. Безопасности": 210, 
        "AI Engineer / Data Scientist": 110
    },
    "between1And3": {
        "Юрист (Правоведение)": 320, 
        "Тестировщик ПО": 450, 
        "Копирайтер / Маркетолог": 280, 
        "Специалист по Информ. Безопасности": 540, 
        "AI Engineer / Data Scientist": 410
    }
}

PROFESSION_TRENDS = {
    "Юрист (Правоведение)": {"ai_impact": 0.15, "market_growth": 0.02},
    "Тестировщик ПО": {"ai_impact": 0.12, "market_growth": 0.05},
    "Копирайтер / Маркетолог": {"ai_impact": 0.22, "market_growth": 0.03},
    "Специалист по Информ. Безопасности": {"ai_impact": 0.02, "market_growth": 0.18},
    "AI Engineer / Data Scientist": {"ai_impact": 0.01, "market_growth": 0.25},
    "Дефолт": {"ai_impact": 0.08, "market_growth": 0.05}
}

# ==========================================
# ЧАСТЬ 2: ФУНКЦИИ ЛОГИКИ И API
# ==========================================

def get_hh_vacancies_smart(keyword, area_id, experience=None):
    url = "https://hh.ru"
    headers = {
        "User-Agent": "PredictiveJobMarketApp/1.0 (your_email@example.com)"
    }
    
    params = {"text": keyword, "area": area_id, "per_page": 1}
    if experience:
        params["experience"] = experience
        
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            found = response.json().get("found", 0)
            if found > 0:
                return found
                
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
        return 999.0, "🔴 КРИТИЧЕСКИЙ ДЕФИЦИТ ВАКАНСИЙ! Рынок перегружен.", "danger"
    
    idx_val = round((resumes + students) / vacancies, 2)
    if idx_val < 2.0:
        return idx_val, "🟢 Высокая нужность. Рекомендуется УВЕЛИЧИТЬ набор.", "success"
    elif 2.0 <= idx_val <= 5.0:
        return idx_val, "🟡 Баланс. Рынок стабилен. Корректировка не требуется.", "warning"
    else:
        return idx_val, "🔴 Риск безработицы! Срочно СОКРАТИТЬ квоты или внедрить ИИ-навыки.", "danger"

# --- НАСТРОЙКИ В БОКОВОЙ ПАНЕЛИ ---
st.sidebar.header("🌐 Параметры моделирования")
selected_city = st.sidebar.selectbox("Регион анализа:", list(REGIONS.keys()))
selected_area_id = REGIONS[selected_city]

selected_exp = st.sidebar.selectbox("Текущий уровень выпускника:", ["Без опыта (Junior)", "От 1 до 3 лет (Middle)"])
exp_api_value = "noExperience" if selected_exp == "Без опыта (Junior)" else "between1And3"

horizon = st.sidebar.slider("Горизонт прогнозирования (лет):", min_value=1, max_value=10, value=5)

# ==========================================
# ЧАСТЬ 3 И 4: РАСЧЕТ, ИНТЕРФЕЙС И ГРАФИК ТАБЛИЦЫ
# ==========================================
st.header(f"📊 Прогноз востребованности через {horizon} л. ({selected_city})")

professions_config = [
    {"name": "Юрист (Правоведение)", "query": "Юрист", "resumes_est": 850, "students": 300},
    {"name": "Тестировщик ПО", "query": "Тестировщик", "resumes_est": 1200, "students": 150},
    {"name": "Копирайтер / Маркетолог", "query": "Копирайтер OR Маркетолог", "resumes_est": 900, "students": 250},
    {"name": "Специалист по Информ. Безопасности", "query": "Информационная безопасность", "resumes_est": 150, "students": 120},
    {"name": "AI Engineer / Data Scientist", "query": "Data Scientist OR Machine Learning", "resumes_est": 90, "students": 60}
]

dynamic_results = []
# Словарь для хранения погодных трендов вакансий (для графика)
chart_data_dict = {"Год": list(range(0, horizon + 1))}

with st.spinner('Расчет прогностических моделей...'):
    for prof in professions_config:
        base_vacancies = get_hh_vacancies_smart(prof["query"], selected_area_id, exp_api_value)
        if base_vacancies == 0:
            base_vacancies = FALLBACK_DATA.get(exp_api_value, {}).get(prof["name"], 100)
            
        trends = PROFESSION_TRENDS.get(prof["name"], PROFESSION_TRENDS["Дефолт"])
        yearly_factor = 1.0 - trends["ai_impact"] + trends["market_growth"]
        
        # Заполняем данные для графика по годам
        prof_years_trend = []
        for year in range(0, horizon + 1):
            v_at_year = int(base_vacancies * (yearly_factor ** year))
            prof_years_trend.append(max(1, v_at_year))
        chart_data_dict[prof["name"]] = prof_years_trend

        # Итоговые значения для таблицы (на конец горизонта)
        predicted_vacancies = prof_years_trend[-1]
            
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

# Выводим таблицу и график в две вкладки для удобства
tab1, tab2 = st.tabs(["📋 Сводная таблица", "📈 Динамика вакансий по годам"])
with tab1:
    st.dataframe(df_dynamic, use_container_width=True)
with tab2:
    st.subheader("Прогноз изменения количества вакансий под влиянием ИИ и рынка:")
    df_chart = pd.DataFrame(chart_data_dict).set_index("Год")
    st.line_chart(df_chart)

st.markdown("---")

# ==========================================
# ЧАСТЬ 5 И 6: СИМУЛЯТОР ВЛИЯНИЯ ИИ С ГРАФИКОМ
# ==========================================
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
            sim_base_vacancies = get_hh_vacancies_smart(clean_keyword, selected_area_id, experience=None)
            
            if sim_base_vacancies == 0:
                st.error(f"❌ Профессия '{clean_keyword}' не найдена на реальном рынке труда региона {selected_city}. Проверьте написание.")
            else:
                junior_vacancies = int(sim_base_vacancies * 0.20) if sim_base_vacancies > 10 else sim_base_vacancies
                if junior_vacancies < 1:
                    junior_vacancies = 1

                # Сбор данных по годам для графика симулятора
                sim_years = list(range(0, horizon + 1))
                vacancies_trend = []
                competition_trend = [] # Сумма Резюме + Студенты
                
                for year in range(0, horizon + 1):
                    # Вакансии падают под ИИ
                    v_year = int(junior_vacancies * ((1.0 - (ai_risk/100)) ** year))
                    vacancies_trend.append(max(1, v_year))
                    
                    # Соискатели растут (базовые резюме * 1.1^год + новые студенты)
                    res_base = int(junior_vacancies * 4)
                    res_year = int(res_base * (1.1 ** year)) if year > 0 else res_base
                    competition_trend.append(res_year + v_students)

                # Итоговые значения для вывода под графиком
                sim_future_vacancies = vacancies_trend[-1]
                sim_resumes = int(junior_vacancies * 4)
                if horizon > 0:
                    sim_resumes = int(sim_resumes * (1.1 ** horizon))

                sim_index, sim_status, alert_type = get_status_logic(sim_future_vacancies, sim_resumes, v_students)

                # Выводим графики симуляции
                st.subheader(f"Визуализация баланса рынка для '{clean_keyword}':")
                
                df_sim_chart = pd.DataFrame({
                    "Год": sim_years,
                    "Доступные вакансии (ИИ-эффект)": vacancies_trend,
                    "Общий поток соискателей (Резюме + Вуз)": competition_trend
                }).set_index("Год")
                
                st.line_chart(df_sim_chart)

                # Вывод текстовых результатов под графиком
                st.subheader("Результаты симуляции:")
                col_res1, col_res2 = st.columns(2)
with col_res1:st.markdown(f"* Всего активных вакансий в регионе сейчас: {sim_base_vacancies}")with col_res2:display_index = "⚠️ Бесконечен (0 вакансий)" if sim_index == 999.0 else sim_indexst.markdown(f"* Прогнозный Индекс Нужности (через {horizon} л.): {display_index}")if alert_type == "success":st.success(sim_status)elif alert_type == "warning":st.warning(sim_status)else:st.error(sim_status)else:st.info("💡 Введите название профессии и нажмите кнопку для расчета прогноза.")
