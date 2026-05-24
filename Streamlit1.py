"""
منصة التداول الشاملة - Trading Platform
متكاملة مع MetaTrader 5 والذكاء الاصطناعي
Developer: AI Expert Trader
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
import base64
import hashlib
from typing import Dict, List, Tuple, Optional
import logging
from functools import wraps
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. إعدادات البيئة والأمان
# ============================================================================

# إعداد Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إعدادات Streamlit
st.set_page_config(
    page_title="منصة التداول الذكية",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تحميل البيئة
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# 2. معالجة الأمان والبيانات الحساسة
# ============================================================================

class SecureStorage:
    """نظام آمن لتخزين البيانات الحساسة"""
    
    @staticmethod
    def encrypt_simple(data: str, key: str = "trading_app_key") -> str:
        """تشفير بسيط للبيانات"""
        return base64.b64encode(data.encode()).decode()
    
    @staticmethod
    def decrypt_simple(encrypted: str, key: str = "trading_app_key") -> str:
        """فك تشفير بسيط"""
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except:
            return ""
    
    @staticmethod
    def init_session_state():
        """تهيئة متغيرات الجلسة الآمنة"""
        if 'mt5_credentials' not in st.session_state:
            st.session_state.mt5_credentials = None
        if 'api_key_openai' not in st.session_state:
            st.session_state.api_key_openai = os.getenv('OPENAI_API_KEY', '')
        if 'is_logged_in' not in st.session_state:
            st.session_state.is_logged_in = False
        if 'trade_log' not in st.session_state:
            st.session_state.trade_log = []
        if 'active_trades' not in st.session_state:
            st.session_state.active_trades = []

# ============================================================================
# 3. كود الاتصال بـ MetaTrader 5
# ============================================================================

class MT5Handler:
    """معالج الاتصال بـ MetaTrader 5"""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MT5Handler, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """تهيئة المعالج"""
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5
            self.initialized = False
        except ImportError:
            logger.warning("MetaTrader5 library not installed. Using demo mode.")
            self.mt5 = None
            self.initialized = False
    
    def connect(self, login: int, password: str, server: str) -> bool:
        """الاتصال بـ MetaTrader 5
        
        Args:
            login: رقم الحساب
            password: كلمة المرور
            server: اسم السيرفر
            
        Returns:
            bool: حالة الاتصال
        """
        try:
            if self.mt5 is None:
                logger.warning("Running in DEMO MODE - MetaTrader5 not available")
                self.initialized = True
                return True
            
            # إذا كان متصلاً بالفعل، قطع الاتصال أولاً
            if self.initialized:
                self.mt5.shutdown()
            
            # محاولة الاتصال
            if not self.mt5.initialize(
                path=None,
                login=login,
                password=password,
                server=server
            ):
                logger.error(f"Failed to initialize MT5: {self.mt5.last_error()}")
                return False
            
            self.initialized = True
            logger.info(f"Successfully connected to MT5 - Login: {login}")
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False
    
    def disconnect(self):
        """قطع الاتصال"""
        try:
            if self.mt5 and self.initialized:
                self.mt5.shutdown()
                self.initialized = False
                logger.info("Disconnected from MT5")
        except Exception as e:
            logger.error(f"Disconnection error: {str(e)}")
    
    def get_account_info(self) -> Dict:
        """الحصول على معلومات الحساب"""
        try:
            if not self.initialized:
                return {}
            
            if self.mt5 is None:
                # Demo data
                return {
                    'balance': 100000,
                    'equity': 99500,
                    'profit': -500,
                    'margin': 5000,
                    'leverage': 100,
                    'currency': 'USD'
                }
            
            account_info = self.mt5.account_info()
            return {
                'balance': account_info.balance,
                'equity': account_info.equity,
                'profit': account_info.profit,
                'margin': account_info.margin,
                'leverage': account_info.leverage,
                'currency': account_info.currency
            }
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {}
    
    @st.cache_data(ttl=300)
    def get_symbol_data(self, symbol: str, timeframe: str = 'H1', 
                       bars: int = 100) -> Optional[pd.DataFrame]:
        """جلب بيانات الرموز
        
        Args:
            symbol: رمز العملة (مثل: EURUSD)
            timeframe: الإطار الزمني (M5, M15, H1, D1)
            bars: عدد البارات
            
        Returns:
            DataFrame: البيانات التاريخية
        """
        try:
            if not self.initialized:
                return None
            
            if self.mt5 is None:
                # توليد بيانات تجريبية
                return self._generate_demo_data(symbol, bars)
            
            # تحويل timeframe إلى ثابت MT5
            timeframe_map = {
                'M1': self.mt5.TIMEFRAME_M1,
                'M5': self.mt5.TIMEFRAME_M5,
                'M15': self.mt5.TIMEFRAME_M15,
                'M30': self.mt5.TIMEFRAME_M30,
                'H1': self.mt5.TIMEFRAME_H1,
                'H4': self.mt5.TIMEFRAME_H4,
                'D1': self.mt5.TIMEFRAME_D1,
                'W1': self.mt5.TIMEFRAME_W1,
                'MN1': self.mt5.TIMEFRAME_MN1,
            }
            
            tf = timeframe_map.get(timeframe, self.mt5.TIMEFRAME_H1)
            
            # جلب البيانات
            rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            
            if rates is None:
                logger.warning(f"No data for {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
            df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            
            return df.sort_values('Time').reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"Error getting symbol data: {str(e)}")
            return None
    
    def _generate_demo_data(self, symbol: str, bars: int) -> pd.DataFrame:
        """توليد بيانات تجريبية للاختبار"""
        dates = pd.date_range(end=datetime.now(), periods=bars, freq='H')
        data = {
            'Time': dates,
            'Open': np.random.uniform(1.0, 1.2, bars),
            'High': np.random.uniform(1.1, 1.3, bars),
            'Low': np.random.uniform(0.9, 1.1, bars),
            'Close': np.random.uniform(1.0, 1.2, bars),
            'Volume': np.random.randint(1000, 10000, bars)
        }
        return pd.DataFrame(data)
    
    def execute_trade(self, symbol: str, action: str, volume: float,
                     price: float = None, stop_loss: float = None,
                     take_profit: float = None) -> Dict:
        """تنفيذ صفقة
        
        Args:
            symbol: رمز العملة
            action: BUY أو SELL
            volume: حجم الصفقة
            price: السعر (None للسوق الحالي)
            stop_loss: وقف الخسارة
            take_profit: جني الأرباح
            
        Returns:
            Dict: نتيجة الصفقة
        """
        try:
            if not self.initialized:
                return {'success': False, 'message': 'Not connected to MT5'}
            
            if self.mt5 is None:
                # مثاكاة صفقة تجريبية
                trade_result = {
                    'success': True,
                    'order_id': np.random.randint(1000000, 9999999),
                    'symbol': symbol,
                    'action': action,
                    'volume': volume,
                    'price': 1.0850,
                    'timestamp': datetime.now(),
                    'message': 'Demo trade executed successfully'
                }
                logger.info(f"Demo trade: {trade_result}")
                return trade_result
            
            # تحديد نوع الأمر
            order_type = self.mt5.ORDER_TYPE_BUY if action.upper() == 'BUY' else self.mt5.ORDER_TYPE_SELL
            
            # إعداد الطلب
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price or self.mt5.symbol_info_tick(symbol).ask,
                "magic": 234000,
                "comment": "Automated Trading Platform",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            if stop_loss:
                request['sl'] = stop_loss
            if take_profit:
                request['tp'] = take_profit
            
            # تنفيذ الطلب
            result = self.mt5.order_send(request)
            
            return {
                'success': result.retcode == self.mt5.TRADE_RETCODE_DONE,
                'order_id': result.order,
                'symbol': symbol,
                'action': action,
                'volume': volume,
                'price': result.price,
                'timestamp': datetime.now(),
                'message': self.mt5.last_error() if result.retcode != self.mt5.TRADE_RETCODE_DONE else 'Trade executed successfully'
            }
            
        except Exception as e:
            logger.error(f"Trade execution error: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'timestamp': datetime.now()
            }
    
    def close_trade(self, ticket: int) -> Dict:
        """إغلاق صفقة مفتوحة"""
        try:
            if not self.initialized or self.mt5 is None:
                return {'success': False, 'message': 'Not connected to MT5'}
            
            # الحصول على معلومات الصفقة
            position = self.mt5.position_get(ticket=ticket)
            if position is None:
                return {'success': False, 'message': 'Position not found'}
            
            # إعداد طلب الإغلاق
            close_order = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": self.mt5.ORDER_TYPE_SELL if position.type == 0 else self.mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "magic": 234000,
                "comment": "Close position",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            result = self.mt5.order_send(close_order)
            
            return {
                'success': result.retcode == self.mt5.TRADE_RETCODE_DONE,
                'message': 'Position closed successfully' if result.retcode == self.mt5.TRADE_RETCODE_DONE else str(result)
            }
        except Exception as e:
            logger.error(f"Error closing trade: {str(e)}")
            return {'success': False, 'message': str(e)}

# ============================================================================
# 4. نظام المؤشرات والاستراتيجية
# ============================================================================

class IndicatorsCalculator:
    """حساب المؤشرات والاستراتيجيات"""
    
    @staticmethod
    def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                            period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """حساب مؤشر SuperTrend
        
        Returns:
            Tuple: (supertrend, direction)
        """
        try:
            import pandas_ta as ta
            supertrend = ta.supertrend(high, low, close, length=period, multiplier=multiplier)
            
            if supertrend is not None and len(supertrend.columns) >= 2:
                return supertrend.iloc[:, 0], supertrend.iloc[:, 2]
            else:
                # حساب يدوي إذا فشل pandas_ta
                return IndicatorsCalculator._calculate_supertrend_manual(
                    high, low, close, period, multiplier
                )
        except ImportError:
            return IndicatorsCalculator._calculate_supertrend_manual(
                high, low, close, period, multiplier
            )
    
    @staticmethod
    def _calculate_supertrend_manual(high: pd.Series, low: pd.Series, close: pd.Series,
                                     period: int, multiplier: float) -> Tuple[pd.Series, pd.Series]:
        """حساب SuperTrend يدوياً"""
        hl2 = (high + low) / 2
        atr = IndicatorsCalculator._calculate_atr(high, low, close, period)
        
        matr = multiplier * atr
        basic_ub = hl2 + matr
        basic_lb = hl2 - matr
        
        final_ub = basic_ub.copy()
        final_lb = basic_lb.copy()
        
        for i in range(1, len(final_ub)):
            final_ub.iloc[i] = basic_ub.iloc[i] if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1] else final_ub.iloc[i-1]
            final_lb.iloc[i] = basic_lb.iloc[i] if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1] else final_lb.iloc[i-1]
        
        supertrend = pd.Series(index=close.index, dtype='float64')
        direction = pd.Series(index=close.index, dtype='int64')
        
        for i in range(len(close)):
            if i == 0:
                supertrend.iloc[i] = final_ub.iloc[i]
                direction.iloc[i] = -1
            else:
                if supertrend.iloc[i-1] == final_ub.iloc[i-1]:
                    supertrend.iloc[i] = final_ub.iloc[i]
                    direction.iloc[i] = -1 if close.iloc[i] <= final_ub.iloc[i] else 1
                else:
                    supertrend.iloc[i] = final_lb.iloc[i]
                    direction.iloc[i] = 1 if close.iloc[i] >= final_lb.iloc[i] else -1
        
        return supertrend, direction
    
    @staticmethod
    def _calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series,
                       period: int = 14) -> pd.Series:
        """حساب Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr
    
    @staticmethod
    def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """حساب مؤشر RSI (Relative Strength Index)"""
        try:
            import pandas_ta as ta
            rsi = ta.rsi(close, length=period)
            return rsi if rsi is not None else IndicatorsCalculator._calculate_rsi_manual(close, period)
        except ImportError:
            return IndicatorsCalculator._calculate_rsi_manual(close, period)
    
    @staticmethod
    def _calculate_rsi_manual(close: pd.Series, period: int = 14) -> pd.Series:
        """حساب RSI يدوياً"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_moving_average(close: pd.Series, period: int) -> pd.Series:
        """حساب المتوسط المتحرك"""
        return close.rolling(window=period).mean()
    
    @staticmethod
    def calculate_short_trade_signal(close: pd.Series, high: pd.Series, 
                                    low: pd.Series) -> pd.Series:
        """حساب إشارة Short Trade Assistant
        
        استراتيجية مخصصة تجمع:
        - تقاطع المتوسطات المتحركة
        - مستويات الدعم والمقاومة
        - تغير الزخم
        """
        try:
            # المتوسطات المتحركة
            sma_20 = IndicatorsCalculator.calculate_moving_average(close, 20)
            sma_50 = IndicatorsCalculator.calculate_moving_average(close, 50)
            
            # التقاطع
            cross_signal = pd.Series(0, index=close.index)
            cross_signal[sma_20 > sma_50] = 1  # إشارة شراء
            cross_signal[sma_20 < sma_50] = -1  # إشارة بيع
            
            # الزخم (Rate of Change)
            momentum = close.pct_change(periods=5)
            
            # الإشارة النهائية
            signal = cross_signal.copy()
            signal[(momentum > 0.005)] = 1  # شراء عند زخم إيجابي قوي
            signal[(momentum < -0.005)] = -1  # بيع عند زخم سلبي قوي
            
            return signal
        except Exception as e:
            logger.error(f"Error calculating short trade signal: {str(e)}")
            return pd.Series(0, index=close.index)
    
    @staticmethod
    def generate_trading_signal(df: pd.DataFrame) -> Dict:
        """توليد إشارات التداول المتكاملة
        
        القاعدة:
        - الشراء: SuperTrend إيجابي + RSI < 40 + Short Trade Assistant = شراء
        - البيع: SuperTrend سلبي + RSI > 60 + Short Trade Assistant = بيع
        """
        try:
            if df is None or len(df) < 50:
                return {'signal': 'HOLD', 'confidence': 0}
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            
            # حساب المؤشرات
            supertrend, direction = IndicatorsCalculator.calculate_supertrend(high, low, close)
            rsi = IndicatorsCalculator.calculate_rsi(close)
            short_signal = IndicatorsCalculator.calculate_short_trade_signal(close, high, low)
            
            # الحصول على آخر قيمة
            st_value = supertrend.iloc[-1]
            rsi_value = rsi.iloc[-1]
            st_direction = direction.iloc[-1]
            short_signal_value = short_signal.iloc[-1]
            
            # منطق اتخاذ القرار
            buy_conditions = (
                st_direction > 0 and  # SuperTrend إيجابي
                rsi_value < 40 and    # RSI منخفض
                short_signal_value > 0  # إشارة Short Trade = شراء
            )
            
            sell_conditions = (
                st_direction < 0 and  # SuperTrend سلبي
                rsi_value > 60 and    # RSI مرتفع
                short_signal_value < 0  # إشارة Short Trade = بيع
            )
            
            # حساب الثقة
            confidence = 0
            if buy_conditions:
             
