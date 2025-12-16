import os

# Project Root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(PROJECT_ROOT), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Database
DB_NAME = 'market_data.db'
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# Binance WebSocket
WS_URL = "wss://stream.binance.com:9443"
# Default symbols to track
SYMBOLS = ['btcusdt', 'ethusdt', 'solusdt', 'bnbusdt']

# Analytics
DEFAULT_TIMEFRAME = '1T'  # 1 Minute
