#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asistencia360 — Generador de datos (data_gen.py)

Descripción:
    Genera datasets sintéticos/anonimizados de asistencia académica para pruebas:
      - data/asistencias.csv
      - data/students.csv

Qué hace:
    - Crea estudiantes (ID + nombre + sexo) y sesiones por fecha, grupo y materia.
    - Define el estado por sesión: P (presente), A (ausente) o J (justificado).

Uso:
    python data_gen.py

Salida:
    Archivos CSV en ./data

Notas:
    - Los datos son ficticios, pensados para demo/estudio.
    - Ajusta semillas/parámetros si deseas diferentes volúmenes o distribuciones.
"""


import numpy as np
import pandas as pd
from pandas.tseries.offsets import CustomBusinessDay


RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

START_DATE = pd.Timestamp("2025-07-01")
END_DATE   = pd.Timestamp("2025-10-31")

GROUPS = {"G1": "Grupo 1", "G2": "Grupo 2", "G3": "Grupo 3"}
SUBJECTS = ["Frontend 2", "Backend 2", "Nuevas Tecnologías"]

# Agenda por grupo: Lunes(0), Miércoles(2), Viernes(4)
SCHEDULE = {
    "G1": {0: "Frontend 2", 2: "Backend 2", 4: "Nuevas Tecnologías"},
    "G2": {0: "Backend 2", 2: "Nuevas Tecnologías", 4: "Frontend 2"},
    "G3": {0: "Nuevas Tecnologías", 2: "Frontend 2", 4: "Backend 2"},
}

BASE_GROUP = {"G1": 0.90, "G2": 0.84, "G3": 0.78}
DELTA_SUBJ = {"Frontend 2": 0.03, "Backend 2": -0.03, "Nuevas Tecnologías": 0.00}
DELTA_DAY  = {0: -0.02, 2: 0.00, 4: 0.01}  # L, X, V

CLAMP_MIN, CLAMP_MAX = 0.55, 0.98
N_STUDENTS_PER_GROUP = 32

# ---------- NUEVO: nombres en español ----------
MALE_FIRST = [
    "Juan","Carlos","Andrés","Felipe","Santiago","Sebastián","Luis","Jorge","Miguel","Diego",
    "Alejandro","Cristian","Nicolás","David","Mario","Fernando","Raúl","Ricardo","Álvaro","Héctor"
]
FEMALE_FIRST = [
    "María","Ana","Camila","Valentina","Daniela","Laura","Carolina","Sofía","Paula","Andrea",
    "Diana","Juliana","Gabriela","Tatiana","Alejandra","Ángela","Mónica","Luisa","Catalina","Verónica"
]
SURNAMES = [
    "García","Rodríguez","Martínez","López","González","Pérez","Sánchez","Ramírez","Torres","Álvarez",
    "Romero","Herrera","Vargas","Castro","Jiménez","Rojas","Navarro","Ortiz","Gómez","Morales",
    "Vega","Guzmán","Castillo","Reyes","Cabrera","Flores","Méndez","Pineda","Salazar","Delgado",
    "Cárdenas","León","Fuentes","Peña","Arroyo","Bravo","Rivero","Barrios","Camacho","Montoya",
    "Valencia","Quintero","Muñoz","Nieto","Cardona","Espinosa","Castañeda","Duarte","Suárez","Arias"
]

def _build_name_pools():
    # Creamos muchas combinaciones y las barajamos para garantizar unicidad y reproducibilidad
    rng = np.random.RandomState(RANDOM_SEED)
    male_pool   = [f"{fn} {sn}" for fn in MALE_FIRST   for sn in SURNAMES]
    female_pool = [f"{fn} {sn}" for fn in FEMALE_FIRST for sn in SURNAMES]
    rng.shuffle(male_pool)
    rng.shuffle(female_pool)
    return male_pool, female_pool

def make_students():
    male_pool, female_pool = _build_name_pools()
    male_idx = female_idx = 0

    records = []
    sid = 1
    for g in GROUPS.keys():
        for _ in range(N_STUDENTS_PER_GROUP):
            sex = np.random.choice(["M","F"])
            if sex == "M":
                full_name = male_pool[male_idx]; male_idx += 1
            else:
                full_name = female_pool[female_idx]; female_idx += 1
            records.append({
                "student_id": f"S{sid:03d}",
                "full_name": full_name,
                "sex": sex,
                "group_id": g
            })
            sid += 1
    return pd.DataFrame(records)

def business_days(start, end):
    # Solo lunes, miércoles y viernes
    mwf = CustomBusinessDay(weekmask="Mon Wed Fri")
    return pd.date_range(start, end, freq=mwf)



def generate_attendance(students: pd.DataFrame) -> pd.DataFrame:
    dates = business_days(START_DATE, END_DATE)
    records = []

    # Sesgo fijo por estudiante (estable en el tiempo)
    bias_per_student = {sid: np.random.uniform(-0.08, 0.08)
                        for sid in students["student_id"].unique()}

    weekday_names = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    for d in dates:
        w = int(d.weekday())
        for g in GROUPS.keys():
            subj = SCHEDULE[g][w]
            subdf = students[students["group_id"] == g]
            for _, row in subdf.iterrows():
                sid = row["student_id"]
                p = BASE_GROUP[g] + DELTA_SUBJ[subj] + DELTA_DAY[w] + bias_per_student[sid]
                p = max(CLAMP_MIN, min(CLAMP_MAX, p))

                # Muestreamos estado
                if np.random.rand() < p:
                    status = "P"
                else:
                    status = "J" if np.random.rand() < 0.10 else "A"

                records.append({
                    "student_id": sid,
                    "student_name": row["full_name"],  # usa nombre realista
                    "sex": row["sex"],
                    "group_id": row["group_id"],
                    "subject": subj,
                    "date": d.date().isoformat(),
                    "weekday": weekday_names[w],
                    "status": status
                })

    df = pd.DataFrame(records).sort_values(
        ["date","group_id","subject","student_id"]
    ).reset_index(drop=True)
    return df

def main():
    students = make_students()
    df = generate_attendance(students)

    import os
    os.makedirs("data", exist_ok=True)
    students.to_csv("data/students.csv", index=False, encoding="utf-8")
    df.to_csv("data/asistencias.csv", index=False, encoding="utf-8")
    print("OK: data/asistencias.csv y data/students.csv generados.")

if __name__ == "__main__":
    main()
