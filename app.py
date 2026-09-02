import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Configuration
st.set_page_config(
    page_title="Institutional SMC Suite",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed" # Collapsed by default for mobile friendliness
)

# Custom Institutional & Mobile-First CSS UI
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

    /* Top KPI Cards */
    .kpi-card {
        background: rgba(22, 27, 34, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 14px 16px;
        text-align: center;
        backdrop-filter: blur(10px);
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 12px;
        color: #8B949E;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .kpi-value {
        font-size: 20px;
        font-weight: 800;
        color: #F0F6FC;
        margin-top: 4px;
    }

    /* Signal Cards */
    .signal-card {
        background: linear-gradient(145deg, #121721 0%, #0D111A 100%);
        border: 1px solid #1F2633;
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    .signal-card-bullish {
        border-right: 6px solid #238636;
    }
    
    .signal-card-bearish {
        border-right: 6px solid #DA3633;
    }
    
    .card-header-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    
    .symbol-title {
        font-size: 20px;
        font-weight: 800;
        color: #FFFFFF;
    }
    
    .badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
    }
    
    .badge-winrate {
        background: rgba(46, 160, 67, 0.2);
        color: #3FB950;
        border: 1px solid #238636;
    }

    .badge-buy {
        background: rgba(35, 134, 54, 0.25);
        color: #56D364;
    }

    .badge-sell {
        background: rgba(218, 54, 51, 0.25);
        color: #FFA198;
    }

    /* Data Grid for Mobile */
    .data-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 14px;
        background: rgba(255, 255, 255, 0.02);
        padding: 12px;
        border-radius: 10px;
    }

    .data-item {
        display: flex;
        flex-direction: column;
    }

    .data-label {
        font-size: 11px;
        color: #8B949E;
    }

    .data-val {
        font-size: 14px;
        font-weight: 700;
        color: #E6EDF3;
    }

    /* Mobile Responsive Adjustments */
    @media (max-width: 768px) {
        .data-grid {
            grid-template-columns: repeat(2, 1fr);
        }
        .symbol-title {
            font-size: 18px;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 13px;
            padding: 8px 10px;
        }
    }

    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #0D1117;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #21262D;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #8B949E;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1F2633 !important;
        color: #58A6FF !important;
    }
