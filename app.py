import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ==========================================
# ЧАСТЬ 1: НАСТРОЙКИ СТРАНИЦЫ И СПРАВОЧНИКИ
# ==========================================

st.set_page_config(page_title="Предиктивный мониторинг рынка труда", layout="wide")
st.title("🔮 Динамический предиктивный мониторинг рынка труда")
st.subheader("Инструмент стратегического планирования квот на основе живых данных HeadHunter и ИИ-трендов")
st.markdown("---")

REGIONS = {
    "Москва":          {"id": "1",  "coef": 1.00},
    "Санкт-Петербург": {"id": "2",  "coef": 0.65},
    "Екатеринбург":    {"id": "3",  "coef": 0.40},
    "Новосибирск":     {"id": "4",  "coef": 0.35},
    "Казань":          {"id": "88", "coef": 0.30},
}

PROFESSION_TRENDS = {
    "Юрист":                      {"ai_impact": 0.15, "market_growth": 0.02},
    "Тестировщик":                {"ai_impact": 0.12, "market_growth": 0.05},
    "Копирайтер":                 {"ai_impact": 0.22, "market_growth": 0.03},
    "Маркетолог":                 {"ai_impact": 0.18, "market_growth": 0.04},
    "Информационная безопасность":{"ai_impact": 0.02, "market_growth": 0.18},
    "Data Scientist":             {"ai_impact": 0.01, "market_growth": 0.25},
    "Дефолт":                     {"ai_impact": 0.08, "market_growth": 0.05},
}

# ==========================================
# СПРАВОЧНИК ПЛОТНОСТИ РЫНКА ПО ПРОФЕССИЯМ
# (резюме / вакансия)
# ==========================================
PROFESSION_MARKET_DENSITY = {
    # IT и технологии
    "разработчик":              1.2,
    "программист":              1.2,
    "data scientist":           1.1,
    "аналитик данных":          1.3,
    "тестировщик":              1.5,
    "devops":                   1.1,
    "информационная безопасность": 1.0,
    "системный аналитик":       1.4,
    # Юриспруденция
    "юрист":                    8.5,
    "адвокат":                  7.0,
    "юрисконсульт":             7.5,
    # Административные профессии
    "администратор":            6.0,
    "офис-менеджер":            6.5,
    "секретарь":                7.0,
    # Экономика и финансы
    "бухгалтер":                5.5,
    "экономист":                5.0,
    "финансист":                4.5,
    # Маркетинг и контент
    "маркетолог":               4.0,
    "копирайтер":               4.5,
    "smm":                      5.0,
    # Медицина
    "врач":                     2.0,
    "медсестра":                1.8,
    "фармацевт":                3.0,
    # Строительство и производство
    "сварщик":                  2.0,
    "инженер":                  2.5,
    "строитель":                2.8,
}

DEFAULT_MARKET_DENSITY = 4.0  # коэффициент по умолчанию, если профессия не найдена


# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

def _get_market_density_coefficient(keyword: str) -> float:
    """
    Возвращает коэффициент резюме/вакансия из справочника PROFESSION_MARKET_DENSITY.
    Поиск ведётся по частичному вхождению (регистронезависимо).
    Если профессия не найдена — возвращает DEFAULT_MARKET_DENSITY.
    """
    kw_lower = keyword.strip().lower()
    for profession, coef in PROFESSION_MARKET_DENSITY.items():
        if profession in kw_lower or kw_lower in profession:
            return coef
    return DEFAULT_MARKET_DENSITY


