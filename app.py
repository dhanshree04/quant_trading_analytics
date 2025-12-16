import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import SYMBOLS
from src.storage import TradeStore
from src.ingestion import ingestion_service
from src.analytics import (
    resample_data, calculate_basic_stats, calculate_hedge_ratio,
    calculate_spread, calculate_zscore, calculate_adf_test,
    calculate_rolling_correlation
)

# Page Config
st.set_page_config(
        page_title="Quant Analytics Dashboard",
        layout="wide",
        page_icon="📈"
    )

# --- Ingestion Control ---
@st.cache_resource
def get_ingestion_service():
    service = ingestion_service
    service.start()
    return service

get_ingestion_service()

# --- Sidebar ---
st.sidebar.title("Configuration")

# Symbol Selection
st.sidebar.subheader("Pair Selection")
symbol_y = st.sidebar.selectbox("Symbol Y (Dependent)", SYMBOLS, index=0)
symbol_x = st.sidebar.selectbox("Symbol X (Independent)", SYMBOLS, index=1)

# Timeframe
timeframe = st.sidebar.selectbox("Timeframe", ['1s', '1Min', '5Min', '1H'], index=0)

# Analytics Params
st.sidebar.subheader("Analytics Parameters")
window_size = st.sidebar.slider("Rolling Window", min_value=10, max_value=200, value=20)
zscore_threshold = st.sidebar.number_input("Z-Score Alert Threshold", value=2.0, step=0.1)

# Refresh
refresh_rate = st.sidebar.slider("Refresh Rate (sec)", 1, 60, 2)

# --- Main Logic ---
st.title("Real-time Quantitative Analytics Dashboard")

# Load Data
store = TradeStore()
# Limit data fetch to manageable size for demo (e.g., last 1000 candles equivalent)
lookback_minutes = 60
if timeframe == '1H': lookback_minutes = 24 * 60
elif timeframe == '1s': lookback_minutes = 10

# Use UTC to match Binance timestamps
end_time = pd.Timestamp.utcnow()
start_time = end_time - pd.Timedelta(minutes=lookback_minutes)

data_loading = st.text("Loading data...")
df_y_raw = store.get_data(symbol_y, start_ts=start_time.value // 10**6)
df_x_raw = store.get_data(symbol_x, start_ts=start_time.value // 10**6)
data_loading.empty()

# Fallback: if time-based query returns empty (e.g., clock skew), fetch latest N ticks
if df_y_raw.empty:
    df_y_raw = store.get_latest_ticks(symbol_y, limit=5000)
    df_y_raw = df_y_raw.sort_index() # timestamps are index? verify storage.py
if df_x_raw.empty:
    df_x_raw = store.get_latest_ticks(symbol_x, limit=5000)
    df_x_raw = df_x_raw.sort_index()

if df_y_raw.empty or df_x_raw.empty:
    st.warning("Waiting for data... Ensure Ingestion is running.")
    st.info(f"Y: {len(df_y_raw)} ticks, X: {len(df_x_raw)} ticks")
    time.sleep(refresh_rate)
    st.rerun()

# Resample
freq_map = {'1s': '1S', '1Min': '1T', '5Min': '5T', '1H': '1H'}
resample_freq = freq_map.get(timeframe, '1T')

df_y = resample_data(df_y_raw, resample_freq)
df_x = resample_data(df_x_raw, resample_freq)

# Align
common_index = df_y.index.intersection(df_x.index)
df_y = df_y.loc[common_index]
df_x = df_x.loc[common_index]

# Allow partial window for demo purposes, just warn
if len(df_y) < window_size:
    st.caption(f"Building history... ({len(df_y)}/{window_size})")

# Analytics
beta, alpha = calculate_hedge_ratio(df_y['close'], df_x['close'])
spread = calculate_spread(df_y['close'], df_x['close'], beta)
zscore = calculate_zscore(spread, window_size)
adf_p = calculate_adf_test(spread)
corr = calculate_rolling_correlation(df_y['close'], df_x['close'], window_size)

# --- Dashboard Layout ---

# Top Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Hedge Ratio (Beta)", f"{beta:.4f}")
c2.metric("Current Z-Score", f"{zscore.iloc[-1]:.4f}", delta_color="inverse")
c3.metric("ADF p-value", f"{adf_p:.4f}" if adf_p is not None else "N/A")
c4.metric("Correlation", f"{corr.iloc[-1]:.4f}")

# Layout: Tabs
tab1, tab2, tab3 = st.tabs(["Charts", "Data", "Alerts"])

with tab1:
    # Row 1: Prices
    fig_price = make_subplots(specs=[[{"secondary_y": True}]])
    fig_price.add_trace(go.Scatter(x=df_y.index, y=df_y['close'], name=symbol_y), secondary_y=False)
    fig_price.add_trace(go.Scatter(x=df_x.index, y=df_x['close'], name=symbol_x), secondary_y=True)
    fig_price.update_layout(title="Price Comparison", height=400)
    st.plotly_chart(fig_price, use_container_width=True, key='price_chart')
    
    # Row 2: Spread & Z-Score
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        fig_spread = go.Figure()
        fig_spread.add_trace(go.Scatter(x=spread.index, y=spread, name="Spread", line=dict(color='orange')))
        fig_spread.add_trace(go.Scatter(x=spread.index, y=spread.rolling(window_size).mean(), name="Mean", line=dict(dash='dash')))
        fig_spread.update_layout(title="Spread (Y - beta*X)", height=350)
        st.plotly_chart(fig_spread, use_container_width=True, key='spread_chart')

    with col_chart2:
        fig_z = go.Figure()
        fig_z.add_trace(go.Scatter(x=zscore.index, y=zscore, name="Z-Score", line=dict(color='purple')))
        fig_z.add_hline(y=zscore_threshold, line_dash="dash", line_color="red")
        fig_z.add_hline(y=-zscore_threshold, line_dash="dash", line_color="red")
        fig_z.add_hline(y=0, line_color="gray")
        fig_z.update_layout(title="Z-Score", height=350)
        st.plotly_chart(fig_z, use_container_width=True, key='zscore_chart')

with tab2:
    st.dataframe(pd.concat([df_y['close'].rename(f'{symbol_y}_close'), 
                            df_x['close'].rename(f'{symbol_x}_close'), 
                            spread.rename('spread'), 
                            zscore.rename('zscore')], axis=1).sort_index(ascending=False))
    
    csv = pd.concat([df_y['close'].rename(f'{symbol_y}_close'), 
                     df_x['close'].rename(f'{symbol_x}_close'), 
                     spread.rename('spread'), 
                     zscore.rename('zscore')], axis=1).to_csv()
    st.download_button("Download Data CSV", csv, "analytics.csv", "text/csv")

with tab3:
    current_z = zscore.iloc[-1]
    if abs(current_z) > zscore_threshold:
        st.error(f"ALERT: Z-Score Threshold Breached! Current: {current_z:.2f}")
    else:
        st.success("No active alerts. Z-Score within limits.")

# Auto-Refresh
time.sleep(refresh_rate)
st.rerun()
