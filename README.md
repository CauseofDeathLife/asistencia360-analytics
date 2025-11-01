# Asistencia360 — Analítica

Dashboard público para analizar asistencia académica con **Python + Pandas + Streamlit + Altair** (opcional **Matplotlib** ejecutiva).
**Demo en vivo:** https://asistencia360-analytics.streamlit.app/ 
**Repositorio:** https://github.com/CauseofDeathLife/asistencia360-analytics

---

## Características
- **Generación de datos** (`data_gen.py`): crea `data/asistencias.csv` y `data/students.csv` (datos sintéticos/anonimizados).
- **Analítica batch** (`analytics/analytics.py`): genera en `outputs/`
  - `day_pattern.csv`, `group_summary.csv`, `monthly_summary.csv`, `student_percentages.csv`.
- **Dashboard** (`app/streamlit_app.py`):
  - Filtros: rango de fechas, grupos, materias y **(opcional) estudiante** por nombre/ID.
  - HU11: tendencia mensual + línea objetivo (80%).
  - HU12: % por estudiante + ranking de riesgo con etiquetas.
  - HU13: resumen por grupo con etiquetas + línea objetivo.
  - Opción **Matplotlib** en HU13 (checkbox).

---

## Estructura
```
asistencia360-analytics/
├─ analytics/
│  └─ analytics.py
├─ app/
│  └─ streamlit_app.py
├─ data/
│  ├─ asistencias.csv
│  └─ students.csv
├─ outputs/
│  ├─ day_pattern.csv
│  ├─ group_summary.csv
│  ├─ monthly_summary.csv
│  └─ student_percentages.csv
├─ data_gen.py
├─ requirements.txt
└─ README.md
```

---

## Requisitos
- **Python 3.10+** (recomendado 3.12).
- Dependencias en `requirements.txt` (pandas, numpy, streamlit, altair, matplotlib).

---

## Uso rápido (local)
```bash
pip install -r requirements.txt
python data_gen.py                       # si no existen los CSV de /data
python -m streamlit run app/streamlit_app.py
```
> Para usar otro CSV de asistencias, define `ASISTENCIAS_INPUT` con la ruta a tu archivo.

---

## Deploy (Streamlit Community Cloud)
- New app → GitHub repo: `CauseofDeathLife/asistencia360-analytics`
- Branch: `main`
- Main file path: `app/streamlit_app.py`

> Streamlit instalará `requirements.txt` y entregará una URL pública.

---

## Licencia
Uso académico/demostrativo. Anonimiza datos antes de publicar.
