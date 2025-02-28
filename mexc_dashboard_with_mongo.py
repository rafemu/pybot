from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import threading
import queue
import time
import logging
from datetime import datetime, timedelta
import os
from db_manager import DatabaseManager  # יבוא מנהל מסד הנתונים

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

# יצירת חיבור למסד הנתונים
db = DatabaseManager(connection_string="mongodb://localhost:27017/")

# משתנים גלובליים
bot = None
bot_thread = None
bot_running = False
bot_log_queue = queue.Queue()
start_time = None

# טעינת מודול הבוט באופן דינמי
def load_bot_module():
    try:
        # בדיקה אם קובץ הבוט קיים
        if not os.path.exists('mexc_bot.py'):
            logger.error("קובץ הבוט mexc_bot.py לא נמצא!")
            return None
        
        # קוד לטעינת המודול...
    except Exception as e:
        logger.error(f"שגיאה בטעינת מודול הבוט: {str(e)}")
        return None

# מטפל לוגים שמעביר לוגים לתור
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

# פונקציה להפעלת הבוט בתהליך נפרד
def run_bot(settings):
    global bot, bot_running, start_time, bot_thread
    
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
        bot.investment_amount = settings['investment']
        bot.trade_size = settings['trade_size']
        bot.stop_loss_percent = settings['stop_loss']
        bot.take_profit_percent = settings['take_profit']
        bot.max_watched_symbols = settings['max_watched']
        bot.max_positions = settings['max_positions']
        bot.symbol_scan_interval = settings['scan_interval']
        
        # הוספת מטפל לוגים לתור
        log_handler = QueueHandler(bot_log_queue)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger("MEXC-TradingBot").addHandler(log_handler)
        
        # הפעלת הבוט
        bot_running = True
        start_time = datetime.now()
        
        # הפעלת פונקציית run של הבוט בתהליך נפרד
        def run_bot_func():
            try:
                bot.run()
            except Exception as e:
                logger.error(f"שגיאה בהפעלת הבוט: {str(e)}")
        
        bot_thread = threading.Thread(target=run_bot_func)
        bot_thread.daemon = True
        bot_thread.start()
        
        return True
    except Exception as e:
        logger.error(f"שגיאה בהפעלת הבוט: {str(e)}")
        return False

# עצירת הבוט
def stop_bot():
    global bot, bot_running
    
    if not bot_running:
        return True
    
    try:
        # עצירת הבוט
        bot_running = False
        
        # כאן יש לממש מנגנון עצירה בתוך הבוט עצמו אם קיים
        if hasattr(bot, 'running'):
            bot.running = False
        
        # יצירת גיבוי של הנתונים
        db.create_backup()
        
        return True
    except Exception as e:
        logger.error(f"שגיאה בעצירת הבוט: {str(e)}")
        return False

# routes Flask

@app.route('/')
def index():
    """דף הבית של הממשק"""
    # טעינת נתונים ממסד הנתונים במקום ממשתנים גלובליים
    settings = db.load_settings()
    open_positions = db.get_open_positions()
    watched_symbols = db.get_watched_symbols()
    
    # חישוב רווח/הפסד כולל מהיסטוריית עסקאות
    trades = db.get_trades(limit=1000)
    total_profit = sum(trade.get('profit', 0) for trade in trades if 'profit' in trade)
    
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
    
    return render_template(
        'index.html',
        settings=settings,
        bot_running=bot_running,
        uptime=uptime_str,
        open_positions=open_positions,
        watched_symbols=watched_symbols,
        total_profit=total_profit,
        logs=logs
    )

@app.route('/start_bot', methods=['POST'])
def start_bot():
    """הפעלת הבוט"""
    if bot_running:
        flash('הבוט כבר רץ!', 'warning')
        return redirect(url_for('index'))
    
    # טעינת הגדרות ממסד הנתונים
    settings = db.load_settings()
    
    # עדכון הגדרות אם נשלחו
    if request.form:
        settings['api_key'] = request.form.get('api_key', settings['api_key'])
        settings['api_secret'] = request.form.get('api_secret', settings['api_secret'])
        settings['test_mode'] = 'test_mode' in request.form
        
        try:
            settings['investment'] = float(request.form.get('investment', settings['investment']))
            settings['trade_size'] = float(request.form.get('trade_size', settings['trade_size']))
            settings['stop_loss'] = float(request.form.get('stop_loss', settings['stop_loss']))
            settings['take_profit'] = float(request.form.get('take_profit', settings['take_profit']))
            settings['max_watched'] = int(request.form.get('max_watched', settings['max_watched']))
            settings['max_positions'] = int(request.form.get('max_positions', settings['max_positions']))
            settings['scan_interval'] = int(request.form.get('scan_interval', settings['scan_interval']))
        except ValueError:
            flash('ערכים לא תקינים בטופס', 'danger')
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
        settings['api_key'] = request.form.get('api_key', '')
        settings['api_secret'] = request.form.get('api_secret', '')
        settings['test_mode'] = 'test_mode' in request.form
        
        try:
            settings['investment'] = float(request.form.get('investment', 100.0))
            settings['trade_size'] = float(request.form.get('trade_size', 10.0))
            settings['stop_loss'] = float(request.form.get('stop_loss', 1.5))
            settings['take_profit'] = float(request.form.get('take_profit', 2.5))
            settings['max_watched'] = int(request.form.get('max_watched', 5))
            settings['max_positions'] = int(request.form.get('max_positions', 3))
            settings['scan_interval'] = int(request.form.get('scan_interval', 15))
        except ValueError:
            flash('ערכים לא תקינים בטופס', 'danger')
            return redirect(url_for('settings_page'))
        
        # שמירת ההגדרות במסד הנתונים
        db.save_settings(settings)
        flash('ההגדרות נשמרו בהצלחה', 'success')
        return redirect(url_for('index'))
    
    # טעינת הגדרות עבור GET
    settings = db.load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/positions')
