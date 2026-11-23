import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BASE_URL = "https://api.nasa.gov"

st.set_page_config(page_title="NASA Dashboard", page_icon="🚀", layout="wide")


# ---------------------------------------------------------------------------
# API key: nunca se escribe en el código. Se lee de:
#   1) .streamlit/secrets.toml  (NASA_API_KEY = "...")
#   2) archivo .env o variable de entorno NASA_API_KEY
#   3) DEMO_KEY (límite muy bajo) si no hay nada configurado
# ---------------------------------------------------------------------------
def get_api_key() -> str:
    try:
        if "NASA_API_KEY" in st.secrets:
            return st.secrets["NASA_API_KEY"]
    except Exception:
        pass
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return os.getenv("NASA_API_KEY", "DEMO_KEY")


API_KEY = get_api_key()


@st.cache_data(ttl=3600, show_spinner=False)
def nasa_get(path: str, params: dict, key: str):
    response = requests.get(
        f"{BASE_URL}{path}", params={**params, "api_key": key}, timeout=30
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Encabezado y barra lateral
# ---------------------------------------------------------------------------
st.title("🚀 Dashboard NASA")
st.caption("Datos en vivo de la API abierta de NASA (api.nasa.gov)")

if API_KEY == "DEMO_KEY":
    st.sidebar.warning("Usando DEMO_KEY (límite bajo). Configura tu NASA_API_KEY.")
else:
    st.sidebar.success("API key cargada correctamente ✅")

st.sidebar.header("Filtros")
today = date.today()

tab_apod, tab_neo, tab_flr = st.tabs(
    ["🌌 Imagen del día (APOD)", "☄️ Asteroides cercanos", "☀️ Erupciones solares"]
)

# ---------------------------------------------------------------------------
# 1) APOD
# ---------------------------------------------------------------------------
with tab_apod:
    apod_date = st.date_input(
        "Fecha", value=today, min_value=date(1995, 6, 16), max_value=today, key="apod"
    )
    try:
        apod = nasa_get("/planetary/apod", {"date": apod_date.isoformat()}, API_KEY)
        st.subheader(apod.get("title", ""))
        col1, col2 = st.columns([3, 2])
        with col1:
            if apod.get("media_type") == "image":
                st.image(apod.get("url"), use_container_width=True)
            else:
                st.video(apod.get("url"))
        with col2:
            st.write(apod.get("explanation", ""))
            if apod.get("copyright"):
                st.caption(f"© {apod['copyright'].strip()}")
            st.caption(f"Fecha: {apod.get('date')}")
    except requests.HTTPError as e:
        st.error(f"Error al consultar APOD: {e}")
    except requests.RequestException as e:
        st.error(f"Problema de conexión: {e}")

# ---------------------------------------------------------------------------
# 2) NeoWs - Asteroides cercanos a la Tierra
# ---------------------------------------------------------------------------
with tab_neo:
    st.write("Objetos cercanos a la Tierra (NeoWs). La API permite máximo 7 días.")
    start = st.date_input("Inicio", value=today - timedelta(days=6), key="neo_start")
    end = min(start + timedelta(days=6), today + timedelta(days=30))
    st.caption(f"Rango consultado: {start} → {end}")

    try:
        data = nasa_get(
            "/neo/rest/v1/feed",
            {"start_date": start.isoformat(), "end_date": end.isoformat()},
            API_KEY,
        )
        rows = []
        for day, objects in data.get("near_earth_objects", {}).items():
            for o in objects:
                approach = o["close_approach_data"][0]
                diameter = o["estimated_diameter"]["meters"]
                rows.append(
                    {
                        "fecha": day,
                        "nombre": o["name"],
                        "peligroso": o["is_potentially_hazardous_asteroid"],
                        "diametro_min_m": diameter["estimated_diameter_min"],
                        "diametro_max_m": diameter["estimated_diameter_max"],
                        "velocidad_km_s": float(
                            approach["relative_velocity"]["kilometers_per_second"]
                        ),
                        "distancia_km": float(approach["miss_distance"]["kilometers"]),
                        "magnitud": o["absolute_magnitude_h"],
                    }
                )
        df = pd.DataFrame(rows)

        if df.empty:
            st.info("No hay datos para este rango.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Asteroides", len(df))
            c2.metric("Potencialmente peligrosos", int(df["peligroso"].sum()))
            c3.metric("Más rápido (km/s)", f"{df['velocidad_km_s'].max():.1f}")
            c4.metric("Más cercano (km)", f"{df['distancia_km'].min():,.0f}")

            left, right = st.columns(2)
            per_day = df.groupby("fecha").size().reset_index(name="cantidad")
            left.plotly_chart(
                px.bar(per_day, x="fecha", y="cantidad", title="Asteroides por día"),
                use_container_width=True,
            )
            right.plotly_chart(
                px.scatter(
                    df,
                    x="distancia_km",
                    y="diametro_max_m",
                    color="peligroso",
                    size="velocidad_km_s",
                    hover_name="nombre",
                    log_x=True,
                    log_y=True,
                    title="Distancia vs. diámetro máximo (escala log)",
                ),
                use_container_width=True,
            )
            st.dataframe(df.sort_values("distancia_km"), use_container_width=True)
    except requests.HTTPError as e:
        st.error(f"Error al consultar NeoWs: {e}")
    except requests.RequestException as e:
        st.error(f"Problema de conexión: {e}")

# ---------------------------------------------------------------------------
# 3) DONKI - Erupciones solares
# ---------------------------------------------------------------------------
with tab_flr:
    days_back = st.slider("Días hacia atrás", 7, 180, 60, key="flr_days")
    try:
        flares = nasa_get(
            "/DONKI/FLR",
            {
                "startDate": (today - timedelta(days=days_back)).isoformat(),
                "endDate": today.isoformat(),
            },
            API_KEY,
        )
        if not flares:
            st.info("No se registraron erupciones en este periodo.")
        else:
            fdf = pd.DataFrame(flares)
            fdf["clase"] = fdf["classType"].str[0]
            fdf["inicio"] = pd.to_datetime(fdf["beginTime"])

            c1, c2 = st.columns(2)
            c1.metric("Erupciones registradas", len(fdf))
            c2.metric("Clase X", int((fdf["clase"] == "X").sum()))

            left, right = st.columns(2)
            by_class = fdf.groupby("clase").size().reset_index(name="cantidad")
            left.plotly_chart(
                px.pie(by_class, names="clase", values="cantidad", title="Por clase"),
                use_container_width=True,
            )
            by_date = fdf.groupby(fdf["inicio"].dt.date).size().reset_index(name="cantidad")
            by_date.columns = ["fecha", "cantidad"]
            right.plotly_chart(
                px.line(by_date, x="fecha", y="cantidad", title="Erupciones por día"),
                use_container_width=True,
            )
            cols = [c for c in ["classType", "beginTime", "peakTime", "sourceLocation"] if c in fdf]
            st.dataframe(fdf[cols], use_container_width=True)
    except requests.HTTPError as e:
        st.error(f"Error al consultar DONKI: {e}")
    except requests.RequestException as e:
        st.error(f"Problema de conexión: {e}")
