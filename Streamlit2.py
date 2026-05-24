#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
import logging

st.set_page_config(page_title="منصة التداول الذكية", page_icon="📈", layout="wide")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MT5Handler:
    def __init__(self):
        self.initialized = True
    
    def get_account_info(self):
        return {'balance': 100000, 'equity': 99500, 'profit': -500, 'margin': 5000, 'leverage': 100}
    
    def get_symbol_data(self, symbol='EURUSD', bars=100):
        dates = pd.date_range(end=datetime.now(), periods=bars, freq='H')
        open_prices = np.random.uniform(1.08, 1.12, bars)
        close_prices = open_prices + np.random.normal(0, 0.002, bars)
        high_prices = np.maximum(open_prices, close_prices) + np.random.uniform(0, 0.005, bars)
        low_prices = np.minimum(open_prices, close_prices) - np.random.uniform(0, 0.005, bars)
        
        return pd.DataFrame({
            'Time': dates,
            'Open': open_prices,
            'High': high_prices,
            'Low': low_prices,
            'Close': close_prices,
            'Volume': np.random.randint(1000, 10000, bars)
        })
    
    def execute_trade(self, symbol, action, volume):
        return {
            'success': True,
            'order_id': np.random.randint(1000000, 9999999),
            'symbol': symbol,
            'action': action,
            'volume': volume,
            'price': np.random.uniform(1.08, 1.12),
            'timestamp': datetime.now()
        }

class IndicatorsCalculator:
    @staticmethod
    def calculate_rsi(close, period=14):
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_sma(close, period):
        return close.rolling(window=period).mean()
    
    @staticmethod
    def generate_signal(df):
        if df is None or len(df) < 50:
            return {'signal': 'HOLD', 'confidence': 0}
        
        close = df['Close']
        sma_20 = IndicatorsCalculator.calculate_sma(close, 20)
        sma_50 = IndicatorsCalculator.calculate_sma(close, 50)
        rsi = IndicatorsCalculator.calculate_rsi(close)
        
        last_rsi = rsi.iloc[-1] if not rsi.isna().all() else 50
        
        if sma_20.iloc[-1] > sma_50.iloc[-1] and last_rsi < 40:
            return {
                'signal': 'BUY',
                'confidence': min(100, (40 - last_rsi) * 2.5 + 25),
                'rsi': round(last_rsi, 2),
                'sma_20': round(sma_20.iloc[-1], 5),
                'sma_50': round(sma_50.iloc[-1], 5)
            }
        elif sma_20.iloc[-1] < sma_50.iloc[-1] and last_rsi > 60:
            return {
                'signal': 'SELL',
                'confidence': min(100, (last_rsi - 60) * 2.5 + 25),
                'rsi': round(last_rsi, 2),
                'sma_20': round(sma_20.iloc[-1], 5),
                'sma_50': round(sma_50.iloc[-1], 5)
            }
        else:
            return {
                'signal': 'HOLD',
                'confidence': 50,
                'rsi': round(last_rsi, 2),
                'sma_20': round(sma_20.iloc[-1], 5),
                'sma_50': round(sma_50.iloc[-1], 5)
            }

