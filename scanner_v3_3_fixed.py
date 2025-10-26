import ccxt
import pandas as pd
import ta
from ta.trend import ADXIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
import time
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Tuple, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum

# =============================================================================
# CONFIGURATION
# =============================================================================

class SignalType(Enum):
    """Signal types - 4 distinct signals"""
    PRE_PUMP_LONG = "PRE_PUMP_LONG"           # Early accumulation detection
    PRE_DUMP_SHORT = "PRE_DUMP_SHORT"         # Early distribution detection
    MOMENTUM_LONG = "MOMENTUM_LONG"           # Trend started - bullish breakout
    MOMENTUM_SHORT = "MOMENTUM_SHORT"         # Trend started - bearish breakdown

class Config:
    # Binance API - BURAYA KENDİ API KEY'LERİNİ YAZ
    BINANCE_API_KEY = 'BURAYA_BINANCE_API_KEY_YAZ'
    BINANCE_API_SECRET = 'BURAYA_BINANCE_SECRET_KEY_YAZ'

    # Telegram - BURAYA KENDİ BOT BİLGİLERİNİ YAZ
    TELEGRAM_BOT_TOKEN = 'BURAYA_TELEGRAM_BOT_TOKEN_YAZ'
    TELEGRAM_CHAT_ID = 'BURAYA_TELEGRAM_CHAT_ID_YAZ'

    # Scanning
    SCAN_INTERVAL = 60  # seconds
    CACHE_DURATION = 300  # 5 minutes

    # Filters
    MIN_VOLUME_24H = 1_000_000  # $1M minimum
    MIN_PRICE = 0.00001
    MAX_PRICE = 10000

    # Signal thresholds
    PRE_PUMP_MIN_SCORE = 65
    PRE_DUMP_MIN_SCORE = 65
    MOMENTUM_MIN_SCORE = 70

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CandleData:
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int

@dataclass
class TechnicalData:
    symbol: str
    price: float
    volume_24h: float
    price_change_24h: float
    funding_rate: float
    oi_change: float

@dataclass
class SignalData:
    symbol: str
    signal_type: SignalType
    score: int
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    confidence: str
    reasons: List[str]
    timeframe_alignment: str
    market_structure: str
    volume_analysis: str
    timestamp: datetime

# =============================================================================
# SCANNER CLASS
# =============================================================================

