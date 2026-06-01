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

INDEX_HELP = (
    "Индекс нужности = (резюме + студенты) / вакансии. "
    "Значение < 2 — острая нехватка кадров, рекомендуется увеличить набор. "
    "2–5 — рынок сбалансирован. "
    "> 5 — избыток соискателей, высок риск безработицы среди выпускников."
)

# ==========================================
# ЧАСТЬ 2: ФУНКЦИИ ЛОГИКИ И API
# ==========================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_hh_vacancies(keyword: str, area_id: str, experience: str | None = None) -> tuple[int, str]:
    """
    Возвращает (количество_вакансий, источник).
    источник: 'live' | 'fallback_exp' | 'simulated'
    """
    url = "https://api.hh.ru/vacancies"
    headers = {"User-Agent": "PredictiveJobMarketApp/1.0"}
    base_params = {"text": keyword.strip(), "area": area_id, "per_page": 1}

    def _fetch(params: dict) -> int:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=7)
            resp.raise_for_status()
            return resp.json().get("found", 0)
        except requests.exceptions.Timeout:
            st.warning("⏱ API hh.ru не ответил вовремя. Используем симуляцию.")
        except requests.exceptions.ConnectionError:
            st.error("🌐 Нет соединения с интернетом. Используем симуляцию.")
        except requests.exceptions.HTTPError as e:
            st.warning(f"⚠️ Ошибка API hh.ru: {e}. Используем симуляцию.")
        except Exception as e:
            st.warning(f"⚠️ Неизвестная ошибка: {e}. Используем симуляцию.")
        return -1  # сигнал об ошибке сети

    # Попытка 1: с фильтром опыта
    if experience:
        result = _fetch({**base_params, "experience": experience})
        if result > 0:
            return result, "live"
        if result == -1:
            return 120, "simulated"

    # Попытка 2: без фильтра опыта
    result = _fetch(base_params)
    if result > 0:
        return result, "fallback_exp"
    if result == -1:
        return 120, "simulated"

    # Попытка 3: данные реально нулевые или скрыты
    return 120, "simulated"


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
    base_resumes  = int(base_vacancies * 4   * regional_coef)
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
