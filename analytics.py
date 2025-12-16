import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

def resample_data(df, interval='1T'):
    """Resample tick data to OHLCV."""
    if df.empty:
        return pd.DataFrame()
    
    # df has datetime index and 'price', 'quantity'
    ohlc = df['price'].resample(interval).ohlc()
    volume = df['quantity'].resample(interval).sum()
    resampled = pd.concat([ohlc, volume], axis=1)
    resampled.rename(columns={'quantity': 'volume'}, inplace=True)
    # Forward fill price data for gaps, fill volume with 0
    resampled['close'] = resampled['close'].ffill()
    resampled['open'] = resampled['open'].fillna(resampled['close'])
    resampled['high'] = resampled['high'].fillna(resampled['close'])
    resampled['low'] = resampled['low'].fillna(resampled['close'])
    resampled['volume'] = resampled['volume'].fillna(0)
    
    return resampled

def calculate_returns(series):
    """Calculate log returns."""
    return np.log(series / series.shift(1)).dropna()

def calculate_basic_stats(series):
    """Return mean, variance, std."""
    if series.empty:
        return {}
    return {
        'mean': series.mean(),
        'variance': series.var(),
        'std': series.std(),
        'min': series.min(),
        'max': series.max(),
        'last': series.iloc[-1]
    }

def calculate_hedge_ratio(y_series, x_series):
    """Calculate OLS Beta (Hedge Ratio) for Y = alpha + beta * X."""
    # Align data
    df = pd.concat([y_series, x_series], axis=1).dropna()
    if df.empty or len(df) < 5:
        return 0, 0
    
    Y = df.iloc[:, 0]
    X = df.iloc[:, 1]
    X_const = sm.add_constant(X)
    
    try:
        model = sm.OLS(Y, X_const).fit()
        return model.params.iloc[1], model.params.iloc[0] # beta, alpha
    except:
        return 0, 0

def calculate_spread(y_series, x_series, hedge_ratio):
    """Calculate Spread = Y - beta * X."""
    # Ensure alignment
    df = pd.concat([y_series, x_series], axis=1)
    # We can compute spread even if there are NaNs, but best to align
    return df.iloc[:, 0] - hedge_ratio * df.iloc[:, 1]

def calculate_zscore(series, window):
    """Calculate rolling Z-Score."""
    # min_periods=window//2 allows early results
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std()
    zscore = (series - rolling_mean) / rolling_std
    return zscore

def calculate_adf_test(series):
    """Calculate Augmented Dickey-Fuller test p-value."""
    clean_series = series.dropna()
    if len(clean_series) < 10: # Reduced threshold
        return None
    try:
        result = adfuller(clean_series)
        return result[1] # p-value
    except:
        return None

def calculate_rolling_correlation(s1, s2, window):
    """Calculate rolling correlation."""
    return s1.rolling(window=window, min_periods=1).corr(s2)
