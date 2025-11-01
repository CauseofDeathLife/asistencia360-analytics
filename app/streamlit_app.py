#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asistencia360 — Dashboard Streamlit (streamlit_app.py)

Descripción:
    Interfaz interactiva con filtros de:
      - Rango de fechas
      - Grupos
      - Materias
      - (Opcional) Estudiante (por nombre o ID)

Pestañas:
    - HU11 — Resumen mensual: línea de tendencia por grupo + línea objetivo (80%).
    - HU12 — % por estudiante: ranking de mayor riesgo con etiquetas.
    - HU13 — Resumen por grupo: barras con etiquetas y línea objetivo.

Detalles técnicos:
    - Gráficos Altair facetados con dataset en nivel superior y línea objetivo mediante alt.datum(80).
    - Opción Matplotlib (checkbox) en HU13 para versión ejecutiva (si falta la lib, no rompe).
    - La ruta de datos puede sobreescribirse con la variable de entorno:
        ASISTENCIAS_INPUT="/ruta/a/asistencias.csv"

Ejecución:
    python -m streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Asistencia360", layout="wide")

BASE_DIR: Final[Path] = Path(__file__).resolve().parents[1]
DEFAULT_INPUT: Final[str] = str(BASE_DIR / "data" / "asistencias.csv")


def pct(p: pd.Series, a: pd.Series) -> pd.Series:
    return p.div(p.add(a)).fillna(0.0).mul(100.0).round(2)


@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    input_path = os.environ.get("ASISTENCIAS_INPUT", DEFAULT_INPUT)
    df = pd.read_csv(input_path, parse_dates=["date"]).copy()

    df["status"] = df["status"].astype(str).str.upper().str.strip()
    df["P"] = df["status"].eq("P").astype("int64")
    df["A"] = df["status"].eq("A").astype("int64")
    df["J"] = df["status"].eq("J").astype("int64")

    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["weekday"] = df["date"].dt.day_name()
    return df


def apply_filters(data: pd.DataFrame) -> pd.DataFrame:
    min_date, max_date = data["date"].min(), data["date"].max()

    st.sidebar.header("Filtros")
    date_range = st.sidebar.date_input("Rango de fechas", (min_date, max_date),
                                       min_value=min_date, max_value=max_date)

    groups = sorted(data["group_id"].unique())
    subjects = sorted(data["subject"].unique())
    sel_groups = st.sidebar.multiselect("Grupos", groups, default=groups)
    sel_subjects = st.sidebar.multiselect("Materias", subjects, default=subjects)

    students_options = (
        data[["student_id", "student_name"]]
        .drop_duplicates()
        .sort_values("student_name")
        .assign(label=lambda d: d["student_name"] + " (" + d["student_id"] + ")")
    )
    sel_student = st.sidebar.selectbox("Filtrar por estudiante (opcional)",
        options=["[Ver todos]"] + students_options["label"].tolist(), index=0)

    mask = (
        data["date"].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
        & data["group_id"].isin(sel_groups)
        & data["subject"].isin(sel_subjects)
    )
    if sel_student != "[Ver todos]":
        chosen_id = students_options.loc[students_options["label"] == sel_student, "student_id"].iloc[0]
        mask &= data["student_id"].eq(chosen_id)

    return data.loc[mask].copy()


def hu11_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    gcols = ["month", "group_id", "subject"]
    out = df.groupby(gcols)[["P", "A", "J"]].sum().reset_index()
    out["total_sesiones"] = out[["P", "A", "J"]].sum(axis=1)
    out["total_effective"] = out["P"] + out["A"]
    out["pct_asistencia"] = pct(out["P"], out["A"])
    return out.sort_values(gcols).reset_index(drop=True)


def hu12_student_percentages(df: pd.DataFrame, thr: float = 0.20) -> pd.DataFrame:
    gcols = ["student_id", "student_name", "sex", "group_id", "subject"]
    s = df.groupby(gcols)[["P", "A", "J"]].sum().reset_index()
    s["total_effective"] = s["P"] + s["A"]
    s["pct_asistencia"] = pct(s["P"], s["A"])
    s["pct_inasistencia"] = s["A"].div(s["total_effective"]).fillna(0.0).mul(100.0).round(2)
    s["riesgo_perdida"] = s["pct_inasistencia"].ge(thr * 100).astype(bool)
    return s.sort_values(["group_id", "subject", "pct_asistencia"], ascending=[True, True, False]).reset_index(drop=True)


def hu13_group_summary(df: pd.DataFrame) -> pd.DataFrame:
    s = hu12_student_percentages(df)
    gcols = ["group_id", "subject"]
    g = s.groupby(gcols).agg(
        mean_pct=("pct_asistencia", "mean"),
        median_pct=("pct_asistencia", "median"),
        std_pct=("pct_asistencia", "std"),
        n_students=("student_id", "nunique"),
        prop_en_riesgo=("riesgo_perdida", "mean"),
    ).reset_index()
    g["mean_pct"] = g["mean_pct"].round(2)
    g["median_pct"] = g["median_pct"].round(2)
    g["std_pct"] = g["std_pct"].fillna(0.0).round(2)
    g["prop_en_riesgo"] = g["prop_en_riesgo"].mul(100.0).round(2)
    return g.sort_values(gcols).reset_index(drop=True)


