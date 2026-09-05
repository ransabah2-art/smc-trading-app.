import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3

# 1. Page Configuration
st.set_page_config(
    page_title="Institutional SMC Terminal v2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Database Initialization (SQLite Persistence)
DB_FILE = "journal_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            direction TEXT,
            entry REAL,
            sl REAL,
            tp1 REAL,
            tp2 REAL,
            tp3 REAL,
            risk_usd REAL,
            status TEXT,
            pnl_usd REAL
        )
    ''')
    conn.commit()
    conn.close()

def load_trades():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()
    return df.to_dict('records')

def save_trade(trade):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades (timestamp, symbol, direction, entry, sl, tp1, tp2, tp3, risk_usd, status, pnl_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (trade['timestamp'], trade['symbol'], trade['direction'], trade['entry'], 
          trade['sl'], trade['tp1'], trade['tp2'], trade['tp3'], trade['risk_usd'], 
          trade['status'], trade['pnl_usd']))
    conn.commit()
    conn.close()

def update_trade_status(trade_id, status, pnl_usd):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE trades SET status = ?, pnl_usd = ? WHERE id = ?', (status, pnl_usd, trade_id))
    conn.commit()
    conn.close()

init_db()

# 3. Session State
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 1000.0
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 1000.0

st.session_state.trade_journal = load_trades()

def navigate_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()

# 4. Mobile-Responsive & RTL Fixed CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] { 
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stApp { 
        background: #06080D; 
        color: #E2E8F0; 
    }

    /* תיקון עיצוב הכרטיסיות והכותרות */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(16, 24, 38, 0.9) 0%, rgba(10, 15, 26, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        direction: rtl;
        text-align: right;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.88rem !important;
        color: #94A3B8 !important;
        direction: rtl !important;
        text-align: right !important;
        justify-content: flex-start !important;
    }
    
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.25rem !important;
        white-space: nowrap !important;
        direction: ltr !important;
        text-align: right !important;
    }

    [data-testid="stMetricDelta"] {
        direction: ltr !important;
    }

    .top-status-bar {
        background: rgba(14, 20, 32, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px 16px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        direction: ltr;
    }

    .status-dot {
        height: 10px; width: 10px;
        background-color: #00E676;
        border-radius: 50%; display: inline-block;
        box-shadow: 0 0 8px #00E676;
    }

    .trade-level-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
        padding: 12px; margin-top: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        direction: rtl;
    }

    @media (max-width: 768px) {
        .top-status-bar { flex-direction: column; align-items: flex-start; gap: 6px; }
    }
</style>
""", unsafe_allow_html=True)

# 5. Data Engine
@st.cache_data(ttl=10)
def fetch_klines(symbol="ETHUSDT", interval="1h", limit=120):
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # MEXC
    try:
        tf_mexc = {"15m": "15m", "1h": "60m", "4h": "4h"}.get(interval, "60m")
        url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval={tf_mexc}&limit={limit}"
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200 and len(res.json()) > 0:
            df = pd.DataFrame(res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct', 'av', 'tr', 'tb', 'tq', 'ig'])
            for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = df[col].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df, "MEXC_LIVE"
    except Exception: pass

    # Binance Mirror
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200 and len(res.json()) > 0:
            df = pd.DataFrame(res.json(), columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'ct', 'qav', 'num', 'tb', 'tq', 'ig'])
            for col in ['open', 'high', 'low', 'close', 'volume']: df[col] = df[col].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df, "BINANCE_LIVE"
    except Exception: pass

    # Fallback
    dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=interval.replace('m', 'min'))
    base_price = 2474.0 if "ETH" in symbol else (79000.0 if "BTC" in symbol else 103.0)
    returns = np.random.normal(0.0001, 0.003, size=limit)
    price_path = base_price * np.exp(np.cumsum(returns))
    df = pd.DataFrame({'timestamp': dates, 'open': price_path * 1.001, 'high': price_path * 1.002, 'low': price_path * 0.998, 'close': price_path, 'volume': np.random.uniform(500, 3000, limit)})
    return df, "FALLBACK_STATIC"

@st.cache_data(ttl=15)
def fetch_open_interest(symbol="ETHUSDT"):
    try:
        url = f"https://api.bybit.com/v5/market/open-interest?category=linear&symbol={symbol}&intervalTime=5min&limit=1"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        if res.status_code == 200 and res.json()['result']['list']:
            return float(res.json()['result']['list'][0]['openInterest'])
    except Exception: pass
    return 124500.0

# 6. Advanced SMC Engine + FVG / Order Block Detection
def analyze_smc_advanced(df, df_4h=None):
    if df is None or len(df) < 30: return None
    
    close = df['close'].iloc[-1]
    range_high, range_low = df['high'].iloc[-50:].max(), df['low'].iloc[-50:].min()
    eq = (range_high + range_low) / 2
    
    is_discount = close < eq
    prev_low = df['low'].iloc[-25:-1].min()
    bull_sweep = df['low'].iloc[-1] < prev_low and close > prev_low

    htf_bias = "BULLISH" if df_4h is not None and df_4h['close'].iloc[-1] > df_4h['close'].iloc[-20] else "BEARISH"

    score = 50
    confluences = []
    
    if is_discount: score += 15; confluences.append("Discount Zone")
    if bull_sweep: score += 20; confluences.append("Liquidity Sweep")
    if htf_bias == "BULLISH": score += 15; confluences.append("4h Trend Alignment")

    # Detect FVG (Fair Value Gaps)
    fvgs = []
    for i in range(2, len(df)-1):
        if df['low'].iloc[i] > df['high'].iloc[i-2]: 
            fvgs.append({'type': 'BULLISH', 'top': df['low'].iloc[i], 'bottom': df['high'].iloc[i-2], 'time': df['timestamp'].iloc[i]})
        elif df['high'].iloc[i] < df['low'].iloc[i-2]:
            fvgs.append({'type': 'BEARISH', 'top': df['low'].iloc[i-2], 'bottom': df['high'].iloc[i], 'time': df['timestamp'].iloc[i]})

    # Detect Order Blocks
    obs = []
    for i in range(10, len(df)-2):
        if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['high'].iloc[i]:
            obs.append({'type': 'BULL_OB', 'high': df['high'].iloc[i], 'low': df['low'].iloc[i], 'time': df['timestamp'].iloc[i]})

    direction = "BUY (LONG) 🟢" if score >= 65 else "NEUTRAL ⏳"

    if "BUY" in direction:
        sl = min(df['low'].iloc[-5:].min(), close * 0.993)
        risk = close - sl
        tp1, tp2, tp3 = close + (risk * 1.5), close + (risk * 2.8), close + (risk * 4.5)
    else:
        sl = max(df['high'].iloc[-5:].max(), close * 1.007)
        risk = sl - close
        tp1, tp2, tp3 = close - (risk * 1.5), close - (risk * 2.8), close - (risk * 4.5)

    rr = round(abs(tp2 - close) / max(abs(close - sl), 1e-6), 2)

    return {
        'direction': direction, 'is_confirmed': score >= 65, 'entry': close,
        'sl': sl, 'tp1': tp1, 'tp2': tp2, 'tp3': tp3, 'rr': rr, 'score': score,
        'htf_bias': htf_bias, 'confluences': confluences, 'fvgs': fvgs[-3:], 'obs': obs[-2:]
    }

# 7. Sidebar Controls
st.sidebar.title("⚡ הגדרות מסחר")
symbol = st.sidebar.selectbox("נכס ראשי", ["ETHUSDT", "BTCUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן", ["15m", "1h", "4h"], index=1)

if st.sidebar.button("🔄 רענן נתונים"):
    st.cache_data.clear()
    st.rerun()

df, data_source = fetch_klines(symbol, timeframe)
df_4h, _ = fetch_klines(symbol, "4h")
oi_val = fetch_open_interest(symbol)
res = analyze_smc_advanced(df, df_4h)

# Top Bar
status_color = "#00E676" if "LIVE" in data_source else "#FFD600"
st.markdown(f"""
<div class="top-status-bar">
    <div>
        <span class="status-dot" style="background-color:{status_color};"></span>
        <strong style="color: #00E676; font-family: 'JetBrains Mono';">INSTITUTIONAL TERMINAL v2.0</strong>
        <span style="color: #00E5FF; font-size: 0.75rem;"> [{data_source}]</span>
    </div>
    <div style="font-family: 'JetBrains Mono'; font-size: 0.85rem;">
        OI: <strong style="color:#00E5FF;">{oi_val:,.0f}</strong> | Equity: <strong style="color:#00E676;">${st.session_state.account_balance:,.2f}</strong>
    </div>
</div>
""", unsafe_allow_html=True)

current_page = st.session_state.current_page

# =========================================================================
# PAGE 1: MAIN EXECUTIVE DASHBOARD
# =========================================================================
if current_page == 'main':
    closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']
    total_pnl = sum([t['pnl_usd'] for t in closed_trades])
    wins = len([t for t in closed_trades if t['pnl_usd'] > 0])
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("שווי תיק (PnL)", f"${st.session_state.account_balance:,.2f}", f"{total_pnl:+,.2f}$")
        if st.button("ביצועים ➔", key="btn_perf", use_container_width=True): navigate_to('performance')

    with c2:
        st.metric("אחוז הצלחה", f"{win_rate:.0f}%", f"{wins}/{len(closed_trades)} עסקאות")
        if st.button("יומן מלא ➔", key="btn_journal", use_container_width=True): navigate_to('journal')

    with c3:
        st.metric("איתות SMC", res['direction'], f"ציון: {res['score']}/100")
        if st.button("Order Flow ➔", key="btn_sig", use_container_width=True): navigate_to('signal_details')

    with c4:
        st.metric("מחשבון סיכון", "1.0% Risk", f"HTF: {res['htf_bias']}")
        if st.button("סימולטור ➔", key="btn_risk", use_container_width=True): navigate_to('risk_details')

    st.markdown("<br>", unsafe_allow_html=True)

    # Market Screener Section
    with st.expander("🔍 סורק שוק אוטומטי (SMC Multi-Asset Screener)", expanded=False):
        screener_symbols = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT"]
        screener_data = []
        for sym in screener_symbols:
            s_df, _ = fetch_klines(sym, "1h", 60)
            s_res = analyze_smc_advanced(s_df)
            if s_res:
                screener_data.append({
                    "נכס": sym,
                    "מחיר": f"${s_res['entry']:,.2f}",
                    "כיוון": s_res['direction'],
                    "ציון SMC": f"{s_res['score']}/100",
                    "מגמת HTF": s_res['htf_bias']
                })
        st.dataframe(pd.DataFrame(screener_data), use_container_width=True)

    col_chart, col_quick_trade = st.columns([2.5, 1.5])

    with col_chart:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
        fig.add_trace(go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00E676', decreasing_line_color='#FF1744'
        ), row=1, col=1)

        for ob in res['obs']:
            fig.add_hrect(y0=ob['low'], y1=ob['high'], fillcolor="rgba(0, 229, 255, 0.15)", line_width=1, line_color="#00E5FF", row=1, col=1)

        for fvg in res['fvgs']:
            color = "rgba(0, 230, 118, 0.2)" if fvg['type'] == 'BULLISH' else "rgba(255, 23, 68, 0.2)"
            fig.add_hrect(y0=fvg['bottom'], y1=fvg['top'], fillcolor=color, line_width=0, row=1, col=1)

        fig.add_trace(go.Bar(
            x=df['timestamp'], y=df['volume'],
            marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 23, 68, 0.3)')
        ), row=2, col=1)

        fig.add_hline(y=res['entry'], line_dash="dash", line_color="#00E5FF", annotation_text="Entry", row=1, col=1)
        fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF1744", annotation_text="SL", row=1, col=1)
        fig.add_hline(y=res['tp1'], line_dash="dot", line_color="#00E676", annotation_text="TP1", row=1, col=1)

        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=420, showlegend=False, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)

    with col_quick_trade:
        st.markdown("<h4 style='text-align: right; direction: rtl;'>🎯 פרטי עסקה ורמות יעד</h4>", unsafe_allow_html=True)
        risk_usd = st.session_state.account_balance * 0.01

        st.markdown(f"""
        <div class="trade-level-box">
            <div style="display:flex; justify-content:space-between;"><span>נכס:</span><strong>{symbol}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>כניסה:</span><strong style="color:#00E5FF;">${res['entry']:,.2f}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>סטופ לוס:</span><strong style="color:#FF1744;">${res['sl']:,.2f}</strong></div>
            <hr style="border-color: rgba(255,255,255,0.08); margin: 6px 0;">
            <div style="display:flex; justify-content:space-between;"><span>יעד 1 (TP1):</span><strong style="color:#00E676;">${res['tp1']:,.2f}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>יעד 2 (TP2):</span><strong style="color:#00E676;">${res['tp2']:,.2f}</strong></div>
            <div style="display:flex; justify-content:space-between;"><span>יחס R:R:</span><strong style="color:#00E5FF;">1:{res['rr']}</strong></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if res['is_confirmed']:
            if st.button("🚀 כניסה לעסקה (שמירה ב-DB)", type="primary", use_container_width=True):
                trade = {
                    'timestamp': datetime.now().strftime("%d/%m %H:%M"),
                    'symbol': symbol, 'direction': res['direction'], 'entry': res['entry'],
                    'sl': res['sl'], 'tp1': res['tp1'], 'tp2': res['tp2'], 'tp3': res['tp3'],
                    'risk_usd': risk_usd, 'status': 'ACTIVE', 'pnl_usd': 0.0
                }
                save_trade(trade)
                st.session_state.trade_journal = load_trades()
                st.success("העסקה נרשמה ב-SQLite!")
                st.rerun()
        else:
            st.button("ממתין לאישור איתות SMC...", disabled=True, use_container_width=True)

# =========================================================================
# OTHER PAGES
# =========================================================================
elif current_page == 'performance':
    if st.button("🔙 חזרה לטרמינל"): navigate_to('main')
    st.markdown("### 📊 אנליטיקת ביצועים (מתוך SQLite DB)")
    st.dataframe(pd.DataFrame(st.session_state.trade_journal), use_container_width=True)

elif current_page == 'signal_details':
    if st.button("🔙 חזרה לטרמינל"): navigate_to('main')
    st.markdown("### 🔬 פירוט FVG ו-Order Blocks")
    st.write("Order Blocks פעילים:", res['obs'])
    st.write("Fair Value Gaps שנמצאו:", res['fvgs'])

elif current_page == 'journal':
    if st.button("🔙 חזרה לטרמינל"): navigate_to('main')
    st.markdown("### 📖 יומן עסקאות קבוע")
    trades = st.session_state.trade_journal
    for t in trades:
        if t['status'] == 'ACTIVE':
            col1, col2 = st.columns([3, 1])
            col1.write(f"#{t['id']} {t['symbol']} | Entry: ${t['entry']:,.2f}")
            if col2.button("סגור ב-TP2", key=f"close_{t['id']}"):
                pnl = t['risk_usd'] * 2.8
                update_trade_status(t['id'], 'CLOSED', pnl)
                st.session_state.account_balance += pnl
                st.session_state.trade_journal = load_trades()
                st.rerun()
    st.dataframe(pd.DataFrame(trades), use_container_width=True)

elif current_page == 'risk_details':
    if st.button("🔙 חזרה לטרמינל"): navigate_to('main')
    st.markdown("### 🧮 סימולטור ניהול סיכונים")
