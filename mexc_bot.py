import time
import hmac
import hashlib
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from urllib.parse import urlencode
import threading
import queue
import os
from db_manager import DatabaseManager

# הגדרת לוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mexc_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MEXC-TradingBot")

# יצירת חיבור למסד הנתונים
db = DatabaseManager(connection_string="mongodb://localhost:27017/")

class MEXCTradingBot:
    def __init__(self, api_key, api_secret, base_url='https://api.mexc.com', test_mode=True):
        """
        אתחול בוט המסחר של MEXC
        :param api_key: מפתח API מ-MEXC
        :param api_secret: הסיסמה הסודית של ה-API
        :param base_url: כתובת הבסיס של ה-API
        :param test_mode: מצב בדיקה (True) או מסחר אמיתי (False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.test_mode = test_mode
        
        # הגדרות מסחר בסיסיות - תחילה מאתחלים עם ערכי ברירת מחדל 
        self.investment_amount = 100  # סכום ההשקעה בדולרים
        self.trade_size = 10  # גודל כל עסקה בדולרים
        self.current_symbol = None
        self.stop_loss_percent = 1.5  # אחוז הפסד מקסימלי לפני יציאה
        self.take_profit_percent = 2.5  # אחוז רווח לפני מימוש
        
        # הגדרות מסחר מתקדמות
        self.max_watched_symbols = 5  # מספר מקסימלי של מטבעות למעקב
        self.max_positions = 3  # מספר מקסימלי של פוזיציות פתוחות במקביל
        self.symbol_scan_interval = 15  # בדיקת מטבעות חדשים כל X דקות
        self.last_scan_time = 0  # זמן הסריקה האחרונה
        self.max_daily_loss = 20  # הגבלת הפסד יומי (דולרים)
        self.trailing_stop_enabled = True  # האם להפעיל trailing stop
        self.trailing_stop_activation = 1.0  # אחוז רווח להפעלת trailing stop
        self.trailing_stop_distance = 0.5  # מרחק ה-trailing stop באחוזים
        
        # ניהול פוזיציות וסימבולים - יאותחלו מהמסד נתונים
        self.open_positions = {}  # מעקב אחרי פוזיציות פתוחות
        self.profit_loss = 0  # מעקב אחרי רווח/הפסד כולל
        self.watched_symbols = []  # רשימת מטבעות פוטנציאליים למעקב
        self.symbol_details = {}  # פרטים על סימבולים
        
        # טעינת נתונים ממסד הנתונים
        self._load_from_database()
        
        # טעינת הגדרות ממסד הנתונים
        self._load_settings()
        
        # בקרת זרימה
        self.running = False  # דגל לבקרת ריצת הבוט
        
        # מנגנון ניסיונות חוזרים
        self.max_retries = 3
        self.retry_delay = 2  # שניות
        
        # יצירת תיקיות חשובות אם לא קיימות
        self._ensure_directories_exist()
        
        logger.info(f"מאתחל בוט מסחר MEXC {'במצב בדיקה' if test_mode else 'במצב מסחר אמיתי'}")
        logger.info(f"הגדרות: מקסימום {self.max_watched_symbols} מטבעות למעקב, מקסימום {self.max_positions} פוזיציות פתוחות במקביל")
    
    def _ensure_directories_exist(self):
        """וידוא שתיקיות חשובות קיימות"""
        directories = ['logs', 'data', 'backups']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"נוצרה תיקייה: {directory}")
    
    def _load_from_database(self):
        """
        טעינת נתונים ממסד הנתונים
        """
        try:
            # טעינת פוזיציות פתוחות
            self.open_positions = db.get_open_positions()
            logger.info(f"נטענו {len(self.open_positions)} פוזיציות פתוחות ממסד הנתונים")
            
            # טעינת רשימת מטבעות במעקב
            self.watched_symbols = db.get_watched_symbols()
            logger.info(f"נטענו {len(self.watched_symbols)} סימבולים במעקב ממסד הנתונים")
            
            # חישוב רווח/הפסד כולל מהיסטוריית עסקאות
            trades = db.get_trades(limit=1000)
            self.profit_loss = sum(trade.get('profit', 0) for trade in trades if 'profit' in trade)
            logger.info(f"רווח/הפסד כולל שחושב: ${self.profit_loss:.2f}")
            
            # אתחול מילון פרטי סימבולים
            self.symbol_details = {}
            
            # טעינת נתוני סימבולים
            for symbol in self.watched_symbols:
                symbol_data = db.get_symbol_data(symbol)
                if symbol_data:
                    self.symbol_details[symbol] = symbol_data
        except Exception as e:
            logger.error(f"שגיאה בטעינת נתונים ממסד הנתונים: {str(e)}")
            logger.warning("ממשיך עם ערכי ברירת מחדל")
    
    def _load_settings(self):
        """
        טעינת הגדרות ממסד הנתונים
        """
        try:
            settings = db.load_settings()
            
            # עדכון הגדרות הבוט מהמסד נתונים (רק אם קיימות)
            self.investment_amount = settings.get('investment', self.investment_amount)
            self.trade_size = settings.get('trade_size', self.trade_size)
            self.stop_loss_percent = settings.get('stop_loss', self.stop_loss_percent)
            self.take_profit_percent = settings.get('take_profit', self.take_profit_percent)
            self.max_watched_symbols = settings.get('max_watched', self.max_watched_symbols)
            self.max_positions = settings.get('max_positions', self.max_positions)
            self.symbol_scan_interval = settings.get('scan_interval', self.symbol_scan_interval)
            self.max_daily_loss = settings.get('max_daily_loss', self.max_daily_loss)
            self.trailing_stop_enabled = settings.get('trailing_stop_enabled', self.trailing_stop_enabled)
            self.trailing_stop_activation = settings.get('trailing_stop_activation', self.trailing_stop_activation)
            self.trailing_stop_distance = settings.get('trailing_stop_distance', self.trailing_stop_distance)
            
            logger.info("הגדרות נטענו בהצלחה ממסד הנתונים")
        except Exception as e:
            logger.error(f"שגיאה בטעינת הגדרות ממסד הנתונים: {str(e)}")
            logger.warning("ממשיך עם ערכי ברירת מחדל")

    def _generate_signature(self, params):
        """
        יצירת חתימה לאימות מול ה-API
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _send_request(self, method, endpoint, params=None, signed=False):
        """
        שליחת בקשה ל-API של MEXC
        """
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if signed:
            if params is None:
                params = {}
                
            # הוספת timestamp ל-params
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            
            # הוספת API Key
            headers['X-MEXC-APIKEY'] = self.api_key
            
            # יצירת חתימה
            signature = self._generate_signature(params)
            params['signature'] = signature
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=params, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, params=params, headers=headers, timeout=10)
            else:
                logger.error(f"שיטת HTTP לא נתמכת: {method}")
                return None
            
            # בדיקת תגובה מה-API
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"שגיאה בבקשה: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"שגיאה בשליחת בקשה: {str(e)}")
            return None
    
    def _send_request_with_retry(self, method, endpoint, params=None, signed=False):
        """
        שליחת בקשה ל-API עם ניסיונות חוזרים
        """
        for attempt in range(self.max_retries):
            try:
                response = self._send_request(method, endpoint, params, signed)
                if response is not None:
                    return response
                
                # אם הגענו לכאן, הבקשה נכשלה אבל לא הועלתה חריגה
                logger.warning(f"ניסיון {attempt+1}/{self.max_retries} נכשל, מנסה שוב...")
                time.sleep(self.retry_delay * (2 ** attempt))  # המתנה מדורגת
            except Exception as e:
                logger.error(f"שגיאה בניסיון {attempt+1}/{self.max_retries}: {str(e)}")
                
                if attempt == self.max_retries - 1:
                    # זהו הניסיון האחרון, נכשל
                    raise
                
                time.sleep(self.retry_delay * (2 ** attempt))  # המתנה מדורגת
        
        return None
    
    def get_exchange_info(self):
        """
        קבלת מידע על הבורסה וזוגות המסחר הזמינים
        """
        endpoint = '/api/v3/exchangeInfo'
        return self._send_request_with_retry('GET', endpoint)
    
    def get_account_info(self):
        """
        קבלת מידע על החשבון
        """
        endpoint = '/api/v3/account'
        return self._send_request_with_retry('GET', endpoint, signed=True)
    
    def get_klines(self, symbol, interval='1m', limit=100):
        """
        קבלת נתוני נרות (קנדלים) עבור סימבול ספציפי
        :param symbol: סימבול המטבע (לדוגמה 'BTCUSDT')
        :param interval: מרווח זמן (ברירת מחדל: '1m' - דקה)
        :param limit: מספר הנרות לקבל (מקסימום 1000)
        """
        endpoint = '/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = self._send_request_with_retry('GET', endpoint, params)
        if response:
            try:
                # בדיקת מספר העמודות בתשובה מה-API
                columns_count = len(response[0]) if response and len(response) > 0 else 0
                
                # המרת הנתונים ל-DataFrame של pandas - מתאימים את העמודות למספר שמתקבל מה-API
                if columns_count == 8:
                    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume']
                else:
                    # הגדרה מקורית עבור 12 עמודות
                    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 
                              'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
                              'taker_buy_quote', 'ignore']
                    # קטיעת רשימת העמודות אם יש פחות מ-12 עמודות
                    columns = columns[:columns_count]
                
                logger.debug(f"התקבלו {columns_count} עמודות מה-API עבור {symbol}")
                df = pd.DataFrame(response, columns=columns)
                
                # המרת שדות מחיר למספרים
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col])
                
                if 'quote_volume' in df.columns:
                    df['quote_volume'] = pd.to_numeric(df['quote_volume'])
                    
                # המרת timestamp לתאריך קריא
                if 'open_time' in df.columns:
                    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
                if 'close_time' in df.columns:
                    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
                
                return df
            except Exception as e:
                logger.error(f"שגיאה בעיבוד נתוני Klines עבור {symbol}: {str(e)}")
                return None
        
        return None
    
    def place_order(self, symbol, side, order_type, quantity, price=None):
        """
        הנחת הוראת קנייה/מכירה
        :param symbol: סימבול המטבע
        :param side: צד העסקה ('BUY' או 'SELL')
        :param order_type: סוג ההוראה ('LIMIT', 'MARKET')
        :param quantity: כמות המטבע לקנייה/מכירה
        :param price: מחיר (רק עבור הוראות LIMIT)
        """
        try:
            # קבלת מחיר שוק נוכחי לתיעוד אם לא סופק מחיר
            current_price = price
            if current_price is None:
                # קבלת מחיר נוכחי מה-API
                ticker_endpoint = '/api/v3/ticker/price'
                ticker_params = {'symbol': symbol}
                ticker_data = self._send_request_with_retry('GET', ticker_endpoint, ticker_params)
                if ticker_data and 'price' in ticker_data:
                    current_price = float(ticker_data['price'])
                else:
                    logger.warning(f"לא ניתן לקבל מחיר נוכחי עבור {symbol}, משתמש במחיר אחרון ידוע")
                    # אם יש לנו פרטי סימבול, ננסה להשתמש במחיר האחרון שידוע לנו
                    if symbol in self.symbol_details and 'current_price' in self.symbol_details[symbol]:
                        current_price = self.symbol_details[symbol]['current_price']
                    else:
                        logger.error(f"לא ניתן לקבל מחיר כלשהו עבור {symbol}")
                        return None
            
            if self.test_mode:
                logger.info(f"[TEST MODE] הנחת הוראה: {side} {quantity} {symbol} במחיר {current_price if current_price else 'שוק'}")
                
                # סימולציה של ביצוע הוראה במצב בדיקה
                simulated_order = {
                    'symbol': symbol,
                    'orderId': f"test_{int(time.time())}",
                    'side': side,
                    'type': order_type,
                    'quantity': quantity,
                    'price': current_price,
                    'status': 'FILLED',
                    'test': True
                }
                
                # תיעוד העסקה במסד הנתונים
                if side == 'BUY':
                    # תיעוד עסקת קנייה
                    db.log_trade(
                        symbol=symbol,
                        action=side,
                        price=current_price,
                        quantity=quantity,
                        reason="Market order"
                    )
                    
                    # כאשר קונים, מוסיפים לרשימת הפוזיציות הפתוחות
                    stop_loss = current_price * (1 - self.stop_loss_percent/100)
                    take_profit = current_price * (1 + self.take_profit_percent/100)
                    
                    self.open_positions[symbol] = {
                        'entry_price': current_price,
                        'quantity': quantity,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'entry_time': datetime.now(),
                        'current_price': current_price,
                        'highest_price': current_price,  # לצורך trailing stop
                        'has_trailing_stop': False  # האם trailing stop מופעל כרגע
                    }
                    
                    # עדכון במסד הנתונים
                    db.update_open_positions(self.open_positions)
                    
                else:  # SELL
                    # בדיקה אם יש פוזיציה פתוחה לצורך חישוב רווח/הפסד
                    entry_price = None
                    profit = None
                    
                    if symbol in self.open_positions:
                        entry_price = self.open_positions[symbol]['entry_price']
                        profit = (current_price - entry_price) * quantity
                        self.profit_loss += profit
                        
                        # הסרת הפוזיציה מהרשימה
                        del self.open_positions[symbol]
                        
                        # עדכון מסד הנתונים
                        db.update_open_positions(self.open_positions)
                    
                    # תיעוד עסקת מכירה
                    db.log_trade(
                        symbol=symbol,
                        action=side,
                        price=current_price,
                        quantity=quantity,
                        entry_price=entry_price,
                        profit=profit,
                        reason="Market order"
                    )
                
                return simulated_order
            
            # במצב אמיתי
            endpoint = '/api/v3/order'
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'timestamp': int(time.time() * 1000)
            }
            
            if order_type == 'LIMIT':
                if price is None:
                    logger.error("חובה לספק מחיר עבור הוראת LIMIT")
                    return None
                
                params['price'] = price
                params['timeInForce'] = 'GTC'  # Good Till Canceled
            
            # שליחת ההוראה ל-API
            order = self._send_request_with_retry('POST', endpoint, params, signed=True)
            
            if order:
                # תיעוד העסקה במסד הנתונים (רק אם ההוראה הצליחה)
                if side == 'BUY':
                    # תיעוד עסקת קנייה
                    executed_price = float(order.get('price', current_price))
                    executed_qty = float(order.get('executedQty', quantity))
                    
                    db.log_trade(
                        symbol=symbol,
                        action=side,
                        price=executed_price,
                        quantity=executed_qty,
                        reason="Market order"
                    )
                    
                    # כאשר קונים, מוסיפים לרשימת הפוזיציות הפתוחות
                    stop_loss = executed_price * (1 - self.stop_loss_percent/100)
                    take_profit = executed_price * (1 + self.take_profit_percent/100)
                    
                    self.open_positions[symbol] = {
                        'entry_price': executed_price,
                        'quantity': executed_qty,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'entry_time': datetime.now(),
                        'current_price': executed_price,
                        'highest_price': executed_price,  # לצורך trailing stop
                        'has_trailing_stop': False  # האם trailing stop מופעל כרגע
                    }
                    
                    # עדכון במסד הנתונים
                    db.update_open_positions(self.open_positions)
                    
                else:  # SELL
                    # בדיקה אם יש פוזיציה פתוחה לצורך חישוב רווח/הפסד
                    entry_price = None
                    profit = None
                    
                    executed_price = float(order.get('price', current_price))
                    executed_qty = float(order.get('executedQty', quantity))
                    
                    if symbol in self.open_positions:
                        entry_price = self.open_positions[symbol]['entry_price']
                        profit = (executed_price - entry_price) * executed_qty
                        self.profit_loss += profit
                        
                        # הסרת הפוזיציה מהרשימה
                        del self.open_positions[symbol]
                        
                        # עדכון מסד הנתונים
                        db.update_open_positions(self.open_positions)
                    
                    # תיעוד עסקת מכירה
                    db.log_trade(
                        symbol=symbol,
                        action=side,
                        price=executed_price,
                        quantity=executed_qty,
                        entry_price=entry_price,
                        profit=profit,
                        reason="Market order"
                    )
            
            return order
        except Exception as e:
            logger.error(f"שגיאה בהנחת הוראה {side} עבור {symbol}: {str(e)}")
            return None
    
    def cancel_order(self, symbol, order_id):
        """
        ביטול הוראה
        """
        endpoint = '/api/v3/order'
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        
        return self._send_request_with_retry('DELETE', endpoint, params, signed=True)
    
    def get_top_volume_symbols(self, quote_asset='USDT', limit=10):
        """
        מציאת הסימבולים עם הנפח הגבוה ביותר
        :param quote_asset: מטבע הבסיס (ברירת מחדל: USDT)
        :param limit: מספר הסימבולים להחזיר
        """
        endpoint = '/api/v3/ticker/24hr'
        response = self._send_request_with_retry('GET', endpoint)
        
        if response:
            # סינון רק סימבולים עם מטבע הבסיס הנכון
            filtered_symbols = [item for item in response if item['symbol'].endswith(quote_asset)]
            
            # מיון לפי נפח מסחר
            sorted_symbols = sorted(filtered_symbols, key=lambda x: float(x['volume']), reverse=True)
            
            # החזרת הסימבולים המובילים
            return sorted_symbols[:limit]
        
        return []
    
    def find_potential_symbols(self):
        """
        מציאת סימבולים פוטנציאליים למסחר על פי האסטרטגיה
        מחזיר רשימה של סימבולים מדורגים
        """
        # קבלת הסימבולים עם הנפח הגבוה ביותר
        top_symbols = self.get_top_volume_symbols(limit=20)
        
        potential_symbols = []
        
        for symbol_data in top_symbols:
            symbol = symbol_data['symbol']
            logger.info(f"בודק סימבול: {symbol}")
            
            # דילוג על סימבולים שכבר במעקב
            if symbol in self.watched_symbols or symbol in self.open_positions:
                continue
                
            # קבלת נתוני המחיר האחרונים
            klines = self.get_klines(symbol, interval='1m', limit=120)  # 2 שעות של נתוני דקה
            
            if klines is None or len(klines) < 60:
                logger.warning(f"לא מספיק נתונים עבור {symbol}, מדלג")
                continue
                
            # חישוב אינדיקטורים טכניים
            rsi_value = self.calculate_rsi(klines, period=14)
            macd, signal, hist = self.calculate_macd(klines)
            
            # חישוב תנודתיות (Volatility)
            volatility = self.calculate_volatility(klines)
            
            # חישוב Bollinger Bands
            upper, middle, lower = self.calculate_bollinger_bands(klines)
            
            # חישוב Stochastic Oscillator
            k, d = self.calculate_stochastic(klines)
            
            # בדיקת תמונת מסחר אידיאלית:
            # RSI לאחר מתקן מתנאי oversold (30-40) - אות קנייה אפשרי
            # MACD מראה התכנסות או חציית קו האפס
            # תנודתיות בטווח בינוני (לא נמוכה מדי ולא גבוהה מדי)
            
            score = 0
            
            # RSI בטווח אידיאלי
            if 30 <= rsi_value <= 40:  # מצב oversold מתקן - פוטנציאל לעלייה
                score += 3
                logger.debug(f"{symbol}: RSI בטווח אידיאלי ({rsi_value:.2f}), +3 נקודות")
            elif 40 < rsi_value <= 50:  # עדיין בטווח טוב לקנייה
                score += 2
                logger.debug(f"{symbol}: RSI בטווח טוב ({rsi_value:.2f}), +2 נקודות")
            
            # MACD חוצה את קו האות - אפשרות לעלייה
            if hist[-2] < 0 and hist[-1] > 0:
                score += 3
                logger.debug(f"{symbol}: MACD חוצה את קו האפס, +3 נקודות")
            elif hist[-3] < 0 and hist[-2] > 0 and hist[-1] > 0:
                score += 2
                logger.debug(f"{symbol}: MACD מעל קו האפס, +2 נקודות")
            
            # בדיקת תנודתיות - מעדיפים תנודתיות בינונית
            if 0.5 <= volatility <= 2.0:
                score += 2
                logger.debug(f"{symbol}: תנודתיות בינונית ({volatility:.2f}%), +2 נקודות")
            elif 0.3 <= volatility < 0.5 or 2.0 < volatility <= 3.0:
                score += 1
                logger.debug(f"{symbol}: תנודתיות סבירה ({volatility:.2f}%), +1 נקודה")
            
            # בדיקת מגמה קצרת טווח
            short_trend = self.calculate_trend(klines, period=20)
            if short_trend > 0.5:  # מגמה עולה חזקה
                score += 2
                logger.debug(f"{symbol}: מגמה עולה חזקה, +2 נקודות")
            elif 0 < short_trend <= 0.5:  # מגמה עולה מתונה
                score += 1
                logger.debug(f"{symbol}: מגמה עולה מתונה, +1 נקודה")
            
            # בדיקת קרבה לתחתית של Bollinger Bands
            current_price = klines['close'].iloc[-1]
            bb_position = (current_price - lower[-1]) / (upper[-1] - lower[-1])
            
            if bb_position < 0.2:  # קרוב לתחתית של הפס
                score += 2
                logger.debug(f"{symbol}: קרוב לתחתית Bollinger Bands, +2 נקודות")
            elif bb_position < 0.4:
                score += 1
                logger.debug(f"{symbol}: בחלק התחתון של Bollinger Bands, +1 נקודה")
            
            # בדיקת Stochastic Oscillator - אם הוא באזור oversold ומתחיל לעלות
            if k[-1] < 30 and k[-1] > k[-2]:
                score += 2
                logger.debug(f"{symbol}: Stochastic Oscillator באזור oversold ומתחיל לעלות, +2 נקודות")
            
            logger.info(f"{symbol} - ציון: {score}, RSI: {rsi_value:.2f}, MACD Hist: {hist[-1]:.6f}, Volatility: {volatility:.2f}%")
            
            # שמירת סימבולים עם ציון מינימלי
            if score >= 4:
                potential_symbols.append({
                    'symbol': symbol,
                    'score': score,
                    'rsi': rsi_value,
                    'macd_hist': hist[-1],
                    'volatility': volatility,
                    'current_price': current_price,
                    'bb_position': bb_position,
                    'stochastic_k': k[-1],
                    'stochastic_d': d[-1]
                })
        
        # מיון לפי ציון
        potential_symbols = sorted(potential_symbols, key=lambda x: x['score'], reverse=True)
        
        if potential_symbols:
            logger.info(f"נמצאו {len(potential_symbols)} סימבולים פוטנציאליים למסחר")
            for symbol_data in potential_symbols[:3]:  # הצגת 3 המובילים
                logger.info(f"סימבול פוטנציאלי: {symbol_data['symbol']} עם ציון {symbol_data['score']}")
        else:
            logger.info("לא נמצאו סימבולים מתאימים לסחר כרגע")
        
        return potential_symbols
    
    def find_best_symbol(self):
        """
        מציאת הסימבול הטוב ביותר למסחר (גרסה ישנה לצורך תאימות אחורה)
        """
        potential_symbols = self.find_potential_symbols()
        
        if potential_symbols:
            best_symbol = potential_symbols[0]['symbol']
            logger.info(f"נבחר סימבול למסחר: {best_symbol} עם ציון {potential_symbols[0]['score']}")
            return best_symbol
        else:
            logger.info("לא נמצא סימבול מתאים לסחר כרגע")
            return None
    
    def update_watched_symbols(self):
        """
        עדכון רשימת המטבעות במעקב עם נתונים נוספים
        """
        # הסרת סימבולים שאינם רלוונטיים יותר
        self.watched_symbols = [s for s in self.watched_symbols if s not in self.open_positions]
        
        # אם יש מקום לסימבולים נוספים, מוסיף סימבולים פוטנציאליים
        if len(self.watched_symbols) < self.max_watched_symbols:
            potential_symbols = self.find_potential_symbols()
            
            # הוספת סימבולים חדשים עד למגבלה
            for symbol_data in potential_symbols:
                symbol = symbol_data['symbol']
                if symbol not in self.watched_symbols and len(self.watched_symbols) < self.max_watched_symbols:
                    self.watched_symbols.append(symbol)
                    logger.info(f"הוספת {symbol} לרשימת המעקב")
        
        # עדכון רשימת המטבעות במעקב במסד הנתונים
        db.update_watched_symbols(self.watched_symbols)
        
        # עדכון מידע מפורט על כל סימבול
        self.symbol_details = {}
        for symbol in self.watched_symbols:
            try:
                # קבלת נתוני קו זמן
                klines = self.get_klines(symbol, interval='1m', limit=60)
                
                if klines is None or len(klines) < 30:
                    logger.warning(f"לא מספיק נתונים עבור {symbol}")
                    continue
                
                # חישוב אינדיקטורים
                current_price = klines['close'].iloc[-1]
                rsi = self.calculate_rsi(klines)
                macd, signal, hist = self.calculate_macd(klines)
                volatility = self.calculate_volatility(klines)
                upper, middle, lower = self.calculate_bollinger_bands(klines)
                k, d = self.calculate_stochastic(klines)
                
                # חישוב ציון כללי
                score = 0
                if 30 <= rsi <= 50:  # טווח RSI טוב
                    score += 2
                
                if hist[-1] > 0:  # MACD חיובי
                    score += 1
                
                if 0.5 <= volatility <= 2.0:  # תנודתיות סבירה
                    score += 1
                
                # שמירת הפרטים
                self.symbol_details[symbol] = {
                    'current_price': current_price,
                    'rsi': round(rsi, 2),
                    'macd_histogram': round(hist[-1], 4),
                    'volatility': round(volatility, 2),
                    'bollinger_upper': round(upper[-1], 8),
                    'bollinger_middle': round(middle[-1], 8),
                    'bollinger_lower': round(lower[-1], 8),
                    'stochastic_k': round(k[-1], 2),
                    'stochastic_d': round(d[-1], 2),
                    'score': score,
                    'updated_at': datetime.now()
                }
                
                # שמירת מידע הסימבול במסד הנתונים
                db.save_symbol_data(symbol, self.symbol_details[symbol])
                
            except Exception as e:
                logger.error(f"שגיאה בעיבוד נתונים עבור {symbol}: {str(e)}")
        
        logger.info(f"סימבולים במעקב: {', '.join(self.watched_symbols) if self.watched_symbols else 'אין'}")
        logger.info(f"פוזיציות פתוחות: {', '.join(self.open_positions.keys()) if self.open_positions else 'אין'}")
        
        return self.symbol_details
    
    def calculate_rsi(self, df, period=14):
        """
        חישוב אינדיקטור RSI (Relative Strength Index)
        """
        # חישוב שינויים יומיים
        delta = df['close'].diff()
        
        # הפרדה בין ימים חיוביים ושליליים
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # חישוב ממוצע נע של רווחים והפסדים
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # חישוב ה-RS (Relative Strength)
        rs = avg_gain / avg_loss
        
        # חישוב ה-RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]  # החזרת הערך האחרון
    
    def calculate_macd(self, df, fast_period=12, slow_period=26, signal_period=9):
        """
        חישוב אינדיקטור MACD (Moving Average Convergence Divergence)
        """
        # חישוב EMA מהיר ואיטי
        fast_ema = df['close'].ewm(span=fast_period, adjust=False).mean()
        slow_ema = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # חישוב קו ה-MACD
        macd_line = fast_ema - slow_ema
        
        # חישוב קו האות (Signal Line)
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # חישוב ההיסטוגרמה
        histogram = macd_line - signal_line
        
        return macd_line.values, signal_line.values, histogram.values
    
    def calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """
        חישוב Bollinger Bands
        """
        # חישוב SMA
        middle_band = df['close'].rolling(window=period).mean()
        
        # חישוב סטיית תקן
        std = df['close'].rolling(window=period).std()
        
        # חישוב הפסים העליון והתחתון
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band.values, middle_band.values, lower_band.values
    
    def calculate_stochastic(self, df, k_period=14, d_period=3):
        """
        חישוב Stochastic Oscillator
        """
        # חישוב הנמוך והגבוה בתקופה
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        # חישוב %K
        k = 100 * ((df['close'] - low_min) / (high_max - low_min))
        
        # חישוב %D (ממוצע נע של %K)
        d = k.rolling(window=d_period).mean()
        
        return k.values, d.values
    
    def calculate_volatility(self, df, period=14):
        """
        חישוב התנודתיות באחוזים
        """
        # חישוב תנודתיות כאחוז שינוי ביחס למחיר הסגירה
        volatility = (df['high'] / df['low'] - 1) * 100
        return volatility.rolling(window=period).mean().iloc[-1]
    
    def calculate_trend(self, df, period=20):
        """
        חישוב חוזק המגמה
        מחזיר ערך בין -1 ל1, כאשר:
        1 = מגמה עולה חזקה
        -1 = מגמה יורדת חזקה
        0 = אין מגמה ברורה
        """
        # חישוב ממוצע נע פשוט
        sma = df['close'].rolling(window=period).mean()
        
        # חישוב השיפוע של הממוצע הנע
        slope = (sma.iloc[-1] - sma.iloc[-period]) / sma.iloc[-period]
        
        # נרמול לטווח בין -1 ל-1
        normalized_slope = np.tanh(slope * 100)
        
        return normalized_slope
    
    def update_trailing_stop(self, symbol, current_price):
        """
        עדכון trailing stop למקסם רווחים
        """
        if not self.trailing_stop_enabled or symbol not in self.open_positions:
            return False
        
        position = self.open_positions[symbol]
        entry_price = position['entry_price']
        
        # חישוב אחוז רווח נוכחי
        current_profit_percent = (current_price - entry_price) / entry_price * 100
        
        # אם הרווח גבוה מסף ההפעלה של ה-trailing stop ועדיין לא הופעל
        if current_profit_percent >= self.trailing_stop_activation and not position['has_trailing_stop']:
            # הפעלת trailing stop
            position['has_trailing_stop'] = True
            position['highest_price'] = current_price
            
            # עדכון stop loss ל-trailing stop
            new_stop_loss = current_price * (1 - self.trailing_stop_distance/100)
            
            # אם ה-stop loss החדש גבוה יותר מהקיים, עדכן אותו
            if new_stop_loss > position['stop_loss']:
                position['stop_loss'] = new_stop_loss
                logger.info(f"הופעל Trailing Stop ל-{symbol} - SL חדש: {new_stop_loss:.8f}")
                return True
        
        # אם ה-trailing stop כבר פעיל, בדוק אם המחיר הנוכחי גבוה יותר מהשיא הקודם
        elif position['has_trailing_stop'] and current_price > position['highest_price']:
            # עדכון המחיר הגבוה ביותר
            position['highest_price'] = current_price
            
            # עדכון stop loss ל-trailing stop
            new_stop_loss = current_price * (1 - self.trailing_stop_distance/100)
            
            # אם ה-stop loss החדש גבוה יותר מהקיים, עדכן אותו
            if new_stop_loss > position['stop_loss']:
                position['stop_loss'] = new_stop_loss
                logger.info(f"עודכן Trailing Stop ל-{symbol} - SL חדש: {new_stop_loss:.8f}")
                return True
        
        return False
    
    def check_daily_loss_limit(self):
        """
        בדיקת מגבלת הפסד יומי
        """
        # חישוב רווח/הפסד יומי מעסקאות היום
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_trades = db.get_trades(start_date=today_start)
        
        daily_profit_loss = sum(trade.get('profit', 0) for trade in today_trades if 'profit' in trade)
        
        if daily_profit_loss < -self.max_daily_loss:
            logger.warning(f"הגעה למגבלת הפסד יומית: ${daily_profit_loss:.2f}. עוצר מסחר.")
            self.running = False
            return True
        
        return False
    
    def check_entry_conditions(self, symbol):
        """
        בדיקת תנאי כניסה לעסקה עבור סימבול ספציפי
        מחזיר True אם תנאי הכניסה מתקיימים, אחרת False
        """
        # אם כבר יש לנו פוזיציה בסימבול זה, לא נכנסים שוב
        if symbol in self.open_positions:
            logger.debug(f"כבר יש פוזיציה פתוחה עבור {symbol}")
            return False
            
        # אם הגענו למספר המקסימלי של פוזיציות פתוחות
        if len(self.open_positions) >= self.max_positions:
            logger.info(f"הגענו למספר המקסימלי של פוזיציות פתוחות ({self.max_positions})")
            return False
        
        # בדיקת מגבלת הפסד יומי
        if self.check_daily_loss_limit():
            logger.warning("הגענו למגבלת ההפסד היומי, לא נכנסים לעסקאות חדשות")
            return False
            
        # קבלת נתוני מחיר עדכניים
        klines = self.get_klines(symbol, interval='1m', limit=60)
        
        if klines is None or len(klines) < 30:
            logger.warning(f"לא ניתן לקבל מספיק נתונים עבור {symbol}")
            return False
        
        # חישוב אינדיקטורים
        current_price = klines['close'].iloc[-1]
        rsi = self.calculate_rsi(klines)
        macd, signal, hist = self.calculate_macd(klines)
        volatility = self.calculate_volatility(klines)
        upper, middle, lower = self.calculate_bollinger_bands(klines)
        k, d = self.calculate_stochastic(klines)
        
        # בדיקת תנאי קנייה משופרים
        buy_condition = (
            rsi <= 45 and  # RSI נמוך
            hist[-1] > 0 and  # היסטוגרמת MACD חיובית
            hist[-2] < hist[-1] and  # עלייה בהיסטוגרמה
            current_price < middle[-1] and  # מחיר מתחת לממוצע
            k[-1] < 40 and k[-1] > k[-2]  # Stochastic נמוך ומתחיל לעלות
        )
        
        # לוגים מפורטים לאבחון
        logger.info(f"בדיקת תנאי כניסה עבור {symbol}:")
        logger.info(f"מחיר נוכחי: ${current_price}")
        logger.info(f"RSI: {rsi:.2f}")
        logger.info(f"MACD Histogram: {hist[-1]:.4f}")
        logger.info(f"תנודתיות: {volatility:.2f}%")
        logger.info(f"Stochastic %K: {k[-1]:.2f}, %D: {d[-1]:.2f}")
        logger.info(f"תנאי כניסה: {buy_condition}")
        
        # עדכון נתוני הסימבול
        if symbol in self.symbol_details:
            self.symbol_details[symbol].update({
                'current_price': current_price,
                'rsi': round(rsi, 2),
                'macd_histogram': round(hist[-1], 4),
                'volatility': round(volatility, 2),
                'stochastic_k': round(k[-1], 2),
                'stochastic_d': round(d[-1], 2),
                'updated_at': datetime.now()
            })
            
            # שמירה במסד הנתונים
            db.save_symbol_data(symbol, self.symbol_details[symbol])
        
        # בדיקת תנאי כניסה
        if buy_condition:
            logger.info(f"תנאי כניסה התקיימו עבור {symbol}!")
            return True
            
        return False

    def execute_trade_strategy(self, symbol):
        """
        ביצוע אסטרטגיית המסחר עבור סימבול נתון
        """
        logger.info(f"בודק אסטרטגיית מסחר עבור {symbol}")
        
        # קבלת נתוני מחיר עדכניים
        klines = self.get_klines(symbol, interval='1m', limit=60)
        
        if klines is None or len(klines) < 30:
            logger.error(f"לא ניתן לקבל מספיק נתונים עבור {symbol}")
            return False
        
        # חישוב אינדיקטורים
        current_price = klines['close'].iloc[-1]
        rsi = self.calculate_rsi(klines)
        macd, signal, hist = self.calculate_macd(klines)
        
        # בדיקת כמות הפוזיציות הפתוחות
        if len(self.open_positions) >= self.max_positions:
            logger.info(f"מספר מקסימלי של פוזיציות פתוחות ({self.max_positions})")
            return False
        
        # בדיקת תנאי כניסה
        buy_condition = (
            rsi <= 45 and  # RSI נמוך יותר מעט
            hist[-1] > 0 and  # היסטוגרמת MACD חיובית
            hist[-2] < hist[-1]  # עלייה בהיסטוגרמה
        )
        
        # לוגים מפורטים
        logger.info(f"תנאי כניסה לביצוע עסקה ב-{symbol}:")
        logger.info(f"מחיר נוכחי: ${current_price}")
        logger.info(f"RSI: {rsi:.2f}")
        logger.info(f"MACD Histogram: {hist[-1]:.4f}")
        logger.info(f"תנאי כניסה: {buy_condition}")
        
        # ביצוע עסקת קנייה
        if buy_condition:
            try:
                # חישוב כמות לקנייה בהתאם לגודל הסחר המוגדר
                amount_to_invest = min(self.trade_size, self.investment_amount)
                quantity = amount_to_invest / current_price
                
                # עיגול הכמות לפי דרישות הבורסה - נניח שהדיוק הוא 6 ספרות אחרי הנקודה
                quantity = round(quantity, 6)
                
                # ביצוע הזמנת קנייה
                order_result = self.place_order(
                    symbol=symbol, 
                    side='BUY', 
                    order_type='MARKET', 
                    quantity=quantity
                )
                
                if order_result:
                    logger.info(f"נפתחה פוזיציה ב-{symbol} במחיר {current_price}")
                    logger.info(f"כמות: {quantity}, Stop Loss: {self.open_positions[symbol]['stop_loss']}, Take Profit: {self.open_positions[symbol]['take_profit']}")
                    
                    return True
            
            except Exception as e:
                logger.error(f"שגיאה בביצוע עסקה עבור {symbol}: {str(e)}")
                return False
        
        return False

    def multi_symbol_trading(self):
        """
        אסטרטגיית מסחר על מספר סימבולים במקביל
        """
        # מעקב אחרי פוזיציות פתוחות
        self.monitor_open_positions()
        
        # בדיקת מגבלת הפסד יומי
        if self.check_daily_loss_limit():
            logger.warning("הגענו למגבלת ההפסד היומי, מפסיק מסחר")
            return
        
        # בדיקת תנאי כניסה לכל הסימבולים שבמעקב
        for symbol in self.watched_symbols.copy():  # עובדים על העתק של הרשימה כדי למנוע שגיאות
            try:
                # בדיקה אם יש מקום לפוזיציה חדשה
                if len(self.open_positions) < self.max_positions:
                    # בדיקת תנאי כניסה
                    if self.check_entry_conditions(symbol):
                        # ביצוע אסטרטגיית מסחר - כניסה לפוזיציה
                        self.execute_trade_strategy(symbol)
            
            except Exception as e:
                logger.error(f"שגיאה בביצוע אסטרטגיית מסחר עבור {symbol}: {str(e)}")

    def monitor_open_positions(self):
        """
        ניטור פוזיציות פתוחות ובדיקת תנאי יציאה
        """
        for symbol in list(self.open_positions.keys()):
            try:
                # קבלת מחיר עדכני
                klines = self.get_klines(symbol, interval='1m', limit=1)
                
                if klines is None or len(klines) == 0:
                    logger.warning(f"לא ניתן לקבל מחיר עדכני עבור {symbol}, מדלג")
                    continue
                    
                current_price = klines['close'].iloc[-1]
                position = self.open_positions[symbol]
                
                # עדכון מחיר נוכחי בפוזיציה
                position['current_price'] = current_price
                
                # בדיקת הפעלת/עדכון trailing stop
                if self.trailing_stop_enabled:
                    self.update_trailing_stop(symbol, current_price)
                
                # בדיקת Stop Loss
                if current_price <= position['stop_loss']:
                    reason = "Stop Loss"
                    if position.get('has_trailing_stop', False):
                        reason = "Trailing Stop"
                    
                    logger.info(f"הופעל {reason} עבור {symbol} במחיר {current_price}")
                    
                    # ביצוע מכירה
                    self.place_order(
                        symbol=symbol, 
                        side='SELL', 
                        order_type='MARKET', 
                        quantity=position['quantity']
                    )
                
                # בדיקת Take Profit
                elif current_price >= position['take_profit']:
                    logger.info(f"הופעל Take Profit עבור {symbol} במחיר {current_price}")
                    
                    # ביצוע מכירה
                    self.place_order(
                        symbol=symbol, 
                        side='SELL', 
                        order_type='MARKET', 
                        quantity=position['quantity']
                    )
            
            except Exception as e:
                logger.error(f"שגיאה בניטור פוזיציה עבור {symbol}: {str(e)}")

    def close_position(self, symbol):
        """
        סגירת פוזיציה ספציפית - לשימוש ע"י ממשק הניהול
        """
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            logger.info(f"סוגר פוזיציה ב-{symbol} לבקשת המשתמש")
            
            # ביצוע הוראת מכירה
            result = self.place_order(
                symbol=symbol,
                side='SELL',
                order_type='MARKET',
                quantity=position['quantity']
            )
            
            if result:
                logger.info(f"פוזיציה ב-{symbol} נסגרה בהצלחה")
                return True
            else:
                logger.error(f"שגיאה בסגירת פוזיציה ב-{symbol}")
                return False
        else:
            logger.warning(f"לא נמצאה פוזיציה פתוחה עבור {symbol}")
            return False

    def run(self):
        """
        הפעלת הבוט במצב לולאה
        """
        logger.info("מתחיל להריץ את בוט המסחר...")
        
        try:
            # אתחול רשימת המטבעות במעקב
            self.update_watched_symbols()
            self.last_scan_time = time.time()
            
            # יצירת גיבוי התחלתי
            db.create_backup()
            
            # התחלת לולאת המסחר
            self.running = True
            while self.running:
                try:
                    # עדכון הפוזיציות הפתוחות במסד הנתונים
                    db.update_open_positions(self.open_positions)
                    
                    # ביצוע אסטרטגיית מסחר על מספר סימבולים
                    self.multi_symbol_trading()
                    
                    # בדיקה אם צריך לסרוק מטבעות חדשים
                    current_time = time.time()
                    if current_time - self.last_scan_time > self.symbol_scan_interval * 60:
                        logger.info(f"סריקת מטבעות חדשים (בוצעה אחרי {int((current_time - self.last_scan_time) / 60)} דקות)")
                        self.update_watched_symbols()
                        self.last_scan_time = current_time
                
                    # שינה למשך 10 שניות (פריים עם יותר הזדמנויות)
                    time.sleep(10)
                    
                except Exception as inner_e:
                    logger.error(f"שגיאה בלולאת המסחר: {str(inner_e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    time.sleep(30)  # המתנה לפני ניסיון מחדש
            
        except KeyboardInterrupt:
            logger.info("עוצר את הבוט...")
        except Exception as e:
            logger.error(f"שגיאה לא צפויה: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self.running = False
            # יצירת גיבוי לפני יציאה
            db.create_backup()
            logger.info("הבוט נעצר ונוצר גיבוי אחרון")

    def stop(self):
        """
        עצירת הבוט בצורה מסודרת
        """
        logger.info("עוצר את הבוט...")
        self.running = False

    def update_data(self):
        """
        עדכון ידני של הנתונים - משמש לצרכי ממשק המשתמש
        """
        # עדכון רשימת המטבעות והאינדיקטורים
        self.update_watched_symbols()
        
        # פתיחת גיבוי
        db.create_backup()
        
        return True

if __name__ == "__main__":
    # קריאת מפתחות API ממסד הנתונים
    settings = db.load_settings()
    
    # אתחול הבוט
    bot = MEXCTradingBot(
        api_key=settings.get('api_key', ''),
        api_secret=settings.get('api_secret', ''),
        test_mode=settings.get('test_mode', True)
    )
    
    # הפעלת הבוט
    bot.run()