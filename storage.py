import sqlite3
import pandas as pd
from datetime import datetime
from .config import DB_PATH

class TradeStore:
    def __init__(self):
        # check_same_thread=False is needed for multi-threaded access (ingestion vs frontend)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        query = """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            price REAL,
            quantity REAL,
            timestamp INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON trades(symbol, timestamp);
        """
        self.conn.executescript(query)
        self.conn.commit()

    def save_tick(self, tick):
        # tick: {s: symbol, p: price, q: qty, T: timestamp}
        query = "INSERT INTO trades (symbol, price, quantity, timestamp) VALUES (?, ?, ?, ?)"
        try:
            self.conn.execute(query, (tick['s'].lower(), float(tick['p']), float(tick['q']), tick['T']))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving tick: {e}")
    
    def get_data(self, symbol, start_ts=None, end_ts=None):
        query = "SELECT timestamp, price, quantity FROM trades WHERE symbol = ?"
        params = [symbol.lower()]
        if start_ts:
            query += " AND timestamp >= ?"
            params.append(start_ts)
        if end_ts:
            query += " AND timestamp <= ?"
            params.append(end_ts)
        
        query += " ORDER BY timestamp ASC"
        
        df = pd.read_sql_query(query, self.conn, params=params)
        if not df.empty:
            # Convert timestamp (ms) to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            # Ensure price/quantity are floats
            df['price'] = df['price'].astype(float)
            df['quantity'] = df['quantity'].astype(float)
        return df

    def get_latest_ticks(self, symbol, limit=100):
        query = "SELECT timestamp, symbol, price, quantity FROM trades WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?"
        df = pd.read_sql_query(query, self.conn, params=[symbol.lower(), limit])
        if not df.empty:
             df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
             df.set_index('timestamp', inplace=True)
             df.sort_index(inplace=True)
        return df