def _get_hh_resume_count(keyword: str, area_id: str) -> int | None:
    """
    Option A: запрос к HH API для получения числа активных резюме по ключевому слову.
    Endpoint GET /resumes требует OAuth — при ошибке доступа (401/403)
    или любом сетевом сбое возвращает None (триггер для перехода к Option B).
    """
    url = "https://api.hh.ru/resumes"
    headers = {"User-Agent": "PredictiveJobMarketApp/1.0 (your_email@example.com)"}
    params = {
        "text": keyword.strip(),
        "area": area_id,
        "per_page": 1,
        "status": "active",
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            found = response.json().get("found")
            if found is not None and found > 0:
                return int(found)
        # 401 / 403 — нет авторизации; любой другой код — API недоступен
        return None
    except Exception:
        return None


def get_hh_vacancies(keyword, area_id, experience=None):
    """
    Возвращает количество вакансий с HH API по ключевому слову, региону и уровню опыта.
    """
    url = "https://api.hh.ru/vacancies"
    headers = {"User-Agent": "PredictiveJobMarketApp/1.0 (your_email@example.com)"}
    search_text = keyword.strip()
    params = {"text": search_text, "area": area_id, "per_page": 1}
    if experience:
        params["experience"] = experience
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get("found", 0)
    except Exception:
        pass
    return 0


def get_resume_estimate(keyword: str, area_id: str, base_vacancies: int) -> tuple[int, str]:
    """
    Определяет расчётное количество резюме по двухуровневой стратегии:

      Option A — живые данные из HH API (GET /resumes).
                 Если API вернул корректное число > 0 — используем его.

      Option B — если API недоступен / требует авторизации:
                 применяем коэффициент из PROFESSION_MARKET_DENSITY.
                 Если профессия не в справочнике — коэффициент = DEFAULT_MARKET_DENSITY (4.0).

    Возвращает: (количество_резюме, описание_источника_для_логов).
    """
    # --- Option A: HH API ---
    hh_count = _get_hh_resume_count(keyword, area_id)
    if hh_count is not None:
        return hh_count, "source=hh_api_resumes"

    # --- Option B: справочник плотности рынка ---
    coef = _get_market_density_coefficient(keyword)
    estimated = int(base_vacancies * coef)
    return estimated, f"source=market_density, coef={coef}"


def get_status_logic(vacancies: int, resumes: int, students: int) -> tuple[float, str, str]:
    if vacancies <= 0:
        return 999.0, "🔴 КРИТИЧЕСКИЙ ДЕФИЦИТ ВАКАНСИЙ! Рынок перегружен.", "danger"
    idx_val = round((resumes + students) / vacancies, 2)
    if idx_val < 2.0:
        return idx_val, "🟢 Высокая нужность. Рекомендуется УВЕЛИЧИТЬ набор.", "success"
    elif idx_val <= 5.0:
        return idx_val, "🟡 Баланс. Рынок стабилен. Корректировка не требуется.", "warning"
    else:
        return idx_val, "🔴 Риск безработицы! Срочно СОКРАТИТЬ квоты или внедрить ИИ-навыки.", "danger"
                
def build_forecast(
    base_vacancies: int,
    regional_coef: float,
    yearly_factor: float,
    horizon: int
) -> tuple[list[int], list[int], list[int]]:
    """Возвращает (vacancies_trend, resumes_trend, students_trend) по годам."""

base_resumes_raw, resume_source = get_resume_estimate(
    clean_keyword, selected_area_id, base_vacancies)
base_resumes = int(base_resumes_raw * regional_coef)
    base_students = int(base_vacancies * 1.5 * regional_coef)

    vacancies_trend, resumes_trend, students_trend = [], [], []
    for year in range(horizon + 1):
        vacancies_trend.append(max(1, int(base_vacancies * (yearly_factor ** year))))
        resumes_trend.append(int(base_resumes  * (1.10 ** year)))
        students_trend.append(int(base_students * (1.05 ** year)))

    return vacancies_trend, resumes_trend, students_trend


def results_to_excel(rows: list[dict]) -> bytes:
    output = BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False, sheet_name="Прогноз")
    return output.getvalue()


# ==========================================
# ЧАСТЬ 3: БОКОВАЯ ПАНЕЛЬ — ПАРАМЕТРЫ
# ==========================================

st.sidebar.header("🌐 Параметры моделирования")

selected_city    = st.sidebar.selectbox("Регион анализа:", list(REGIONS.keys()))
selected_area_id = REGIONS[selected_city]["id"]
regional_coef    = REGIONS[selected_city]["coef"]

selected_exp = st.sidebar.selectbox(
    "Уровень выпускника:",
    ["Без опыта (Junior)", "От 1 до 3 лет (Middle)"]
)
exp_api_value = "noExperience" if "Junior" in selected_exp else "between1And3"

horizon = st.sidebar.slider("Горизонт прогнозирования (лет):", min_value=1, max_value=10, value=5)

st.sidebar.markdown("---")
st.sidebar.info(INDEX_HELP)


# ==========================================
# ЧАСТЬ 4: ГЛАВНЫЙ ИНТЕРФЕЙС
# ==========================================

st.header("🔍 Интеллектуальный анализ профессий")
st.caption(
    "Введите одну или несколько профессий через запятую, "
    "чтобы запустить сквозной поиск по реальному рынку труда."
)

raw_input = st.text_input(
    "Профессии для анализа (например: Бухгалтер, Сварщик, Системный аналитик):",
    value=""
)
btn_calc = st.button("🚀 Запустить предиктивный расчёт")

