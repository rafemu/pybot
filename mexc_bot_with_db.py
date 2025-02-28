import time
import logging
from datetime import datetime
from db_manager import DatabaseManager

# שימוש במנהל מסד הנתונים
db = DatabaseManager(connection_string="mongodb://localhost:27017/")

# דוגמה לשינויים שיש לבצע במחלקת הבוט
class MEXCTradingBot:
    def __init__(self, api_key, api_secret, base_url='https://api.mexc.com', test_mode=True):
        """
        אתחול בוט המסחר של MEXC עם שימוש במסד נתונים
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.test_mode = test_mode
        
        # הגדרות מסחר בסיסיות
        self.investment_amount = 100  # סכום ההשקעה בדולרים
        self.trade_size = 10  # גודל כל עסקה בדולרים
        self.current_symbol = None
        self.stop_loss_percent = 1.5  # אחוז הפסד מקסימלי לפני יציאה
        self.take_profit_percent = 2.5  # אחוז רווח לפני מימוש
        
        # טעינת נתונים ממסד הנתונים
        self._load_from_database()
        
        # בקרת זרימה
        self.running = False  # דגל לבקרת ריצת הבוט

    def _load_from_database(self):
        """
        טעינת נתונים ממסד הנתונים
        """
        # טעינת פוזיציות פתוחות
        self.open_positions = db.get_open_positions()
        
        # טעינת רשימת מטבעות במעקב
        self.watched_symbols = db.get_watched_symbols()
        
        # חישוב רווח/הפסד כולל מהיסטוריית עסקאות
        trades = db.get_trades(limit=1000)
        self.profit_loss = sum(trade.get('profit', 0) for trade in trades if 'profit' in trade)
        
        # אתחול מילון פרטי סימבולים
        self.symbol_details = {}
        
        # טעינת נתוני סימבולים
        for symbol in self.watched_symbols:
            symbol_data = db.get_symbol_data(symbol)
            if symbol_data:
                self.symbol_details[symbol] = symbol_data

    def update_watched_symbols(self):
        """
        עדכון רשימת המטבעות במעקב עם נתונים נוספים
        """
        # הקוד המקורי של עדכון הסימבולים במעקב...
        
        # עדכון מסד הנתונים
        db.update_watched_symbols(self.watched_symbols)
        
        # עדכון מידע מפורט לכל סימבול
        for symbol in self.watched_symbols:
            # ...קוד חישוב אינדיקטורים ומידע נוסף...
            
            # שמירת המידע במסד הנתונים
            db.save_symbol_data(symbol, self.symbol_details[symbol])
        
        return self.symbol_details

    def place_order(self, symbol, side, order_type, quantity, price=None):
        """
        הנחת הוראת קנייה/מכירה עם תיעוד במסד נתונים
        """
        # הקוד המקורי...
        if self.test_mode:
            # ...קוד סימולציה של ביצוע הוראה...
            
            # תיעוד העסקה במסד הנתונים
            if side == 'BUY':
                db.log_trade(
                    symbol=symbol,
                    action=side,
                    price=price if price else current_price,
                    quantity=quantity,
                    reason="Manual order"
                )
            else:  # SELL
                # חישוב רווח/הפסד אם קיימת פוזיציה
                if symbol in self.open_positions:
                    entry_price = self.open_positions[symbol]['entry_price']
                    current_price = price if price else market_price
                    profit = (current_price - entry_price) * quantity
                    
                    db.log_trade(
                        symbol=symbol,
                        action=side,
                        price=current_price,
                        quantity=quantity,
                        entry_price=entry_price,
                        profit=profit,
                        reason="Manual order"
                    )
            
            # ...המשך הקוד המקורי...
        
        # ...המשך הקוד המקורי...

    def monitor_open_positions(self):
        """
        ניטור פוזיציות פתוחות ובדיקת תנאי יציאה
        """
        for symbol in list(self.open_positions.keys()):
            try:
                # ...קוד ניטור פוזיציות...
                
                # בדיקת Stop Loss
                if current_price <= position['stop_loss']:
                    # ...קוד ביצוע מכירה...
                    
                    # עדכון במסד הנתונים
                    db.log_trade(
                        symbol=symbol,
                        action='SELL',
                        price=current_price,
                        quantity=position['quantity'],
                        entry_price=position['entry_price'],
                        profit=profit,
                        reason="Stop Loss"
                    )
                    
                    # עדכון הפוזיציות הפתוחות במסד הנתונים
                    db.update_open_positions(self.open_positions)
                
                # בדיקת Take Profit
                elif current_price >= position['take_profit']:
                    # ...קוד ביצוע מכירה...
                    
                    # עדכון במסד הנתונים
                    db.log_trade(
                        symbol=symbol,
                        action='SELL',
                        price=current_price,
                        quantity=position['quantity'],
                        entry_price=position['entry_price'],
                        profit=profit,
                        reason="Take Profit"
                    )
                    
                    # עדכון הפוזיציות הפתוחות במסד הנתונים
                    db.update_open_positions(self.open_positions)
            
            except Exception as e:
                logging.error(f"שגיאה בניטור פוזיציה עבור {symbol}: {str(e)}")

    def execute_trade_strategy(self, symbol):
        """
        ביצוע אסטרטגיית המסחר עבור סימבול נתון
        """
        # ...הקוד המקורי...
        
        # ביצוע עסקת קנייה
        if buy_condition:
            try:
                # ...קוד ביצוע עסקה...
                
                # תיעוד במסד הנתונים
                db.log_trade(
                    symbol=symbol,
                    action='BUY',
                    price=current_price,
                    quantity=quantity,
                    reason="Strategy signal"
                )
                
                # עדכון הפוזיציות הפתוחות במסד הנתונים
                db.update_open_positions(self.open_positions)
                
                return True
            except Exception as e:
                logging.error(f"שגיאה בביצוע עסקה עבור {symbol}: {str(e)}")
                return False
        
        return False

    def close_position(self, symbol):
        """
        סגירת פוזיציה ספציפית - לשימוש ע"י ממשק הניהול
        """
        if symbol in self.open_positions:
            position = self.open_positions[symbol]
            logging.info(f"סוגר פוזיציה ב-{symbol} לבקשת המשתמש")
            
            # ביצוע הוראת מכירה
            order = self.place_order(
                symbol=symbol,
                side='SELL',
                order_type='MARKET',
                quantity=position['quantity']
            )
            
            if order:
                # חישוב רווח/הפסד
                current_price = position.get('current_price', position['entry_price'])
                profit = (current_price - position['entry_price']) * position['quantity']
                
                self.profit_loss += profit
                
                # תיעוד העסקה במסד הנתונים
                db.log_trade(
                    symbol=symbol,
                    action='SELL',
                    price=current_price,
                    quantity=position['quantity'],
                    entry_price=position['entry_price'],
                    profit=profit,
                    reason="Manual close"
                )
                
                # הסרת הפוזיציה
                del self.open_positions[symbol]
                
                # עדכון הפוזיציות הפתוחות במסד הנתונים
                db.update_open_positions(self.open_positions)
                
                return True
            else:
                logging.error(f"שגיאה בסגירת פוזיציה עבור {symbol}")
                return False
        else:
            logging.warning(f"לא נמצאה פוזיציה עבור {symbol}")
            return False
    
    def run(self):
        """
        הפעלת הבוט במצב לולאה
        """
        logging.info("מתחיל להריץ את בוט המסחר...")
        
        self.running = True
        
        try:
            # אתחול רשימת המטבעות במעקב
            self.update_watched_symbols()
            self.last_scan_time = time.time()
            
            # התחלת לולאת המסחר
            while self.running:
                # ...לוגיקת מסחר...
                
                # עדכון מסד הנתונים לפני שינה
                db.update_open_positions(self.open_positions)
                
                # שינה למשך 10 שניות
                time.sleep(10)
            
        except KeyboardInterrupt:
            logging.info("עוצר את הבוט...")
        except Exception as e:
            logging.error(f"שגיאה לא צפויה: {str(e)}")
            raise
        finally:
            self.running = False
            # גיבוי סופי של מסד הנתונים
            db.create_backup()