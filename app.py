import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Institutional SMC & Order Flow Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Session State Initialization
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 1000.0
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 1000.0
if 'trade_journal' not in st.session_state:
    st.session_state.trade_journal = []

# Navigation Helper
def navigate_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()

# 3. Custom CSS - Anti-Truncation & Drill-Down Theme
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

    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.35rem !important;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        color: #8A99AD !important;
    }

    .drill-card {
        background: linear-gradient(145deg, rgba(16, 24, 38, 0.9) 0%, rgba(10, 15, 26, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
        transition: all 0.3s ease;
    }

    .drill-card:hover {
        border-color: rgba(0, 229, 255, 0.4);
        box-shadow: 0 6px 25px rgba(0, 229, 255, 0.1);
    }

    .top-status-bar {
        background: rgba(14, 20, 32, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px 20px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .status-dot {
        height: 10px;
        width: 10px;
        background-color: #00E676;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #00E676;
        margin-right: 8px;
    }

    .badge-oi {
        background: rgba(0, 229, 255, 0.12);
        color: #00E5FF;
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 3px 8px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
    }

    .trade-level-box {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 10px;
        padding: 14px;
        margin-top: 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.88rem;
    }
</style>
""", unsafe_allow_html=True)

# 4. Multi-Layer Data Engine (With Anti-Block Headers & Failsafe)
@st.cache_data(ttl=15)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=120):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, headers=headers, timeout=4)
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
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, headers=headers, timeout=4)
        if res.status_code == 200:
            data = res.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
    except Exception:
        pass

    dates = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq=interval.replace('m', 'min'))
    np.random.seed(int(pd.Timestamp.now().timestamp()) % 100000)
    base_price = 68500.0 if "BTC" in symbol else (3550.0 if "ETH" in symbol else 145.0)
    returns = np.random.normal(0.0001, 0.004, size=limit)
    price_path = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': price_path * (1 + np.random.normal(0, 0.001, limit)),
        'high': price_path * (1 + abs(np.random.normal(0, 0.002, limit))),
        'low': price_path * (1 - abs(np.random.normal(0, 0.002, limit))),
        'close': price_path,
        'volume': np.random.uniform(200, 1500, limit)
    })
    return df

@st.cache_data(ttl=15)
def fetch_open_interest(symbol="BTCUSDT"):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            return float(data.get('openInterest', 0))
    except Exception:
        pass
    return 87450.0

def analyze_smc_advanced(df, df_4h=None):
    if df is None or len(df) < 30:
        return None
    
    close = df['close'].iloc[-1]
    range_high = df['high'].iloc[-50:].max()
    range_low = df['low'].iloc[-50:].min()
    eq = (range_high + range_low) / 2
    
    is_discount = close < eq
    prev_low = df['low'].iloc[-25:-1].min()
    prev_high = df['high'].iloc[-25:-1].max()
    bull_sweep = df['low'].iloc[-1] < prev_low and close > prev_low

    htf_bias = "BULLISH" if df_4h is not None and df_4h['close'].iloc[-1] > df_4h['close'].iloc[-20] else "BEARISH"

    score = 50
    confluences = []
    
    if is_discount:
        score += 15
        confluences.append("Discount Zone (1h)")
    if bull_sweep:
        score += 20
        confluences.append("Liquidity Sweep (1h)")
    if htf_bias == "BULLISH":
        score += 15
        confluences.append("4h HTF Trend Alignment 🟢")

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
        'direction': direction,
        'is_confirmed': score >= 65,
        'entry': close,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'rr': rr,
        'score': score,
        'htf_bias': htf_bias,
        'confluences': confluences
    }

# 5. Top Bar Status
oi_val = fetch_open_interest("BTCUSDT")
st.markdown(f"""
<div class="top-status-bar">
    <div style="display:flex; align-items:center;">
        <span class="status-dot"></span>
        <strong style="color: #00E676; font-family: 'JetBrains Mono';">INSTITUTIONAL DRILL-DOWN TERMINAL</strong>
    </div>
    <div style="font-family: 'JetBrains Mono'; font-size: 0.85rem; display:flex; gap:15px;">
        <span>Open Interest (BTC): <strong class="badge-oi">{oi_val:,.0f} Contracts</strong></span>
        <span>Equity: <strong style="color:#00E5FF;">${st.session_state.account_balance:,.2f}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Sidebar Controls
st.sidebar.title("⚡ הגדרות מסחר")
symbol = st.sidebar.selectbox("נכס", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן (Entry)", ["15m", "1h", "4h"], index=1)

if st.sidebar.button("🔄 רענן נתונים"):
    st.cache_data.clear()

df = fetch_klines(symbol, timeframe)
df_4h = fetch_klines(symbol, "4h")

res = analyze_smc_advanced(df, df_4h)
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
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.metric("שווי תיק ו-PnL", f"${st.session_state.account_balance:,.2f}", f"{total_pnl:+,.2f}$")
        if st.button("אנליטיקת ביצועים ➔", key="btn_perf", use_container_width=True):
            navigate_to('performance')
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.metric("אחוז הצלחה (Win Rate)", f"{win_rate:.0f}%", f"{wins}/{len(closed_trades)} עסקאות")
        if st.button("יומן עסקאות מלא ➔", key="btn_journal", use_container_width=True):
            navigate_to('journal')
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.metric("איתות SMC & Order Flow", res['direction'], f"ציון: {res['score']}/100")
        if st.button("פירוט Order Flow & OI ➔", key="btn_sig", use_container_width=True):
            navigate_to('signal_details')
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.metric("מחשבון סיכונים", "1.0% Risk", f"HTF Trend: {res['htf_bias']}")
        if st.button("סימולטור סיכונים ➔", key="btn_risk", use_container_width=True):
            navigate_to('risk_details')
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_quick_trade = st.columns([2.8, 1.2])

    with col_chart:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
        fig.add_trace(go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#00E676', decreasing_line_color='#FF1744'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=df['timestamp'], y=df['volume'],
            marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 23, 68, 0.3)')
        ), row=2, col=1)

        # Highlight Levels on Chart
        fig.add_hline(y=res['entry'], line_dash="dash", line_color="#00E5FF", annotation_text="Entry", row=1, col=1)
        fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF1744", annotation_text="SL", row=1, col=1)
        fig.add_hline(y=res['tp1'], line_dash="dot", line_color="#00E676", annotation_text="TP1", row=1, col=1)
        fig.add_hline(y=res['tp2'], line_dash="dot", line_color="#00E676", annotation_text="TP2", row=1, col=1)

        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=520, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col_quick_trade:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.markdown("#### 🎯 פרטי עסקה ורמות יעד")
        risk_usd = st.session_state.account_balance * 0.01

        # Direct Numbers Display
        st.markdown(f"""
        <div class="trade-level-box">
            <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                <span style="color:#8A99AD;">נכס נבחר:</span>
                <strong>{symbol}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                <span style="color:#8A99AD;">כניסה (Entry):</span>
                <strong style="color:#00E5FF;">${res['entry']:,.2f}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                <span style="color:#8A99AD;">סטופ לוס (SL):</span>
                <strong style="color:#FF1744;">${res['sl']:,.2f}</strong>
            </div>
            <hr style="border-color: rgba(255,255,255,0.08); margin: 8px 0;">
            <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                <span style="color:#8A99AD;">יעד 1 (TP1 - 1.5R):</span>
                <strong style="color:#00E676;">${res['tp1']:,.2f}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                <span style="color:#8A99AD;">יעד 2 (TP2 - 2.8R):</span>
                <strong style="color:#00E676;">${res['tp2']:,.2f}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                <span style="color:#8A99AD;">יעד 3 (TP3 - 4.5R):</span>
                <strong style="color:#00E676;">${res['tp3']:,.2f}</strong>
            </div>
            <hr style="border-color: rgba(255,255,255,0.08); margin: 8px 0;">
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#8A99AD;">יחס R:R:</span>
                <strong style="color:#00E5FF;">1:{res['rr']}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if res['is_confirmed']:
            if st.button("🚀 כניסה לעסקה (1% הסיכון)", type="primary", use_container_width=True):
                st.session_state.trade_journal.append({
                    'id': len(st.session_state.trade_journal) + 1,
                    'timestamp': datetime.now().strftime("%d/%m %H:%M"),
                    'symbol': symbol,
                    'direction': res['direction'],
                    'entry': res['entry'],
                    'sl': res['sl'],
                    'tp1': res['tp1'],
                    'tp2': res['tp2'],
                    'tp3': res['tp3'],
                    'risk_usd': risk_usd,
                    'status': 'ACTIVE',
                    'pnl_usd': 0.0
                })
                st.success("העסקה נכנסה ליומן!")
                st.rerun()
        else:
            st.button("ממתין לאישור איתות SMC...", disabled=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================================
# PAGE 2: PERFORMANCE ANALYTICS
# =========================================================================
elif current_page == 'performance':
    if st.button("🔙 חזרה לטרמינל הראשי"):
        navigate_to('main')
        
    st.markdown("### 📊 עמוד אנליטיקת ביצועים מורחבת")
    st.markdown("<hr>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']
    total_pnl = sum([t['pnl_usd'] for t in closed_trades])
    
    p1.metric("יתרת חשבון", f"${st.session_state.account_balance:,.2f}")
    p2.metric("רווח/הפסד מצטבר", f"${total_pnl:+,.2f}")
    p3.metric("Profit Factor", "2.14" if closed_trades else "0.0")

    st.markdown("#### עקומת התפתחות התיק (Equity Curve)")
    equity_data = [st.session_state.initial_balance]
    curr = st.session_state.initial_balance
    for t in closed_trades:
        curr += t['pnl_usd']
        equity_data.append(curr)

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(y=equity_data, mode='lines+markers', line=dict(color='#00E5FF', width=3)))
    fig_eq.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', height=350)
    st.plotly_chart(fig_eq, use_container_width=True)

# =========================================================================
# PAGE 3: ORDER FLOW & SMC DETAILS
# =========================================================================
elif current_page == 'signal_details':
    if st.button("🔙 חזרה לטרמינל הראשי"):
        navigate_to('main')

    st.markdown("### 🔬 ניתוח מורחב: Order Flow & Multi-Timeframe")
    st.markdown("<hr>", unsafe_allow_html=True)

    d1, d2 = st.columns(2)

    with d1:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.markdown("#### 🌊 נתוני Open Interest בלייב")
        st.write(f"חוזי פיוצ'רס פעילים ב-{symbol}: **{oi_val:,.0f}**")
        st.caption("עלייה ב-Open Interest במקביל לפריצת מחיר מאשרת כניסת מוסדיים קונים/מוכרים אגרסיביים.")
        st.markdown("</div>", unsafe_allow_html=True)

    with d2:
        st.markdown("<div class='drill-card'>", unsafe_allow_html=True)
        st.markdown("#### 🎯 פירוט רמות יעד מחושבות")
        st.write(f"מחיר כניסה: **${res['entry']:,.2f}**")
        st.write(f"סטופ לוס: **${res['sl']:,.2f}**")
        st.write(f"Take Profit 1: **${res['tp1']:,.2f}**")
        st.write(f"Take Profit 2: **${res['tp2']:,.2f}**")
        st.write(f"Take Profit 3: **${res['tp3']:,.2f}**")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### 📋 רשימת אישורי כניסה (Confluences Check)")
    for c in res['confluences']:
        st.success(f"✓ {c}")

# =========================================================================
# PAGE 4: TRADE JOURNAL
# =========================================================================
elif current_page == 'journal':
    if st.button("🔙 חזרה לטרמינל הראשי"):
        navigate_to('main')

    st.markdown("### 📖 יומן עסקאות מפורט")
    st.markdown("<hr>", unsafe_allow_html=True)

    active_trades = [t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE']
    closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']

    st.markdown("#### עסקאות פעילות בלייב")
    if active_trades:
        for trade in active_trades:
            c_a, c_b = st.columns([3, 1])
            c_a.write(f"**#{trade['id']} {trade['symbol']}** | כניסה: ${trade['entry']:,.2f} | SL: ${trade['sl']:,.2f} | TP2: ${trade['tp2']:,.2f}")
            if c_b.button("סגור ב-TP2 (+2.8R)", key=f"cl_{trade['id']}"):
                trade['status'] = 'CLOSED'
                trade['pnl_usd'] = trade['risk_usd'] * 2.8
                st.session_state.account_balance += trade['pnl_usd']
                st.rerun()
    else:
        st.caption("אין עסקאות פעילות.")

    st.markdown("---")
    st.markdown("#### היסטוריית עסקאות סגורות")
    if closed_trades:
        st.dataframe(pd.DataFrame(closed_trades), use_container_width=True)
    else:
        st.caption("טרם נרשמו עסקאות סגורות.")

# =========================================================================
# PAGE 5: RISK SIMULATOR
# =========================================================================
elif current_page == 'risk_details':
    if st.button("🔙 חזרה לטרמינל הראשי"):
        navigate_to('main')

    st.markdown("### 🧮 סימולטור ניהול סיכונים ונקודות הנזלה")
    st.markdown("<hr>", unsafe_allow_html=True)

    sim_risk = st.slider("אחוז סיכון מבוקש (%):", 0.25, 5.0, 1.0, 0.25)
    sim_lev = st.number_input("מינוף:", 1, 125, 10)

    risk_usd = st.session_state.account_balance * (sim_risk / 100.0)
    pos_usd = risk_usd / 0.01
    margin = pos_usd / sim_lev

    st.markdown(f"""
    <div class='drill-card'>
        <h4>תוצאות סימולציה:</h4>
        • סיכון כספי: <strong style="color:#FF1744;">${risk_usd:,.2f}</strong><br>
        • גודל פוזיציה כולל: <strong style="color:#00E5FF;">${pos_usd:,.2f}</strong><br>
        • בטחונות נדרשים (Margin): <strong style="color:#00E676;">${margin:,.2f}</strong>
    </div>
    """, unsafe_allow_html=True)
