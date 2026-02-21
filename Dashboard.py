
from pathlib import Path
import io
import base64
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# -------------------------
# Config / Dataset path
# -------------------------
DATA_PATH = Path(r"C:\Users\User\Desktop\Data Visualization\global_warming_dataset.csv")


# -------------------------
# Utility helpers
# -------------------------
@st.cache_data
def load_df(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at {path}")
    # allow flexible separators (tab or comma)
    df = pd.read_csv(path, engine="python", sep=None)
    # normalize column names
    df.columns = [c.strip() for c in df.columns]
    return df

def generate_fake_iso(country_name: str) -> str:
    """Create a stable fake ISO3 from Country_### style names."""
    try:
        tail = country_name.split("_")[-1]
        # create 3-char code (C + up to 2 digits or hash)
        if tail.isdigit():
            n = int(tail) % 1000
            return f"C{n:02d}" if n < 100 else f"C{n}"
        else:
            # fallback: take letters
            s = ''.join([c for c in country_name if c.isalpha()])[:3].upper()
            return s.ljust(3, "X")[:3]
    except Exception:
        return country_name[:3].upper()

def csv_download_link(df: pd.DataFrame, filename="filtered.csv"):
    csv = df.to_csv(index=False).encode("utf-8")
    b64 = base64.b64encode(csv).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download filtered CSV</a>'
    return href

def fig_to_png_download(fig, filename="chart.png", width=1200, height=700, scale=2):
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=scale)
    b64 = base64.b64encode(img_bytes).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}">Download PNG</a>'
    return href

# -------------------------
# Load data
# -------------------------
st.set_page_config(page_title="Global Climate Indicators", layout="wide")
st.title("🌍 Global Climate Indicators Dashboard")
st.markdown("Focused dashboard showcasing the long-term trends and country comparisons for key climate indicators.")

try:
    df = load_df(DATA_PATH)
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

# -------------------------
# COLUMN DETECTION & MAPPING
# -------------------------
# Recommended primary & secondary indicators (heuristics + fallback to actual names)
colnames = {c.lower(): c for c in df.columns}

def find_col(*keywords):
    for kw in keywords:
        for lower, orig in colnames.items():
            if kw.lower() in lower:
                return orig
    return None

# Primary (core) indicators
COL_YEAR = find_col("year", "yr") or "Year"
COL_COUNTRY = find_col("country", "country_name") or "Country"
COL_TEMP = find_col("temperature_anomaly", "temperature", "average_temperature", "temp")
COL_CO2 = find_col("co2_emissions", "co2", "co2_concentration")
COL_SEA = find_col("sea_level_rise", "sea_level")

# Secondary indicators (contextual)
COL_ARCTIC = find_col("arctic_ice", "arctic")
COL_OCEAN_ACID = find_col("ocean_acidification", "ocean_acidification")
COL_RENEW = find_col("renewable_energy_usage", "renewable")
COL_DEFOREST = find_col("deforestation_rate", "deforest")
COL_BIODIV = find_col("biodiversity_index", "biodiversity")
COL_PERCAP = find_col("per_capita_emissions", "per_capita")
COL_AIRPOLL = find_col("air_pollution_index", "air_pollution")

# Build list of selected columns for the professional dashboard
primary_metrics = {
    "Temperature Anomaly": COL_TEMP,
    "CO2 Emissions": COL_CO2,
    "Sea Level Rise": COL_SEA
}
secondary_metrics = {
    "Arctic Ice Extent": COL_ARCTIC,
    "Ocean Acidification": COL_OCEAN_ACID,
    "Renewable Energy Usage": COL_RENEW,
    "Deforestation Rate": COL_DEFOREST,
    "Biodiversity Index": COL_BIODIV,
    "Per Capita Emissions": COL_PERCAP,
    "Air Pollution Index": COL_AIRPOLL
}

# Validate Year & Country presence
if COL_YEAR not in df.columns:
    st.error("Could not detect 'Year' column. Please ensure dataset contains a Year column.")
    st.stop()
if COL_COUNTRY not in df.columns:
    st.error("Could not detect 'Country' column. Please ensure dataset contains a Country column.")
    st.stop()

# Cast Year to int if possible
try:
    df[COL_YEAR] = df[COL_YEAR].astype(int)
except Exception:
    pass

# Create ISO3 (fake) to allow choropleth rendering
if "ISO3" not in df.columns:
    df["ISO3"] = df[COL_COUNTRY].astype(str).apply(generate_fake_iso)

# -------------------------
# UI: Sidebar controls
# -------------------------
st.sidebar.header("Filters & Settings")
min_year = int(df[COL_YEAR].min())
max_year = int(df[COL_YEAR].max())
year_range = st.sidebar.slider("Year range", min_year, max_year, (min_year, max_year), step=1)

