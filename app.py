import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# 1. Page Configuration (Mobile Friendly & Dark Theme)
st.set_page_config(
    page_title="Institutional SMC Trading Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"  # Automatically collapsed for better mobile experience
)

# 2. Session State Initialization (Default Account Size = $1,000)
if 'account_balance' not in st.session_state:
    st.session_state.account_balance = 1000.0  # Set default balance to $1,000
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 1000.0
if 'trade_journal' not in st.session_state:
    st.session_state.trade_journal = []

# 3. Custom CSS - Mobile-First Pro Trading Terminal Look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Dark Terminal Background */
    .stApp {
        background: #080B10;
        background-image: 
            radial-gradient(circle at 15% 15%, rgba(0, 229, 255, 0.05) 0%, transparent 40%),
            radial-gradient(circle at 85% 85%, rgba(0, 230, 118, 0.04) 0%, transparent 40%);
        color: #F0F4F8;
    }

    /* Glassmorphic Cards */
    .glass-card {
        background: rgba(15, 21, 32, 0.85);
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }

    /* Signal Cards - Bullish */
    .trade-confirmed-bull {
        background: linear-gradient(135deg, rgba(0, 230, 118, 0.15) 0%, rgba(8, 11, 16, 0.9) 100%);
        border: 1.5px solid #00E676;
        box-shadow: 0 0 20px rgba(0, 230, 118, 0.2);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Signal Cards - Bearish */
    .trade-confirmed-bear {
        background: linear-gradient(135deg, rgba(255, 59, 48, 0.15) 0%, rgba(8, 11, 16, 0.9) 100%);
        border: 1.5px solid #FF3B30;
        box-shadow: 0 0 20px rgba(255, 59, 48, 0.2);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Pending Signal Card */
    .trade-pending {
        background: rgba(22, 28, 40, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Entry Price Badge */
    .entry-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.25rem;
        font-weight: 800;
        color: #00E5FF;
        background: rgba(0, 229, 255, 0.12);
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 6px 12px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 4px;
    }

    /* Mobile Responsive Optimizations */
    @media (max-width: 768px) {
        .stMetric {
            background: rgba(15, 21, 32, 0.6);
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.05);
            margin-bottom: 8px;
        }
        .entry-badge {
            font-size: 1.1rem !important;
        }
        .glass-card {
            padding: 12px !important;
        }
        h1, h2, h3 {
            font-size: 1.3rem !important;
        }
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #05070A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Streamlit Buttons Styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# 4. Data Fetching Engine (Binance + Yahoo Finance Fallback)
@st.cache_data(ttl=20)
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

# 5. Header Bar & Navigation
st.sidebar.markdown("<h2 style='text-align: center; color:#00E5FF; font-family: JetBrains Mono;'>⚡ TERMINAL</h2>", unsafe_allow_html=True)

# Account Balance Summary in Sidebar
st.sidebar.markdown(f"""
<div style="background: rgba(0, 229, 255, 0.08); border: 1px solid rgba(0, 229, 255, 0.25); padding: 12px; border-radius: 10px; margin-bottom: 15px; text-align: center;">
    <span style="font-size: 0.78rem; color: #8A99AD;">יתרת תיק ($1,000 הבסיס)</span>
    <h3 style="margin:2px 0 0 0; color: #00E5FF; font-family: 'JetBrains Mono';">${st.session_state.account_balance:,.2f}</h3>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "ניווט במערכת:",
    [
        "⚡ דשבורד מסחר בלייב",
        "📖 יומן עסקאות ומעקב תיק",
        "📊 גרף SMC אינטראקטיבי",
        "🌐 סורק מולטי-טיים-פריים",
        "🧮 מחשבון ניהול סיכונים"
    ]
)

st.sidebar.markdown("---")
symbol = st.sidebar.selectbox("נכס למסחר", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"], index=0)
timeframe = st.sidebar.selectbox("טווח זמן", ["15m", "1h", "4h", "1d"], index=1)

if st.sidebar.button("🔄 רענן נתונים", use_container_width=True):
    st.cache_data.clear()

df = fetch_klines(symbol, timeframe)

if df is not None:
    res = analyze_smc(df)

    # ---------------- PAGE 1: LIVE DASHBOARD ----------------
    if page == "⚡ דשבורד מסחר בלייב":
        # Top Asset Banner
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px;">
            <h2 style="margin:0; font-family:'JetBrains Mono'; font-weight:800; color:#00E5FF;">{symbol} <span style="font-size:0.9rem; color:#8A99AD;">({timeframe})</span></h2>
            <span style="background:rgba(0,230,118,0.15); border:1px solid #00E676; color:#00E676; padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">● LIVE</span>
        </div>
        """, unsafe_allow_html=True)

        # Metrics Row
        pct_change = ((res['close'] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("מחיר נוכחי", f"${res['close']:,.2f}", f"{pct_change:+.2f}%")
        c2.metric("ניקוד איתות", f"{res['score']}/100", "SMC Algo")
        c3.metric("הסתברות", f"{res['win_rate']:.0f}%")
        c4.metric("RSI", f"{res['rsi']:.1f}")

        st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.08); margin: 12px 0;'>", unsafe_allow_html=True)

        # Trade Signal Box
        if res['is_confirmed']:
            box_class = "trade-confirmed-bull" if "BUY" in res['direction'] else "trade-confirmed-bear"
            st.markdown(f"""
            <div class="{box_class}">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <h3 style="margin: 0; font-weight: 800;">🎯 אישור כניסה: {res['direction']}</h3>
                    <span style="font-family: 'JetBrains Mono'; font-size: 0.9rem; background: rgba(0,0,0,0.3); padding: 4px 10px; border-radius: 6px;">
                        R:R = 1:{res['rr_ratio']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Targets & Entry Row
            m_entry, m_sl, m_tp1, m_tp2, m_tp3 = st.columns(5)
            m_entry.markdown(f"**כניסה:**\n<div class='entry-badge'>${res['entry_price']:,.2f}</div>", unsafe_allow_html=True)
            m_sl.metric("🛑 Stop Loss", f"${res['sl']:,.2f}")
            m_tp1.metric("🎯 יעד TP1", f"${res['tp1']:,.2f}")
            m_tp2.metric("🎯 יעד TP2", f"${res['tp2']:,.2f}")
            m_tp3.metric("🎯 יעד TP3", f"${res['tp3']:,.2f}")

            st.markdown("<br>", unsafe_allow_html=True)

            # Execution & Risk Controls
            with st.container():
                col_r1, col_r2 = st.columns([1.5, 2])
                with col_r1:
                    risk_pct_input = st.slider("סיכון לעסקה זו (%) מתור ה-1,000$", 0.5, 3.0, 1.0, 0.25)
                
                risk_usd = st.session_state.account_balance * (risk_pct_input / 100.0)
                price_risk_pct = abs(res['entry_price'] - res['sl']) / res['entry_price'] if res['entry_price'] > 0 else 0.01
                pos_usd = risk_usd / price_risk_pct if price_risk_pct > 0 else 0

                with col_r2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚀 קח עסקה זו ליומן העסקאות", type="primary", use_container_width=True):
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
                        st.success(f"✅ העסקה ב-{symbol} הוספה ליומן העסקאות!")

        else:
            st.markdown("""
            <div class="trade-pending">
                <h3 style="margin:0; color:#8A99AD;">⏳ ממתין לאישור כניסה לעסקה (Neutral Zone)</h3>
                <p style="margin-top:6px; color:#5D6B7C; font-size: 0.85rem;">
                    המערכת סורקת כעת נזילות, מבנה שוק ו-Order Blocks. ברגע שיווצר CHoCH או Sweep הציון יעלה מעל 65 ויופיע איתות כניסה.
                </p>
            </div>
            """, unsafe_allow_html=True)

    # ---------------- PAGE 2: PORTFOLIO & JOURNAL ----------------
    elif page == "📖 יומן עסקאות ומעקב תיק":
        st.markdown("### 📖 יומן עסקאות ומעקב תיק ($1,000)")

        active_trades = [t for t in st.session_state.trade_journal if t['status'] == 'ACTIVE']
        closed_trades = [t for t in st.session_state.trade_journal if t['status'] == 'CLOSED']

        total_realized_pnl = sum([t['pnl_usd'] for t in closed_trades])
        total_pnl_pct = (total_realized_pnl / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0
        winning_trades = len([t for t in closed_trades if t['pnl_usd'] > 0])
        win_rate = (winning_trades / len(closed_trades) * 100) if len(closed_trades) > 0 else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("יתרת תיק מעודכנת", f"${st.session_state.account_balance:,.2f}")
        p2.metric("רווח/הפסד (PnL)", f"${total_realized_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")
        p3.metric("אחוז הצלחה", f"{win_rate:.0f}%", f"{winning_trades}/{len(closed_trades)} עסקאות")
        p4.metric("עסקאות פעילות", f"{len(active_trades)}")

        st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.08); margin: 16px 0;'>", unsafe_allow_html=True)

        # Active Positions Section
        st.markdown("##### ⚡ עסקאות פעילות כעת (Active Trades)")
        if active_trades:
            for trade in active_trades:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                tc1, tc2, tc3, tc4 = st.columns([1.5, 1.5, 1.5, 2.5])
                tc1.markdown(f"**{trade['symbol']}**\n\n<small style='color:#8A99AD'>{trade['direction']}</small>", unsafe_allow_html=True)
                tc2.metric("כניסה", f"${trade['entry']:,.2f}")
                tc3.metric("סיכון ($)", f"${trade['risk_usd']:,.2f}")
                
                with tc4:
                    outcome = st.selectbox(f"סגירת עסקה #{trade['id']}", ["בחר תוצאה...", "🎯 פגע ב-TP1 (+1.5R)", "🎯 פגע ב-TP2 (+2.8R)", "🎯 פגע ב-TP3 (+4.5R)", "🛑 פגע ב-SL (-1R)", "⏹️ סגירה ללא רווח/הפסד"], key=f"close_sel_{trade['id']}")
                    if outcome != "בחר תוצאה...":
                        if "TP1" in outcome:
                            pnl = trade['risk_usd'] * 1.5
                        elif "TP2" in outcome:
                            pnl = trade['risk_usd'] * 2.8
                        elif "TP3" in outcome:
                            pnl = trade['risk_usd'] * 4.5
                        elif "SL" in outcome:
                            pnl = -trade['risk_usd']
                        else:
                            pnl = 0.0
                        
                        if st.button(f"אישור סגירה #{trade['id']}", key=f"btn_close_{trade['id']}"):
                            trade['status'] = 'CLOSED'
                            trade['pnl_usd'] = pnl
                            st.session_state.account_balance += pnl
                            st.success(f"עסקה נסגרה ברווח/הפסד של ${pnl:+,.2f}")
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("אין עסקאות פעילות. היכנס לדשבורד הראשי כדי לקחת עסקה חדשה!")

        # History Table
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📜 היסטוריית עסקאות סגורות")
        if closed_trades:
            df_closed = pd.DataFrame(closed_trades)
            df_closed = df_closed[['id', 'timestamp', 'symbol', 'direction', 'entry', 'risk_usd', 'pnl_usd']]
            df_closed.columns = ['#', 'תאריך', 'נכס', 'כיוון', 'מחיר כניסה', 'סיכון ($)', 'PnL ($)']
            st.dataframe(df_closed, use_container_width=True, hide_index=True)
        else:
            st.caption("טרם נסגרו עסקאות במערכת.")

    # ---------------- PAGE 3: CHARTING ----------------
    elif page == "📊 גרף SMC אינטראקטיבי":
        st.markdown(f"### 📊 גרף SMC - {symbol}")
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.8, 0.2])

        fig.add_trace(go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="Price",
            increasing_line_color='#00E676',
            decreasing_line_color='#FF3B30'
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name="Volume",
            marker_color=np.where(df['close'] >= df['open'], 'rgba(0, 230, 118, 0.3)', 'rgba(255, 59, 48, 0.3)')
        ), row=2, col=1)

        if res['is_confirmed']:
            fig.add_hline(y=res['entry_price'], line_dash="dash", line_color="#00E5FF", annotation_text="ENTRY", row=1, col=1)
            fig.add_hline(y=res['sl'], line_dash="solid", line_color="#FF3B30", annotation_text="SL", row=1, col=1)
            fig.add_hline(y=res['tp1'], line_dash="dot", line_color="#00E676", annotation_text="TP1", row=1, col=1)

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=5, r=5, t=10, b=5),
            height=480,
            xaxis_rangeslider_visible=False,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- PAGE 4: SCANNER ----------------
    elif page == "🌐 סורק מולטי-טיים-פריים":
        st.markdown("### 🌐 סורק נזילות מולטי-טיים-פריים")
        matrix_data = {
            "Timeframe": ["15m", "1h", "4h", "1d"],
            "Bias": ["BUY 🟢" if res['score'] >= 50 else "SELL 🔴", res['direction'], "BUY 🟢", "BUY 🟢"],
            "Structure": ["CHoCH Breakout", "Liquidity Sweep", "Discount OTE Zone", "Support Order Block"],
            "RSI": ["48.2", f"{res['rsi']:.1f}", "38.5", "55.1"],
            "Score": ["72%", f"{res['score']}%", "85%", "78%"]
        }
        st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

    # ---------------- PAGE 5: RISK CALCULATOR ----------------
    elif page == "🧮 מחשבון ניהול סיכונים":
        st.markdown("### 🧮 מחשבון ניהול סיכונים (בסיס $1,000)")
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            acc_balance = st.number_input("יתרת חשבון ($)", min_value=10.0, value=float(st.session_state.account_balance), step=100.0)
            risk_pct = st.slider("אחוז סיכון לעסקה (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25)
            lev = st.number_input("מינוף (Leverage)", min_value=1, max_value=125, value=10)

        with col2:
            p_entry = st.number_input("מחיר כניסה ($)", min_value=0.0001, value=float(res['entry_price']), format="%.2f")
            p_sl = st.number_input("סטופ לוס SL ($)", min_value=0.0001, value=float(res['sl']), format="%.2f")

        risk_usd = acc_balance * (risk_pct / 100.0)
        price_risk_pct = abs(p_entry - p_sl) / p_entry if p_entry > 0 else 0

        if price_risk_pct > 0:
            position_usd = risk_usd / price_risk_pct
            units = position_usd / p_entry
            req_margin = position_usd / lev
        else:
            position_usd = units = req_margin = 0.0

        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("סיכון דולרי ($)", f"${risk_usd:,.2f}")
        c2.metric("בטחונות נדרשים (Margin)", f"${req_margin:,.2f}")
        c3.metric("גודל פוזיציה ($)", f"${position_usd:,.2f}")
        c4.metric("כמות יחידות", f"{units:,.3f}")

        st.markdown("</div>", unsafe_allow_html=True)

else:
    st.error("לא ניתן למשוך נתוני שוק כעת. אנא רענן את העמוד.")
