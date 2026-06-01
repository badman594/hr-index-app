import streamlit as st
import pandas as pd
import requests

# ==========================================
# ЧАСТЬ 1: НАСТРОЙКИ СТРАНИЦЫ И СПРАВОЧНИКИ
# ==========================================
st.set_page_config(page_title="Предиктивный мониторинг рынка труда", layout="wide")

st.title("🔮 Динамический предиктивный мониторинг рынка труда")
st.subheader("Инструмент стратегического планирования квот на основе живых данных HeadHunter и ИИ-трендов")
st.markdown("---")

REGIONS = {
    "Москва": "1",
    "Санкт-Петербург": "2",
    "Новосибирск": "4",
    "Казань": "88",
    "Екатеринбург": "3"
}

# Оставляем тренды для известных системе базовых групп, остальные получат "Дефолт"
PROFESSION_TRENDS = {
    "Юрист": {"ai_impact": 0.15, "market_growth": 0.02},
    "Тестировщик": {"ai_impact": 0.12, "market_growth": 0.05},
    "Копирайтер": {"ai_impact": 0.22, "market_growth": 0.03},
    "Маркетолог": {"ai_impact": 0.18, "market_growth": 0.04},
    "Информационная безопасность": {"ai_impact": 0.02, "market_growth": 0.18},
    "Data Scientist": {"ai_impact": 0.01, "market_growth": 0.25},
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
# ЧАСТЬ 3: ИНТЕРФЕЙС ВВОДА ПРОФЕССИИ
# ==========================================
st.header("🔍 Интеллектуальный анализ профессии")
st.caption("Введите название интересующей специальности, чтобы запустить сквозной поиск по реальному рынку труда.")

prof_keyword = st.text_input("Профессия для анализа (например: Бухгалтер, Дизайнер, Системный аналитик):", value="")
btn_calc = st.button("🚀 Запустить предиктивный расчет")

if btn_calc:
    clean_keyword = prof_keyword.strip()
    
    if len(clean_keyword) < 3:
        st.warning("⚠️ Пожалуйста, введите корректное название профессии (минимум 3 символа).")
    else:
        with st.spinner(f'Сбор живых данных из hh.ru и расчет трендов для "{clean_keyword}"...'):
            
            # 1. Получаем реальные данные с API HeadHunter
            base_vacancies = get_hh_vacancies_smart(clean_keyword, selected_area_id, exp_api_value)
            
            if base_vacancies == 0:
                st.error(f"❌ Профессия '{clean_keyword}' не найдена на рынке труда в регионе {selected_city}. Проверьте правильность написания.")
            else:
                # 2. Определяем ИИ-тренды (ищем точное совпадение или даем Дефолт)
                trends = PROFESSION_TRENDS.get(clean_keyword, PROFESSION_TRENDS["Дефолт"])
                yearly_factor = 1.0 - trends["ai_impact"] + trends["market_growth"]
                
                # 3. Генерируем массив данных по годам для графика
                years_list = list(range(0, horizon + 1))
                vacancies_trend = []
                competition_trend = []
                
                # Эмпирический расчет базового объема резюме и студентов на основе текущего рынка
                regional_coef = 0.4 if selected_city != "Москва" else 1.0
                base_resumes = int(base_vacancies * 4 * regional_coef)
                base_students = int(base_vacancies * 1.5 * regional_coef)
                
                for year in range(0, horizon + 1):
                    # Моделируем вакансии
                    v_year = int(base_vacancies * (yearly_factor ** year))
                    vacancies_trend.append(max(1, v_year))
                    
                    # Моделируем соискателей (рост резюме + студенты)
                    res_year = int(base_resumes * (1.1 ** year)) if year > 0 else base_resumes
                    stud_year = int(base_students * (1.05 ** year)) if year > 0 else base_students
                    competition_trend.append(res_year + stud_year)

                # Итоговые параметры на конец горизонта планирования
                predicted_vacancies = vacancies_trend[-1]
                final_resumes = int(base_resumes * (1.1 ** horizon)) if horizon > 0 else base_resumes
                final_students = int(base_students * (1.05 ** horizon)) if horizon > 0 else base_students
                
                val, status, alert_type = get_status_logic(predicted_vacancies, final_resumes, final_students)
                
                # 4. Формируем динамическую таблицу (Dataframe)
                dynamic_results = [{
                    "Параметр": f"Анализ для '{clean_keyword}' ({selected_city})",
                    "Текущие вакансии (HH)": base_vacancies,
                    f"Прогноз вакансий через {horizon} л.": predicted_vacancies,
                    "Индекс Нужности": "⚠️ Бесконечен" if val == 999.0 else val,
                    "Рекомендация для Вуза": status
                }]
                df_dynamic = pd.DataFrame(dynamic_results)
                
                # ==========================================
                # ЧАСТЬ 4: ВЫВОД РЕЗУЛЬТАТОВ НА ЭКРАН
                # ==========================================
                st.markdown("---")
                st.subheader(f"📊 Результаты стратегического прогноза через {horizon} лет:")
                st.dataframe(df_dynamic, use_container_width=True)
                
                # Вывод графиков во вкладках
                tab1, tab2 = st.tabs(["📈 График баланса рынка", "📉 Только динамика вакансий"])
                
                with tab1:
                    st.caption("Сравнение падения спроса (вакансии под ИИ) и роста предложения (резюме + студенты):")
                    df_balance_chart = pd.DataFrame({
                        "Год": years_list,
                        "Доступные вакансии": vacancies_trend,
                        "Общий поток соискателей": competition_trend
                    }).set_index("Год")
                    st.line_chart(df_balance_chart)
                    
                with tab2:
                    st.caption(f"Чистый тренд изменения рабочих мест для '{clean_keyword}' по годам:")
                    df_vac_chart = pd.DataFrame({
                        "Год": years_list,
                        "Вакансии": vacancies_trend
                    }).set_index("Год")
                    st.line_chart(df_vac_chart)
                
                # Дублируем главное решение крупным цветным блоком внизу
                if alert_type == "success":
                    st.success(f"**Итоговый вердикт:** {status}")
                elif alert_type == "warning":
                    st.warning(f"**Итоговый вердикт:** {status}")
                else:
                    st.error(f"**Итоговый вердикт:** {status}")
else:
    st.info("💡 Введите название любой профессии в поле выше и нажмите кнопку, чтобы построить живой прогноз рынка труда.")