# Choose which primary & secondary to show
st.sidebar.markdown("### Primary indicators (time-series)")
show_temp = st.sidebar.checkbox("Temperature Anomaly", value=bool(COL_TEMP in df.columns))
show_co2 = st.sidebar.checkbox("CO2 Emissions", value=bool(COL_CO2 in df.columns))
show_sea = st.sidebar.checkbox("Sea Level Rise", value=bool(COL_SEA in df.columns))

st.sidebar.markdown("### Secondary indicators (context)")
secondary_selection = st.sidebar.multiselect(
    "Select secondary indicators to include in overview",
    options=[k for k,v in secondary_metrics.items() if v in df.columns],
    default=[k for k,v in secondary_metrics.items() if v in df.columns][:3]
)

normalize = st.sidebar.checkbox("Normalize (0-1) for small multiples", value=False)
rolling_window = st.sidebar.slider("Rolling average window (years, 0 = off)", 0, 30, 3)
show_choropleth = st.sidebar.checkbox("Show choropleth (country map)", value=True)
story_mode = st.sidebar.checkbox("Enable story mode (decade autoplay)", value=False)

# Filter dataframe by year range
df_filt = df[(df[COL_YEAR] >= year_range[0]) & (df[COL_YEAR] <= year_range[1])].copy()

# -------------------------
# KPI Cards (top row)
# -------------------------
st.markdown("## Key global KPIs (latest year in range)")
latest_year = int(df_filt[COL_YEAR].max())
latest_df = df_filt[df_filt[COL_YEAR] == latest_year]

def summarize_metric(col):
    if col and col in df_filt.columns:
        global_avg = df_filt.groupby(COL_YEAR)[col].mean().iloc[-1]
        prev = df_filt.groupby(COL_YEAR)[col].mean().iloc[0] if len(df_filt[COL_YEAR].unique())>1 else global_avg
        delta = global_avg - prev
        return global_avg, delta
    return None, None

kcol1, kcol2, kcol3, kcol4 = st.columns([1,1,1,1])

# Temperature KPI
if show_temp and COL_TEMP in df_filt.columns:
    gavg, delta = summarize_metric(COL_TEMP)
    kcol1.metric("Global Temp Anomaly (avg)", f"{gavg:.3f} °C" if gavg is not None else "n/a",
                f"{delta:+.3f} since start")
else:
    kcol1.info("Temperature not available")

# CO2 KPI
if show_co2 and COL_CO2 in df_filt.columns:
    gavg, delta = summarize_metric(COL_CO2)
    kcol2.metric("CO₂ Emissions (avg)", f"{gavg:,.1f}" if gavg is not None else "n/a", f"{delta:+.1f} since start")
else:
    kcol2.info("CO₂ not available")

# Sea level KPI
if show_sea and COL_SEA in df_filt.columns:
    gavg, delta = summarize_metric(COL_SEA)
    kcol3.metric("Global Sea Level (avg)", f"{gavg:.2f}" if gavg is not None else "n/a", f"{delta:+.2f} since start")
else:
    kcol3.info("Sea level not available")

# Secondary quick KPI (first chosen)
if secondary_selection:
    sec_name = secondary_selection[0]
    sec_col = secondary_metrics.get(sec_name)
    if sec_col in df_filt.columns:
        savg, sdelta = summarize_metric(sec_col)
        kcol4.metric(sec_name, f"{savg:.2f}" if savg is not None else "n/a", f"{sdelta:+.2f} since start")
    else:
        kcol4.info("Secondary not available")
else:
    kcol4.info("Select secondary on sidebar")

st.markdown("---")

# -------------------------
# Time-series panels
# -------------------------
st.markdown("## Time-series Overview")
ts_col1, ts_col2 = st.columns([2,1])

with ts_col1:
    # show combined multi-line of primary indicators
    lines = []
    for label, col in primary_metrics.items():
        if col and col in df_filt.columns and ((label == "Temperature Anomaly" and show_temp) or (label=="CO2 Emissions" and show_co2) or (label=="Sea Level Rise" and show_sea)):
            df_year = df_filt.groupby(COL_YEAR)[col].mean().reset_index()
            if rolling_window > 0:
                df_year[col + "_roll"] = df_year[col].rolling(window=rolling_window, min_periods=1).mean()
                ycol = col + "_roll"
            else:
                ycol = col
            if normalize:
                s = df_year[ycol]
                df_year[ycol] = (s - s.min()) / (s.max() - s.min())
            lines.append((label, df_year, ycol))
    if lines:
        fig = go.Figure()
        for label, dfy, ycol in lines:
            fig.add_trace(go.Scatter(x=dfy[COL_YEAR], y=dfy[ycol], mode='lines+markers', name=label))
        fig.update_layout(title="Primary indicators over time", xaxis_title="Year", height=480)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No primary indicator selected or available.")

