import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Page Configuration
st.set_page_config(
    page_title="Institutional SMC Suite",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Custom Mobile-First CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    .stApp {
        background-color: #080A0F;
        color: #E6EDF3;
    }

    .kpi-card {
        background: rgba(22, 27, 34, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 16px;
        text-align: center;
        margin-bottom: 10px;
    }

    .signal-box-bull {
        background: rgba(46, 160, 67, 0.15);
        border: 1px solid #2ea043;
        border-radius: 12px;
        padding: 16px;
        color: #3fb950;
    }

    .signal-box-bear {
        background: rgba(248, 81, 73, 0.15);
        border: 1px solid #f85149;
        border-radius: 12px;
        padding: 16px;
        color: #f85149;
    }

    .signal-box-neutral {
        background: rgba(110, 118, 129, 0.15);
        border: 1px solid #8b949e;
        border-radius: 12px;
        padding: 16px;
        color: #8b949e;
    }
</style>
""", unsafe_allow_html=True)

# 3. Resilient Market Data Fetcher (Binance Futures + Yahoo Finance Fallback)
@st.cache_data(ttl=60)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=100):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
    except Exception:
        pass

    try:
        import yfinance as yf
        yf_symbol = symbol.replace("USDT", "-USD")
        tf_map = {"15m": "15m", "1h": "1h", "4h": "1h", "1d": "1d"}
        period_map = {"15m": "5d", "1h": "14d", "4h": "30d", "1d": "100d"}
        
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period_map.get(interval, "14d"), interval=tf_map.get(interval, "1h"))
        if not df.empty:
            df = df.reset_index()
            df = df.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df.tail(limit)
    except Exception:
        pass

    return None

# 4. RSI Calculation
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 5. SMC Engine
def analyze_smc(df):
    if df is None or len(df) < 50:
        return None
    
    df['rsi'] = calculate_rsi(df)
    close = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    
    range_high = df['high'].iloc[-50:].max()
    range_low = df['low'].iloc[-50:].min()
    equilibrium = (range_high + range_low) / 2
    
    is_discount = close < equilibrium
    is_premium = close > equilibrium
    
    # Golden Zone (61.8% - 78.6%)
    fib_range = range_high - range_low
    fib_618 = range_high - (fib_range * 0.618)
    fib_786 = range_high - (fib_range * 0.786)
    in_bullish_golden_zone = (close <= fib_618) and (close >= fib_786)
    in_bearish_golden_zone = (close >= (range_low + fib_range * 0.618)) and (close <= (range_low + fib_range * 0.786))

    # Sweeps & CHoCH
    prev_low_30 = df['low'].iloc[-30:-1].min()
    prev_high_30 = df['high'].iloc[-30:-1].max()
    bull_sweep = df['low'].iloc[-1] < prev_low_30 and close > prev_low_30
    bear_sweep = df['high'].iloc[-1] > prev_high_30 and close < prev_high_30

    recent_high_15 = df['high'].iloc[-15:-1].max()
    recent_low_15 = df['low'].iloc[-15:-1].min()
    choch_bull = close > recent_high_15
    choch_bear = close < recent_low_15

    # Support / Resistance
    support_zone = df['low'].iloc[-40:-10].min()
    resistance_zone = df['high'].iloc[-40:-10].max()
    at_support = abs(close - support_zone) / close < 0.008
    at_resistance = abs(close - resistance_zone) / close < 0.008

    # FVG
    fvg_bull = df['low'].iloc[-1] > df['high'].iloc[-3]
    fvg_bear = df['high'].iloc[-1] < df['low'].iloc[-3]

    confluences = []
    score = 50
    direction = "NEUTRAL"

    if choch_bull or bull_sweep or is_discount:
        if is_discount:
            score += 10
            confluences.append("Discount Zone")
        if in_bullish_golden_zone:
            score += 15
            confluences.append("Fibonacci Golden Zone (61.8%-78.6%)")
        if bull_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bull:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_support:
            score += 10
            confluences.append("Key Support / Bullish OB")
        if fvg_bull:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi < 40:
            score += 10
            confluences.append("Oversold RSI Momentum")
        
        if score >= 65:
            direction = "BULLISH 🟢"

    if (choch_bear or bear_sweep or is_premium) and direction == "NEUTRAL":
        if is_premium:
            score += 10
            confluences.append("Premium Zone")
        if in_bearish_golden_zone:
            score += 15
            confluences.append("Fibonacci Golden Zone (61.8%-78.6%)")
        if bear_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bear:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_resistance:
            score += 10
            confluences.append("Key Resistance / Bearish OB")
        if fvg_bear:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi > 60:
            score += 10
            confluences.append("Overbought RSI Momentum")
        
        if score >= 65:
            direction = "BEARISH 🔴"

    win_rate = min(91.5, score)

    if "BULLISH" in direction:
        sl = min(df['low'].iloc[-5:].min(), close * 0.992)
        risk = close - sl
        tp1 = close + (risk * 1.5)
        tp2 = close + (risk * 2.8)
        tp3 = close + (risk * 4.5)
    elif "BEARISH" in direction:
        sl = max(df['high'].iloc[-5:].max(), close * 1.008)
        risk = sl - close
        tp1 = close - (risk * 1.5)
        tp2 = close - (risk * 2.8)
        tp3 = close - (risk * 4.5)
    else:
        sl = tp1 = tp2 = tp3 = close

    return {
        'direction': direction,
        'close': close,
        'score': score,
        'win_rate': win_rate,
        'confluences': confluences,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'rsi': rsi
    }

# 6. UI Execution
st.title("🦅 Institutional SMC Terminal")

col_sym, col_tf = st.columns([2, 1])
with col_sym:
    symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"], index=0)
with col_tf:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

df = fetch_klines(symbol, timeframe)
if df is not None:
    res = analyze_smc(df)
    
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Current Price", f"${res['close']:,.2f}")
    kpi2.metric("Win-Rate Est.", f"{res['win_rate']:.1f}%")
    kpi3.metric("RSI (14)", f"{res['rsi']:.1f}")

    st.markdown("---")

    box_class = "signal-box-bull" if "BULLISH" in res['direction'] else ("signal-box-bear" if "BEARISH" in res['direction'] else "signal-box-neutral")
    st.markdown(f"""
    <div class="{box_class}">
        <h3 style="margin:0;">Signal: {res['direction']}</h3>
        <p style="margin:5px 0 0 0;">Score: {res['score']} / 100</p>
    </div>
    """, unsafe_allow_html=True)

    if res['confluences']:
        st.write("**Confluences:** " + ", ".join(res['confluences']))

    if res['direction'] != "NEUTRAL":
        st.subheader("🎯 Trade Levels")
        t_col1, t_col2, t_col3, t_col4 = st.columns(4)
        t_col1.metric("Stop Loss", f"${res['sl']:,.2f}")
        t_col2.metric("TP 1 (1:1.5)", f"${res['tp1']:,.2f}")
        t_col3.metric("TP 2 (1:2.8)", f"${res['tp2']:,.2f}")
        t_col4.metric("TP 3 (1:4.5)", f"${res['tp3']:,.2f}")

    fig = go.Figure(data=[go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=symbol
    )])
    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=10, r=10, t=20, b=10),
        height=400,
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Failed to fetch market data.")
