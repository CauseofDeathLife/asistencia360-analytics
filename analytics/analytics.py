#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asistencia360 — Analítica batch (analytics.py)

Descripción:
    Lee data/asistencias.csv y calcula resúmenes estadísticos.
    Escribe 4 archivos en ./outputs:

      1) day_pattern.csv           -> patrón por día de la semana
      2) group_summary.csv         -> métricas por grupo x materia
      3) monthly_summary.csv       -> % asistencia por mes x grupo x materia
      4) student_percentages.csv   -> % por estudiante + flag de riesgo

Uso:
    python analytics/analytics.py

Entradas:
    - ./data/asistencias.csv

Salidas:
    - ./outputs/*.csv (sobrescribe si existen)

Notas:
    - Las funciones usan Pandas y son idempotentes.
    - Maneja fechas en columna 'date' (datetime64[ns]).
    - Las columnas auxiliares P/A/J se calculan como enteros (0/1).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd


# -------------------------- Paths y configuración --------------------------
BASE_DIR: Final[Path] = Path(__file__).resolve().parents[1]  # .../analytics -> repo raíz
INPUT: Final[str] = os.environ.get("ASISTENCIAS_INPUT") or str(BASE_DIR / "data" / "asistencias.csv")
OUTDIR: Final[str] = os.environ.get("ASISTENCIAS_OUTDIR") or str(BASE_DIR / "outputs")
THRESH_RIESGO: Final[float] = float(os.environ.get("ASISTENCIAS_RISK", "0.20"))


# -------------------------- Utilidades --------------------------
def pct_asistencia_from_pa(p: pd.Series, a: pd.Series) -> pd.Series:
    """Devuelve % asistencia (0-100) como Series. Sin divisiones por cero."""
    denom = p.add(a)
    pct = p.div(denom).fillna(0.0).mul(100.0)
    return pct.round(2)


# -------------------------- Carga y features --------------------------
def load_data(path: str = INPUT) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"]).copy()

    # Normalizar y filtrar status
    df["status"] = df["status"].astype(str).str.upper().str.strip()
    df = df[df["status"].isin(["P", "A", "J"])].copy()

    # Máscaras tipadas para contentar al analizador estático
    mask_p: pd.Series = df["status"].eq("P")
    mask_a: pd.Series = df["status"].eq("A")
    mask_j: pd.Series = df["status"].eq("J")

    df["P"] = mask_p.astype("int64")
    df["A"] = mask_a.astype("int64")
    df["J"] = mask_j.astype("int64")

    # Derivadas temporales
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["weekday"] = df["date"].dt.day_name()

    # Validación de columnas que usa el pipeline
    needed = {"group_id", "subject", "student_id", "student_name", "sex"}
    missing = sorted(c for c in needed if c not in df.columns)
    if missing:
        raise ValueError(
            "Faltan columnas en el CSV de asistencias.\n"
            f"CSV: {path}\nFaltantes: {missing}\n"
            "Ejecuta data_gen.py y verifica el esquema."
        )
    return df


# -------------------------- Analíticas --------------------------
def hu11_monthly_summary(data: pd.DataFrame) -> pd.DataFrame:
    keys = ["month", "group_id", "subject"]
    agg = data.groupby(keys)[["P", "A", "J"]].sum().reset_index()
    agg["total_sesiones"] = agg[["P", "A", "J"]].sum(axis=1)
    agg["total_effective"] = agg["P"].add(agg["A"])  # P+A
    agg["pct_asistencia"] = pct_asistencia_from_pa(agg["P"], agg["A"])
    return agg.sort_values(keys).reset_index(drop=True)


def hu12_student_percentages(data: pd.DataFrame) -> pd.DataFrame:
    keys = ["student_id", "student_name", "sex", "group_id", "subject"]
    s = data.groupby(keys)[["P", "A", "J"]].sum().reset_index()
    s["total_effective"] = s["P"].add(s["A"])
    s["pct_asistencia"] = pct_asistencia_from_pa(s["P"], s["A"])
    riesgo = s["A"].div(s["total_effective"]).fillna(0.0).ge(THRESH_RIESGO)
    s["riesgo_perdida"] = riesgo.astype(bool)
    return s.sort_values(["group_id", "subject", "pct_asistencia"], ascending=[True, True, False]).reset_index(drop=True)


def hu13_group_summary(data: pd.DataFrame) -> pd.DataFrame:
    s = hu12_student_percentages(data)
    keys = ["group_id", "subject"]
    g = s.groupby(keys).agg(
        mean_pct=("pct_asistencia", "mean"),
        median_pct=("pct_asistencia", "median"),
        std_pct=("pct_asistencia", "std"),
        n_students=("student_id", "nunique"),
        prop_en_riesgo=("riesgo_perdida", "mean"),
    ).reset_index()
    g["mean_pct"] = g["mean_pct"].round(2)
    g["median_pct"] = g["median_pct"].round(2)
    g["std_pct"] = g["std_pct"].fillna(0.0).round(2)
    g["prop_en_riesgo"] = g["prop_en_riesgo"].mul(100.0).round(2)  # en %
    return g.sort_values(keys).reset_index(drop=True)


def day_pattern(data: pd.DataFrame) -> pd.DataFrame:
    keys = ["weekday", "group_id", "subject"]
    d = data.groupby(keys)[["P", "A", "J"]].sum().reset_index()
    d["total_effective"] = d["P"].add(d["A"])  # P+A
    d["pct_asistencia"] = pct_asistencia_from_pa(d["P"], d["A"])
    return d.sort_values(keys).reset_index(drop=True)


# -------------------------- Main --------------------------
def main() -> None:
    outdir = Path(OUTDIR)
    outdir.mkdir(parents=True, exist_ok=True)

    data = load_data()

    hu11_monthly_summary(data).to_csv(outdir / "monthly_summary.csv", index=False, encoding="utf-8")
    hu12_student_percentages(data).to_csv(outdir / "student_percentages.csv", index=False, encoding="utf-8")
    hu13_group_summary(data).to_csv(outdir / "group_summary.csv", index=False, encoding="utf-8")
    day_pattern(data).to_csv(outdir / "day_pattern.csv", index=False, encoding="utf-8")

    print(f"OK: outputs generados en {outdir}")


if __name__ == "__main__":
    main()
