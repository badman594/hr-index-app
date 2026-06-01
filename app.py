import streamlit as st
import pandas as pd

# Настройка страницы
st.set_page_config(page_title="Мониторинг востребованности профессий", layout="wide")

st.title("📊 Система динамического прогнозирования индекса нужности профессий")
st.subheader("Инструмент предиктивной аналитики для Вузов и Университетов")
st.markdown("---")

# Описание логики
st.sidebar.header("🛠️ Калькулятор Индекса")
st.sidebar.markdown("""
**Формула расчета:**  
`Индекс = (Резюме + Студенты) / Вакансии`

* **Ниже 2.0** — 🟢 Дефицит кадров
* **От 2.0 до 5.0** — 🟡 Стабильный баланс
* **Выше 5.0** — 🔴 Перепроизводство специалистов
""")

# Функция расчета индекса
def get_status(vacancies, resumes, students):
    if vacancies == 0:
        return float('inf'), "🔴 КРИТИЧЕСКИЙ ДЕФИЦИТ ВАКАНСИЙ! Рынок закрыт.", "danger"
    
    idx_val = round((resumes + students) / vacancies, 2)
    
    if idx_val < 2.0:
        return idx_val, "🟢 Дефицит кадров. Рекомендуется УВЕЛИЧИТЬ набор.", "success"
    elif 2.0 <= idx_val <= 5.0:
        return idx_val, "🟡 Баланс. Рынок стабилен. Корректировка не требуется.", "warning"
    else:
        return idx_val, "🔴 Перепроизводство! Рекомендуется СОКРАТИТЬ набор или внедрить ИИ-навыки.", "error"

# Вкладка 1: Готовая аналитика рынка
st.header("📈 Текущая ситуация по ключевым направлениям (РФ)")

# Базовые данные (ИСПРАВЛЕНО: все списки полностью заполнены числами)
initial_data = {
    "Профессия": [
        "Юрист (Первичный аудит)", 
        "Тестировщик ПО (Junior QA)", 
        "Копирайтер / Контент-менеджер", 
        "Специалист по Информ. Безопасности", 
        "AI Engineer / Data Scientist"
    ],
    "Вакансии": [200, 400, 300, 1500, 2500],
    "Резюме новичков": [3000, 3500, 4500, 2000, 1200],
    "Выпускники Вузов (План)": [1250, 1000, 1200, 3000, 1950]
}

df = pd.DataFrame(initial_data)
processed_results = []

for _, row in df.iterrows():
    val, status, _ = get_status(row["Вакансии"], row["Резюме новичков"], row["Выпускники Вузов (План)"])
    processed_results.append({"Профессия": row["Профессия"], "Индекс Нужности": val, "Рекомендация для Вуза": status})

df_res = pd.DataFrame(processed_results)
st.table(df_res)

st.markdown("---")

# Вкладка 2: Симулятор для Декана (Интерактив)
st.header("🎛️ Интерактивный симулятор для моделирования квот вуза")
st.caption("Изменяйте параметры ниже, чтобы увидеть, как изменится востребованность вашей специальности в реальном времени.")

col1, col2, col3 = st.columns(3)

with col1:
    v_input = st.number_input("Доступные вакансии на рынке (Junior/Начальный уровень):", min_value=0, value=100, step=10)
with col2:
    r_input = st.number_input("Количество резюме активных соискателей:", min_value=0, value=400, step=50)
with col3:
    s_input = st.slider("Ваш планируемый выпуск студентов (План приема):", min_value=10, max_value=1000, value=150, step=10)

# Расчет симулятора
calculated_index, text_status, alert_type = get_status(v_input, r_input, s_input)

st.markdown(f"### Текущий расчетный индекс: **{calculated_index}**")

if alert_type == "success":
    st.success(text_status)
elif alert_type == "warning":
    st.warning(text_status)
elif alert_type == "error" or alert_type == "danger":
    st.error(text_status)
