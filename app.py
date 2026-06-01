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