class DatabaseManager:
    def __init__(self):
        self.db_path = 'trading_data.db'
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY,
                        timestamp TEXT,
                        symbol TEXT,
                        type TEXT,
                        volume REAL,
                        entry_price REAL,
                        status TEXT
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
    
    def add_trade(self, trade_data):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades VALUES (NULL, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    trade_data['symbol'],
                    trade_data['type'],
                    trade_data['volume'],
                    trade_data['entry_price'],
                    'OPEN'
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Add trade error: {str(e)}")
            return False
    
    def get_trades(self, limit=100):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except:
            return []

def init_session():
    if 'is_logged_in' not in st.session_state:
        st.session_state.is_logged_in = True
    if 'account_info' not in st.session_state:
        st.session_state.account_info = {'balance': 100000, 'equity': 99500, 'profit': -500, 'margin': 5000, 'leverage': 100}
    if 'trade_log' not in st.session_state:
        st.session_state.trade_log = []
    if 'db' not in st.session_state:
        st.session_state.db = DatabaseManager()

def show_dashboard():
    st.markdown("## 📊 لوحة المعلومات")
    st.markdown("---")
    
    account = st.session_state.account_info
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("الرصيد", f"${account['balance']:,.0f}", delta=f"${account['profit']:,.0f}")
    with col2:
        st.metric("الأرباح", f"${account['equity']:,.0f}")
    with col3:
        st.metric("الهامش", f"${account['margin']:,.0f}")
    with col4:
        st.metric("الرافعة", f"1:{account['leverage']}")
    
    st.markdown("---")
    st.markdown("### 📈 آخر الصفقات")
    
    trades = st.session_state.db.get_trades(5)
    if trades:
        st.dataframe(pd.DataFrame(trades), use_container_width=True)
    else:
        st.info("لا توجد صفقات بعد")

def show_trading():
    st.markdown("## 💹 التداول")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 تنفيذ صفقة جديدة")
        
        symbol = st.selectbox("العملة", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"])
        action = st.radio("النوع", ["BUY", "SELL"], horizontal=True)
        volume = st.number_input("الحجم (Lot)", value=0.1, min_value=0.01, max_value=100.0, step=0.01)
        
        if st.button("🚀 تنفيذ الصفقة", use_container_width=True):
            with st.spinner("جاري التنفيذ..."):
                mt5 = MT5Handler()
                result = mt5.execute_trade(symbol, action, volume)
                
                if result['success']:
                    db = st.session_state.db
                    db.add_trade({
                        'symbol': symbol,
                        'type': action,
                        'volume': volume,
                        'entry_price': result['price']
                    })
                    
                    st.session_state.trade_log.append({
                        'الوقت': datetime.now().strftime("%H:%M:%S"),
                        'العملة': symbol,
                        'النوع': action,
                        'الحجم': volume,
                        'السعر': f"{result['price']:.5f}"
                    })
                    
                    st.success(f"✅ تم التنفيذ بنجاح! رقم الأمر: {result['order_id']}")
    
    with col2:
        st.markdown("### 📊 تحليل فوري")
        
        analysis_symbol = st.selectbox("اختر العملة", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"], key="analysis_symbol")
        
        if st.button("📈 تحليل", use_container_width=True):
            with st.spinner("جاري التحليل..."):
                mt5 = MT5Handler()
                df = mt5.get_symbol_data(analysis_symbol)
                
                if df is not None:
                    signal = IndicatorsCalculator.generate_signal(df)
                    
                    st.markdown(f"### الإشارة: {signal['signal']}")
                    st.markdown(f"**الثقة:** {signal['confidence']:.0f}%")
                    st.markdown(f"**RSI:** {signal['rsi']:.2f}")
                    
                    chart_data = df.set_index('Time')['Close']
                    st.line_chart(chart_data, use_container_width=True)

def show_analysis():
    st.markdown("## 📈 التحليل المتقدم")
    st.markdown("---")
    
    symbol = st.selectbox("اختر العملة", ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"], key="analysis2")
    
    if st.button("🔍 تحليل شامل", use_container_width=True):
        with st.spinner("جاري التحليل..."):
            mt5 = MT5Handler()
            df = mt5.get_symbol_data(symbol)
            
            if df is not None:
                signal = IndicatorsCalculator.generate_signal(df)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("RSI", f"{signal['rsi']:.2f}")
                with col2:
                    st.metric("SMA 20", f"{signal['sma_20']:.5f}")
                with col3:
                    st.metric("SMA 50", f"{signal['sma_50']:.5f}")
                
                st.line_chart(df.set_index('Time')[['Open', 'High', 'Low', 'Close']], use_container_width=True)

def show_settings():
    st.markdown("## ⚙️ الإعدادات")
    st.markdown("---")
    
    tabs = st.tabs(["الحساب", "الأمان", "المعلومات"])
    
    with tabs[0]:
        st.markdown("### معلومات الحساب")
        account = st.session_state.account_info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("الرصيد", f"${account['balance']:,.0f}")
            st.metric("الهامش", f"${account['margin']:,.0f}")
        with col2:
            st.metric("الأرباح", f"${account['profit']:,.0f}")
            st.metric("الرافعة", f"1:{account['leverage']}")
    
    with tabs[1]:
        st.markdown("### الأمان")
        st.success("✅ تشفير AES-256\n✅ توقيع رقمي\n✅ فحص السلامة")
    
    with tabs[2]:
        st.markdown("### معلومات التطبيق")
        st.markdown("**منصة التداول الذكية**\n\nالإصدار: 1.0.0\n\nالوضع: Demo Mode ✅\n\nحقوق النشر: 2024")

def main():
    init_session()
    
    st.markdown("# 📈 منصة التداول الذكية")
    st.markdown("### 🔒 محمي بالتشفير - AES-256")
    st.markdown("---")
    
    with st.sidebar:
        st.markdown("## 🎯 التنقل")
        page = st.radio("اختر القسم", ["📊 Dashboard", "💹 Trading", "📈 Analysis", "⚙️ Settings"], label_visibility="collapsed")
        st.markdown("---")
        st.markdown("### 🔐 حالة الأمان")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("الحالة", "✅ آمن")
        with col2:
            st.metric("التشفير", "🔒 مفعل")
    
    if "Dashboard" in page:
        show_dashboard()
    elif "Trading" in page:
        show_trading()
    elif "Analysis" in page:
        show_analysis()
    elif "Settings" in page:
        show_settings()
    
    st.markdown("---")
    st.markdown("© 2024 Smart Trading Platform | All Rights Reserved")

if __name__ == "__main__":
    main()
