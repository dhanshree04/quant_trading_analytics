import websocket
import json
import threading
import time
from .config import WS_URL, SYMBOLS
from .storage import TradeStore

class BinanceIngestion:
    def __init__(self):
        self.store = TradeStore()
        self.ws = None
        self.running = False
        self.streams = [f"{s}@trade" for s in SYMBOLS]
        self.stream_url = f"{WS_URL}/stream?streams={'/'.join(self.streams)}"
        self.thread = None

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if 'data' in data:
                tick = data['data']
                # tick structure: {e: trade, E: event_time, s: symbol, t: trade_id, p: price, q: quantity, ...}
                self.store.save_tick(tick)
        except Exception as e:
            print(f"Error processing message: {e}")

    def on_error(self, ws, error):
        print(f"WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket Closed")
        self.running = False

    def on_open(self, ws):
        print("WebSocket Connected")

    def _run(self):
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.stream_url,
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                self.ws.run_forever()
            except Exception as e:
                print(f"Connection error: {e}")
                time.sleep(5) # Retry delay

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

# Singleton instance for simple import
ingestion_service = BinanceIngestion()