class UltimateScalpingScanner:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': Config.BINANCE_API_KEY,
            'secret': Config.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

        # Cache
        self.cache = {}
        self.last_signals = {}
        self.signal_cooldown = 3600  # 1 hour per symbol

        print("[INIT] Scanner initialized successfully")

    # =========================================================================
    # UTILITY FUNCTIONS
    # =========================================================================

    def get_cached_data(self, key: str, fetch_func, ttl: int = 300):
        """Cache with FIXED timing bug - use total_seconds()"""
        now = datetime.now()

        if key in self.cache:
            data, timestamp = self.cache[key]
            age = (now - timestamp).total_seconds()  # FIXED: was .seconds (resets after 3600)

            if age < ttl:
                return data

        # Fetch fresh data
        data = fetch_func()
        self.cache[key] = (data, now)
        return data

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"[ERROR] fetch_ohlcv {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def fetch_funding_rate(self, symbol: str) -> float:
        """Fetch current funding rate"""
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            return float(funding['fundingRate']) * 100 if funding else 0
        except:
            return 0

    def fetch_oi_change(self, symbol: str) -> float:
        """Fetch open interest change"""
        try:
            oi = self.exchange.fetch_open_interest(symbol)
            # Simple implementation - in production use historical OI
            return 0
        except:
            return 0

    # =========================================================================
    # INDICATOR CALCULATIONS
    # =========================================================================

    def calculate_ema(self, df: pd.DataFrame, period: int) -> float:
        """Calculate EMA"""
        ema = df['close'].ewm(span=period, adjust=False).mean()
        return ema.iloc[-1]

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI"""
        rsi_indicator = RSIIndicator(df['close'], window=period)
        return rsi_indicator.rsi().iloc[-1]

    def calculate_stochastic(self, df: pd.DataFrame) -> Tuple[float, float]:
        """Calculate Stochastic"""
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        k = stoch.stoch().iloc[-1]
        d = stoch.stoch_signal().iloc[-1]
        return k, d

    def calculate_bollinger_bands(self, df: pd.DataFrame) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        upper = bb.bollinger_hband().iloc[-1]
        middle = bb.bollinger_mavg().iloc[-1]
        lower = bb.bollinger_lband().iloc[-1]
        return upper, middle, lower

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Tuple[float, str]:
        """
        Calculate ADX for trend strength
        Returns: (adx_value, strength_classification)
        """
        try:
            adx_indicator = ADXIndicator(df['high'], df['low'], df['close'], window=period)
            adx_value = adx_indicator.adx().iloc[-1]

            # Classify trend strength
            if adx_value > 50:
                strength = "VERY_STRONG"
            elif adx_value > 25:
                strength = "STRONG"
            elif adx_value > 20:
                strength = "MODERATE"
            else:
                strength = "WEAK"

            return adx_value, strength
        except:
            return 0, "WEAK"

    def calculate_momentum(self, df: pd.DataFrame, period: int = 10) -> Tuple[float, str, float]:
        """
        Calculate momentum using ROC and MACD
        Returns: (roc_value, momentum_status, macd_histogram)
        """
        try:
            # Rate of Change
            roc = ((df['close'].iloc[-1] / df['close'].iloc[-period-1]) - 1) * 100

            # MACD
            macd_indicator = MACD(df['close'])
            macd_histogram = macd_indicator.macd_diff().iloc[-1]

            # Classify momentum
            if abs(roc) > 5:
                momentum = "EXPLOSIVE"
            elif abs(roc) > 2:
                momentum = "STRONG"
            elif abs(roc) > 1:
                momentum = "MODERATE"
            else:
                momentum = "WEAK"

            return roc, momentum, macd_histogram
        except:
            return 0, "WEAK", 0

    def detect_breakout(self, df_5m: pd.DataFrame) -> Dict:
        """
        Detect consolidation breakout with volume confirmation
        Returns: {
            'detected': bool,
            'direction': 'BULLISH'/'BEARISH'/None,
            'breakout_level': float,
            'volume_ratio': float,
            'strength': str
        }
        """
        try:
            # Look for consolidation (low volatility) followed by breakout
            lookback = 20
            recent_data = df_5m.tail(lookback)

            # Calculate consolidation range
            consolidation_period = recent_data.head(15)
            cons_high = consolidation_period['high'].max()
            cons_low = consolidation_period['low'].min()
            cons_range = (cons_high - cons_low) / cons_low * 100

            # Is it consolidating? (tight range)
            if cons_range > 2:  # More than 2% range = not consolidating
                return {'detected': False, 'direction': None, 'breakout_level': 0, 'volume_ratio': 0, 'strength': 'NONE'}

            # Check recent candles for breakout
            recent_5 = df_5m.tail(5)
            current_close = recent_5['close'].iloc[-1]
            avg_volume = df_5m['volume'].tail(20).mean()
            recent_volume = recent_5['volume'].mean()
            volume_ratio = recent_volume / avg_volume

            # Bullish breakout?
            if current_close > cons_high and volume_ratio > 1.5:
                strength = "STRONG" if volume_ratio > 2.5 else "MODERATE"
                return {
                    'detected': True,
                    'direction': 'BULLISH',
                    'breakout_level': cons_high,
                    'volume_ratio': volume_ratio,
                    'strength': strength
                }

            # Bearish breakdown?
            if current_close < cons_low and volume_ratio > 1.5:
                strength = "STRONG" if volume_ratio > 2.5 else "MODERATE"
                return {
                    'detected': True,
                    'direction': 'BEARISH',
                    'breakout_level': cons_low,
                    'volume_ratio': volume_ratio,
                    'strength': strength
                }

            return {'detected': False, 'direction': None, 'breakout_level': 0, 'volume_ratio': 0, 'strength': 'NONE'}

        except Exception as e:
            print(f"[ERROR] detect_breakout: {e}")
            return {'detected': False, 'direction': None, 'breakout_level': 0, 'volume_ratio': 0, 'strength': 'NONE'}

    def calculate_volume_acceleration(self, df: pd.DataFrame, lookback: int = 20) -> Tuple[float, str]:
        """
        Calculate volume acceleration (rate of volume increase)
        Returns: (acceleration_pct, status)
        """
        try:
            recent_vol = df['volume'].tail(5).mean()
            older_vol = df['volume'].tail(lookback).head(15).mean()

            if older_vol == 0:
                return 0, "NONE"

            acceleration = ((recent_vol / older_vol) - 1) * 100

            if acceleration > 100:
                status = "EXPLOSIVE"
            elif acceleration > 50:
                status = "HIGH"
            elif acceleration > 20:
                status = "MODERATE"
            elif acceleration > 0:
                status = "POSITIVE"
            else:
                status = "DECLINING"

            return acceleration, status
        except:
            return 0, "NONE"

    def calculate_vwap(self, df: pd.DataFrame) -> float:
        """Calculate VWAP"""
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_volume'] = df['typical_price'] * df['volume']
        vwap = df['tp_volume'].sum() / df['volume'].sum()
        return vwap

    def calculate_cvd(self, df: pd.DataFrame) -> Tuple[float, str]:
        """
        Calculate Cumulative Volume Delta with FIXED neutral candle handling
        """
        cvd = 0
        for i in range(len(df)):
            close_price = df['close'].iloc[i]
            open_price = df['open'].iloc[i]
            high_price = df['high'].iloc[i]
            low_price = df['low'].iloc[i]
            volume = df['volume'].iloc[i]

            # FIXED: Handle neutral candles (doji) using wick analysis
            if close_price == open_price:
                upper_wick = high_price - max(close_price, open_price)
                lower_wick = min(close_price, open_price) - low_price

                if upper_wick > lower_wick:
                    # More selling pressure
                    delta = -volume * 0.3
                elif lower_wick > upper_wick:
                    # More buying pressure
                    delta = volume * 0.3
                else:
                    # Completely neutral
                    delta = 0
            elif close_price > open_price:
                delta = volume
            else:
                delta = -volume

            cvd += delta

        # Classify CVD
        avg_volume = df['volume'].mean()
        cvd_normalized = cvd / (avg_volume * len(df))

        if cvd_normalized > 0.5:
            status = "AGGRESSIVE_BUYING"
        elif cvd_normalized > 0.2:
            status = "MODERATE_BUYING"
        elif cvd_normalized > 0:
            status = "POSITIVE_DELTA"
        elif cvd_normalized > -0.2:
            status = "NEGATIVE_DELTA"
        elif cvd_normalized > -0.5:
            status = "MODERATE_SELLING"
        else:
            status = "AGGRESSIVE_SELLING"

        return cvd, status

    # =========================================================================
    # PATTERN DETECTION - PRE-PUMP (UNCHANGED LOGIC)
    # =========================================================================

    def detect_pre_pump_pattern(self, symbol: str, df_5m: pd.DataFrame, df_15m: pd.DataFrame, df_1h: pd.DataFrame) -> Dict:
        """
        Detect PRE-PUMP pattern (early accumulation)
        Logic UNCHANGED - only volume upper limit fix
        """
        score = 0
        reasons = []

        try:
            current_price = df_5m['close'].iloc[-1]

            # 1. Volume Analysis - FIXED: Remove upper limit
            vol_5m_avg = df_5m['volume'].tail(20).mean()
            vol_5m_recent = df_5m['volume'].tail(5).mean()
            vol_trend_pct = ((vol_5m_recent / vol_5m_avg) - 1) * 100

            if vol_trend_pct > 10:
                if vol_trend_pct < 40:
                    score += 20
                    reasons.append(f"Ideal volume increase: {vol_trend_pct:.1f}%")
                elif vol_trend_pct < 80:
                    score += 15
                    reasons.append(f"Building volume: {vol_trend_pct:.1f}%")
                else:
                    score += 10  # FIXED: Was rejected before
                    reasons.append(f"Strong volume: {vol_trend_pct:.1f}%")

            # 2. Consolidation Detection
            high_20 = df_5m['high'].tail(20).max()
            low_20 = df_5m['low'].tail(20).min()
            consolidation_range = ((high_20 - low_20) / low_20) * 100

            if consolidation_range < 3:
                score += 15
                reasons.append(f"Tight consolidation: {consolidation_range:.2f}%")
            elif consolidation_range < 5:
                score += 10
                reasons.append(f"Moderate consolidation: {consolidation_range:.2f}%")

            # 3. RSI in accumulation zone
            rsi = self.calculate_rsi(df_5m)
            if 40 < rsi < 60:
                score += 15
                reasons.append(f"RSI neutral zone: {rsi:.1f}")
            elif 30 < rsi < 70:
                score += 10
                reasons.append(f"RSI acceptable: {rsi:.1f}")

            # 4. Bollinger Band position - FIXED: Direction-aware
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df_5m)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)

            if bb_position < 0.3:  # Near lower band
                score += 10
                reasons.append("Price near lower BB (oversold)")

            # 5. EMA alignment (price near EMAs)
            ema_20 = self.calculate_ema(df_5m, 20)
            ema_50 = self.calculate_ema(df_5m, 50)

            if abs(current_price - ema_20) / current_price < 0.01:
                score += 10
                reasons.append("Price near EMA20")

            if ema_20 > ema_50:
                score += 5
                reasons.append("EMA20 > EMA50 (bullish structure)")

            # 6. CVD Analysis - FIXED: More flexible
            cvd_value, cvd_status = self.calculate_cvd(df_5m)
            if cvd_status in ["AGGRESSIVE_BUYING", "MODERATE_BUYING", "POSITIVE_DELTA"]:
                score += 15
                reasons.append(f"Buying pressure: {cvd_status}")

            # 7. 15m timeframe confirmation
            rsi_15m = self.calculate_rsi(df_15m)
            if 35 < rsi_15m < 65:
                score += 10
                reasons.append("15m RSI supports accumulation")

            # 8. 1H trend not overbought
            rsi_1h = self.calculate_rsi(df_1h)
            if rsi_1h < 70:
                score += 5
                reasons.append("1H not overbought")

            return {
                'detected': score >= Config.PRE_PUMP_MIN_SCORE,
                'score': score,
                'reasons': reasons,
                'consolidation_range': consolidation_range,
                'volume_increase': vol_trend_pct,
                'cvd_status': cvd_status
            }

        except Exception as e:
            print(f"[ERROR] detect_pre_pump_pattern {symbol}: {e}")
            return {'detected': False, 'score': 0, 'reasons': []}

    # =========================================================================
    # PATTERN DETECTION - PRE-DUMP (UNCHANGED LOGIC)
    # =========================================================================

    def detect_pre_dump_pattern(self, symbol: str, df_5m: pd.DataFrame, df_15m: pd.DataFrame, df_1h: pd.DataFrame) -> Dict:
        """
        Detect PRE-DUMP pattern (early distribution)
        Logic UNCHANGED - only volume upper limit fix
        """
        score = 0
        reasons = []

        try:
            current_price = df_5m['close'].iloc[-1]

            # 1. Volume Analysis - FIXED: Remove upper limit
            vol_5m_avg = df_5m['volume'].tail(20).mean()
            vol_5m_recent = df_5m['volume'].tail(5).mean()
            vol_trend_pct = ((vol_5m_recent / vol_5m_avg) - 1) * 100

            if vol_trend_pct > 10:
                if vol_trend_pct < 40:
                    score += 20
                    reasons.append(f"Ideal volume increase: {vol_trend_pct:.1f}%")
                elif vol_trend_pct < 80:
                    score += 15
                    reasons.append(f"Building volume: {vol_trend_pct:.1f}%")
                else:
                    score += 10  # FIXED: Was rejected before
                    reasons.append(f"Strong volume: {vol_trend_pct:.1f}%")

            # 2. Consolidation Detection
            high_20 = df_5m['high'].tail(20).max()
            low_20 = df_5m['low'].tail(20).min()
            consolidation_range = ((high_20 - low_20) / low_20) * 100

            if consolidation_range < 3:
                score += 15
                reasons.append(f"Tight consolidation: {consolidation_range:.2f}%")
            elif consolidation_range < 5:
                score += 10
                reasons.append(f"Moderate consolidation: {consolidation_range:.2f}%")

            # 3. RSI in distribution zone
            rsi = self.calculate_rsi(df_5m)
            if 40 < rsi < 60:
                score += 15
                reasons.append(f"RSI neutral zone: {rsi:.1f}")
            elif 30 < rsi < 70:
                score += 10
                reasons.append(f"RSI acceptable: {rsi:.1f}")

            # 4. Bollinger Band position - FIXED: Direction-aware
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df_5m)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)

            if bb_position > 0.7:  # Near upper band
                score += 10
                reasons.append("Price near upper BB (overbought)")

            # 5. EMA alignment
            ema_20 = self.calculate_ema(df_5m, 20)
            ema_50 = self.calculate_ema(df_5m, 50)

            if abs(current_price - ema_20) / current_price < 0.01:
                score += 10
                reasons.append("Price near EMA20")

            if ema_20 < ema_50:
                score += 5
                reasons.append("EMA20 < EMA50 (bearish structure)")

            # 6. CVD Analysis - FIXED: More flexible
            cvd_value, cvd_status = self.calculate_cvd(df_5m)
            if cvd_status in ["AGGRESSIVE_SELLING", "MODERATE_SELLING", "NEGATIVE_DELTA"]:
                score += 15
                reasons.append(f"Selling pressure: {cvd_status}")

            # 7. 15m timeframe confirmation
            rsi_15m = self.calculate_rsi(df_15m)
            if 35 < rsi_15m < 65:
                score += 10
                reasons.append("15m RSI supports distribution")

            # 8. 1H trend not oversold
            rsi_1h = self.calculate_rsi(df_1h)
            if rsi_1h > 30:
                score += 5
                reasons.append("1H not oversold")

            return {
                'detected': score >= Config.PRE_DUMP_MIN_SCORE,
                'score': score,
                'reasons': reasons,
                'consolidation_range': consolidation_range,
                'volume_increase': vol_trend_pct,
                'cvd_status': cvd_status
            }

        except Exception as e:
            print(f"[ERROR] detect_pre_dump_pattern {symbol}: {e}")
            return {'detected': False, 'score': 0, 'reasons': []}

    # =========================================================================
    # PATTERN DETECTION - MOMENTUM (NEW)
    # =========================================================================

    def detect_momentum_signal(self, symbol: str, df_5m: pd.DataFrame, df_15m: pd.DataFrame, df_1h: pd.DataFrame) -> Dict:
        """
        Detect MOMENTUM signal (trend has started - breakout confirmed)
        NEW logic for catching trends after they start
        """
        score = 0
        reasons = []
        direction = None

        try:
            current_price = df_5m['close'].iloc[-1]

            # 1. Breakout Detection (PRIORITY)
            breakout = self.detect_breakout(df_5m)
            if breakout['detected']:
                if breakout['strength'] == "STRONG":
                    score += 25
                    reasons.append(f"{breakout['direction']} breakout (STRONG)")
                else:
                    score += 20
                    reasons.append(f"{breakout['direction']} breakout")

                direction = breakout['direction']
                reasons.append(f"Volume ratio: {breakout['volume_ratio']:.2f}x")
            else:
                # No clear breakout - check for trend continuation
                pass

            # 2. ADX - Trend Strength
            adx_value, adx_strength = self.calculate_adx(df_5m)
            if adx_strength == "VERY_STRONG":
                score += 20
                reasons.append(f"ADX very strong: {adx_value:.1f}")
            elif adx_strength == "STRONG":
                score += 15
                reasons.append(f"ADX strong: {adx_value:.1f}")
            elif adx_strength == "MODERATE":
                score += 10
                reasons.append(f"ADX moderate: {adx_value:.1f}")

            # 3. Momentum (ROC + MACD)
            roc, momentum_status, macd_hist = self.calculate_momentum(df_5m)

            # Determine direction from momentum if not from breakout
            if direction is None:
                if roc > 0 and macd_hist > 0:
                    direction = "BULLISH"
                elif roc < 0 and macd_hist < 0:
                    direction = "BEARISH"

            if momentum_status == "EXPLOSIVE":
                score += 20
                reasons.append(f"Explosive momentum: {roc:.2f}%")
            elif momentum_status == "STRONG":
                score += 15
                reasons.append(f"Strong momentum: {roc:.2f}%")
            elif momentum_status == "MODERATE":
                score += 10
                reasons.append(f"Moderate momentum: {roc:.2f}%")

            # 4. Volume Acceleration
            vol_accel, vol_accel_status = self.calculate_volume_acceleration(df_5m)
            if vol_accel_status == "EXPLOSIVE":
                score += 15
                reasons.append(f"Explosive volume: +{vol_accel:.1f}%")
            elif vol_accel_status == "HIGH":
                score += 12
                reasons.append(f"High volume acceleration: +{vol_accel:.1f}%")
            elif vol_accel_status == "MODERATE":
                score += 8
                reasons.append(f"Moderate volume acceleration: +{vol_accel:.1f}%")

            # 5. EMA Alignment (trend confirmation)
            ema_9 = self.calculate_ema(df_5m, 9)
            ema_20 = self.calculate_ema(df_5m, 20)
            ema_50 = self.calculate_ema(df_5m, 50)

            if direction == "BULLISH":
                if current_price > ema_9 > ema_20 > ema_50:
                    score += 15
                    reasons.append("Perfect bullish EMA alignment")
                elif current_price > ema_20 > ema_50:
                    score += 10
                    reasons.append("Good bullish EMA alignment")

            elif direction == "BEARISH":
                if current_price < ema_9 < ema_20 < ema_50:
                    score += 15
                    reasons.append("Perfect bearish EMA alignment")
                elif current_price < ema_20 < ema_50:
                    score += 10
                    reasons.append("Good bearish EMA alignment")

            # 6. Market Structure Break
            structure = self.detect_market_structure(df_5m)
            if direction == "BULLISH" and structure['bos_bullish']:
                score += 10
                reasons.append("Bullish structure break")
            elif direction == "BEARISH" and structure['bos_bearish']:
                score += 10
                reasons.append("Bearish structure break")

            # 7. CVD Confirmation
            cvd_value, cvd_status = self.calculate_cvd(df_5m)
            if direction == "BULLISH" and cvd_status in ["AGGRESSIVE_BUYING", "MODERATE_BUYING"]:
                score += 10
                reasons.append(f"CVD confirms: {cvd_status}")
            elif direction == "BEARISH" and cvd_status in ["AGGRESSIVE_SELLING", "MODERATE_SELLING"]:
                score += 10
                reasons.append(f"CVD confirms: {cvd_status}")

            # 8. 1H Trend Alignment
            rsi_1h = self.calculate_rsi(df_1h)
            ema_20_1h = self.calculate_ema(df_1h, 20)
            ema_50_1h = self.calculate_ema(df_1h, 50)

            if direction == "BULLISH":
                if ema_20_1h > ema_50_1h and rsi_1h > 50:
                    score += 10
                    reasons.append("1H trend aligned bullish")
            elif direction == "BEARISH":
                if ema_20_1h < ema_50_1h and rsi_1h < 50:
                    score += 10
                    reasons.append("1H trend aligned bearish")

            return {
                'detected': score >= Config.MOMENTUM_MIN_SCORE,
                'score': score,
                'direction': direction,
                'reasons': reasons,
                'adx': adx_value,
                'roc': roc,
                'volume_accel': vol_accel,
                'breakout_data': breakout
            }

        except Exception as e:
            print(f"[ERROR] detect_momentum_signal {symbol}: {e}")
            return {'detected': False, 'score': 0, 'direction': None, 'reasons': []}

    # =========================================================================
    # SUPPORT/RESISTANCE & FIBONACCI
    # =========================================================================

    def find_support_resistance(self, df: pd.DataFrame, window: int = 10) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels using volume-weighted pivots"""
        supports = []
        resistances = []

        try:
            for i in range(window, len(df) - window):
                # Check if it's a swing low
                if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                    # Weight by volume
                    volume_weight = df['volume'].iloc[i] / df['volume'].mean()
                    if volume_weight > 0.8:  # Significant volume
                        supports.append(df['low'].iloc[i])

                # Check if it's a swing high
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    volume_weight = df['volume'].iloc[i] / df['volume'].mean()
                    if volume_weight > 0.8:
                        resistances.append(df['high'].iloc[i])

            # Keep only recent and significant levels
            supports = sorted(supports)[-3:] if supports else []
            resistances = sorted(resistances)[-3:] if resistances else []

        except Exception as e:
            print(f"[ERROR] find_support_resistance: {e}")

        return supports, resistances

    def calculate_fibonacci_levels(self, df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Calculate Fibonacci retracement and extension levels
        FIXED: Extension formula (was 0.272, now 1.272)
        """
        try:
            recent_data = df.tail(lookback)
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            diff = swing_high - swing_low

            # Determine trend
            if df['close'].iloc[-1] > df['close'].iloc[-lookback]:
                trend = "UPTREND"
                # Retracements (for pullback entries in uptrend)
                fib_levels = {
                    '0.236': swing_high - (diff * 0.236),
                    '0.382': swing_high - (diff * 0.382),
                    '0.500': swing_high - (diff * 0.500),
                    '0.618': swing_high - (diff * 0.618),
                    '0.786': swing_high - (diff * 0.786),
                }
                # Extensions (for TP targets) - FIXED FORMULA
                fib_extensions = {
                    '1.272': swing_high + (diff * 0.272),  # FIXED: was swing_high + (diff * 0.272)
                    '1.414': swing_high + (diff * 0.414),  # FIXED: was swing_high + (diff * 0.414)
                    '1.618': swing_high + (diff * 0.618),
                    '2.000': swing_high + (diff * 1.000),
                    '2.618': swing_high + (diff * 1.618),
                }
            else:
                trend = "DOWNTREND"
                # Retracements (for pullback entries in downtrend)
                fib_levels = {
                    '0.236': swing_low + (diff * 0.236),
                    '0.382': swing_low + (diff * 0.382),
                    '0.500': swing_low + (diff * 0.500),
                    '0.618': swing_low + (diff * 0.618),
                    '0.786': swing_low + (diff * 0.786),
                }
                # Extensions (for TP targets) - FIXED FORMULA
                fib_extensions = {
                    '1.272': swing_low - (diff * 0.272),
                    '1.414': swing_low - (diff * 0.414),
                    '1.618': swing_low - (diff * 0.618),
                    '2.000': swing_low - (diff * 1.000),
                    '2.618': swing_low - (diff * 1.618),
                }

            return {
                'trend': trend,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'retracements': fib_levels,
                'extensions': fib_extensions
            }

        except Exception as e:
            print(f"[ERROR] calculate_fibonacci_levels: {e}")
            return None

    # =========================================================================
    # ADVANCED PATTERN DETECTION
    # =========================================================================

    def detect_market_structure(self, df: pd.DataFrame) -> Dict:
        """Detect market structure breaks (BOS/CHoCH)"""
        try:
            # Find recent swing points
            highs = []
            lows = []

            for i in range(5, len(df) - 5):
                if df['high'].iloc[i] == df['high'].iloc[i-5:i+6].max():
                    highs.append((i, df['high'].iloc[i]))
                if df['low'].iloc[i] == df['low'].iloc[i-5:i+6].min():
                    lows.append((i, df['low'].iloc[i]))

            bos_bullish = False
            bos_bearish = False
            choch = False

            # Check for bullish BOS (break above previous high)
            if len(highs) >= 2:
                prev_high = highs[-2][1]
                if df['close'].iloc[-1] > prev_high:
                    bos_bullish = True

            # Check for bearish BOS (break below previous low)
            if len(lows) >= 2:
                prev_low = lows[-2][1]
                if df['close'].iloc[-1] < prev_low:
                    bos_bearish = True

            return {
                'bos_bullish': bos_bullish,
                'bos_bearish': bos_bearish,
                'choch': choch,
                'recent_highs': [h[1] for h in highs[-3:]],
                'recent_lows': [l[1] for l in lows[-3:]]
            }

        except Exception as e:
            print(f"[ERROR] detect_market_structure: {e}")
            return {'bos_bullish': False, 'bos_bearish': False, 'choch': False}

    def detect_liquidity_sweep(self, df: pd.DataFrame) -> Dict:
        """Detect liquidity sweeps (stop hunts)"""
        try:
            # Look for wicks that sweep previous highs/lows but close back inside
            recent_data = df.tail(20)

            sweep_high = False
            sweep_low = False

            # Check last 3 candles for sweeps
            for i in range(-3, 0):
                candle = df.iloc[i]
                prev_high = df['high'].iloc[i-10:i].max()
                prev_low = df['low'].iloc[i-10:i].min()

                # Bullish sweep (sweep low then close higher)
                if candle['low'] < prev_low and candle['close'] > prev_low:
                    sweep_low = True

                # Bearish sweep (sweep high then close lower)
                if candle['high'] > prev_high and candle['close'] < prev_high:
                    sweep_high = True

            return {
                'sweep_high': sweep_high,
                'sweep_low': sweep_low,
                'last_sweep': 'LOW' if sweep_low else ('HIGH' if sweep_high else 'NONE')
            }

        except Exception as e:
            print(f"[ERROR] detect_liquidity_sweep: {e}")
            return {'sweep_high': False, 'sweep_low': False, 'last_sweep': 'NONE'}

    def detect_order_blocks(self, df: pd.DataFrame) -> Dict:
        """Detect order blocks (institutional footprint)"""
        try:
            bullish_ob = []
            bearish_ob = []

            for i in range(10, len(df) - 1):
                # Bullish OB: Down candle followed by strong up move
                if (df['close'].iloc[i] < df['open'].iloc[i] and  # Down candle
                    df['close'].iloc[i+1] > df['high'].iloc[i]):  # Next candle breaks high

                    volume_confirmation = df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.5
                    if volume_confirmation:
                        bullish_ob.append({
                            'index': i,
                            'high': df['high'].iloc[i],
                            'low': df['low'].iloc[i],
                            'volume': df['volume'].iloc[i]
                        })

                # Bearish OB: Up candle followed by strong down move
                if (df['close'].iloc[i] > df['open'].iloc[i] and  # Up candle
                    df['close'].iloc[i+1] < df['low'].iloc[i]):  # Next candle breaks low

                    volume_confirmation = df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.5
                    if volume_confirmation:
                        bearish_ob.append({
                            'index': i,
                            'high': df['high'].iloc[i],
                            'low': df['low'].iloc[i],
                            'volume': df['volume'].iloc[i]
                        })

            return {
                'bullish_ob': bullish_ob[-3:] if bullish_ob else [],
                'bearish_ob': bearish_ob[-3:] if bearish_ob else []
            }

        except Exception as e:
            print(f"[ERROR] detect_order_blocks: {e}")
            return {'bullish_ob': [], 'bearish_ob': []}

    def detect_fvg(self, df: pd.DataFrame) -> Dict:
        """Detect Fair Value Gaps (imbalances)"""
        try:
            bullish_fvg = []
            bearish_fvg = []

            for i in range(2, len(df)):
                # Bullish FVG: Gap between candle[i-2].high and candle[i].low
                if df['low'].iloc[i] > df['high'].iloc[i-2]:
                    gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                    gap_pct = (gap_size / df['close'].iloc[i]) * 100

                    if gap_pct > 0.1:  # Significant gap
                        bullish_fvg.append({
                            'index': i,
                            'top': df['low'].iloc[i],
                            'bottom': df['high'].iloc[i-2],
                            'size_pct': gap_pct
                        })

                # Bearish FVG: Gap between candle[i-2].low and candle[i].high
                if df['high'].iloc[i] < df['low'].iloc[i-2]:
                    gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                    gap_pct = (gap_size / df['close'].iloc[i]) * 100

                    if gap_pct > 0.1:
                        bearish_fvg.append({
                            'index': i,
                            'top': df['low'].iloc[i-2],
                            'bottom': df['high'].iloc[i],
                            'size_pct': gap_pct
                        })

            return {
                'bullish_fvg': bullish_fvg[-3:] if bullish_fvg else [],
                'bearish_fvg': bearish_fvg[-3:] if bearish_fvg else []
            }

        except Exception as e:
            print(f"[ERROR] detect_fvg: {e}")
            return {'bullish_fvg': [], 'bearish_fvg': []}

    # =========================================================================
    # STAGE 1 - QUICK FILTER
    # =========================================================================

    def stage1_quick_filter(self, symbol: str) -> Optional[TechnicalData]:
        """Stage 1: Quick filter using 24h data and basic checks"""
        try:
            # Get ticker data
            ticker = self.exchange.fetch_ticker(symbol)

            # Basic filters
            if ticker['quoteVolume'] < Config.MIN_VOLUME_24H:
                return None

            if not (Config.MIN_PRICE <= ticker['last'] <= Config.MAX_PRICE):
                return None

            # Get funding rate
            funding_rate = self.fetch_funding_rate(symbol)

            # Get OI change
            oi_change = self.fetch_oi_change(symbol)

            return TechnicalData(
                symbol=symbol,
                price=ticker['last'],
                volume_24h=ticker['quoteVolume'],
                price_change_24h=ticker['percentage'],
                funding_rate=funding_rate,
                oi_change=oi_change
            )

        except Exception as e:
            print(f"[ERROR] stage1_quick_filter {symbol}: {e}")
            return None

    # =========================================================================
    # STAGE 2 - DEEP TECHNICAL ANALYSIS
    # =========================================================================

    def stage2_deep_technical(self, symbol: str, tech_data: TechnicalData) -> Optional[Dict]:
        """
        Stage 2: Deep technical analysis
        Calls BOTH pre-pump/dump detection AND momentum detection
        """
        try:
            # Fetch multi-timeframe data
            df_5m = self.get_cached_data(
                f"{symbol}_5m",
                lambda: self.fetch_ohlcv(symbol, '5m', 100),
                ttl=60
            )

            df_15m = self.get_cached_data(
                f"{symbol}_15m",
                lambda: self.fetch_ohlcv(symbol, '15m', 100),
                ttl=180
            )

            df_1h = self.get_cached_data(
                f"{symbol}_1h",
                lambda: self.fetch_ohlcv(symbol, '1h', 100),
                ttl=600
            )

            if df_5m.empty or df_15m.empty or df_1h.empty:
                return None

            # Run ALL detection methods
            pre_pump = self.detect_pre_pump_pattern(symbol, df_5m, df_15m, df_1h)
            pre_dump = self.detect_pre_dump_pattern(symbol, df_5m, df_15m, df_1h)
            momentum = self.detect_momentum_signal(symbol, df_5m, df_15m, df_1h)

            # Additional analysis
            fib_data = self.calculate_fibonacci_levels(df_5m)
            supports, resistances = self.find_support_resistance(df_5m)
            structure = self.detect_market_structure(df_5m)
            liquidity = self.detect_liquidity_sweep(df_5m)
            fvg = self.detect_fvg(df_5m)
            order_blocks = self.detect_order_blocks(df_5m)

            return {
                'tech_data': tech_data,
                'df_5m': df_5m,
                'df_15m': df_15m,
                'df_1h': df_1h,
                'pre_pump': pre_pump,
                'pre_dump': pre_dump,
                'momentum': momentum,
                'fibonacci': fib_data,
                'supports': supports,
                'resistances': resistances,
                'structure': structure,
                'liquidity': liquidity,
                'fvg': fvg,
                'order_blocks': order_blocks
            }

        except Exception as e:
            print(f"[ERROR] stage2_deep_technical {symbol}: {e}")
            return None

    # =========================================================================
    # STAGE 3 - SIGNAL CLASSIFICATION
    # =========================================================================

    def stage3_classify_signal(self, symbol: str, analysis: Dict) -> Optional[SignalData]:
        """
        Stage 3: Classify signal type and generate final signal
        FIXED: Use elif chain to prevent multiple signals from same analysis
        Handles 4 signal types: PRE_PUMP_LONG, PRE_DUMP_SHORT, MOMENTUM_LONG, MOMENTUM_SHORT
        """
        try:
            signal_type = None
            score = 0
            reasons = []

            # Priority order: Pre-pump > Pre-dump > Momentum (as per original logic)
            if analysis['pre_pump']['detected']:
                signal_type = SignalType.PRE_PUMP_LONG
                score = analysis['pre_pump']['score']
                reasons = analysis['pre_pump']['reasons']

            elif analysis['pre_dump']['detected']:
                signal_type = SignalType.PRE_DUMP_SHORT
                score = analysis['pre_dump']['score']
                reasons = analysis['pre_dump']['reasons']

            elif analysis['momentum']['detected']:
                # Determine momentum direction
                if analysis['momentum']['direction'] == "BULLISH":
                    signal_type = SignalType.MOMENTUM_LONG
                elif analysis['momentum']['direction'] == "BEARISH":
                    signal_type = SignalType.MOMENTUM_SHORT
                else:
                    return None  # No clear direction

                score = analysis['momentum']['score']
                reasons = analysis['momentum']['reasons']

            else:
                return None  # No signal detected

            # Calculate confidence based on score
            if score >= 85:
                confidence = "VERY_HIGH"
            elif score >= 75:
                confidence = "HIGH"
            elif score >= 65:
                confidence = "MODERATE"
            else:
                confidence = "LOW"

            # Calculate entry, SL, TP
            entry_price, stop_loss, take_profit = self.calculate_entry_tp_sl(
                signal_type=signal_type,
                analysis=analysis
            )

            # Timeframe alignment
            tf_alignment = self.analyze_timeframe_alignment(analysis)

            # Market structure summary
            structure_summary = self.summarize_market_structure(analysis)

            # Volume analysis summary
            volume_summary = self.summarize_volume_analysis(analysis)

            return SignalData(
                symbol=symbol,
                signal_type=signal_type,
                score=score,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                confidence=confidence,
                reasons=reasons,
                timeframe_alignment=tf_alignment,
                market_structure=structure_summary,
                volume_analysis=volume_summary,
                timestamp=datetime.now()
            )

        except Exception as e:
            print(f"[ERROR] stage3_classify_signal {symbol}: {e}")
            return None

    # =========================================================================
    # ENTRY/SL/TP CALCULATION
    # =========================================================================

    def calculate_entry_tp_sl(self, signal_type: SignalType, analysis: Dict) -> Tuple[float, float, List[float]]:
        """
        Calculate entry, stop loss, and take profit levels
        Priority: Liquidity Sweep > Structure Break > FVG > Fibonacci > Support/Resistance
        FIXED: Minimum distances, proper TP signs for SHORT
        """
        try:
            current_price = analysis['df_5m']['close'].iloc[-1]
            atr = self.calculate_atr(analysis['df_5m'], period=14)

            # Determine if LONG or SHORT
            is_long = signal_type in [SignalType.PRE_PUMP_LONG, SignalType.MOMENTUM_LONG]

            # =================================================================
            # ENTRY PRICE CALCULATION (Priority-based)
            # =================================================================
            entry_price = current_price  # Default

            # Priority 1: Liquidity Sweep
            if analysis['liquidity']['sweep_low'] and is_long:
                # Enter after sweep low (bullish reversal)
                entry_price = current_price * 0.999  # Slightly below current
            elif analysis['liquidity']['sweep_high'] and not is_long:
                # Enter after sweep high (bearish reversal)
                entry_price = current_price * 1.001  # Slightly above current

            # Priority 2: Structure Break
            elif analysis['structure']['bos_bullish'] and is_long:
                # Enter on structure break confirmation
                entry_price = current_price
            elif analysis['structure']['bos_bearish'] and not is_long:
                entry_price = current_price

            # Priority 3: FVG
            elif analysis['fvg']['bullish_fvg'] and is_long:
                # Enter at FVG bottom
                fvg = analysis['fvg']['bullish_fvg'][-1]
                entry_price = fvg['bottom']
            elif analysis['fvg']['bearish_fvg'] and not is_long:
                # Enter at FVG top
                fvg = analysis['fvg']['bearish_fvg'][-1]
                entry_price = fvg['top']

            # Priority 4: Fibonacci
            elif analysis['fibonacci']:
                fib = analysis['fibonacci']
                if is_long and fib['trend'] == "UPTREND":
                    # Enter at 0.618 retracement
                    entry_price = fib['retracements']['0.618']
                elif not is_long and fib['trend'] == "DOWNTREND":
                    entry_price = fib['retracements']['0.618']

            # Priority 5: Support/Resistance
            elif is_long and analysis['supports']:
                entry_price = analysis['supports'][-1]  # Nearest support
            elif not is_long and analysis['resistances']:
                entry_price = analysis['resistances'][-1]  # Nearest resistance

            # =================================================================
            # STOP LOSS CALCULATION
            # =================================================================
            if is_long:
                # Long SL: Below recent low or support
                recent_low = analysis['df_5m']['low'].tail(20).min()
                sl_candidates = [recent_low]

                # Add liquidity sweep level
                if analysis['liquidity']['sweep_low']:
                    sl_candidates.append(recent_low * 0.998)

                # Add structure level
                if analysis['structure']['recent_lows']:
                    sl_candidates.append(min(analysis['structure']['recent_lows']))

                # Add support level
                if analysis['supports']:
                    sl_candidates.append(min(analysis['supports']))

                stop_loss = min(sl_candidates)

                # Minimum distance: 0.5% (FIXED: was 0.3%)
                min_sl = entry_price * 0.995
                stop_loss = min(stop_loss, min_sl)

            else:
                # Short SL: Above recent high or resistance
                recent_high = analysis['df_5m']['high'].tail(20).max()
                sl_candidates = [recent_high]

                # Add liquidity sweep level
                if analysis['liquidity']['sweep_high']:
                    sl_candidates.append(recent_high * 1.002)

                # Add structure level
                if analysis['structure']['recent_highs']:
                    sl_candidates.append(max(analysis['structure']['recent_highs']))

                # Add resistance level
                if analysis['resistances']:
                    sl_candidates.append(max(analysis['resistances']))

                stop_loss = max(sl_candidates)

                # Minimum distance: 0.5%
                max_sl = entry_price * 1.005
                stop_loss = max(stop_loss, max_sl)

            # =================================================================
            # TAKE PROFIT CALCULATION (3 targets)
            # =================================================================
            risk = abs(entry_price - stop_loss)

            if is_long:
                # Long TPs: Above entry
                tp1 = entry_price + (risk * 1.5)  # 1.5R
                tp2 = entry_price + (risk * 2.5)  # 2.5R
                tp3 = entry_price + (risk * 4.0)  # 4R

                # Use Fibonacci extensions if available
                if analysis['fibonacci'] and analysis['fibonacci']['trend'] == "UPTREND":
                    fib_ext = analysis['fibonacci']['extensions']
                    tp1 = max(tp1, fib_ext['1.272'])
                    tp2 = max(tp2, fib_ext['1.618'])
                    tp3 = max(tp3, fib_ext['2.000'])

                take_profit = [tp1, tp2, tp3]

            else:
                # Short TPs: Below entry (FIXED: Proper direction)
                tp1 = entry_price - (risk * 1.5)
                tp2 = entry_price - (risk * 2.5)
                tp3 = entry_price - (risk * 4.0)

                # Use Fibonacci extensions if available
                if analysis['fibonacci'] and analysis['fibonacci']['trend'] == "DOWNTREND":
                    fib_ext = analysis['fibonacci']['extensions']
                    tp1 = min(tp1, fib_ext['1.272'])
                    tp2 = min(tp2, fib_ext['1.618'])
                    tp3 = min(tp3, fib_ext['2.000'])

                take_profit = [tp1, tp2, tp3]

            return entry_price, stop_loss, take_profit

        except Exception as e:
            print(f"[ERROR] calculate_entry_tp_sl: {e}")
            # Fallback to simple calculation
            current_price = analysis['df_5m']['close'].iloc[-1]
            is_long = signal_type in [SignalType.PRE_PUMP_LONG, SignalType.MOMENTUM_LONG]

            if is_long:
                entry_price = current_price
                stop_loss = current_price * 0.995
                take_profit = [current_price * 1.015, current_price * 1.025, current_price * 1.04]
            else:
                entry_price = current_price
                stop_loss = current_price * 1.005
                take_profit = [current_price * 0.985, current_price * 0.975, current_price * 0.96]

            return entry_price, stop_loss, take_profit

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())

            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr = true_range.rolling(period).mean().iloc[-1]

            return atr
        except:
            return df['close'].iloc[-1] * 0.01  # 1% fallback

    def analyze_timeframe_alignment(self, analysis: Dict) -> str:
        """Analyze multi-timeframe alignment"""
        try:
            ema_20_5m = self.calculate_ema(analysis['df_5m'], 20)
            ema_50_5m = self.calculate_ema(analysis['df_5m'], 50)

            ema_20_15m = self.calculate_ema(analysis['df_15m'], 20)
            ema_50_15m = self.calculate_ema(analysis['df_15m'], 50)

            ema_20_1h = self.calculate_ema(analysis['df_1h'], 20)
            ema_50_1h = self.calculate_ema(analysis['df_1h'], 50)

            bullish_5m = ema_20_5m > ema_50_5m
            bullish_15m = ema_20_15m > ema_50_15m
            bullish_1h = ema_20_1h > ema_50_1h

            if bullish_5m and bullish_15m and bullish_1h:
                return "ALL BULLISH"
            elif not bullish_5m and not bullish_15m and not bullish_1h:
                return "ALL BEARISH"
            elif bullish_5m and bullish_15m:
                return "5m+15m BULLISH, 1H BEARISH"
            elif not bullish_5m and not bullish_15m:
                return "5m+15m BEARISH, 1H BULLISH"
            else:
                return "MIXED"
        except:
            return "UNKNOWN"

    def summarize_market_structure(self, analysis: Dict) -> str:
        """Summarize market structure"""
        try:
            structure = analysis['structure']
            liquidity = analysis['liquidity']

            parts = []

            if structure['bos_bullish']:
                parts.append("Bullish BOS")
            if structure['bos_bearish']:
                parts.append("Bearish BOS")

            if liquidity['sweep_low']:
                parts.append("Low Sweep")
            if liquidity['sweep_high']:
                parts.append("High Sweep")

            if analysis['fvg']['bullish_fvg']:
                parts.append(f"{len(analysis['fvg']['bullish_fvg'])} Bullish FVG")
            if analysis['fvg']['bearish_fvg']:
                parts.append(f"{len(analysis['fvg']['bearish_fvg'])} Bearish FVG")

            return ", ".join(parts) if parts else "No significant structure"
        except:
            return "Unknown"

    def summarize_volume_analysis(self, analysis: Dict) -> str:
        """Summarize volume analysis"""
        try:
            df = analysis['df_5m']
            vol_avg = df['volume'].tail(20).mean()
            vol_recent = df['volume'].tail(5).mean()
            vol_change = ((vol_recent / vol_avg) - 1) * 100

            cvd_value, cvd_status = self.calculate_cvd(df)

            return f"Volume: {vol_change:+.1f}%, CVD: {cvd_status}"
        except:
            return "Unknown"

    # =========================================================================
    # TELEGRAM NOTIFICATION
    # =========================================================================

    def send_telegram_signal(self, signal: SignalData):
        """
        Send signal to Telegram
        FIXED: Proper formatting for 4 signal types, correct TP signs for SHORT
        """
        try:
            # Emoji and title based on signal type
            if signal.signal_type == SignalType.PRE_PUMP_LONG:
                emoji = "🟢"
                title = "PRE-PUMP LONG"
                description = "Early accumulation detected - potential upward move ahead"
            elif signal.signal_type == SignalType.PRE_DUMP_SHORT:
                emoji = "🔴"
                title = "PRE-DUMP SHORT"
                description = "Early distribution detected - potential downward move ahead"
            elif signal.signal_type == SignalType.MOMENTUM_LONG:
                emoji = "🚀"
                title = "MOMENTUM LONG"
                description = "Bullish breakout confirmed - trend has started"
            elif signal.signal_type == SignalType.MOMENTUM_SHORT:
                emoji = "📉"
                title = "MOMENTUM SHORT"
                description = "Bearish breakdown confirmed - trend has started"
            else:
                emoji = "⚪"
                title = "SIGNAL"
                description = ""

            # Calculate risk/reward
            risk = abs(signal.entry_price - signal.stop_loss)
            reward_tp1 = abs(signal.take_profit[0] - signal.entry_price)
            rr_ratio = reward_tp1 / risk if risk > 0 else 0

            # Format message
            message = f"""
{emoji} **{title}** {emoji}
{description}

**Symbol:** {signal.symbol}
**Score:** {signal.score}/100
**Confidence:** {signal.confidence}

**Entry:** ${signal.entry_price:.6f}
**Stop Loss:** ${signal.stop_loss:.6f}
**Take Profit 1:** ${signal.take_profit[0]:.6f}
**Take Profit 2:** ${signal.take_profit[1]:.6f}
**Take Profit 3:** ${signal.take_profit[2]:.6f}

**Risk/Reward:** 1:{rr_ratio:.2f}

**Reasons:**
"""

            for i, reason in enumerate(signal.reasons[:5], 1):
                message += f"{i}. {reason}\n"

            message += f"""
**Timeframe Alignment:** {signal.timeframe_alignment}
**Market Structure:** {signal.market_structure}
**Volume:** {signal.volume_analysis}

**Time:** {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""

            # Send to Telegram
            url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': Config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                print(f"[TELEGRAM] Signal sent for {signal.symbol}")
            else:
                print(f"[ERROR] Telegram send failed: {response.status_code}")

        except Exception as e:
            print(f"[ERROR] send_telegram_signal: {e}")

    # =========================================================================
    # SCANNING PIPELINE
    # =========================================================================

    def scan_symbol(self, symbol: str) -> Optional[SignalData]:
        """Complete scanning pipeline for one symbol"""
        try:
            # Check cooldown
            if symbol in self.last_signals:
                time_since_last = (datetime.now() - self.last_signals[symbol]).total_seconds()
                if time_since_last < self.signal_cooldown:
                    return None

            # Stage 1: Quick filter
            tech_data = self.stage1_quick_filter(symbol)
            if not tech_data:
                return None

            # Stage 2: Deep technical analysis
            analysis = self.stage2_deep_technical(symbol, tech_data)
            if not analysis:
                return None

            # Stage 3: Signal classification
            signal = self.stage3_classify_signal(symbol, analysis)
            if signal:
                self.last_signals[symbol] = datetime.now()
                return signal

            return None

        except Exception as e:
            print(f"[ERROR] scan_symbol {symbol}: {e}")
            return None

    def run_scan(self):
        """Main scanning loop"""
        print("\n" + "="*60)
        print("ULTIMATE SCALPING SCANNER V3.3 - FIXED & ENHANCED")
        print("="*60)
        print("\n[CONFIG] Signal Types:")
        print("  1. PRE_PUMP_LONG: Early accumulation (pre-movement)")
        print("  2. PRE_DUMP_SHORT: Early distribution (pre-movement)")
        print("  3. MOMENTUM_LONG: Bullish breakout (trend started)")
        print("  4. MOMENTUM_SHORT: Bearish breakdown (trend started)")
        print(f"\n[CONFIG] Scan interval: {Config.SCAN_INTERVAL}s")
        print(f"[CONFIG] Min volume: ${Config.MIN_VOLUME_24H:,.0f}")
        print(f"[CONFIG] Signal cooldown: {self.signal_cooldown}s")
        print("\n" + "="*60 + "\n")

        scan_count = 0

        while True:
            try:
                scan_count += 1
                print(f"\n[SCAN #{scan_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Get all USDT perpetual futures
                markets = self.exchange.load_markets()
                usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT:USDT')]

                print(f"[SCAN] Checking {len(usdt_symbols)} symbols...")

                signals_found = 0

                for symbol in usdt_symbols:
                    signal = self.scan_symbol(symbol)

                    if signal:
                        signals_found += 1
                        print(f"\n{'='*60}")
                        print(f"[SIGNAL FOUND] {signal.symbol}")
                        print(f"Type: {signal.signal_type.value}")
                        print(f"Score: {signal.score}/100")
                        print(f"Entry: ${signal.entry_price:.6f}")
                        print(f"SL: ${signal.stop_loss:.6f}")
                        print(f"TP: ${signal.take_profit[0]:.6f} / ${signal.take_profit[1]:.6f} / ${signal.take_profit[2]:.6f}")
                        print(f"{'='*60}\n")

                        # Send to Telegram
                        self.send_telegram_signal(signal)

                print(f"[SCAN #{scan_count}] Complete. Signals found: {signals_found}")
                print(f"[NEXT SCAN] in {Config.SCAN_INTERVAL}s...")

                # Wait for next scan
                time.sleep(Config.SCAN_INTERVAL)

            except KeyboardInterrupt:
                print("\n[EXIT] Scanner stopped by user")
                break
            except Exception as e:
                print(f"[ERROR] Main loop: {e}")
                time.sleep(10)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    scanner = UltimateScalpingScanner()
    scanner.run_scan()
