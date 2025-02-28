import time
import threading
import queue
import json
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_socketio import SocketIO, emit
import importlib.util
import sys
import traceback
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from db_manager import DatabaseManager
from threading import Lock

# ===== הגדרות בסיסיות =====

# הגדרות לוגים
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MEXC-Dashboard")

# יצירת אפליקציית Flask
app = Flask(__name__)
app.secret_key = 'mexc_bot_secret_key'
app.wsgi_app = ProxyFix(app.wsgi_app)

# הוספת תמיכה בSocketIO לעדכונים בזמן אמת
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# יצירת חיבור למסד הנתונים
db = DatabaseManager(connection_string="mongodb://localhost:27017/")

# נתיבים לתיקיות חשובות
UPLOAD_FOLDER = './uploads'
BACKUP_FOLDER = './backups'
DATA_FOLDER = './data'
LOG_FOLDER = './logs'

# וידוא שהתיקיות קיימות
for folder in [UPLOAD_FOLDER, BACKUP_FOLDER, DATA_FOLDER, LOG_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# הגדרות Flask
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB מקסימום

# ===== משתנים גלובליים =====

bot = None
bot_thread = None
bot_running = False
bot_log_queue = queue.Queue()
watched_symbols = []
open_positions = {}
profit_history = []
total_profit = 0.0
start_time = None
thread_lock = Lock()
update_thread = None

# מעקב אחר חיבורים פעילים
active_connections = 0
bot_monitor_thread = None
last_data_update = datetime.now()
last_price_update = datetime.now()
price_update_interval = 5  # בשניות
data_update_interval = 15  # בשניות

# ===== פונקציות עזר =====

def ensure_directories_exist():
    """וידוא שכל התיקיות הדרושות קיימות"""
    for dir_path in [UPLOAD_FOLDER, BACKUP_FOLDER, DATA_FOLDER, LOG_FOLDER, 'templates', 'static']:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.info(f"נוצרה תיקייה: {dir_path}")

def load_bot_module():
    """
    טעינת מודול הבוט באופן דינמי
    """
    try:
        # בדיקה אם קובץ הבוט קיים
        if not os.path.exists('mexc_bot_complete.py'):
            # נסה למצוא קובץ בוט אחר
            bot_files = [f for f in os.listdir('.') if f.startswith('mexc_bot') and f.endswith('.py')]
            if not bot_files:
                logger.error("לא נמצא קובץ בוט מתאים!")
                return None
            
            bot_file = bot_files[0]
            logger.info(f"משתמש בקובץ בוט: {bot_file}")
        else:
            bot_file = 'mexc_bot_complete.py'
        
        # טעינת המודול באופן דינמי
        module_name = bot_file[:-3]  # הסרת הסיומת .py
        spec = importlib.util.spec_from_file_location(module_name, bot_file)
        mexc_bot = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mexc_bot
        spec.loader.exec_module(mexc_bot)
        
        return mexc_bot
    except Exception as e:
        logger.error(f"שגיאה בטעינת מודול הבוט: {str(e)}")
        logger.error(traceback.format_exc())
        return None

class QueueHandler(logging.Handler):
    """מטפל לוגים שמעביר לוגים לתור"""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
            
            # שלח את ההודעה גם ל-Socket.IO אם היא קיימת
            try:
                socketio.emit('log_update', {'log': msg})
            except:
                pass
        except Exception:
            self.handleError(record)

# ===== ניהול הבוט =====

def run_bot(settings):
    """
    הפעלת הבוט בתהליך נפרד
    """
    global bot, bot_running, start_time, bot_thread, total_profit, open_positions, watched_symbols
    
    with thread_lock:
        mexc_bot_module = load_bot_module()
        if not mexc_bot_module:
            logger.error("שגיאה בטעינת מודול הבוט!")
            return False
        
        try:
            # יצירת בוט חדש עם ההגדרות
            bot = mexc_bot_module.MEXCTradingBot(
                api_key=settings['api_key'],
                api_secret=settings['api_secret'],
                test_mode=settings['test_mode']
            )
            
            # עדכון הגדרות נוספות
            bot.investment_amount = float(settings['investment'])
            bot.trade_size = float(settings['trade_size'])
            bot.stop_loss_percent = float(settings['stop_loss'])
            bot.take_profit_percent = float(settings['take_profit'])
            bot.max_watched_symbols = int(settings['max_watched'])
            bot.max_positions = int(settings['max_positions'])
            bot.symbol_scan_interval = int(settings['scan_interval'])
            
            # הגדרות נוספות אם קיימות
            if 'max_daily_loss' in settings:
                bot.max_daily_loss = float(settings['max_daily_loss'])
            
            if 'trailing_stop_enabled' in settings:
                bot.trailing_stop_enabled = settings['trailing_stop_enabled']
            
            if 'trailing_stop_activation' in settings:
                bot.trailing_stop_activation = float(settings['trailing_stop_activation'])
            
            if 'trailing_stop_distance' in settings:
                bot.trailing_stop_distance = float(settings['trailing_stop_distance'])
            
            # הוספת מטפל לוגים לתור
            log_handler = QueueHandler(bot_log_queue)
            log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logging.getLogger("MEXC-TradingBot").addHandler(log_handler)
            
            # הפעלת הבוט בתהליך נפרד
            def run_bot_func():
                try:
                    bot.run()
                except Exception as e:
                    logger.error(f"שגיאה בהפעלת הבוט: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # עדכון משתנים גלובליים במקרה של שגיאה
                    global bot_running
                    with thread_lock:
                        bot_running = False
            
            # הפעלת הבוט
            bot_thread = threading.Thread(target=run_bot_func)
            bot_thread.daemon = True
            bot_thread.start()
            
            # עדכון משתנים גלובליים
            bot_running = True
            start_time = datetime.now()
            
            # התחלת תהליך עדכון נתונים בזמן אמת
            start_data_update_thread()
            
            # יצירת גיבוי התחלתי
            db.create_backup()
            
            return True
        except Exception as e:
            logger.error(f"שגיאה בהפעלת הבוט: {str(e)}")
            logger.error(traceback.format_exc())
            return False

def stop_bot():
    """
    עצירת הבוט
    """
    global bot, bot_running, update_thread
    
    with thread_lock:
        if not bot_running:
            return True
        
        try:
            # עצירת הבוט
            if hasattr(bot, 'stop'):
                bot.stop()
            else:
                # אם אין מתודת stop, נשנה את דגל הריצה
                bot.running = False
            
            # עדכון משתנים גלובליים
            bot_running = False
            
            # יצירת גיבוי של הנתונים
            db.create_backup()
            
            # המתנה לסיום התהליך
            if bot_thread and bot_thread.is_alive():
                bot_thread.join(timeout=5)
            
            # עצירת תהליך עדכון הנתונים
            if update_thread and update_thread.is_alive():
                update_thread = None
            
            return True
        except Exception as e:
            logger.error(f"שגיאה בעצירת הבוט: {str(e)}")
            logger.error(traceback.format_exc())
            return False

def fetch_latest_data():
    """
    קבלת הנתונים העדכניים ביותר מהבוט
    """
    global open_positions, watched_symbols, total_profit
    
    with thread_lock:
        if bot and bot_running:
            try:
                # עדכון פוזיציות פתוחות
                if hasattr(bot, 'open_positions'):
                    open_positions = bot.open_positions
                    db.update_open_positions(open_positions)
                
                # עדכון רשימת מטבעות במעקב
                if hasattr(bot, 'watched_symbols'):
                    watched_symbols = bot.watched_symbols
                
                # עדכון רווח/הפסד כולל
                if hasattr(bot, 'profit_loss'):
                    total_profit = bot.profit_loss
                
                # עדכון מחירים עדכניים במסד הנתונים
                if hasattr(bot, 'symbol_details') and bot.symbol_details:
                    for symbol, details in bot.symbol_details.items():
                        if 'current_price' in details:
                            db.update_symbol_price(symbol, details['current_price'])
                
                return True
            except Exception as e:
                logger.error(f"שגיאה בעדכון נתונים מהבוט: {str(e)}")
                logger.error(traceback.format_exc())
                return False
    
    # אם אין בוט פעיל, טען מהמסד
    try:
        open_positions = db.get_open_positions()
        watched_symbols = db.get_watched_symbols()
        
        # חישוב רווח/הפסד כולל מהיסטוריית עסקאות
        trades = db.get_trades(limit=1000)
        total_profit = sum(trade.get('profit', 0) for trade in trades if 'profit' in trade)
        
        return True
    except Exception as e:
        logger.error(f"שגיאה בטעינת נתונים ממסד הנתונים: {str(e)}")
        return False

def update_data_thread():
    """
    תהליך רקע לעדכון נתונים בזמן אמת
    """
    global last_data_update, last_price_update
    
    logger.info("תהליך עדכון נתונים החל לפעול")
    
    while bot_running:
        try:
            current_time = datetime.now()
            
            # עדכון מחירים בתדירות גבוהה
            if (current_time - last_price_update).total_seconds() >= price_update_interval:
                # עדכון מחירים בלבד
                if bot and hasattr(bot, 'symbol_details') and bot.symbol_details:
                    price_data = {}
                    for symbol, details in bot.symbol_details.items():
                        if 'current_price' in details:
                            price_data[symbol] = {
                                'price': details['current_price'],
                                'updated_at': datetime.now().isoformat()
                            }
                    
                    # שליחת עדכון דרך Socket.IO
                    if price_data:
                        socketio.emit('price_update', {'prices': price_data})
                
                # שימוש ב-socketio להעברת מידע על פוזיציות פתוחות
                if bot and hasattr(bot, 'open_positions') and bot.open_positions:
                    position_updates = {}
                    for symbol, position in bot.open_positions.items():
                        current_price = position.get('current_price', position['entry_price'])
                        entry_price = position['entry_price']
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                        profit_usd = (current_price - entry_price) * position['quantity']
                        
                        position_updates[symbol] = {
                            'current_price': current_price,
                            'profit_pct': profit_pct,
                            'profit_usd': profit_usd
                        }
                    
                    if position_updates:
                        socketio.emit('position_update', {'positions': position_updates})
                
                last_price_update = current_time
            
            # עדכון מלא של הנתונים בתדירות נמוכה יותר
            if (current_time - last_data_update).total_seconds() >= data_update_interval:
                # עדכון כל הנתונים
                fetch_latest_data()
                
                # שליחת אות עדכון כללי
                socketio.emit('data_update', {'timestamp': current_time.isoformat()})
                
                last_data_update = current_time
            
            # שינה קצרה
            time.sleep(1)
        except Exception as e:
            logger.error(f"שגיאה בתהליך עדכון נתונים: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(5)

def start_data_update_thread():
    """
    התחלת תהליך עדכון הנתונים
    """
    global update_thread
    
    # אם יש כבר תהליך פעיל, עצור אותו
    if update_thread and update_thread.is_alive():
        return
    
    # התחלת תהליך חדש
    update_thread = threading.Thread(target=update_data_thread)
    update_thread.daemon = True
    update_thread.start()

def generate_trade_performance_chart():
    """
    יצירת נתונים לתרשים ביצועי מסחר
    """
    try:
        # קבלת עסקאות אחרונות
        trades = db.get_trades(limit=500)
        
        if not trades:
            return None
        
        # המרה לDataFrame
        df = pd.DataFrame(trades)
        
        # סינון רק עסקאות מכירה עם רווח/הפסד
        df = df[df['action'] == 'SELL']
        
        if df.empty:
            return None
        
        # התאמת תאריכים
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        
        # מיון לפי תאריך
        df = df.sort_values('timestamp')
        
        # חישוב רווח מצטבר
        df['cumulative_profit'] = df['profit'].cumsum()
        
        # חישוב רווח יומי
        daily_profit = df.groupby('date')['profit'].sum().reset_index()
        
        # יצירת נתונים לגרף
        chart_data = {
            'dates': [d.strftime('%Y-%m-%d') for d in daily_profit['date']],
            'daily_profit': daily_profit['profit'].tolist(),
            'cumulative_dates': [d.strftime('%Y-%m-%d') for d in df['date']],
            'cumulative_profit': df['cumulative_profit'].tolist()
        }
        
        return chart_data
    except Exception as e:
        logger.error(f"שגיאה ביצירת נתוני גרף ביצועים: {str(e)}")
        return None

def calculate_performance_metrics(days=30):
    """
    חישוב מדדי ביצוע עבור תקופה מוגדרת
    """
    try:
        # קבלת סטטיסטיקות מהמסד
        stats = db.get_trading_statistics(days=days)
        
        # חישוב מדדים נוספים
        if stats['total_trades'] > 0:
            stats['avg_profit_per_trade'] = stats['total_profit'] / stats['total_trades']
        else:
            stats['avg_profit_per_trade'] = 0
        
        if stats['profitable_trades'] > 0:
            stats['avg_profit_on_winning'] = stats['total_profit'] / stats['profitable_trades']
        else:
            stats['avg_profit_on_winning'] = 0
        
        if stats['loss_trades'] > 0:
            stats['avg_loss_on_losing'] = stats['total_profit'] / stats['loss_trades']
        else:
            stats['avg_loss_on_losing'] = 0
        
        # חישוב יחס סיכוי-הפסד (Risk-Reward Ratio)
        if stats['avg_loss_on_losing'] != 0:
            stats['risk_reward_ratio'] = abs(stats['avg_profit_on_winning'] / stats['avg_loss_on_losing'])
        else:
            stats['risk_reward_ratio'] = 0
        
        # חישוב אחוז הצלחה (אם יש עסקאות)
        if stats['total_trades'] > 0:
            stats['success_rate'] = (stats['profitable_trades'] / stats['total_trades']) * 100
        else:
            stats['success_rate'] = 0
        
        return stats
    except Exception as e:
        logger.error(f"שגיאה בחישוב מדדי ביצוע: {str(e)}")
        return {}

# ===== Flask Routes =====

@app.route('/')
def index():
    """דף הבית של הממשק"""
    # טעינת נתונים ממסד הנתונים
    settings = db.load_settings()
    
    # איחזור נתונים עדכניים
    fetch_latest_data()
    
    # חישוב זמן פעילות
    uptime = datetime.now() - start_time if start_time else None
    
    # בניית זמן פעילות כמחרוזת קריאה
    uptime_str = ""
    if uptime:
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            uptime_str += f"{int(days)} ימים "
        
        uptime_str += f"{int(hours)}:{int(minutes):02d}:{int(seconds):02d}"
    else:
        uptime_str = "לא פעיל"
    
    # קבלת לוגים אחרונים
    logs = []
    while not bot_log_queue.empty() and len(logs) < 100:
        try:
            logs.append(bot_log_queue.get_nowait())
        except queue.Empty:
            break
    
    logs.reverse()  # הלוגים החדשים ביותר למעלה
    
    # קבלת נתוני ביצועים
    performance_metrics = calculate_performance_metrics(days=7)
    
    # קבלת נתונים לגרף ביצועים
    chart_data = generate_trade_performance_chart()
    
    return render_template(
        'index.html',
        settings=settings,
        bot_running=bot_running,
        uptime=uptime_str,
        open_positions=open_positions,
        watched_symbols=watched_symbols,
        total_profit=total_profit,
        logs=logs,
        performance=performance_metrics,
        chart_data=chart_data
    )

@app.route('/start_bot', methods=['POST'])
def start_bot_route():
    """הפעלת הבוט"""
    global bot, bot_running, start_time, bot_thread
    
    if bot_running:
        flash('הבוט כבר רץ!', 'warning')
        return redirect(url_for('index'))
    
    # טעינת הגדרות ממסד הנתונים
    settings = db.load_settings()
    
    # עדכון הגדרות אם נשלחו
    if request.form:
        # הגדרות בסיסיות
        settings['api_key'] = request.form.get('api_key', settings.get('api_key', ''))
        settings['api_secret'] = request.form.get('api_secret', settings.get('api_secret', ''))
        settings['test_mode'] = 'test_mode' in request.form
        
        try:
            # הגדרות מספריות
            numeric_fields = [
                'investment', 'trade_size', 'stop_loss', 'take_profit', 
                'max_watched', 'max_positions', 'scan_interval',
                'max_daily_loss', 'trailing_stop_activation', 'trailing_stop_distance'
            ]
            
            for field in numeric_fields:
                if field in request.form and request.form.get(field):
                    settings[field] = float(request.form.get(field))
            
            # הגדרות boolean
            bool_fields = ['trailing_stop_enabled']
            for field in bool_fields:
                settings[field] = field in request.form
                
        except ValueError as e:
            flash(f'ערכים לא תקינים בטופס: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    # שמירת ההגדרות במסד הנתונים
    db.save_settings(settings)
    
    # הפעלת הבוט
    if run_bot(settings):
        flash('הבוט הופעל בהצלחה', 'success')
    else:
        flash('שגיאה בהפעלת הבוט', 'danger')
    
    return redirect(url_for('index'))

@app.route('/stop_bot', methods=['POST'])
def stop_bot_route():
    """עצירת הבוט"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('index'))
    
    if stop_bot():
        flash('הבוט נעצר בהצלחה', 'success')
    else:
        flash('שגיאה בעצירת הבוט', 'danger')
    
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """דף הגדרות"""
    if request.method == 'POST':
        # טעינת הגדרות נוכחיות
        settings = db.load_settings()
        
        # עדכון הגדרות מהטופס
        # הגדרות בסיסיות
        settings['api_key'] = request.form.get('api_key', '')
        settings['api_secret'] = request.form.get('api_secret', '')
        settings['test_mode'] = 'test_mode' in request.form
        
        try:
            # הגדרות מספריות
            settings['investment'] = float(request.form.get('investment', 100.0))
            settings['trade_size'] = float(request.form.get('trade_size', 10.0))
            settings['stop_loss'] = float(request.form.get('stop_loss', 1.5))
            settings['take_profit'] = float(request.form.get('take_profit', 2.5))
            settings['max_watched'] = int(request.form.get('max_watched', 5))
            settings['max_positions'] = int(request.form.get('max_positions', 3))
            settings['scan_interval'] = int(request.form.get('scan_interval', 15))
            
            # הגדרות מתקדמות
            if 'max_daily_loss' in request.form:
                settings['max_daily_loss'] = float(request.form.get('max_daily_loss', 20))
            
            settings['trailing_stop_enabled'] = 'trailing_stop_enabled' in request.form
            
            if 'trailing_stop_activation' in request.form:
                settings['trailing_stop_activation'] = float(request.form.get('trailing_stop_activation', 1.0))
            
            if 'trailing_stop_distance' in request.form:
                settings['trailing_stop_distance'] = float(request.form.get('trailing_stop_distance', 0.5))
            
        except ValueError:
            flash('ערכים לא תקינים בטופס', 'danger')
            return redirect(url_for('settings_page'))
        
        # שמירת ההגדרות במסד הנתונים
        db.save_settings(settings)
        
        # עדכון הגדרות הבוט אם הוא פעיל
        if bot_running and bot:
            try:
                # עדכון הגדרות בסיסיות
                bot.investment_amount = settings['investment']
                bot.trade_size = settings['trade_size']
                bot.stop_loss_percent = settings['stop_loss']
                bot.take_profit_percent = settings['take_profit']
                bot.max_watched_symbols = settings['max_watched']
                bot.max_positions = settings['max_positions']
                bot.symbol_scan_interval = settings['scan_interval']
                
                # עדכון הגדרות מתקדמות
                if 'max_daily_loss' in settings:
                    bot.max_daily_loss = settings['max_daily_loss']
                
                bot.trailing_stop_enabled = settings['trailing_stop_enabled']
                
                if 'trailing_stop_activation' in settings:
                    bot.trailing_stop_activation = settings['trailing_stop_activation']
                
                if 'trailing_stop_distance' in settings:
                    bot.trailing_stop_distance = settings['trailing_stop_distance']
                
                flash('ההגדרות עודכנו בהצלחה בבוט הפעיל', 'success')
            except Exception as e:
                logger.error(f"שגיאה בעדכון הגדרות הבוט: {str(e)}")
        
        flash('ההגדרות נשמרו בהצלחה', 'success')
        return redirect(url_for('index'))
    
    # טעינת הגדרות עבור GET
    settings = db.load_settings()
    
    # הגדרות נוספות אם לא קיימות
    if 'max_daily_loss' not in settings:
        settings['max_daily_loss'] = 20.0
    
    if 'trailing_stop_enabled' not in settings:
        settings['trailing_stop_enabled'] = False
    
    if 'trailing_stop_activation' not in settings:
        settings['trailing_stop_activation'] = 1.0
    
    if 'trailing_stop_distance' not in settings:
        settings['trailing_stop_distance'] = 0.5
    
    return render_template('settings.html', settings=settings)

@app.route('/positions')
def positions_page():
    """דף פוזיציות פתוחות"""
    # עדכון הנתונים לפני הצגת הדף
    fetch_latest_data()
    
    return render_template('positions.html', positions=open_positions)

@app.route('/watchlist')
def watchlist_page():
    """דף רשימת מעקב"""
    # עדכון הנתונים לפני הצגת הדף
    fetch_latest_data()
    
    symbols = watched_symbols
    
    # קבלת פרטי סימבולים מהמסד
    symbol_details = {}
    for symbol in symbols:
        data = db.get_symbol_data(symbol)
        if data:
            symbol_details[symbol] = data
    
    # קבלת מחירים נוכחיים
    current_prices = {}
    for symbol in symbols:
        price = db.get_symbol_price(symbol)
        if price:
            current_prices[symbol] = price
    
    return render_template('watchlist.html', 
                           symbols=symbols,
                           symbol_details=symbol_details,
                           current_prices=current_prices)

@app.route('/logs')
def logs_page():
    """דף לוגים"""
    logs = []
    while not bot_log_queue.empty():
        try:
            logs.append(bot_log_queue.get_nowait())
        except queue.Empty:
            break
    
    logs.reverse()  # הלוגים החדשים ביותר למעלה
    
    # אם אין לוגים בתור, קרא מהקובץ
    if not logs and os.path.exists("mexc_bot.log"):
        try:
            with open("mexc_bot.log", 'r', encoding='utf-8') as f:
                logs = f.readlines()
            logs = [line.strip() for line in logs[-1000:]]  # רק 1000 השורות האחרונות
        except Exception as e:
            logger.error(f"שגיאה בקריאת קובץ לוג: {str(e)}")
    
    return render_template('logs.html', logs=logs)

@app.route('/statistics')
def statistics_page():
    """דף סטטיסטיקות מסחר"""
    # קבלת פרמטרים מה-URL
    days = request.args.get('days', default=30, type=int)
    
    # עדכון הנתונים לפני הצגת הדף
    fetch_latest_data()
    
    # קבלת סטטיסטיקות ממסד הנתונים
    stats = db.get_trading_statistics(days=days)
    
    # חישוב מדדי ביצוע נוספים
    performance_metrics = calculate_performance_metrics(days=days)
    
    # מיזוג הנתונים
    if stats and performance_metrics:
        stats.update(performance_metrics)
    
    # קבלת כל העסקאות לתרשים
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    trades = db.get_trades(start_date=start_date, end_date=end_date, limit=1000)
    
    # יצירת נתונים לגרף ביצועים
    chart_data = generate_trade_performance_chart()
    
    return render_template(
        'statistics.html',
        stats=stats,
        days=days,
        trades=trades,
        chart_data=chart_data
    )

@app.route('/add_symbol', methods=['POST'])
def add_symbol():
    """הוספת סימבול לרשימת המעקב"""
    symbol = request.form.get('symbol', '').upper()
    
    if not symbol:
        flash('נא להזין סימבול תקין', 'warning')
        return redirect(url_for('watchlist_page'))
    
    # עדכון במסד הנתונים
    current_symbols = db.get_watched_symbols()
    
    if symbol not in current_symbols:
        current_symbols.append(symbol)
        db.update_watched_symbols(current_symbols)
        
        # עדכון בבוט אם רץ
        if bot_running and bot and hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = current_symbols
            
            # נסה לעדכן את הנתונים של הסימבול
            if hasattr(bot, 'update_symbol_data'):
                bot.update_symbol_data(symbol)
    
    flash(f'הסימבול {symbol} נוסף בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/remove_symbol/<symbol>', methods=['POST'])
def remove_symbol(symbol):
    """הסרת סימבול מרשימת המעקב"""
    # עדכון במסד הנתונים
    current_symbols = db.get_watched_symbols()
    
    if symbol in current_symbols:
        current_symbols.remove(symbol)
        db.update_watched_symbols(current_symbols)
        
        # עדכון בבוט אם רץ
        if bot_running and bot and hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = current_symbols
    
    flash(f'הסימבול {symbol} הוסר בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/close_position/<symbol>', methods=['POST'])
def close_position(symbol):
    """סגירת פוזיציה פתוחה"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('positions_page'))
    
    # בדיקה אם הפוזיציה עדיין קיימת
    positions = db.get_open_positions()
    
    if symbol not in positions:
        flash(f'לא נמצאה פוזיציה פתוחה עבור {symbol}', 'warning')
        return redirect(url_for('positions_page'))
    
    try:
        # הפעלת פונקציית סגירת פוזיציה של הבוט
        if hasattr(bot, 'close_position'):
            success = bot.close_position(symbol)
            if success:
                flash(f'הפוזיציה ב-{symbol} נסגרה בהצלחה', 'success')
            else:
                flash('שגיאה בסגירת הפוזיציה', 'danger')
        else:
            flash('הבוט אינו תומך בסגירת פוזיציות ידנית', 'warning')
    except Exception as e:
        flash(f'שגיאה בסגירת הפוזיציה: {str(e)}', 'danger')
    
    return redirect(url_for('positions_page'))

@app.route('/scan_symbols', methods=['POST'])
def scan_symbols():
    """סריקת מטבעות חדשים"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('watchlist_page'))
    
    try:
        # הפעלת פונקציית סריקת מטבעות של הבוט
        if hasattr(bot, 'update_watched_symbols'):
            bot.update_watched_symbols()
            
            # עדכון המשתנים הגלובליים
            global watched_symbols
            watched_symbols = bot.watched_symbols
            
            flash('סריקת מטבעות חדשים הושלמה בהצלחה', 'success')
        else:
            flash('הבוט אינו תומך בסריקת מטבעות ידנית', 'warning')
    except Exception as e:
        flash(f'שגיאה בסריקת מטבעות: {str(e)}', 'danger')
    
    return redirect(url_for('watchlist_page'))

@app.route('/edit_sltp', methods=['POST'])
def edit_sltp():
    """עריכת רמות Stop Loss ו-Take Profit"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('positions_page'))
    
    symbol = request.form.get('symbol')
    
    try:
        stop_loss = float(request.form.get('stop_loss', 0))
        take_profit = float(request.form.get('take_profit', 0))
    except ValueError:
        flash('ערכים לא תקינים', 'danger')
        return redirect(url_for('positions_page'))
    
    # קבלת פוזיציות ממסד הנתונים
    positions = db.get_open_positions()
    
    if not symbol or symbol not in positions:
        flash('לא נמצאה פוזיציה פתוחה', 'warning')
        return redirect(url_for('positions_page'))
    
    if stop_loss <= 0 or take_profit <= 0:
        flash('ערכים לא תקינים', 'danger')
        return redirect(url_for('positions_page'))
    
    # עדכון ערכי SL/TP
    positions[symbol]['stop_loss'] = stop_loss
    positions[symbol]['take_profit'] = take_profit
    
    # עדכון במסד הנתונים
    db.update_open_positions(positions)
    
    # עדכון ערכים בבוט אם הוא רץ
    if bot_running and hasattr(bot, 'open_positions'):
        bot.open_positions[symbol]['stop_loss'] = stop_loss
        bot.open_positions[symbol]['take_profit'] = take_profit
    
    flash(f'רמות SL/TP עבור {symbol} עודכנו בהצלחה', 'success')
    return redirect(url_for('positions_page'))

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    """ניקוי לוגים"""
    global bot_log_queue
    while not bot_log_queue.empty():
        try:
            bot_log_queue.get_nowait()
        except queue.Empty:
            break
    
    return jsonify({'success': True})

@app.route('/create_backup', methods=['POST'])
def create_backup_route():
    """יצירת גיבוי של מסד הנתונים"""
    backup_file = db.create_backup()
    
    if backup_file:
        flash(f'גיבוי נוצר בהצלחה: {backup_file}', 'success')
    else:
        flash('שגיאה ביצירת גיבוי', 'danger')
    
    return redirect(url_for('index'))

@app.route('/restore_backup', methods=['POST'])
def restore_backup_route():
    """שחזור מסד נתונים מגיבוי"""
    if bot_running:
        flash('לא ניתן לשחזר מגיבוי כאשר הבוט פעיל', 'warning')
        return redirect(url_for('index'))
    
    # בדיקה אם קובץ הועלה
    if 'backup_file' in request.files:
        file = request.files['backup_file']
        if file.filename == '':
            flash('לא נבחר קובץ', 'warning')
            return redirect(url_for('index'))
        
        if file:
            # שמירת הקובץ באופן זמני
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # שחזור מהקובץ
            if db.restore_from_backup(filepath):
                flash('מסד הנתונים שוחזר בהצלחה', 'success')
            else:
                flash('שגיאה בשחזור מסד הנתונים', 'danger')
            
            # ניקיון
            try:
                os.remove(filepath)
            except:
                pass
            
            return redirect(url_for('index'))
    
    # אם לא הועלה קובץ, בדוק אם נבחר גיבוי מהרשימה
    backup_file = request.form.get('backup_select')
    
    if not backup_file:
        flash('לא נבחר קובץ גיבוי', 'warning')
        return redirect(url_for('backups_page'))
    
    backup_path = os.path.join(BACKUP_FOLDER, backup_file)
    
    if not os.path.exists(backup_path):
        flash('קובץ הגיבוי לא נמצא', 'danger')
        return redirect(url_for('backups_page'))
    
    if db.restore_from_backup(backup_path):
        flash('מסד הנתונים שוחזר בהצלחה', 'success')
    else:
        flash('שגיאה בשחזור מסד הנתונים', 'danger')
    
    return redirect(url_for('index'))

@app.route('/backups')
def backups_page():
    """דף ניהול גיבויים"""
    # קבלת רשימת קבצי גיבוי
    backups = []
    if os.path.exists(BACKUP_FOLDER):
        for file in os.listdir(BACKUP_FOLDER):
            if file.endswith('.json'):
                file_path = os.path.join(BACKUP_FOLDER, file)
                file_size = os.path.getsize(file_path)
                file_date = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                backups.append({
                    'name': file,
                    'size': file_size,
                    'date': file_date,
                    'path': file_path
                })
    
    # מיון לפי תאריך (החדש ביותר למעלה)
    backups = sorted(backups, key=lambda x: x['date'], reverse=True)
    
    return render_template('backups.html', backups=backups)

@app.route('/download_backup/<filename>')
def download_backup(filename):
    """הורדת קובץ גיבוי"""
    return send_file(os.path.join(BACKUP_FOLDER, filename), as_attachment=True)

@app.route('/delete_backup/<filename>', methods=['POST'])
def delete_backup(filename):
    """מחיקת קובץ גיבוי"""
    file_path = os.path.join(BACKUP_FOLDER, filename)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            flash(f'הגיבוי {filename} נמחק בהצלחה', 'success')
        except Exception as e:
            flash(f'שגיאה במחיקת הגיבוי: {str(e)}', 'danger')
    else:
        flash('קובץ הגיבוי לא נמצא', 'warning')
    
    return redirect(url_for('backups_page'))

@app.route('/api/logs')
def get_logs():
    """קבלת לוגים חדשים"""
    logs = []
    while not bot_log_queue.empty():
        try:
            logs.append(bot_log_queue.get_nowait())
        except queue.Empty:
            break
    
    return jsonify({'logs': logs})

@app.route('/api/data')
def get_data():
    """נקודת קצה API לקבלת נתונים עדכניים"""
    # עדכון נתונים
    fetch_latest_data()
    
    # המרת הנתונים לפורמט המתאים לממשק
    positions_list = []
    for symbol, pos in open_positions.items():
        # המרת datetime לstring אם צריך
        entry_time = pos['entry_time']
        if isinstance(entry_time, datetime):
            entry_time = entry_time.strftime('%Y-%m-%d %H:%M:%S')
        
        # חישוב מחיר נוכחי - אם חסר בשימוש במחיר הכניסה
        current_price = pos.get('current_price', pos['entry_price'])
        
        positions_list.append({
            'symbol': symbol,
            'entry_price': pos['entry_price'],
            'quantity': pos['quantity'],
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'entry_time': entry_time,
            'current_price': current_price,
            'profit_pct': ((current_price - pos['entry_price']) / pos['entry_price']) * 100,
            'profit_usd': (current_price - pos['entry_price']) * pos['quantity']
        })
    
    data = {
        'bot_running': bot_running,
        'open_positions': positions_list,
        'watched_symbols': watched_symbols,
        'total_profit': total_profit
    }
    
    return jsonify(data)

@app.route('/api/prices')
def get_prices():
    """API לקבלת מחירים עדכניים"""
    symbols = request.args.get('symbols', '')
    
    if symbols:
        symbol_list = symbols.split(',')
    else:
        # אם לא סופקו סימבולים, השתמש ברשימת המעקב והפוזיציות הפתוחות
        symbol_list = watched_symbols + list(open_positions.keys())
        symbol_list = list(set(symbol_list))  # הסרת כפילויות
    
    prices = {}
    
    # עדכון מהבוט אם פעיל
    if bot_running and bot and hasattr(bot, 'symbol_details'):
        for symbol in symbol_list:
            if symbol in bot.symbol_details and 'current_price' in bot.symbol_details[symbol]:
                prices[symbol] = bot.symbol_details[symbol]['current_price']
    
    # השלמה מהמסד
    for symbol in symbol_list:
        if symbol not in prices:
            price = db.get_symbol_price(symbol)
            if price:
                prices[symbol] = price
    
    return jsonify({'prices': prices})

@app.route('/api/refresh_data', methods=['POST'])
def refresh_data():
    """
    רענון נתונים מהבוט באופן יזום
    """
    if bot and bot_running:
        try:
            logger.info("מרענן נתונים מהבוט באופן יזום...")
            
            # עדכון נתונים
            fetch_latest_data()
            
            # אם יש לבוט מתודת רענון, נקרא לה
            if hasattr(bot, 'update_data'):
                bot.update_data()
            
            return jsonify({'success': True, 'message': 'נתונים רועננו בהצלחה'})
        except Exception as e:
            logger.error(f"שגיאה ברענון נתונים: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'הבוט אינו רץ'}), 400

@app.route('/debug')
def debug_page():
    """דף דיבאג למידע מפורט על הבוט"""
    # מידע בסיסי
    debug_info = {
        'bot_running': bot_running,
        'bot_exists': bot is not None,
        'bot_type': str(type(bot)) if bot else None,
        'bot_thread_alive': bot_thread.is_alive() if bot_thread else None,
        'update_thread_alive': update_thread.is_alive() if update_thread else None,
        'open_positions': open_positions,
        'open_positions_len': len(open_positions),
        'watched_symbols': watched_symbols,
        'watched_symbols_len': len(watched_symbols),
        'total_profit': total_profit,
        'start_time': start_time,
        'last_data_update': last_data_update,
        'last_price_update': last_price_update
    }
    
    # בדיקת תכונות הבוט
    bot_attrs = {}
    bot_methods = {}
    if bot:
        # בדיקת תכונות
        for attr in ['running', 'open_positions', 'watched_symbols', 'profit_loss', 'symbol_details']:
            bot_attrs[attr] = hasattr(bot, attr)
        
        # בדיקת מתודות
        for method in ['run', 'stop', 'update_data', 'check_entry_conditions', 'execute_trade_strategy', 'monitor_open_positions']:
            bot_methods[method] = hasattr(bot, method)
    
    # מידע על מסד הנתונים
    db_info = {}
    try:
        db_info['trades_count'] = len(db.get_trades(limit=10000))
        db_info['symbols_count'] = len(db.get_watched_symbols())
        db_info['positions_count'] = len(db.get_open_positions())
        db_info['settings_exists'] = db.load_settings() is not None
        
        # מידע על קבצי גיבוי
        db_info['backups_count'] = len([f for f in os.listdir(BACKUP_FOLDER) if f.endswith('.json')])
    except Exception as e:
        db_info['error'] = str(e)
    
    return render_template('debug.html', 
                           debug_info=debug_info, 
                           bot_attrs=bot_attrs,
                           bot_methods=bot_methods,
                           db_info=db_info)

# ===== Socket.IO Events =====

@socketio.on('connect')
def handle_connect():
    """חיבור לקוח חדש"""
    global active_connections
    active_connections += 1
    logger.debug(f"לקוח חדש התחבר. מספר חיבורים פעילים: {active_connections}")

@socketio.on('disconnect')
def handle_disconnect():
    """ניתוק לקוח"""
    global active_connections
    active_connections -= 1
    logger.debug(f"לקוח התנתק. מספר חיבורים פעילים: {active_connections}")

@socketio.on('request_update')
def handle_request_update():
    """בקשה לעדכון נתונים מהלקוח"""
    # עדכון נתונים
    fetch_latest_data()
    
    # שליחת עדכון
    emit('data_update', {'timestamp': datetime.now().isoformat()})

# ===== הפעלת השרת =====

if __name__ == '__main__':
    # וידוא קיום תיקיות
    ensure_directories_exist()
    
    # הפעלת השרת עם תמיכה ב-Socket.IO
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)