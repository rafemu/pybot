# קובץ הגדרות לבוט מסחר MEXC
# העתק קובץ זה ל- config.py ומלא את הפרטים שלך

# מפתחות API של MEXC
API_KEY = "mx0vglHyxTIMWlutTn"
API_SECRET = "eed4312d95ca45c59ddb743ad3061cb5"


# הגדרות מסחר
INVESTMENT_AMOUNT = 100  # סכום ההשקעה הכולל בדולרים
TRADE_SIZE = 10  # גודל כל עסקה בדולרים
STOP_LOSS_PERCENT = 1.5  # אחוז הפסד מקסימלי לעסקה
TAKE_PROFIT_PERCENT = 2.5  # אחוז רווח לפני מימוש

# הגדרות מסחר מרובה סימבולים
MAX_WATCHED_SYMBOLS = 5  # מספר מקסימלי של מטבעות למעקב
MAX_POSITIONS = 3  # מספר מקסימלי של פוזיציות פתוחות במקביל
SYMBOL_SCAN_INTERVAL = 15  # בדיקת מטבעות חדשים כל X דקות


# הגדרות מערכת
TEST_MODE = False  # שנה ל-False כדי לסחור באופן אמיתי
