# app_streamlit.py – Front‑end elegante para la Calculadora de Gasificadores
# ---------------------------------------------------------------------------
# Ejecuta:  streamlit run app_streamlit.py
# Requiere:  pip install streamlit pandas
# ---------------------------------------------------------------------------

import streamlit as st
import pandas as pd
from calculadora_gasificador import (
    FinTubeGeometry, ModuleConfig, AmbientConditions, Gasifier
)

st.set_page_config(page_title="Calculadora de Gasificadores LNG→NG", layout="wide")

st.title("🔷 Calculadora de Gasificadores Atmosféricos (GNL → GNG)")
st.markdown("""
Ajusta los parámetros geométricos, ambientales y de disposición de módulos para
estimar la **capacidad de vaporización** y el **footprint**. Basado en el modelo
referencia y escalado validado en conversaciones previas.
""")

# --------------------------- Sidebar --------------------------------------
with st.sidebar:
    st.header("🎛️ Parámetros de Entrada")

    # Geometría de tubo aletado
    st.subheader("Geometría del Tubo Aletado")
    tube_od = st.number_input("Ø liner (mm)", 20, 60, 28)
    fin_height = st.slider("Altura de aleta (mm)", 50, 500, 200, 10)
    fins_per_tube = st.slider("Número de aletas por tubo", 6, 40, 12)
    fin_eff = st.slider("Eficiencia de aleta (ε)", 0.3, 1.0, 0.85, 0.01)

    # Disposición de módulos
    st.subheader("Matriz de Tubos por Módulo")
    tubes_x = st.number_input("Tubos en X", 1, 30, 9)
    tubes_y = st.number_input("Tubos en Y", 1, 30, 8)
    spacing_x = st.number_input("Espaciado X (mm)", 100, 400, 215)
    spacing_y = st.number_input("Espaciado Y (mm)", 100, 400, 300)
    n_modules = st.number_input("Cantidad de módulos", 1, 4, 1)
    connection = st.selectbox("Conexión entre módulos", ("Paralelo", "Serie"))

    # Longitud y ambiente
    st.subheader("Longitud & Ambiente")
    tube_length = st.number_input("Longitud de tubo (mm)", 1000, 15000, 4600)
    T_air = st.slider("Temperatura ambiente (°C)", -20, 40, 15)
    wind = st.slider("Velocidad de viento (m/s)", 0.0, 5.0, 0.5, 0.1)

# --------------------------- Cálculo --------------------------------------
geom = FinTubeGeometry(
    tube_od_mm=tube_od,
    fin_height_mm=fin_height,
    fins_per_tube=fins_per_tube,
    fin_efficiency=fin_eff,
)
mod = ModuleConfig(
    tubes_x=tubes_x,
    tubes_y=tubes_y,
    spacing_x_mm=spacing_x,
    spacing_y_mm=spacing_y,
)
amb = AmbientConditions(T_air=T_air, v_wind=wind)

single = Gasifier(geom, mod, tube_length_mm=tube_length, ambient=amb)
cap_single = single.capacity()

if connection == "Paralelo":
    capacity_total = cap_single * n_modules
else:  # Serie
    capacity_total = cap_single  # restricción térmica una vez

# --------------------------- Salida ---------------------------------------
tab1, tab2 = st.tabs(["📊 Resultados", "📐 Footprint"])

with tab1:
    st.subheader("Resumen de Capacidad")
    df = pd.DataFrame([
        {
            "Módulos": n_modules,
            "Conexión": connection,
            "Tubos totales": mod.n_tubes * n_modules,
            "Capacidad Nm³/h": round(capacity_total),
            "Área total m²": round(single.summary()["area_total_m2"] * n_modules if connection == "Paralelo" else single.summary()["area_total_m2"], 1),
            "τ térmico (h)": single.summary()["tau_h"],
        }
    ])
    st.table(df)

with tab2:
    fx, fy = mod.footprint_mm(geom.tube_od_mm + 2 * geom.fin_height_mm)
    st.subheader("Dimensiones por Módulo")
    st.write(f"**X:** {round(fx)} mm | **Y:** {round(fy)} mm | **Z (altura):** {tube_length} mm")
    st.caption("*Las dimensiones globales dependen de la disposición en campo y separación entre módulos.*")

st.success("Cálculo actualizado.")