def render() -> None:
    data = apply_filters(load_data())

    st.title("Asistencia360 — Analítica")
    tab11, tab12, tab13 = st.tabs(["HU11 — Resumen mensual", "HU12 — % por estudiante", "HU13 — Resumen por grupo"])

    # -------------------- HU11 --------------------
    with tab11:
        st.subheader("Resumen mensual por grupo y materia")
        t11 = hu11_monthly_summary(data)
        st.dataframe(t11, use_container_width=True)

        # Gráfico original (conservado)
        c1 = alt.Chart(t11).mark_bar().encode(
            x="month:N", y="pct_asistencia:Q", color="group_id:N", column="subject:N",
            tooltip=list(t11.columns)
        )
        st.altair_chart(c1, use_container_width=True)

        # === FIX: Facet con data en el nivel superior y línea objetivo constante ===
        st.markdown("##### Tendencia mensual (línea objetivo 80%) — FIX")
        base11 = alt.Chart(t11).properties(width=260)
        line = base11.mark_line(point=True).encode(
            x=alt.X("month:N", title="Mes", sort="ascending"),
            y=alt.Y("pct_asistencia:Q", title="% Asistencia"),
            color=alt.Color("group_id:N", title="Grupo"),
            tooltip=list(t11.columns)
        )
        rule = base11.mark_rule(strokeDash=[4,4]).encode(y=alt.datum(80))
        hu11_chart = alt.layer(line, rule).facet(column=alt.Column("subject:N", title=None))
        st.altair_chart(hu11_chart, use_container_width=True)

    # -------------------- HU12 --------------------
    with tab12:
        st.subheader("% de asistencia por estudiante")
        t12 = hu12_student_percentages(data)
        st.dataframe(t12, use_container_width=True)

        left, right = st.columns(2)
        with left:
            st.caption("Top 15 asistencia")
            st.dataframe(t12.sort_values("pct_asistencia", ascending=False).head(15), use_container_width=True)
        with right:
            st.caption("Bottom 15 asistencia")
            st.dataframe(t12.sort_values("pct_asistencia", ascending=True).head(15), use_container_width=True)

        st.markdown("##### Estudiantes en mayor riesgo (ordenado por asistencia más baja)")
        worst = t12.sort_values("pct_asistencia", ascending=True).head(20).copy()
        worst["riesgo_color"] = worst["riesgo_perdida"].map({True: "En riesgo", False: "OK"})
        bars = alt.Chart(worst).mark_bar().encode(
            x=alt.X("student_name:N", sort="-y", title="Estudiante"),
            y=alt.Y("pct_asistencia:Q", title="% Asistencia"),
            color=alt.Color("riesgo_color:N", title="Estado"),
            tooltip=["student_id","student_name","group_id","subject","pct_asistencia","pct_inasistencia","riesgo_perdida"]
        ).properties(height=400)
        labels = alt.Chart(worst).mark_text(dy=-5, fontWeight="bold").encode(
            x=alt.X("student_name:N", sort="-y"),
            y="pct_asistencia:Q",
            text=alt.Text("pct_asistencia:Q", format=".1f")
        )
        st.altair_chart(bars + labels, use_container_width=True)

    # -------------------- HU13 --------------------
    with tab13:
        st.subheader("Resumen por grupo")
        t13 = hu13_group_summary(data)
        st.dataframe(t13, use_container_width=True)

        # Gráfico original (conservado)
        c3 = alt.Chart(t13).mark_bar().encode(
            x="group_id:N", y="mean_pct:Q", color="subject:N", column="subject:N",
            tooltip=list(t13.columns)
        )
        st.altair_chart(c3, use_container_width=True)

        # === FIX: misma idea de top-level data + facet ===
        st.markdown("##### Comparativo por grupo con línea objetivo 80% — FIX")
        base13 = alt.Chart(t13).properties(width=260)
        bars13 = base13.mark_bar().encode(
            x=alt.X("group_id:N", title="Grupo"),
            y=alt.Y("mean_pct:Q", title="Asistencia promedio (%)", scale=alt.Scale(domain=[0,100])),
            color=alt.Color("subject:N", title="Materia"),
            tooltip=list(t13.columns)
        )
        labels13 = base13.mark_text(dy=-8, fontWeight="bold").encode(
            x="group_id:N",
            y="mean_pct:Q",
            text=alt.Text("mean_pct:Q", format=".1f")
        )
        rule13 = base13.mark_rule(strokeDash=[4,4]).encode(y=alt.datum(80))
        fixed13 = alt.layer(bars13, labels13, rule13).facet(column=alt.Column("subject:N", title=None))
        st.altair_chart(fixed13, use_container_width=True)


if __name__ == "__main__":
    render()