with ts_col2:
    st.markdown("### Snapshot controls & export")
    if st.button("Export primary chart PNG"):
        # generate PNG from last built fig if exists
        try:
            img_bytes = fig.to_image(format="png", width=1200, height=600, scale=2)
            st.image(img_bytes)
            b64 = base64.b64encode(img_bytes).decode()
            st.markdown(f'<a href="data:image/png;base64,{b64}" download="primary_chart.png">Download PNG</a>', unsafe_allow_html=True)
        except Exception as e:
            st.error("PNG export failed: " + str(e))
    st.write("Story mode: step through decades (if enabled will autoplay).")
    if story_mode:
        decades = sorted(df_filt[COL_YEAR].apply(lambda y: (y // 10) * 10).unique())
        dec_slider = st.slider("Decade index", 0, max(0, len(decades)-1), 0)
        current_dec = decades[dec_slider]
        st.write(f"Showing decade: {current_dec}s")

st.markdown("---")

# -------------------------
# Small multiples for selected primary + secondary (professional layout)
# -------------------------
st.markdown("## Small multiples (decade facets) — focused view")

# Build the metric list to show: primary (selected) + top N secondary
metrics_to_show = []
if show_temp and COL_TEMP in df_filt.columns:
    metrics_to_show.append(( "Temperature Anomaly", COL_TEMP))
if show_co2 and COL_CO2 in df_filt.columns:
    metrics_to_show.append(( "CO2 Emissions", COL_CO2))
if show_sea and COL_SEA in df_filt.columns:
    metrics_to_show.append(( "Sea Level Rise", COL_SEA))

# add up to 4 secondary
for sec in secondary_selection[:4]:
    sec_col = secondary_metrics.get(sec)
    if sec_col in df_filt.columns:
        metrics_to_show.append((sec, sec_col))

# plot small multiples (one row per metric)
df_filt["Decade"] = (df_filt[COL_YEAR] // 10) * 10
for label, col in metrics_to_show:
    try:
        fig = px.line(df_filt, x=COL_YEAR, y=col, color="Decade", facet_col="Decade", facet_col_wrap=4,
                      title=f"{label} — decade facets", height=320)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not render small multiples for {label}: {e}")

st.markdown("---")

# -------------------------
# Country comparison & Choropleth
# -------------------------
st.markdown("## Country comparison & map")

left, right = st.columns([2,1])

with left:
    st.write("Select countries to compare time-series (top 8 recommended)")
    countries = sorted(df[COL_COUNTRY].unique())
    selected_countries = st.multiselect("Countries", countries, default=countries[:6])
    compare_metric = st.selectbox("Compare metric", options=[m for m,_ in metrics_to_show] if metrics_to_show else [k for k in primary_metrics])
    # find column for compare_metric
    compare_col = None
    for name,col in metrics_to_show:
        if name == compare_metric:
            compare_col = col
            break
    if compare_col:
        df_comp = df_filt[df_filt[COL_COUNTRY].isin(selected_countries)]
        fig_comp = px.line(df_comp, x=COL_YEAR, y=compare_col, color=COL_COUNTRY, title=f"{compare_metric} — country comparison")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Choose a valid compare metric.")

with right:
    st.write("Choropleth (latest year in selection)")
    if show_choropleth:
        latest = df_filt.sort_values(COL_YEAR).groupby(COL_COUNTRY, as_index=False).last()
        if "ISO3" in latest.columns:
            metric_for_map = metrics_to_show[0][1] if metrics_to_show else COL_TEMP
            try:
                fig_map = px.choropleth(latest, locations="ISO3", color=metric_for_map,
                                        hover_name=COL_COUNTRY, title=f"{metrics_to_show[0][0]} by country (latest)")
                st.plotly_chart(fig_map, use_container_width=True)
            except Exception as e:
                st.error("Map rendering failed: " + str(e))
        else:
            st.info("No ISO3 codes available; the app generates fake ISO3 from Country_### automatically.")

st.markdown("---")

# -------------------------
# Correlation heatmap (selected metrics)
# -------------------------
st.markdown("## Correlations (focused metrics)")
corr_metrics = [col for _,col in metrics_to_show if col in df_filt.columns]
if len(corr_metrics) >= 2:
    corr_df = df_filt[corr_metrics].corr()
    fig_corr = px.imshow(corr_df, text_auto=".2f", title="Correlation matrix — selected metrics")
    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("Add more metrics (sidebar) to see correlations.")

st.markdown("---")

# -------------------------
# Dataset preview & export
# -------------------------
st.markdown("## Data & export")
st.write(f"Showing filtered rows: {len(df_filt):,} (years {year_range[0]}–{year_range[1]})")
st.dataframe(df_filt.head(200))

st.markdown(csv_download_link(df_filt, filename=f"filtered_climate_{year_range[0]}_{year_range[1]}.csv"), unsafe_allow_html=True)


st.markdown("---")

