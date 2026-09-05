import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 1. Page Configuration (Pro Mobile & Desktop Terminal)
st.set_page_config(
    page_title="Institutional SMC Pro Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Session State Initialization (Default Account Size = $1,000)
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 1000.0
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 1000.0
if 'trade_journal' not in st.session_state:
    st.session_state.trade_journal = []

# 3. Custom CSS - Institutional Pro Glassmorphism & High-Contrast Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: #07090E;
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(0, 229, 255, 0.04) 0%, transparent 40%),
            radial-gradient(circle at 90% 90%, rgba(0, 230, 118, 0.03) 0%, transparent 40%);
        color: #E2E8F0;
    }

    /* Top Live Ticker Bar */
    .top-status-bar {
        background: rgba(14, 20, 32, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 8px 16px;
        margin-bottom: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(10px);
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

    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(15, 22, 35, 0.85);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    /* Signal Card - Bullish */
    .signal-bullish {
        background: linear-gradient(135deg, rgba(0, 230, 118, 0.12) 0%, rgba(15, 22, 35, 0.9) 100%);
        border: 1.5px solid #00E676;
        box-shadow: 0 0 25px rgba(0, 230, 118, 0.18);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Signal Card - Bearish */
    .signal-bearish {
        background: linear-gradient(135deg, rgba(255, 23, 68, 0.12) 0%, rgba(15, 22, 35, 0.9) 100%);
        border: 1.5px solid #FF1744;
        box-shadow: 0 0 25px rgba(255, 23, 68, 0.18);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
    }

    .entry-price-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.3rem;
        font-weight: 800;
        color: #00E5FF;
        background: rgba(0, 229, 255, 0.12);
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 6px 12px;
        border-radius: 8px;
        display: inline-block;
    }

    /* Number / Price Typography */
    .mono-num {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
    }

    /* Responsive Mobile Adjustments */
    @media (max-width: 768px) {
        .top-status-bar {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
        }
        .entry-price-tag {
            font-size: 1.1rem !important;
        }
        .glass-card {
            padding: 12px !important;
        }
    }

    section[data-testid="stSidebar"] {
        background-color: #04060A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
</style>
""", unsafe_allow_html=True)

# 4. Data Engine (Binance + Yahoo Finance Backup)
@st.cache_data(ttl=15)
def fetch_klines(symbol="BTCUSDT", interval="1h", limit=120):
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

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

def analyze_smc(df):
    if df is None or len(df) < 50:
        return None
    
    df['rsi'] = calculate_rsi(df)
    close = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    
    range_high = df['high'].iloc[-60:].max()
    range_low = df['low'].iloc[-60:].min()
    equilibrium = (range_high + range_low) / 2
    
    is_discount = close < equilibrium
    is_premium = close > equilibrium
    
    fib_range = range_high - range_low
    fib_618 = range_high - (fib_range * 0.618)
    fib_786 = range_high - (fib_range * 0.786)
    in_bull_ote = (close <= fib_618) and (close >= fib_786)
    in_bear_ote = (close >= (range_low + fib_range * 0.618)) and (close <= (range_low + fib_range * 0.786))

    prev_low_30 = df['low'].iloc[-30:-1].min()
    prev_high_30 = df['high'].iloc[-30:-1].max()
    bull_sweep = df['low'].iloc[-1] < prev_low_30 and close > prev_low_30
    bear_sweep = df['high'].iloc[-1] > prev_high_30 and close < prev_high_30

    recent_high_15 = df['high'].iloc[-15:-1].max()
    recent_low_15 = df['low'].iloc[-15:-1].min()
    choch_bull = close > recent_high_15
    choch_bear = close < recent_low_15

    support_zone = df['low'].iloc[-40:-10].min()
    resistance_zone = df['high'].iloc[-40:-10].max()
    at_support = abs(close - support_zone) / close < 0.008
    at_resistance = abs(close - resistance_zone) / close < 0.008

    fvg_bull = df['low'].iloc[-1] > df['high'].iloc[-3]
    fvg_bear = df['high'].iloc[-1] < df['low'].iloc[-3]

    confluences = []
    score = 50
    direction = "NEUTRAL"

    if choch_bull or bull_sweep or is_discount:
        if is_discount:
            score += 10
            confluences.append("Discount Zone")
        if in_bull_ote:
            score += 15
            confluences.append("OTE Golden Zone")
        if bull_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bull:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_support:
            score += 10
            confluences.append("Bullish Order Block")
        if fvg_bull:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi < 40:
            score += 10
            confluences.append("Oversold RSI")
        
        if score >= 65:
            direction = "BUY (LONG) 🟢"

    if (choch_bear or bear_sweep or is_premium) and "BUY" not in direction:
        if is_premium:
            score += 10
            confluences.append("Premium Zone")
        if in_bear_ote:
            score += 15
            confluences.append("OTE Golden Zone")
        if bear_sweep:
            score += 15
            confluences.append("Liquidity Sweep")
        if choch_bear:
            score += 15
            confluences.append("CHoCH / BOS Breakout")
        if at_resistance:
            score += 10
            confluences.append("Bearish Order Block")
        if fvg_bear:
            score += 10
            confluences.append("Fair Value Gap (FVG)")
        if rsi > 60:
            score += 10
            confluences.append("Overbought RSI")
        
        if score >= 65:
            direction = "SELL (SHORT) 🔴"

    win_rate = min(92.0, score)

    if "BUY" in direction:
        entry_price = close
        sl = min(df['low'].iloc[-5:].min(), close * 0.992)
        risk = entry_price - sl
        tp1 = entry_price + (risk * 1.5)
        tp2 = entry_price + (risk * 2.8)
        tp3 = entry_price + (risk * 4.5)
        rr_ratio = round((tp2 - entry_price) / max(entry_price - sl, 1e-6), 2)
    elif "SELL" in direction:
        entry_price = close
        sl = max(df['high'].iloc[-5:].max(), close * 1.008)
        risk = sl - entry_price
        tp1 = entry_price - (risk * 1.5)
        tp2 = entry_price - (risk * 2.8)
        tp3 = entry_price - (risk * 4.5)
        rr_ratio = round((entry_price - tp2) / max(sl - entry_price, 1e-6), 2)
    else:
        entry_price = sl = tp1 = tp2 = tp3 = close
        rr_ratio = 0.0

    return {
        'direction': direction,
        'is_confirmed': score >= 65,
        'entry_price': entry_price,
        'close': close,
        'score': score,
        'win_rate': win_rate,
        'confluences': confluences,
        'sl': sl,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'rr_ratio': rr_ratio,
        'rsi': rsi
    }

# 5. TOP STATUS BAR (Live System Bar)
st.markdown(f"""
<div class="top-status-bar">
    <div style="display: flex; align-items: center;">
        <span class="status-dot"></span>
        <strong style="color: #00E676; font-size: 0.85rem; font-family: 'JetBrains Mono';">LIVE SYSTEM ONLINE</strong>
        <span style="margin: 0 10px; color: rgba(255,255,255,0.2);">|</span>
        <span style="font-size: 0.85rem; color: #8A99AD;">SMC Terminal v2.5</span>
    </div>
    <div style="display: flex; gap: 18px; font-family: 'JetBrains Mono'; font-size: 0.85rem;">
        <span>BTC/USDT: <strong style="color:#00E5FF;">Live</strong></span>
        <span>ETH/USDT: <strong style="color:#00E5FF;">Live</strong></span>
        <span>Equity: <strong style="color:#00E676;">${st.session_state.account_balance:,.2f}</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# 6. SIDEBAR SETUP
st.sidebar.markdown("<h2 style='text-align: center; color:#00E5FF; font-family: JetBrains Mono;'>⚡ PRO TERMINAL</h2>", unsafe_allow_html=True)

symbol = st.sidebar.selectbox("נכס למסחר (Asset)", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן (Timeframe)", ["15m", "1h", "4h", "1d"], index=1)

if st.sidebar.button("🔄 רענן נתונים בזמן אמת", use_container_width=True):
    st.cache_data.clear()

st.sidebar.markdown("---")
st.sidebar.markdown("##### ⚙️ הגדרת חשבון")
if st.sidebar.button("איפוס יתרה ל-$1,000", use_container_width=True):
    st.session_state.account_balance = 1000.0
    st.session_state.initial_balance = 1000.0
    st.session_state.trade_journal = []
    st.rerun()

df = fetch_klines(symbol, timeframe)

if df is not None:
    res = analyze_smc(df)

    # 7. MAIN 3-COLUMN MODULAR LAYOUT
    col_left, col_main, col_right = st.columns([1, 2.6, 1.2])

    # ---------------- LEFT COLUMN: WATCHLIST & ALERTS ----------------
    with col_left:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 10px 0; color:#00E5FF;'>📋 Watchlist</h4>", unsafe_allow_html=True)
        
        tickers = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
        for t in tickers:
            is_curr = (t == symbol)
            bg = "rgba(0, 229, 255, 0.15)" if is_curr else "rgba(255,255,255,0.02)"
            border = "1px solid #00E5FF" if is_curr else "1px solid rgba(255,255,255,0.05)"
            st.markdown(f"""
            <div style="background:{bg}; border:{border}; padding:8px 12px; border-radius:8px; margin-bottom:6px; display:flex; justify-content:space-between; align-items:center;">
                <span class="mono-num" style="font-weight:700;">{t}</span>
                <span style="font-size:0.75rem; color:#00E676;">SMC Active</span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # SMC Radar Card
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 10px 0; color:#00E5FF;'>⚡ SMC Alerts Radar</h4>", unsafe_allow_html=True)
        for conf in res['confluences'][:4]:
            st.markdown(f"<div style='font-size:0.8rem; background:rgba(255,255,255,0.03); padding:5px 8px; border-radius:6px; margin-bottom:4px;'>🔹 {conf}</div>", unsafe_allow_html=True)
        if not res['confluences']:
            st.caption("אין התראות מיוחדות כעת.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------------- MAIN COLUMN: DASHBOARD & CANVAS ----------------
    with col_main:
        # Top KPI Metrics Row
        closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']
        active_trades = [t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE']
        
        total_pnl = sum([t['pnl_usd'] for t in closed_trades])
        pnl_pct = (total_pnl / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0
        winning_trades = len([t for t in closed_trades if t['pnl_usd'] > 0])
        win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0.0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("יתרת תיק", f"${st.session_state.account_balance:,.2f}")
        k2.metric("PnL מצטבר", f"${total_pnl:+,.2f}", f"{pnl_pct:+.1f}%")
        k3.metric("Win Rate", f"{win_rate:.0f}%", f"{winning_trades}/{len(closed_trades)}")
        k4.metric("פוזיציות", f"{len(active_trades)}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Institutional Signal Execution Banner
        if res['is_confirmed']:
            sig_class = "signal-bullish" if "BUY" in res['direction'] else "signal-bearish"
            st.markdown(f"""
            <div class="{sig_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; font-weight:800;">🎯 אישור כניסה: {res['direction']}</h3>
                    <span class="mono-num" style="background:rgba(0,0,0,0.4); padding:4px 10px; border-radius:6px; font-size:0.85rem;">
                        R:R = 1:{res['rr_ratio']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            m_entry, m_sl, m_tp1, m_tp2, m_tp3 = st.columns(5)
            m_entry.markdown(f"**כניסה:**\n<div class='entry-price-tag'>${res['entry_price']:,.2f}</div>", unsafe_allow_html=True)
            m_sl.metric("🛑 SL", f"${res['sl']:,.2f}")
            m_tp1.metric("🎯 TP1", f"${res['tp1']:,.2f}")
            m_tp2.metric("🎯 TP2", f"${res['tp2']:,.2f}")
            m_tp3.metric("🎯 TP3", f"${res['tp3']:,.2f}")
        else:
            st.markdown("""
            <div style="background:rgba(20, 27, 40, 0.6); border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:14px; margin-bottom:14px;">
                <h4 style="margin:0; color:#8A99AD;">⏳ ממתין לאישור כניסה לעסקה (Neutral Zone)</h4>
                <p style="margin:4px 0 0 0; color:#5D6B7C; font-size:0.82rem;">המערכת מזהה מבנה ניטרלי. ברגע שיתקבל Sweep או CHoCH הציון יעלה מ-65 וייווצר איתות.</p>
            </div>
            """, unsafe_allow_html=True)

        # Plotly Trading Chart Canvas
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])

        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='#00E676',
            decreasing_line_color='#FF1744'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name="Volume",
            marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 23, 68, 0.3)')
        ), row=2, col=1)

        if res['is_confirmed']:
            fig.add_hline(y=res['entry_price'], line_dash="dash", line_color="#00E5FF", annotation_text="ENTRY", row=1, col=1)
            fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF1744", annotation_text="SL", row=1, col=1)
            fig.add_hline(y=res['tp2'], line_dash="dot", line_color="#00E676", annotation_text="TP2", row=1, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=5, r=5, t=5, b=5),
            height=420,
            xaxis_rangeslider_visible=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tabbed Journal & Positions Section
        tab_active, tab_journal = st.tabs(["⚡ עסקאות פעילות (Active)", "📖 יומן עסקאות סגורות"])
        
        with tab_active:
            if active_trades:
                for trade in active_trades:
                    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                    tc1, tc2, tc3, tc4 = st.columns([1.5, 1.2, 1.2, 2])
                    tc1.markdown(f"**{trade['symbol']}** ({trade['direction']})\n\n<small>{trade['timestamp']}</small>", unsafe_allow_html=True)
                    tc2.metric("כניסה", f"${trade['entry']:,.2f}")
                    tc3.metric("סיכון ($)", f"${trade['risk_usd']:,.2f}")
                    
                    with tc4:
                        outcome = st.selectbox(f"סגור עסקה #{trade['id']}", ["תוצאה...", "🎯 TP1 (+1.5R)", "🎯 TP2 (+2.8R)", "🎯 TP3 (+4.5R)", "🛑 SL (-1R)", "⏹️ סגירה שטוחה"], key=f"c_sel_{trade['id']}")
                        if outcome != "תוצאה...":
                            if "TP1" in outcome: pnl = trade['risk_usd'] * 1.5
                            elif "TP2" in outcome: pnl = trade['risk_usd'] * 2.8
                            elif "TP3" in outcome: pnl = trade['risk_usd'] * 4.5
                            elif "SL" in outcome: pnl = -trade['risk_usd']
                            else: pnl = 0.0
                            
                            if st.button(f"אישור #{trade['id']}", key=f"c_btn_{trade['id']}"):
                                trade['status'] = 'CLOSED'
                                trade['pnl_usd'] = pnl
                                st.session_state.account_balance += pnl
                                st.success(f"עסקה נסגרה ב-{pnl:+,.2f}$")
                                st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.caption("אין עסקאות פעילות כרגע.")

        with tab_journal:
            if closed_trades:
                df_c = pd.DataFrame(closed_trades)[['id', 'timestamp', 'symbol', 'direction', 'entry', 'risk_usd', 'pnl_usd']]
                df_c.columns = ['#', 'זמן', 'נכס', 'כיוון', 'כניסה', 'סיכון ($)', 'PnL ($)']
                st.dataframe(df_c, use_container_width=True, hide_index=True)
            else:
                st.caption("אין עדיין עסקאות סגורות ביומן.")

    # ---------------- RIGHT COLUMN: SMART ORDER & RISK ENGINE ----------------
    with col_right:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin:0 0 12px 0; color:#00E5FF;'>🧮 Smart Risk Engine</h4>", unsafe_allow_html=True)

        st.caption(f"יתרת חשבון: **${st.session_state.account_balance:,.2f}**")
        risk_pct_input = st.slider("סיכון לעסקה (%):", 0.25, 3.0, 1.0, 0.25)
        leverage = st.number_input("מינוף (Leverage):", 1, 100, 10)

        risk_usd = st.session_state.account_balance * (risk_pct_input / 100.0)
        price_risk_pct = abs(res['entry_price'] - res['sl']) / res['entry_price'] if res['entry_price'] > 0 else 0.01
        pos_usd = risk_usd / price_risk_pct if price_risk_pct > 0 else 0
        req_margin = pos_usd / leverage if leverage > 0 else pos_usd
        units = pos_usd / res['entry_price'] if res['entry_price'] > 0 else 0

        st.markdown("<hr style='border:0.5px solid rgba(255,255,255,0.08); margin:12px 0;'>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="font-family:'JetBrains Mono'; font-size:0.85rem; line-height:1.8;">
            <div>סיכון דולרי: <strong style="color:#FF1744;">${risk_usd:,.2f}</strong></div>
            <div>גודל פוזיציה: <strong style="color:#00E5FF;">${pos_usd:,.2f}</strong></div>
            <div>בטחונות (Margin): <strong style="color:#00E676;">${req_margin:,.2f}</strong></div>
            <div>כמות יחידות: <strong style="color:#E2E8F0;">{units:,.3f}</strong></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if res['is_confirmed']:
            if st.button("🚀 קח עסקה זו ליומן", type="primary", use_container_width=True):
                new_trade = {
                    'id': len(st.session_state.trade_journal) + 1,
                    'timestamp': datetime.now().strftime("%d/%m %H:%M"),
                    'symbol': symbol,
                    'direction': res['direction'],
                    'entry': res['entry_price'],
                    'sl': res['sl'],
                    'tp1': res['tp1'],
                    'tp2': res['tp2'],
                    'tp3': res['tp3'],
                    'risk_usd': risk_usd,
                    'pos_usd': pos_usd,
                    'status': 'ACTIVE',
                    'pnl_usd': 0.0
                }
                st.session_state.trade_journal.append(new_trade)
                st.success(f"✅ עסקה ב-{symbol} נלקחה בהצלחה!")
                st.rerun()
        else:
            st.button("🚀 ממתין לאיתות...", disabled=True, use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.error("לא ניתן למשוך נתוני שוק כעת. אנא רענן את העמוד.")