def positions_page():
    """דף פוזיציות פתוחות"""
    positions = db.get_open_positions()
    return render_template('positions.html', positions=positions)

@app.route('/watchlist')
def watchlist_page():
    """דף רשימת מעקב"""
    symbols = db.get_watched_symbols()
    
    # קבלת פרטי סימבולים מהמסד
    symbol_details = {}
    for symbol in symbols:
        data = db.get_symbol_data(symbol)
        if data:
            symbol_details[symbol] = data
    
    return render_template('watchlist.html', 
                           symbols=symbols,
                           symbol_details=symbol_details)

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
    return render_template('logs.html', logs=logs)

@app.route('/add_symbol', methods=['POST'])
def add_symbol():
    """הוספת סימבול לרשימת המעקב"""
    symbol = request.form.get('symbol', '').upper()
    
    if not symbol:
        flash('נא להזין סימבול תקין', 'warning')
        return redirect(url_for('watchlist_page'))
    
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('watchlist_page'))
    
    # קבלת רשימת סימבולים נוכחית
    watched_symbols = db.get_watched_symbols()
    
    if symbol not in watched_symbols:
        watched_symbols.append(symbol)
        # עדכון במסד הנתונים
        db.update_watched_symbols(watched_symbols)
        
        # עדכון בבוט אם רץ
        if bot and hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = watched_symbols
    
    flash(f'הסימבול {symbol} נוסף בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/remove_symbol/<symbol>', methods=['POST'])
def remove_symbol(symbol):
    """הסרת סימבול מרשימת המעקב"""
    # קבלת רשימת סימבולים נוכחית
    watched_symbols = db.get_watched_symbols()
    
    if symbol in watched_symbols:
        watched_symbols.remove(symbol)
        # עדכון במסד הנתונים
        db.update_watched_symbols(watched_symbols)
        
        # עדכון בבוט אם רץ
        if bot and hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = watched_symbols
    
    flash(f'הסימבול {symbol} הוסר בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/close_position/<symbol>', methods=['POST'])
def close_position(symbol):
    """סגירת פוזיציה פתוחה"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('positions_page'))
    
    # קבלת פוזיציות ממסד הנתונים
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
    stop_loss = float(request.form.get('stop_loss', 0))
    take_profit = float(request.form.get('take_profit', 0))
    
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
    # קבלת נתונים ממסד הנתונים
    positions = db.get_open_positions()
    watched_symbols = db.get_watched_symbols()
    
    # חישוב רווח/הפסד כולל מהיסטוריית עסקאות
    trades = db.get_trades(limit=1000)
    total_profit = sum(trade.get('profit', 0) for trade in trades if 'profit' in trade)
    
    # המרת הנתונים לפורמט המתאים לממשק
    positions_list = []
    for symbol, pos in positions.items():
        # המרת datetime לstring אם צריך
        entry_time = pos['entry_time']
        if isinstance(entry_time, datetime):
            entry_time = entry_time.strftime('%Y-%m-%d %H:%M:%S')
        
        positions_list.append({
            'symbol': symbol,
            'entry_price': pos['entry_price'],
            'quantity': pos['quantity'],
            'stop_loss': pos['stop_loss'],
            'take_profit': pos['take_profit'],
            'entry_time': entry_time,
            'profit_pct': ((pos.get('current_price', pos['entry_price']) - pos['entry_price']) / pos['entry_price']) * 100,
            'profit_usd': (pos.get('current_price', pos['entry_price']) - pos['entry_price']) * pos['quantity']
        })
    
    data = {
        'bot_running': bot_running,
        'open_positions': positions_list,
        'watched_symbols': watched_symbols,
        'total_profit': total_profit
    }
    
    return jsonify(data)

@app.route('/statistics')
def statistics_page():
    """דף סטטיסטיקות מסחר"""
    # קבלת פרמטרים מה-URL
    days = request.args.get('days', default=30, type=int)
    
    # קבלת סטטיסטיקות ממסד הנתונים
    stats = db.get_trading_statistics(days=days)
    
    # קבלת כל העסקאות לתרשים
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    trades = db.get_trades(start_date=start_date, end_date=end_date, limit=1000)
    
    return render_template(
        'statistics.html',
        stats=stats,
        days=days,
        trades=trades
    )

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
    
    backup_file = request.form.get('backup_file')
    
    if not backup_file:
        flash('לא נבחר קובץ גיבוי', 'warning')
        return redirect(url_for('index'))
    
    if not os.path.exists(backup_file):
        flash('קובץ הגיבוי לא נמצא', 'danger')
        return redirect(url_for('index'))
    
    if db.restore_from_backup(backup_file):
        flash('מסד הנתונים שוחזר בהצלחה', 'success')
    else:
        flash('שגיאה בשחזור מסד הנתונים', 'danger')
    
    return redirect(url_for('index'))

# הפעלת השרת
if __name__ == '__main__':
    # בדיקה אם תיקיות נדרשות קיימות
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    if not os.path.exists('static'):
        os.makedirs('static')
    
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    # הפעלת השרת
    app.run(debug=True, host='0.0.0.0', port=5000)