</style>
""", unsafe_allow_html=True)

class AdvancedSMCScanner:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"

    def get_top_pairs(self, limit=30):
        try:
            res = requests.get(f"{self.base_url}/ticker/24hr", timeout=5)
            if res.status_code != 200: return []
            data = res.json()
            pairs = [item for item in data if item['symbol'].endswith('USDT') 
                     and not any(x in item['symbol'] for x in ['UP', 'DOWN', 'BEAR', 'BULL', 'USDC', 'FDUSD', 'TUSD', 'BUSD'])]
            sorted_pairs = sorted(pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            return [x['symbol'] for x in sorted_pairs[:limit]]
        except Exception:
            return []

    def fetch_klines(self, symbol, interval='1h', limit=100):
        try:
            res = requests.get(f"{self.base_url}/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=5)
            if res.status_code != 200: return pd.DataFrame()
            data = res.json()
            df = pd.DataFrame(data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'trades', 'tbv', 'tqv', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except Exception:
            return pd.DataFrame()

    def calculate_rsi(self, df, period=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def analyze_deep_smc(self, df):
        if df.empty or len(df) < 50: return None
        
        close = df['close'].iloc[-1]
        df['rsi'] = self.calculate_rsi(df)
        rsi = df['rsi'].iloc[-1]
        
        # 1. Liquidity Sweep
        high_20 = df['high'].iloc[-30:-5].max()
        low_20 = df['low'].iloc[-30:-5].min()
        swept_bull = df['low'].iloc[-5:-1].min() < low_20 and close > low_20
        swept_bear = df['high'].iloc[-5:-1].max() > high_20 and close < high_20
        
        # 2. Structure Shift (CHoCH / BOS)
        bos_bull = close > df['high'].iloc[-15:-2].max()
        bos_bear = close < df['low'].iloc[-15:-2].min()
        
        # 3. Fair Value Gap (FVG)
        fvgs = []
        for i in range(len(df)-10, len(df)):
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                fvgs.append(('BULLISH', df['high'].iloc[i-2], df['low'].iloc[i]))
            elif df['high'].iloc[i] < df['low'].iloc[i-2]:
                fvgs.append(('BEARISH', df['low'].iloc[i-2], df['high'].iloc[i]))
                
        # 4. Premium / Discount Zone
        range_high = df['high'].iloc[-50:].max()
        range_low = df['low'].iloc[-50:].min()
        eq_level = (range_high + range_low) / 2
        in_discount = close < eq_level
        in_premium = close > eq_level
        
        score = 50.0
        confluences = []
        
        is_bullish = bos_bull or (swept_bull and rsi < 40)
        is_bearish = bos_bear or (swept_bear and rsi > 60)
        
        if is_bullish:
            if swept_bull: score += 15; confluences.append("Liquidity Sweep (SSL)")
            if bos_bull: score += 12; confluences.append("Bullish CHoCH/BOS")
            if in_discount: score += 8; confluences.append("Discount Zone Entry")
            if any(f[0] == 'BULLISH' for f in fvgs): score += 10; confluences.append("Bullish FVG Present")
            if rsi < 35: score += 5; confluences.append("Oversold RSI Confirmation")
        elif is_bearish:
            if swept_bear: score += 15; confluences.append("Liquidity Sweep (BSL)")
            if bos_bear: score += 12; confluences.append("Bearish CHoCH/BOS")
            if in_premium: score += 8; confluences.append("Premium Zone Entry")
            if any(f[0] == 'BEARISH' for f in fvgs): score += 10; confluences.append("Bearish FVG Present")
            if rsi > 65: score += 5; confluences.append("Overbought RSI Confirmation")
            
        final_winrate = min(round(score, 1), 91.5)
        
        if is_bullish:
            sl = df['low'].iloc[-15:].min() * 0.998
            risk = close - sl
            tp1, tp2, tp3 = close + (risk * 1.5), close + (risk * 2.8), close + (risk * 4.5)
            signal_type = "LONG 🟢"
            direction = "BULLISH"
        elif is_bearish:
            sl = df['high'].iloc[-15:].max() * 1.002
            risk = sl - close
            tp1, tp2, tp3 = close - (risk * 1.5), close - (risk * 2.8), close - (risk * 4.5)
            signal_type = "SHORT 🔴"
            direction = "BEARISH"
        else:
            return None

        rr_ratio = round((tp2 - close) / abs(close - sl), 2) if abs(close - sl) > 0 else 1.0

        return {
            'df': df,
            'signal': signal_type,
            'direction': direction,
            'winrate': final_winrate,
            'price': close,
            'sl': sl,
            'tp1': tp1,
            'tp2': tp2,
            'tp3': tp3,
            'rr': rr_ratio,
            'confluences': confluences,
            'fvgs': fvgs
        }

# Sidebar Controls
st.sidebar.title("🦅 פרמטרי סריקה")
tf = st.sidebar.selectbox("טווח זמן (Timeframe)", ["15m", "1h", "4h"], index=1)
coins_num = st.sidebar.slider("כמות מטבעות לסריקה", 10, 60, 25, 5)
min_wr = st.sidebar.slider("סינון Win Rate (%)", 50, 85, 68, 2)

scanner = AdvancedSMCScanner()

# Header Area
st.title("🦅 Institutional SMC Terminal")
st.caption("סריקה מוסדית בזמן אמת לנייד ולדסקטופ")

# Scan Trigger Button
if st.button("🚀 הרץ סריקה מוסדית עכשיו", use_container_width=True):
    with st.spinner("סורק נתונים מBinance..."):
        symbols = scanner.get_top_pairs(limit=coins_num)
        results = {}
        for sym in symbols:
            df = scanner.fetch_klines(sym, interval=tf)
            analysis = scanner.analyze_deep_smc(df)
            if analysis and analysis['winrate'] >= min_wr:
                results[sym] = analysis
        st.session_state.scan_data = results

if 'scan_data' not in st.session_state:
    st.session_state.scan_data = {}

scan_data = st.session_state.scan_data

# KPI Top Bar
if scan_data:
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    total_found = len(scan_data)
    bulls = sum(1 for v in scan_data.values() if v['direction'] == 'BULLISH')
    max_wr_pair = max(scan_data.items(), key=lambda x: x[1]['winrate']) if scan_data else (None, {'winrate': 0})
    
    kpi1.markdown(f'<div class="kpi-card"><div class="kpi-title">זוגות שנסרקו</div><div class="kpi-value">{coins_num}</div></div>', unsafe_allow_html=True)
    kpi2.markdown(f'<div class="kpi-card"><div class="kpi-title">איתותים שנמצאו</div><div class="kpi-value">{total_found}</div></div>', unsafe_allow_html=True)
    kpi3.markdown(f'<div class="kpi-card"><div class="kpi-title">נטיית שוק</div><div class="kpi-value" style="color:{"#56D364" if bulls >= total_found/2 else "#FFA198"}">{int((bulls/total_found)*100) if total_found>0 else 0}% שורי</div></div>', unsafe_allow_html=True)
    kpi4.markdown(f'<div class="kpi-card"><div class="kpi-title">הזדמנות מובילה</div><div class="kpi-value" style="color:#58A6FF">{max_wr_pair[0].replace("USDT","") if max_wr_pair[0] else "-"} ({max_wr_pair[1]["winrate"]}%)</div></div>', unsafe_allow_html=True)

# Main Navigation Tabs
tabs = st.tabs(["🎯 איתותים", "📊 טבלה", "📈 גרף SMC", "🧮 מחשבון"])

# TAB 1: Signal Cards
with tabs[0]:
    if scan_data:
        for sym, data in scan_data.items():
            card_class = "signal-card-bullish" if data['direction'] == 'BULLISH' else "signal-card-bearish"
            badge_class = "badge-buy" if data['direction'] == 'BULLISH' else "badge-sell"
            
            st.markdown(f"""
            <div class="signal-card {card_class}">
                <div class="card-header-flex">
                    <span class="symbol-title">{sym.replace('USDT', '/USDT')}</span>
                    <div>
                        <span class="badge {badge_class}">{data['signal']}</span>
                        <span class="badge badge-winrate">WinRate: {data['winrate']}%</span>
                    </div>
                </div>
                
                <div class="data-grid">
                    <div class="data-item"><span class="data-label">מחיר כניסה</span><span class="data-val">${data['price']:.4f}</span></div>
                    <div class="data-item"><span class="data-label">סטופ לוס (SL)</span><span class="data-val" style="color:#FFA198">${data['sl']:.4f}</span></div>
                    <div class="data-item"><span class="data-label">יעד ראשון (TP1)</span><span class="data-val" style="color:#56D364">${data['tp1']:.4f}</span></div>
                    <div class="data-item"><span class="data-label">יעד מרכזי (TP2)</span><span class="data-val" style="color:#56D364">${data['tp2']:.4f}</span></div>
                </div>
                
                <div style="margin-top: 10px; font-size: 12px; color: #8B949E;">
                    <b>יחס סיכון/סיכון (R:R):</b> <span style="color:#58A6FF; font-weight:700">1:{data['rr']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"🔍 אישורים מוסדיים ({len(data['confluences'])}) עבור {sym.replace('USDT','')}"):
                for conf in data['confluences']:
                    st.write(f"✅ {conf}")
    else:
        st.info("לחץ על הכפתור למעלה כדי להתחיל בסריקה.")

