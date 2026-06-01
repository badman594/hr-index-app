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

# Бэкап-данные на случай сбоев API
FALLBACK_DATA = {
    "noExperience": {"Юрист": 45, "Тестировщик": 80, "Копирайтер": 60, "Информационная безопасность": 210, "Data Scientist": 110},
    "between1And3": {"Юрист": 320, "Тестировщик": 450, "Копирайтер": 280, "Информационная безопасность": 540, "Data Scientist": 410},
    "between3And6": {"Юрист": 680, "Тестировщик": 920, "Копирайтер": 510, "Информационная безопасность": 1150, "Data Scientist": 980}
}

# Базовые ИИ-риски и тренды для профессий
PROFEESION_TRENDS = {
    "Юрист (Правоведение)": {"ai_impact": 0.15, "market_growth": 0.02},
    "Тестировщик ПО": {"ai_impact": 0.12, "market_growth": 0.05},
    "Копирайтер / Маркетолог": {"ai_impact": 0.22, "market_growth": 0.03},
    "Специалист по Информ. Безопасности": {"ai_impact": 0.02, "market_growth": 0.18},
    "AI Engineer / Data Scientist": {"ai_impact": 0.01, "market_growth": 0.25},
    "Дефолт": {"ai_impact": 0.08, "market_growth": 0.05}
}

def get_hh_vacancies_count(keyword, area_id, experience, fallback_key):
    url = "https://hh.ru"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    params = {"text": keyword, "area": area_id, "experience": experience, "per_page": 1}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            found_vacancies = response.json().get("found", 0)
            if found_vacancies > 0:
                return found_vacancies
        return FALLBACK_DATA.get(experience, {}).get(fallback_key, 100)
    except Exception:
        return FALLBACK_DATA.get(experience, {}).get(fallback_key, 100)

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

# --- РАСЧЕТ ПРОГНОЗА ПО ГОТОВЫМ НАПРАВЛЕНИЯМ ---
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
        base_vacancies = get_hh_vacancies_count(prof["query"], selected_area_id, exp_api_value, prof["fb_key"])
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

# --- ИНТЕРАКТИВНЫЙ СИМУЛЯТОР С ПРЕДПРОВЕРКОЙ ВВОДА ---
st.header("🎛️ Симулятор влияния ИИ на специальность")
st.caption("Проверьте любую профессию на устойчивость к искусственному интеллекту.")

col1, col2, col3 = st.columns(3)
with col1:
    # Изначально строка пустая, чтобы спровоцировать осознанный ввод со стороны пользователя
    prof_keyword = st.text_input("Профессия для теста (например: Бухгалтер, Дизайнер):", value="")
with col2:
    ai_risk = st.slider("Уровень угрозы со стороны ИИ (% замещения задач в год):", 0, 50, 15)
with col3:
    v_students = st.slider("План набора студентов на 1 курс:", 10, 300, 60)

# Кнопка для старта — запрос к API пойдет только после её нажатия
btn_calc = st.button("🚀 Рассчитать прогноз по ИИ")

# Логика предпроверки строки ввода
if btn_calc:
    clean_keyword = prof_keyword.strip()
    
    # 1. Защита от слишком коротких и бессмысленных слов
    if len(clean_keyword) < 4:
        st.warning("⚠️ Пожалуйста, введите корректное и полное название профессии (минимум 4 символа).")
    else:
        with st.spinner(f'Выполняю реальный запрос на HH.ru для "{clean_keyword}"...'):
            
            # Изменяем логику: для симулятора передаем специальный маркер, чтобы не брать ложный бэкап
            url = "https://hh.ru"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            params = {"text": clean_keyword, "area": selected_area_id, "experience": exp_api_value, "per_page": 1}
            
            try:
                response = requests.get(url, headers=headers, params=params, timeout=5)
                sim_base_vacancies = response.json().get("found", 0) if response.status_code == 200 else 0
            except Exception:
                sim_base_vacancies = 0

            # 2. Если HH честно вернул 0 — значит такой профессии нет, останавливаем расчет
            if sim_base_vacancies == 0:
                st.error(f"❌ Профессия '{clean_keyword}' не найдена в базе вакансий HeadHunter для региона {selected_city}. Проверьте правильность написания.")
            else:
                # Расчет будущего, если вакансии реально найдены
                sim_future_vacancies = int(sim_base_vacancies * ((1.0 - (ai_risk/100)) ** horizon))
                if sim_future_vacancies < 1:
                    sim_future_vacancies = 1

                sim_resumes = int(sim_base_vacancies * 3.5)
                if horizon > 0:
                    sim_resumes = int(sim_resumes * (1.1 ** horizon))

                sim_index, sim_status, alert_type = get_status_logic(sim_future_vacancies, sim_resumes, v_students)

                st.subheader(f"Результат симуляции для '{clean_keyword}' к моменту выпуска:")
                st.markdown(f"* Вакансий сейчас на рынке: **{sim_base_vacancies}** ➔ Ожидается через {horizon} лет: **{sim_future_vacancies}**")
                st.markdown(f"* Прогнозный Индекс Нужности: **{sim_index}**")

                if alert_type == "success":
                    st.success(sim_status)
                elif alert_type == "warning":
                    st.warning(sim_status)
                else:
                    st.error(sim_status)

else:
    st.info("💡 Введите название интересующей профессии выше и нажмите кнопку «Рассчитать прогноз по ИИ», чтобы запустить симуляцию.")
