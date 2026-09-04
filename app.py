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

# 2. Custom Mobile-First Glassmorphic CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at 50% -20%, #1a1e29, #080a0f 80%);
        color: #E6EDF3;
    }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(22, 27, 34, 0.65);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Signal Indicators */
    .signal-bull {
        background: linear-gradient(135deg, rgba(46, 160, 67, 0.2) 0%, rgba(46, 160, 67, 0.05) 100%);
        border: 1px solid #3fb950;
        box-shadow: 0 0 15px rgba(63, 185, 80, 0.2);
        border-radius: 14px;
        padding: 18px;
        color: #3fb950;
    }

    .signal-bear {
        background: linear-gradient(135deg, rgba(248, 81, 73, 0.2) 0%, rgba(248, 81, 73, 0.05) 100%);
        border: 1px solid #f85149;
        box-shadow: 0 0 15px rgba(248, 81, 73, 0.2);
        border-radius: 14px;
        padding: 18px;
        color: #f85149;
    }

    .signal-neutral {
        background: linear-gradient(135deg, rgba(110, 118, 129, 0.2) 0%, rgba(110, 118, 129, 0.05) 100%);
        border: 1px solid #8b949e;
        border-radius: 14px;
        padding: 18px;
        color: #8b949e;
    }

    /* Confluence Badge Pills */
    .conf-badge {
        display: inline-block;
        background: rgba(56, 139, 253, 0.15);
        border: 1px solid rgba(56, 139, 253, 0.4);
        color: #58a6ff;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        margin: 3px 4px 3px 0;
    }

    /* Streamlit Tabs Styling Override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(13, 17, 23, 0.8);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 8px;
        color: #8b949e;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Market Data Fetcher
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

# 4. Indicators & SMC Engine
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

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
    
    # Golden Zone
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
            confluences.append("Oversold RSI")
        
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
            confluences.append("Overbought RSI")
        
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

# 5. Application Header & Navigation
st.markdown("<h2 style='text-align: center; font-weight: 800; letter-spacing: -0.5px;'>🦅 INSTITUTIONAL SMC TERMINAL</h2>", unsafe_allow_html=True)

col_sym, col_tf = st.columns([2, 1])
with col_sym:
    symbol = st.selectbox("Market Asset", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"], index=0)
with col_tf:
    timeframe = st.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)

df = fetch_klines(symbol, timeframe)

if df is not None:
    res = analyze_smc(df)

    # Top KPI Bar
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Current Price", f"${res['close']:,.2f}")
    k2.metric("Signal Score", f"{res['score']}/100")
    k3.metric("Est. Win Rate", f"{res['win_rate']:.1f}%")
    k4.metric("RSI (14)", f"{res['rsi']:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Navigation Tabs
    tab_terminal, tab_calculator = st.tabs(["📊 Trading Dashboard", "🧮 Position Size Calculator"])

    # ---------------- TAB 1: TRADING DASHBOARD ----------------
    with tab_terminal:
        # Signal Card
        box_style = "signal-bull" if "BULLISH" in res['direction'] else ("signal-bear" if "BEARISH" in res['direction'] else "signal-neutral")
        
        badges_html = "".join([f'<span class="conf-badge">{c}</span>' for c in res['confluences']]) if res['confluences'] else "<span style='color:#8b949e;'>No active confluence triggers</span>"
        
        st.markdown(f"""
        <div class="{box_style}">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin:0; font-weight:700;">Signal: {res['direction']}</h3>
                <span style="font-size: 0.9rem; font-weight:600; opacity:0.8;">{symbol} • {timeframe}</span>
            </div>
            <div style="margin-top: 10px;">
                {badges_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Trade Levels Metrics
        if res['direction'] != "NEUTRAL":
            st.markdown("#### 🎯 Execution Plan & Trade Levels")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Stop Loss (SL)", f"${res['sl']:,.2f}")
            t2.metric("Target 1 (1:1.5)", f"${res['tp1']:,.2f}")
            t3.metric("Target 2 (1:2.8)", f"${res['tp2']:,.2f}")
            t4.metric("Target 3 (1:4.5)", f"${res['tp3']:,.2f}")

        # Candlestick Chart with Level Overlays
        fig = go.Figure(data=[go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=symbol,
            increasing_line_color='#2ea043',
            decreasing_line_color='#f85149'
        )])

        # Draw Trade Lines on Chart if Signal Active
        if res['direction'] != "NEUTRAL":
            fig.add_hline(y=res['close'], line_dash="dash", line_color="#58a6ff", annotation_text="ENTRY", annotation_position="top left")
            fig.add_hline(y=res['sl'], line_dash="solid", line_color="#f85149", annotation_text="SL", annotation_position="bottom left")
            fig.add_hline(y=res['tp1'], line_dash="dot", line_color="#3fb950", annotation_text="TP1", annotation_position="top right")
            fig.add_hline(y=res['tp2'], line_dash="dot", line_color="#2ea043", annotation_text="TP2", annotation_position="top right")
            fig.add_hline(y=res['tp3'], line_dash="dot", line_color="#238636", annotation_text="TP3", annotation_position="top right")

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=20, b=10),
            height=430,
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- TAB 2: POSITION CALCULATOR ----------------
    with tab_calculator:
        st.markdown("### 🧮 Institutional Risk & Position Sizer")
        st.caption("Calculates exact contract size based on account capital, risk tolerance, and trade levels.")

        c_col1, c_col2 = st.columns([1, 1])

        with c_col1:
            account_balance = st.number_input("Account Balance ($)", min_value=10.0, value=10000.0, step=500.0)
            risk_percent = st.slider("Risk Tolerance per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            leverage = st.number_input("Leverage (x)", min_value=1, max_value=125, value=10)

        with c_col2:
            entry_p = st.number_input("Entry Price ($)", min_value=0.0001, value=float(res['close']), format="%.4f")
            sl_p = st.number_input("Stop Loss Price ($)", min_value=0.0001, value=float(res['sl']), format="%.4f")

        # Calculations
        risk_amount_usd = account_balance * (risk_percent / 100.0)
        price_risk_percent = abs(entry_p - sl_p) / entry_p if entry_p > 0 else 0

        if price_risk_percent > 0:
            position_value_usd = risk_amount_usd / price_risk_percent
            units = position_value_usd / entry_p
            required_margin = position_value_usd / leverage
        else:
            position_value_usd = units = required_margin = 0.0

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📐 Calculated Risk Metrics")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Max Risk ($)", f"${risk_amount_usd:,.2f}")
        m2.metric("Position Size ($)", f"${position_value_usd:,.2f}")
        m3.metric("Contract Units", f"{units:,.4f} {symbol.replace('USDT','')}")
        m4.metric("Req. Margin (Initial)", f"${required_margin:,.2f}")

        if required_margin > account_balance:
            st.warning("⚠️ Warning: Required Margin exceeds your total Account Balance. Consider increasing leverage or reducing risk %.")
        else:
            st.success(f"✅ Safe Trade Setup: You are risking exactly **${risk_amount_usd:,.2f}** ({risk_percent}% of account) with **{leverage}x** leverage.")

else:
    st.error("Failed to fetch market data.")