if btn_calc:
    keywords = [k.strip() for k in raw_input.split(",") if len(k.strip()) >= 3]

    if not keywords:
        st.warning("⚠️ Пожалуйста, введите хотя бы одну профессию (минимум 3 символа).")
    else:
        summary_rows = []

        for keyword in keywords:
            st.markdown(f"### 📌 {keyword} — {selected_city}")

            with st.spinner(f'Запрос к hh.ru: «{keyword}»...'):
                base_vacancies, source = get_hh_vacancies(keyword, selected_area_id, exp_api_value)

            # Информируем о качестве данных
            if source == "simulated":
                st.warning(
                    f"📋 Живые данные для «{keyword}» недоступны. "
                    "Включена предиктивная симуляция на базе среднерыночной ёмкости."
                )
            elif source == "fallback_exp":
                st.info(
                    f"💡 Вакансий для уровня «{selected_exp}» не найдено. "
                    "Расчёт ведётся по общей ёмкости рынка."
                )

            # Тренды и прогноз
            trends       = PROFESSION_TRENDS.get(keyword, PROFESSION_TRENDS["Дефолт"])
            yearly_factor = 1.0 - trends["ai_impact"] + trends["market_growth"]

            vacancies_trend, resumes_trend, students_trend = build_forecast(
                base_vacancies, regional_coef, yearly_factor, horizon
            )
            years_list = list(range(horizon + 1))

            predicted_vacancies = vacancies_trend[-1]
            final_resumes        = resumes_trend[-1]
            final_students       = students_trend[-1]

            idx_val, status, alert_type = get_status_logic(
                predicted_vacancies, final_resumes, final_students
            )
# Итоговый вердикт
            if alert_type == "success":
                st.success(f"Итог через {horizon} лет: {status}")
            elif alert_type == "warning":
                st.warning(f"Итог через {horizon} лет: {status}")
            else:
                st.error(f"Итог через {horizon} лет: {status}")

            # Метрики
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Вакансии сейчас",          f"{base_vacancies:,}")
            col2.metric(f"Вакансии через {horizon}л.", f"{predicted_vacancies:,}",
                        delta=f"{predicted_vacancies - base_vacancies:+,}")
            col3.metric("Поток соискателей",         f"{final_resumes + final_students:,}")
            col4.metric("Индекс нужности",
                        "∞" if idx_val == 999.0 else str(idx_val),
                        help=INDEX_HELP)

            # Графики
            tab1, tab2 = st.tabs(["📈 Баланс рынка", "📉 Динамика вакансий"])

            with tab1:
                st.caption("Спрос (вакансии) vs предложение (резюме + студенты):")
                df_balance = pd.DataFrame({
                    "Год":                    years_list,
                    "Доступные вакансии":     vacancies_trend,
                    "Общий поток соискателей":[r + s for r, s in zip(resumes_trend, students_trend)],
                }).set_index("Год")
                st.line_chart(df_balance)

            with tab2:
                st.caption(f"Чистый тренд рабочих мест для «{keyword}»:")
                df_vac = pd.DataFrame({
                    "Год":     years_list,
                    "Вакансии": vacancies_trend,
                }).set_index("Год")
                st.line_chart(df_vac)

            st.markdown("---")

            # Накапливаем для сводной таблицы и экспорта
            summary_rows.append({
                "Профессия":                   keyword,
                "Регион":                      selected_city,
                "Вакансии (сейчас)":           base_vacancies,
                f"Вакансии (через {horizon}л.)": predicted_vacancies,
                "Поток соискателей":           final_resumes + final_students,
                "Индекс нужности":             "∞" if idx_val == 999.0 else idx_val,
                "Источник данных":             {"live": "hh.ru (live)", "fallback_exp": "hh.ru (без фильтра)", "simulated": "Симуляция"}[source],
                "Рекомендация":                status,
            })

        # Сводная таблица (если профессий > 1)
        if len(summary_rows) > 1:
            st.subheader("📊 Сводное сравнение профессий")
            st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        # Экспорт
        st.subheader("💾 Экспорт результатов")
        col_csv, col_xlsx = st.columns(2)
        with col_csv:
            csv_data = pd.DataFrame(summary_rows).to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="⬇️ Скачать CSV",
                data=csv_data,
                file_name=f"hr_forecast_{selected_city}.csv",
                mime="text/csv",
            )
        with col_xlsx:
            xlsx_data = results_to_excel(summary_rows)
            st.download_button(
                label="⬇️ Скачать Excel",
                data=xlsx_data,
                file_name=f"hr_forecast_{selected_city}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

else:
    st.info("💡 Введите профессии через запятую и нажмите кнопку, чтобы построить прогноз.")
