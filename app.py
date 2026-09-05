import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Institutional SMC Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Session State Initialization
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 1000.0
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 1000.0
if 'trade_journal' not in st.session_state:
    st.session_state.trade_journal = []

# 3. Custom CSS - Anti-Truncation & Window Cards
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background: #07090E;
        color: #E2E8F0;
    }

    /* Fix Metric Truncation (...) */
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.25rem !important;
        white-space: nowrap !important;
        text-overflow: clip !important;
        overflow: visible !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #8A99AD !important;
    }

    /* Top Live Status Bar */
    .top-status-bar {
        background: rgba(15, 22, 35, 0.95);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 10px 18px;
        margin-bottom: 15px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .status-dot {
        height: 9px;
        width: 9px;
        background-color: #00E676;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #00E676;
        margin-right: 6px;
    }

    /* Window Cards */
    .window-card {
        background: rgba(15, 22, 35, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .signal-window-bull {
        background: linear-gradient(135deg, rgba(0, 230, 118, 0.1) 0%, rgba(15, 22, 35, 0.95) 100%);
        border: 1.5px solid #00E676;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 15px;
    }

    .signal-window-bear {
        background: linear-gradient(135deg, rgba(255, 23, 68, 0.1) 0%, rgba(15, 22, 35, 0.95) 100%);
        border: 1.5px solid #FF1744;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 15px;
    }

    .price-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        color: #00E5FF;
        background: rgba(0, 229, 255, 0.1);
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 4px 8px;
        border-radius: 6px;
        display: inline-block;
    }

    /* Styled Tabs Navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(15, 22, 35, 0.6);
        padding: 6px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        color: #8A99AD;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #00E5FF !important;
        color: #07090E !important;
    }
</style>
""", unsafe_allow_html=True)

# 4. Data Engine (Binance + Fallback)
@st.cache_data(ttl=15)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=120):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=5)
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
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="14d", interval="1h")
        if not df.empty:
            df = df.reset_index()
            df = df.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df.tail(limit)
    except Exception:
        pass

    return None

def analyze_smc(df):
    if df is None or len(df) < 30:
        return None
    
    close = df['close'].iloc[-1]
    range_high = df['high'].iloc[-50:].max()
    range_low = df['low'].iloc[-50:].min()
    equilibrium = (range_high + range_low) / 2
    
    is_discount = close < equilibrium
    is_premium = close > equilibrium

    prev_low = df['low'].iloc[-25:-1].min()
    prev_high = df['high'].iloc[-25:-1].max()
    bull_sweep = df['low'].iloc[-1] < prev_low and close > prev_low
    bear_sweep = df['high'].iloc[-1] > prev_high and close < prev_high

    score = 50
    confluences = []
    direction = "NEUTRAL"

    if is_discount:
        score += 15
        confluences.append("Discount Zone")
    if bull_sweep:
        score += 20
        confluences.append("Liquidity Sweep")
    if close > df['high'].iloc[-10:-1].max():
        score += 20
        confluences.append("CHoCH / BOS Breakout")

    if score >= 65:
        direction = "BUY (LONG) 🟢"
    elif is_premium or bear_sweep:
        score = 70
        direction = "SELL (SHORT) 🔴"
        confluences.append("Premium Zone Sweep")

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
        'confluences': confluences
    }

# 5. Top Bar Status
st.markdown(f"""
<div class="top-status-bar">
    <div>
        <span class="status-dot"></span>
        <strong style="color: #00E676; font-family: 'JetBrains Mono';">LIVE SYSTEM ONLINE</strong>
    </div>
    <div style="font-family: 'JetBrains Mono'; font-size: 0.9rem;">
        יתרת תיק: <strong style="color:#00E5FF;">${st.session_state.account_balance:,.2f}</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# 6. Sidebar Controls
st.sidebar.title("⚡ הגדרות מסחר")
symbol = st.sidebar.selectbox("נכס", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן", ["15m", "1h", "4h", "1d"], index=1)

if st.sidebar.button("🔄 רענן נתונים"):
    st.cache_data.clear()

df = fetch_klines(symbol, timeframe)

if df is not None:
    res = analyze_smc(df)

    # 7. MAIN NAVIGATION TABS (עמודים מתחלפים)
    tab_main, tab_radar, tab_journal, tab_risk = st.tabs([
        "📈 טרמינל מסחר בלייב", 
        "📡 רדאר SMC & Watchlist", 
        "📖 יומן עסקאות ואנליטיקה", 
        "🧮 מחשבון סיכונים"
    ])

    # ================= TAB 1: MAIN TERMINAL =================
    with tab_main:
        # Top KPI Cards (Full Width - No Cutoffs)
        c1, c2, c3, c4 = st.columns(4)
        closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']
        total_pnl = sum([t['pnl_usd'] for t in closed_trades])
        wins = len([t for t in closed_trades if t['pnl_usd'] > 0])
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0

        c1.metric("שווי תיק נוכחי", f"${st.session_state.account_balance:,.2f}")
        c2.metric("PnL מצטבר", f"${total_pnl:+,.2f}")
        c3.metric("אחוז הצלחה", f"{win_rate:.0f}%")
        c4.metric("עסקאות פעילות", f"{len([t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE'])}")

        st.markdown("<br>", unsafe_allow_html=True)

        col_chart, col_action = st.columns([2.8, 1.2])

        with col_chart:
            # Signal Window
            if res['is_confirmed']:
                win_class = "signal-window-bull" if "BUY" in res['direction'] else "signal-window-bear"
                st.markdown(f"""
                <div class="{win_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <h3 style="margin:0;">🎯 אישור כניסה: {res['direction']}</h3>
                        <span style="font-family:'JetBrains Mono'; background:rgba(0,0,0,0.4); padding:4px 10px; border-radius:6px;">
                            יחס סיכון/סיכוי: 1:{res['rr']}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                p1, p2, p3, p4, p5 = st.columns(5)
                p1.metric("כניסה", f"${res['entry']:,.2f}")
                p2.metric("🛑 SL", f"${res['sl']:,.2f}")
                p3.metric("🎯 TP1", f"${res['tp1']:,.2f}")
                p4.metric("🎯 TP2", f"${res['tp2']:,.2f}")
                p5.metric("🎯 TP3", f"${res['tp3']:,.2f}")
            else:
                st.info("⏳ המערכת בסריקה. ניטרלי כעת - ממתין לאיתות SMC ברמת אמינות גבוהה.")

            # Main Chart Canvas
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])
            fig.add_trace(go.Candlestick(
                x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00E676', decreasing_line_color='#FF1744'
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=df['timestamp'], y=df['volume'],
                marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 23, 68, 0.3)')
            ), row=2, col=1)

            if res['is_confirmed']:
                fig.add_hline(y=res['entry'], line_dash="dash", line_color="#00E5FF", row=1, col=1)
                fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF1744", row=1, col=1)
                fig.add_hline(y=res['tp2'], line_dash="dot", line_color="#00E676", row=1, col=1)

            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=480, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with col_action:
            st.markdown("<div class='window-card'>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#00E5FF; margin-top:0;'>⚡ ביצוע עסקה מהיר</h4>", unsafe_allow_html=True)
            
            risk_pct = st.slider("סיכון (%):", 0.25, 3.0, 1.0, 0.25)
            leverage = st.number_input("מינוף:", 1, 100, 10)
            
            risk_usd = st.session_state.account_balance * (risk_pct / 100.0)
            price_risk_pct = abs(res['entry'] - res['sl']) / res['entry'] if res['entry'] > 0 else 0.01
            pos_usd = risk_usd / price_risk_pct
            margin = pos_usd / leverage

            st.markdown(f"""
            <div style="font-family:'JetBrains Mono'; font-size:0.85rem; line-height:2;">
                סיכון ב-$: <strong style="color:#FF1744;">${risk_usd:,.2f}</strong><br>
                גודל פוזיציה: <strong style="color:#00E5FF;">${pos_usd:,.2f}</strong><br>
                בטחונות דרושים: <strong style="color:#00E676;">${margin:,.2f}</strong>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            if res['is_confirmed']:
                if st.button("🚀 היכנס לעסקה בלחיצה אחת", type="primary", use_container_width=True):
                    st.session_state.trade_journal.append({
                        'id': len(st.session_state.trade_journal) + 1,
                        'timestamp': datetime.now().strftime("%d/%m %H:%M"),
                        'symbol': symbol,
                        'direction': res['direction'],
                        'entry': res['entry'],
                        'sl': res['sl'],
                        'tp2': res['tp2'],
                        'risk_usd': risk_usd,
                        'status': 'ACTIVE',
                        'pnl_usd': 0.0
                    })
                    st.success("העסקה נרשמה בהצלחה!")
                    st.rerun()
            else:
                st.button("ממתין לאיתות...", disabled=True, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

    # ================= TAB 2: MARKET RADAR =================
    with tab_radar:
        st.markdown("### 📡 סורק שוק ואינדיקטורי SMC")
        r1, r2 = st.columns([1, 1])
        
        with r1:
            st.markdown("<div class='window-card'>", unsafe_allow_html=True)
            st.markdown("#### 📋 רשימת מעקב (Watchlist)")
            for t in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]:
                st.markdown(f"• **{t}** — <span style='color:#00E676;'>SMC Active</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with r2:
            st.markdown("<div class='window-card'>", unsafe_allow_html=True)
            st.markdown("#### 🔍 התראות מבנה שוק (Confluences)")
            for c in res['confluences']:
                st.write(f"✅ {c}")
            if not res['confluences']:
                st.write("אין התראות מיוחדות כרגע.")
            st.markdown("</div>", unsafe_allow_html=True)

    # ================= TAB 3: TRADE JOURNAL =================
    with tab_journal:
        st.markdown("### 📖 יומן עסקאות וניהול ביצועים")
        
        active_trades = [t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE']
        
        if active_trades:
            st.markdown("#### עסקאות פתוחות")
            for trade in active_trades:
                col_t1, col_t2 = st.columns([3, 1])
                col_t1.write(f"**#{trade['id']} {trade['symbol']}** ({trade['direction']}) | כניסה: ${trade['entry']:,.2f} | סיכון: ${trade['risk_usd']:,.2f}")
                if col_t2.button(f"סגור ב-TP2 (+2.8R)", key=f"close_{trade['id']}"):
                    trade['status'] = 'CLOSED'
                    trade['pnl_usd'] = trade['risk_usd'] * 2.8
                    st.session_state.account_balance += trade['pnl_usd']
                    st.rerun()
        else:
            st.info("אין עסקאות פתוחות כרגע.")

        st.markdown("---")
        st.markdown("#### היסטוריית עסקאות סגורות")
        if closed_trades:
            st.dataframe(pd.DataFrame(closed_trades)[['id', 'timestamp', 'symbol', 'direction', 'entry', 'risk_usd', 'pnl_usd']], use_container_width=True)
        else:
            st.caption("טרם נרשמו עסקאות סגורות.")

    # ================= TAB 4: RISK CALCULATOR =================
    with tab_risk:
        st.markdown("### 🧮 מחשבון ניהול סיכונים מפורט")
        st.markdown("<div class='window-card'>", unsafe_allow_html=True)
        st.write(f"יתרה נוכחית: **${st.session_state.account_balance:,.2f}**")
        c_risk = st.number_input("הגדר סיכון ב-$ מקסימלי לעסקה:", 10.0, 500.0, 20.0)
        c_entry = st.number_input("מחיר כניסה מתוכנן:", value=res['entry'])
        c_sl = st.number_input("מחיר Stop Loss מתוכנן:", value=res['sl'])
        
        if c_entry > 0 and c_sl > 0:
            diff_pct = abs(c_entry - c_sl) / c_entry
            calc_pos = c_risk / diff_pct if diff_pct > 0 else 0
            st.success(f"גודל פוזיציה מומלץ: **${calc_pos:,.2f}**")
        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.error("שגיאה במשיכת נתוני שוק. אנא נסה לרענן.")
