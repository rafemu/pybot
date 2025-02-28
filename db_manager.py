import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
import json
import os
from bson.objectid import ObjectId

# הגדרת לוגר
logger = logging.getLogger("MEXC-Database")

class DatabaseManager:
    """
    מנהל מסד נתונים MongoDB לבוט מסחר MEXC
    """
    
    def __init__(self, connection_string=None, db_name="mexc_trading_bot"):
        """
        אתחול החיבור למסד הנתונים
        
        :param connection_string: מחרוזת חיבור ל-MongoDB (אם לא מסופק, ישתמש בשרת מקומי)
        :param db_name: שם מסד הנתונים
        """
        # אם לא ניתנה מחרוזת חיבור, השתמש בשרת מקומי
        if not connection_string:
            connection_string = "mongodb+srv://rafemu:Neel27283@cluster0.v9vnt.mongodb.net/trading-bot?retryWrites=true&w=majority&appName=Cluster0"
            
        try:
            # התחברות למסד הנתונים
            self.client = MongoClient(connection_string)
            self.db = self.client[db_name]
            
            # בדיקת החיבור
            self.client.admin.command('ping')
            logger.info("חיבור מוצלח למסד נתונים MongoDB")
            
            # יצירת אינדקסים לביצועים טובים יותר
            self._create_indexes()
            
        except Exception as e:
            logger.error(f"שגיאה בהתחברות ל-MongoDB: {str(e)}")
            raise
    
    def _create_indexes(self):
        """יצירת אינדקסים לביצועים טובים יותר"""
        try:
            # אינדקס על סימבול בטבלת עסקאות
            self.db.trades.create_index([("symbol", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
            
            # אינדקס על תאריך בטבלת עסקאות להקלת חיפוש לפי תאריך
            self.db.trades.create_index("timestamp")
            
            # אינדקס על סימבול בטבלת פוזיציות פתוחות
            self.db.positions.create_index("symbol", unique=True)
            
            # יצירת אינדקס ייחודי לשמות מטבעות במעקב
            self.db.watched_symbols.create_index("symbol", unique=True)
            
            logger.info("אינדקסים נוצרו בהצלחה")
        except Exception as e:
            logger.warning(f"שגיאה ביצירת אינדקסים: {str(e)}")
    
    def save_settings(self, settings):
        """
        שמירת הגדרות הבוט
        
        :param settings: מילון עם הגדרות הבוט
        :return: המזהה של המסמך שנשמר
        """
        try:
            # קודם מחק את ההגדרות הקיימות (רק מסמך אחד של הגדרות)
            self.db.settings.delete_many({})
            
            # הוסף חותמת זמן לנתונים
            settings['updated_at'] = datetime.now()
            
            # הכנס את ההגדרות החדשות
            result = self.db.settings.insert_one(settings)
            logger.info(f"הגדרות נשמרו בהצלחה (ID: {result.inserted_id})")
            
            return result.inserted_id
        except Exception as e:
            logger.error(f"שגיאה בשמירת הגדרות: {str(e)}")
            return None
    
    def load_settings(self):
        """
        טעינת הגדרות הבוט
        
        :return: מילון עם הגדרות הבוט או הגדרות ברירת מחדל אם אין הגדרות שמורות
        """
        try:
            settings = self.db.settings.find_one()
            
            if settings:
                # הסרת שדה ה-_id של MongoDB להקלת השימוש
                if '_id' in settings:
                    settings['_id'] = str(settings['_id'])
                
                logger.info("הגדרות נטענו בהצלחה")
                return settings
            else:
                # אם אין הגדרות, החזר הגדרות ברירת מחדל
                logger.info("אין הגדרות שמורות, מחזיר הגדרות ברירת מחדל")
                return self._get_default_settings()
        except Exception as e:
            logger.error(f"שגיאה בטעינת הגדרות: {str(e)}")
            return self._get_default_settings()
    
    def _get_default_settings(self):
        """מחזיר הגדרות ברירת מחדל"""
        return {
            'api_key': '',
            'api_secret': '',
            'investment': 100.0,
            'trade_size': 10.0,
            'stop_loss': 1.5,
            'take_profit': 2.5,
            'max_watched': 5,
            'max_positions': 3,
            'scan_interval': 15,
            'test_mode': True
        }
    
    def update_open_positions(self, positions):
        """
        עדכון רשימת הפוזיציות הפתוחות
        
        :param positions: מילון של פוזיציות פתוחות {symbol: position_data, ...}
        """
        try:
            # מחיקת כל הפוזיציות הקיימות
            self.db.positions.delete_many({})
            
            # אם אין פוזיציות, סיימנו
            if not positions:
                logger.info("אין פוזיציות פתוחות לעדכון")
                return
            
            # המרת הפוזיציות למסמכים
            position_docs = []
            for symbol, position in positions.items():
                pos_doc = dict(position)
                pos_doc['symbol'] = symbol
                
                # המרת אובייקטי datetime לפורמט MongoDB
                if 'entry_time' in pos_doc and isinstance(pos_doc['entry_time'], datetime):
                    pass  # MongoDB מקבל אובייקטי datetime
                
                position_docs.append(pos_doc)
            
            # הוספת כל הפוזיציות בפעולה אחת
            if position_docs:
                self.db.positions.insert_many(position_docs)
                logger.info(f"עודכנו {len(position_docs)} פוזיציות פתוחות")
        except Exception as e:
            logger.error(f"שגיאה בעדכון פוזיציות פתוחות: {str(e)}")
    
    def get_open_positions(self):
        """
        קבלת רשימת הפוזיציות הפתוחות
        
        :return: מילון של פוזיציות פתוחות {symbol: position_data, ...}
        """
        try:
            positions = {}
            cursor = self.db.positions.find({})
            
            for doc in cursor:
                symbol = doc.pop('symbol')  # הסרת השדה 'symbol' מהמסמך
                
                # הסרת שדה ה-_id של MongoDB
                if '_id' in doc:
                    doc.pop('_id')
                
                positions[symbol] = doc
            
            return positions
        except Exception as e:
            logger.error(f"שגיאה בקבלת פוזיציות פתוחות: {str(e)}")
            return {}
    
    def update_watched_symbols(self, symbols):
        """
        עדכון רשימת הסימבולים במעקב
        
        :param symbols: רשימת סימבולים
        """
        try:
            # מחיקת כל הסימבולים הקיימים
            self.db.watched_symbols.delete_many({})
            
            # אם אין סימבולים, סיימנו
            if not symbols:
                logger.info("אין סימבולים במעקב לעדכון")
                return
            
            # יצירת מסמכים עבור הסימבולים
            symbol_docs = [{'symbol': symbol, 'added_at': datetime.now()} for symbol in symbols]
            
            # הוספת כל הסימבולים בפעולה אחת
            self.db.watched_symbols.insert_many(symbol_docs)
            logger.info(f"עודכנו {len(symbol_docs)} סימבולים במעקב")
        except Exception as e:
            logger.error(f"שגיאה בעדכון סימבולים במעקב: {str(e)}")
    
    def get_watched_symbols(self):
        """
        קבלת רשימת הסימבולים במעקב
        
        :return: רשימת סימבולים
        """
        try:
            symbols = []
            cursor = self.db.watched_symbols.find({})
            
            for doc in cursor:
                symbols.append(doc['symbol'])
            
            return symbols
        except Exception as e:
            logger.error(f"שגיאה בקבלת סימבולים במעקב: {str(e)}")
            return []
    
    def log_trade(self, symbol, action, price, quantity, entry_price=None, profit=None, reason=None):
        """
        תיעוד עסקה חדשה
        
        :param symbol: סימבול המטבע
        :param action: סוג הפעולה (BUY/SELL)
        :param price: מחיר העסקה
        :param quantity: כמות
        :param entry_price: מחיר כניסה (עבור מכירות)
        :param profit: רווח/הפסד בדולרים (עבור מכירות)
        :param reason: סיבת העסקה
        :return: המזהה של המסמך שנוצר
        """
        try:
            trade_doc = {
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': quantity,
                'value': price * quantity,
                'timestamp': datetime.now()
            }
            
            # הוספת שדות אופציונליים
            if entry_price:
                trade_doc['entry_price'] = entry_price
            
            if profit is not None:
                trade_doc['profit'] = profit
                # חישוב אחוז רווח אם יש גם מחיר כניסה
                if entry_price:
                    trade_doc['profit_percentage'] = (price - entry_price) / entry_price * 100
            
            if reason:
                trade_doc['reason'] = reason
            
            # הוספת העסקה למסד הנתונים
            result = self.db.trades.insert_one(trade_doc)
            logger.info(f"עסקה נרשמה בהצלחה: {action} {quantity} {symbol} במחיר {price}")
            
            return result.inserted_id
        except Exception as e:
            logger.error(f"שגיאה בתיעוד עסקה: {str(e)}")
            return None
    
    def get_trades(self, symbol=None, start_date=None, end_date=None, limit=100):
        """
        קבלת היסטוריית עסקאות
        
        :param symbol: סינון לפי סימבול ספציפי (אופציונלי)
        :param start_date: תאריך התחלה (אופציונלי)
        :param end_date: תאריך סיום (אופציונלי)
        :param limit: הגבלת מספר התוצאות
        :return: רשימת עסקאות
        """
        try:
            # בניית פילטר חיפוש
            query = {}
            
            if symbol:
                query['symbol'] = symbol
            
            if start_date or end_date:
                query['timestamp'] = {}
                
                if start_date:
                    query['timestamp']['$gte'] = start_date
                
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            # ביצוע השאילתה עם הפילטר
            cursor = self.db.trades.find(query).sort('timestamp', pymongo.DESCENDING).limit(limit)
            
            # המרת המסמכים לרשימה
            trades = []
            for doc in cursor:
                # המרת ObjectId ל-string
                doc['_id'] = str(doc['_id'])
                trades.append(doc)
            
            return trades
        except Exception as e:
            logger.error(f"שגיאה בקבלת היסטוריית עסקאות: {str(e)}")
            return []
    
    def get_trading_statistics(self, days=30):
        """
        קבלת סטטיסטיקות מסחר
        
        :param days: מספר הימים האחרונים לחישוב סטטיסטיקות
        :return: מילון עם סטטיסטיקות מסחר
        """
        try:
            # תאריך התחלה לחישוב סטטיסטיקות
            start_date = datetime.now() - timedelta(days=days)
            
            # שאילתה מצטברת לחישוב סטטיסטיקות
            pipeline = [
                {
                    '$match': {
                        'timestamp': {'$gte': start_date}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_trades': {'$sum': 1},
                        'buy_trades': {'$sum': {'$cond': [{'$eq': ['$action', 'BUY']}, 1, 0]}},
                        'sell_trades': {'$sum': {'$cond': [{'$eq': ['$action', 'SELL']}, 1, 0]}},
                        'total_volume': {'$sum': '$value'},
                        'total_profit': {'$sum': {'$ifNull': ['$profit', 0]}},
                        'profitable_trades': {'$sum': {'$cond': [{'$gt': ['$profit', 0]}, 1, 0]}},
                        'loss_trades': {'$sum': {'$cond': [{'$lt': ['$profit', 0]}, 1, 0]}}
                    }
                }
            ]
            
            # הוספת פריסה לפי סימבולים
            symbol_pipeline = [
                {
                    '$match': {
                        'timestamp': {'$gte': start_date},
                        'action': 'SELL'  # רק עסקאות מכירה שיש להן רווח/הפסד
                    }
                },
                {
                    '$group': {
                        '_id': '$symbol',
                        'trades': {'$sum': 1},
                        'profit': {'$sum': {'$ifNull': ['$profit', 0]}},
                        'volume': {'$sum': '$value'}
                    }
                },
                {
                    '$sort': {'profit': -1}
                }
            ]
            
            # ביצוע השאילתות
            result = list(self.db.trades.aggregate(pipeline))
            symbol_results = list(self.db.trades.aggregate(symbol_pipeline))
            
            # פירמוט התוצאות
            stats = {}
            
            if result and len(result) > 0:
                stats = result[0]
                stats.pop('_id')
                
                # חישוב אחוז עסקאות מרוויחות
                if stats['total_trades'] > 0:
                    stats['win_rate'] = (stats['profitable_trades'] / (stats['profitable_trades'] + stats['loss_trades'])) * 100 if (stats['profitable_trades'] + stats['loss_trades']) > 0 else 0
            else:
                stats = {
                    'total_trades': 0,
                    'buy_trades': 0,
                    'sell_trades': 0,
                    'total_volume': 0,
                    'total_profit': 0,
                    'profitable_trades': 0,
                    'loss_trades': 0,
                    'win_rate': 0
                }
            
            # הוספת נתונים לפי סימבול
            stats['symbols'] = symbol_results
            
            return stats
        except Exception as e:
            logger.error(f"שגיאה בקבלת סטטיסטיקות מסחר: {str(e)}")
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_volume': 0,
                'total_profit': 0,
                'profitable_trades': 0,
                'loss_trades': 0,
                'win_rate': 0,
                'symbols': []
            }
    
    def save_symbol_data(self, symbol, data):
        """
        שמירת נתוני סימבול (מחירים, אינדיקטורים, וכו')
        
        :param symbol: סימבול המטבע
        :param data: נתוני הסימבול
        :return: תוצאת השמירה
        """
        try:
            # עדכון נתוני הסימבול
            data['updated_at'] = datetime.now()
            
            result = self.db.symbol_data.update_one(
                {'symbol': symbol},
                {'$set': data},
                upsert=True
            )
            
            return result
        except Exception as e:
            logger.error(f"שגיאה בשמירת נתוני סימבול {symbol}: {str(e)}")
            return None
    
    def get_symbol_data(self, symbol):
        """
        קבלת נתוני סימבול
        
        :param symbol: סימבול המטבע
        :return: נתוני הסימבול או None אם לא נמצא
        """
        try:
            data = self.db.symbol_data.find_one({'symbol': symbol})
            
            if data:
                # הסרת שדה ה-_id של MongoDB
                data.pop('_id', None)
            
            return data
        except Exception as e:
            logger.error(f"שגיאה בקבלת נתוני סימבול {symbol}: {str(e)}")
            return None
    
    def create_backup(self, backup_dir="./backups"):
        """
        יצירת גיבוי של מסד הנתונים
        
        :param backup_dir: תיקיית הגיבוי
        :return: שם קובץ הגיבוי או None אם נכשל
        """
        try:
            # וידוא שתיקיית הגיבוי קיימת
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # יצירת שם קובץ הגיבוי עם חותמת זמן
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"mexc_bot_backup_{timestamp}.json")
            
            # קבלת נתונים מכל האוספים הרלוונטיים
            data = {
                'settings': list(self.db.settings.find({})),
                'positions': list(self.db.positions.find({})),
                'watched_symbols': list(self.db.watched_symbols.find({})),
                'trades': list(self.db.trades.find({})),
                'symbol_data': list(self.db.symbol_data.find({}))
            }
            
            # המרת ObjectId למחרוזות
            for collection in data.values():
                for document in collection:
                    if '_id' in document:
                        document['_id'] = str(document['_id'])
                    
                    # המרת תאריכים למחרוזות
                    for key, value in document.items():
                        if isinstance(value, datetime):
                            document[key] = value.isoformat()
            
            # שמירת הנתונים לקובץ JSON
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"גיבוי נוצר בהצלחה: {backup_file}")
            
            return backup_file
        except Exception as e:
            logger.error(f"שגיאה ביצירת גיבוי: {str(e)}")
            return None
    
    def restore_from_backup(self, backup_file):
        """
        שחזור מסד נתונים מגיבוי
        
        :param backup_file: נתיב לקובץ הגיבוי
        :return: True אם הצליח, False אם נכשל
        """
        try:
            # בדיקה שהקובץ קיים
            if not os.path.exists(backup_file):
                logger.error(f"קובץ גיבוי לא נמצא: {backup_file}")
                return False
            
            # קריאת הנתונים מהקובץ
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # מחיקת כל הנתונים הקיימים
            self.db.settings.delete_many({})
            self.db.positions.delete_many({})
            self.db.watched_symbols.delete_many({})
            self.db.symbol_data.delete_many({})
            # לא מוחקים היסטוריית עסקאות
            
            # המרת מחרוזות תאריך לאובייקטי datetime
            for collection_name, documents in data.items():
                collection = self.db[collection_name]
                
                # דילוג על מסמכים ריקים
                if not documents:
                    continue
                
                # הסרת _id מהמסמכים (MongoDB יצור _id חדשים)
                for doc in documents:
                    if '_id' in doc:
                        doc.pop('_id')
                    
                    # המרת מחרוזות תאריך לאובייקטי datetime
                    for key, value in list(doc.items()):
                        if isinstance(value, str) and 'T' in value and value.endswith('Z'):
                            try:
                                doc[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except:
                                pass  # אם לא הצליח להמיר, השאר כמחרוזת
                
                # הוספת המסמכים לאוסף
                if documents:
                    collection.insert_many(documents)
            
            logger.info(f"שחזור מגיבוי הושלם בהצלחה: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"שגיאה בשחזור מגיבוי: {str(e)}")
            return False
    
    def __del__(self):
        """סגירת החיבור למסד הנתונים"""
        try:
            if hasattr(self, 'client'):
                self.client.close()
        except:
            pass