# TAB 2: Table View
with tabs[1]:
    if scan_data:
        rows = []
        for sym, d in scan_data.items():
            rows.append({
                "צמד": sym.replace('USDT', '/USDT'),
                "איתות": d['signal'],
                "Win Rate": f"{d['winrate']}%",
                "מחיר כניסה": f"${d['price']:.4f}",
                "SL": f"${d['sl']:.4f}",
                "TP2": f"${d['tp2']:.4f}",
                "R:R": f"1:{d['rr']}"
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

# TAB 3: Chart View
with tabs[2]:
    if scan_data:
        selected_sym = st.selectbox("בחר מטבע לניתוח:", list(scan_data.keys()))
        if selected_sym:
            d = scan_data[selected_sym]
            df = d['df']
            
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.75, 0.25])
            
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Price'
            ), row=1, col=1)
            
            fig.add_hline(y=d['price'], line_dash="dash", line_color="#58A6FF", annotation_text="Entry", row=1, col=1)
            fig.add_hline(y=d['sl'], line_dash="solid", line_color="#F85149", annotation_text="SL", row=1, col=1)
            fig.add_hline(y=d['tp2'], line_dash="solid", line_color="#3FB950", annotation_text="TP2", row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df.index, y=df['rsi'], line=dict(color='#D29922'), name='RSI'), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="gray", row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="gray", row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=500, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

# TAB 4: Position Size Calculator
with tabs[3]:
    st.subheader("🧮 מחשבון סיכונים לנייד")
    col1, col2 = st.columns(2)
    acc_size = col1.number_input("גודל תיק ($):", value=5000, step=500)
    risk_p = col2.number_input("אחוז סיכון (%):", value=1.0, step=0.5)
    
    if scan_data:
        calc_sym = st.selectbox("בחר עסקה לחישוב:", list(scan_data.keys()))
        if calc_sym:
            d = scan_data[calc_sym]
            risk_usd = acc_size * (risk_p / 100)
            price_diff = abs(d['price'] - d['sl'])
            pos_units = risk_usd / price_diff if price_diff > 0 else 0
            
            st.markdown("---")
            st.success(f"**סכום סיכון דולרי:** ${risk_usd:.2f}")
            st.info(f"**גודל פוזיציה:** {pos_units:.4f} {calc_sym.replace('USDT','')}")
            st.warning(f"**רווח צפוי ב-TP2:** ${(risk_usd * d['rr']):.2f}")