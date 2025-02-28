<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>בוט מסחר MEXC - לוח בקרה</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
        .profit {
            color: green;
        }
        .loss {
            color: red;
        }
        .bot-status {
            font-weight: bold;
        }
        .status-running {
            color: green;
        }
        .status-stopped {
            color: red;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">סטטוס בוט</h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-6">
                                <strong>סטטוס:</strong> 
                                <span class="bot-status {% if bot_running %}status-running{% else %}status-stopped{% endif %}">
                                    {% if bot_running %}פעיל{% else %}לא פעיל{% endif %}
                                </span>
                            </div>
                            <div class="col-6">
                                <strong>זמן פעילות:</strong> {{ uptime }}
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-6">
                                <strong>פוזיציות פתוחות:</strong> {{ open_positions|length }}
                            </div>
                            <div class="col-6">
                                <strong>סה״כ רווח:</strong> 
                                <span class="{% if total_profit > 0 %}profit{% elif total_profit < 0 %}loss{% endif %}">
                                    ${{ "%.2f"|format(total_profit) }}
                                </span>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-6">
                                <strong>מטבעות במעקב:</strong> {{ watched_symbols|length }}
                            </div>
                            <div class="col-6">
                                <strong>מצב:</strong> {% if settings.test_mode %}מצב בדיקה{% else %}מסחר אמיתי{% endif %}
                            </div>
                        </div>
                    </div>
                    <div class="card-footer">
                        {% if bot_running %}
                            <form action="/stop_bot" method="post" class="d-inline">
                                <button type="submit" class="btn btn-danger">
                                    <i class="bi bi-stop-circle"></i> עצור בוט
                                </button>
                            </form>
                        {% else %}
                            <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#startBotModal">
                                <i class="bi bi-play-circle"></i> הפעל בוט
                            </button>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">פוזיציות פתוחות</h5>
                    </div>
                    <div class="card-body">
                        {% if open_positions %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>מטבע</th>
                                            <th>מחיר כניסה</th>
                                            <th>רווח/הפסד</th>
                                            <th>פעולות</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for symbol, position in open_positions.items() %}
                                            {% set profit_pct = ((position.current_price if position.current_price is defined else position.entry_price) - position.entry_price) / position.entry_price * 100 %}
                                            {% set profit_usd = (position.current_price if position.current_price is defined else position.entry_price - position.entry_price) * position.quantity %}
                                            <tr>
                                                <td>{{ symbol }}</td>
                                                <td>${{ "%.8f"|format(position.entry_price) }}</td>
                                                <td class="{% if profit_pct > 0 %}profit{% elif profit_pct < 0 %}loss{% endif %}">
                                                    {{ "%.2f"|format(profit_pct) }}% (${{ "%.2f"|format(profit_usd) }})
                                                </td>
                                                <td>
                                                    <form action="/close_position/{{ symbol }}" method="post" class="d-inline">
                                                        <button type="submit" class="btn btn-sm btn-outline-danger">סגור</button>
                                                    </form>
                                                </td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="alert alert-info">אין פוזיציות פתוחות כרגע</div>
                        {% endif %}
                    </div>
                    <div class="card-footer">
                        <a href="/positions" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">מטבעות במעקב</h5>
                    </div>
                    <div class="card-body">
                        {% if watched_symbols %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>מטבע</th>
                                            <th>פעולות</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for symbol in watched_symbols %}
                                            <tr>
                                                <td>{{ symbol }}</td>
                                                <td>
                                                    <form action="/remove_symbol/{{ symbol }}" method="post" class="d-inline">
                                                        <button type="submit" class="btn btn-sm btn-outline-danger">הסר</button>
                                                    </form>
                                                </td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="alert alert-info">אין מטבעות במעקב כרגע</div>
                        {% endif %}
                    </div>
                    <div class="card-footer">
                        <a href="/watchlist" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">לוגים אחרונים</h5>
                    </div>
                    <div class="card-body">
                        <div style="max-height: 300px; overflow-y: auto;">
                            {% if logs %}
                                <div class="list-group">
                                    {% for log in logs[:10] %}
                                        <div class="list-group-item list-group-item-action">{{ log }}</div>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <div class="alert alert-info">אין לוגים כרגע</div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="card-footer">
                        <a href="/logs" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- מודל הפעלת בוט -->
    <div class="modal fade" id="startBotModal" tabindex="-1" aria-labelledby="startBotModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="startBotModalLabel">הפעלת בוט</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form action="/start_bot" method="post">
                    <div class="modal-body">
                        <div class="mb-3">
                                        <td>
                                            <form action="/close_position/{{ symbol }}" method="post" class="d-inline">
                                                <button type="submit" class="btn btn-sm btn-outline-danger">סגור פוזיציה</button>
                                            </form>
                                            <button type="button" class="btn btn-sm btn-outline-primary edit-sl-tp" data-symbol="{{ symbol }}" data-sl="{{ position.stop_loss }}" data-tp="{{ position.take_profit }}">
                                                ערוך SL/TP
                                            </button>
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="alert alert-info">אין פוזיציות פתוחות כרגע</div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- מודל עריכת SL/TP -->
    <div class="modal fade" id="editSLTPModal" tabindex="-1" aria-labelledby="editSLTPModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="editSLTPModalLabel">עריכת רמות Stop Loss / Take Profit</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form id="sltp-form" action="/edit_sltp" method="post">
                    <div class="modal-body">
                        <input type="hidden" id="edit-symbol" name="symbol">
                        <div class="mb-3">
                            <label for="edit-sl" class="form-label">Stop Loss ($)</label>
                            <input type="number" class="form-control" id="edit-sl" name="stop_loss" step="0.00000001">
                        </div>
                        <div class="mb-3">
                            <label for="edit-tp" class="form-label">Take Profit ($)</label>
                            <input type="number" class="form-control" id="edit-tp" name="take_profit" step="0.00000001">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ביטול</button>
                        <button type="submit" class="btn btn-primary">שמור</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // פתיחת מודל עריכת SL/TP
        document.querySelectorAll('.edit-sl-tp').forEach(button => {
            button.addEventListener('click', function() {
                const symbol = this.getAttribute('data-symbol');
                const sl = this.getAttribute('data-sl');
                const tp = this.getAttribute('data-tp');
                
                document.getElementById('edit-symbol').value = symbol;
                document.getElementById('edit-sl').value = sl;
                document.getElementById('edit-tp').value = tp;
                
                const modal = new bootstrap.Modal(document.getElementById('editSLTPModal'));
                modal.show();
            });
        });

        // עדכון אוטומטי של הנתונים
        setInterval(function() {
            location.reload();
        }, 30000); // רענון כל 30 שניות
    </script>
</body>
</html>
        ''',
        'watchlist.html': '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>רשימת מעקב - בוט מסחר MEXC</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">הוספת מטבע לרשימת המעקב</h5>
                    </div>
                    <div class="card-body">
                        <form action="/add_symbol" method="post" class="row g-3">
                            <div class="col-9">
                                <input type="text" class="form-control" id="symbol" name="symbol" placeholder="הזן סימבול (לדוגמה: BTCUSDT)" required>
                            </div>
                            <div class="col-3">
                                <button type="submit" class="btn btn-primary w-100">הוסף</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">סריקת מטבעות חדשים</h5>
                    </div>
                    <div class="card-body">
                        <p>הפעל סריקה אוטומטית של מטבעות חדשים על פי האסטרטגיה.</p>
                        <form action="/scan_symbols" method="post">
                            <button type="submit" class="btn btn-success">
                                <i class="bi bi-search"></i> התחל סריקה
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">מטבעות במעקב</h5>
                <span class="badge bg-light text-dark">{{ symbols|length }} מטבעות</span>
            </div>
            <div class="card-body">
                {% if symbols %}
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>מטבע</th>
                                    <th>מחיר נוכחי</th>
                                    <th>RSI</th>
                                    <th>MACD</th>
                                    <th>תנודתיות</th>
                                    <th>ציון</th>
                                    <th>פעולות</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for symbol in symbols %}
                                    <tr>
                                        <td>{{ symbol }}</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>-</td>
                                        <td>
                                            <form action="/remove_symbol/{{ symbol }}" method="post" class="d-inline">
                                                <button type="submit" class="btn btn-sm btn-outline-danger">הסר</button>
                                            </form>
                                        </td>
                                    </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <div class="alert alert-info">אין מטבעות במעקב כרגע</div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // עדכון אוטומטי של הנתונים
        setInterval(function() {
            location.reload();
        }, 30000); // רענון כל 30 שניות
    </script>
</body>
</html>
        ''',
        'logs.html': '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>לוגים - בוט מסחר MEXC</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
        .log-container {
            max-height: 700px;
            overflow-y: auto;
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px;
            font-family: monospace;
        }
        .log-entry {
            border-bottom: 1px solid #e0e0e0;
            padding: 5px 0;
            white-space: pre-wrap;
            word-break: break-word;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">לוגים של הבוט</h5>
                <div>
                    <button id="refresh-logs" class="btn btn-sm btn-light">
                        <i class="bi bi-arrow-clockwise"></i> רענן
                    </button>
                    <button id="clear-logs" class="btn btn-sm btn-light">
                        <i class="bi bi-trash"></i> נקה
                    </button>
                    <button id="save-logs" class="btn btn-sm btn-light">
                        <i class="bi bi-download"></i> שמור
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="log-container" id="log-container">
                    {% if logs %}
                        {% for log in logs %}
                            <div class="log-entry">{{ log }}</div>
                        {% endfor %}
                    {% else %}
                        <div class="text-center text-muted py-3">אין לוגים כרגע</div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // רענון לוגים
        document.getElementById('refresh-logs').addEventListener('click', function() {
            location.reload();
        });

        // ניקוי לוגים
        document.getElementById('clear-logs').addEventListener('click', function() {
            if (confirm('האם אתה בטוח שברצונך לנקות את כל הלוגים?')) {
                fetch('/clear_logs', {
                    method: 'POST',
                }).then(() => {
                    location.reload();
                });
            }
        });

        // שמירת לוגים
        document.getElementById('save-logs').addEventListener('click', function() {
            const logs = Array.from(document.querySelectorAll('.log-entry')).map(el => el.textContent).join('\\n');
            const blob = new Blob([logs], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'mexc_bot_logs_' + new Date().toISOString().replace(/[:.]/g, '-') + '.log';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });

        // גלילה לחלק התחתון של הלוגים
        document.getElementById('log-container').scrollTop = document.getElementById('log-container').scrollHeight;

        // עדכון אוטומטי של הלוגים
        setInterval(function() {
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    if (data.logs && data.logs.length > 0) {
                        const logContainer = document.getElementById('log-container');
                        const wasScrolledToBottom = logContainer.scrollHeight - logContainer.clientHeight <= logContainer.scrollTop + 5;
                        
                        // הוספת לוגים חדשים
                        data.logs.forEach(log => {
                            const logEntry = document.createElement('div');
                            logEntry.className = 'log-entry';
                            logEntry.textContent = log;
                            logContainer.appendChild(logEntry);
                        });
                        
                        // שמירה על גלילה לחלק התחתון אם היינו בחלק התחתון
                        if (wasScrolledToBottom) {
                            logContainer.scrollTop = logContainer.scrollHeight;
                        }
                    }
                })
                .catch(error => console.error('Error fetching logs:', error));
        }, 5000); // בדיקת לוגים חדשים כל 5 שניות
    </script>
</body>
</html>
        '''
    }
    
    # יצירת תבניות
    for filename, content in templates.items():
        if not os.path.exists(f"templates/{filename}"):
            with open(f"templates/{filename}", "w", encoding="utf-8") as f:
                f.write(content)

# הוספת routes נוספים
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
    
    if not symbol or symbol not in open_positions:
        flash('לא נמצאה פוזיציה פתוחה', 'warning')
        return redirect(url_for('positions_page'))
    
    if stop_loss <= 0 or take_profit <= 0:
        flash('ערכים לא תקינים', 'danger')
        return redirect(url_for('positions_page'))
    
    # עדכון ערכי SL/TP
    open_positions[symbol]['stop_loss'] = stop_loss
    open_positions[symbol]['take_profit'] = take_profit
    
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
        'settings.html': '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>הגדרות - בוט מסחר MEXC</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card">
            <div class="card-header bg-primary text-white">
                <h5 class="card-title mb-0">הגדרות בוט</h5>
            </div>
            <div class="card-body">
                <form action="/settings" method="post">
                    <div class="row mb-4">
                        <div class="col-lg-6">
                            <h6 class="mb-3">הגדרות API</h6>
                            <div class="mb-3">
                                <label for="api_key" class="form-label">API Key</label>
                                <input type="text" class="form-control" id="api_key" name="api_key" value="{{ settings.api_key }}">
                            </div>
                            <div class="mb-3">
                                <label for="api_secret" class="form-label">API Secret</label>
                                <div class="input-group">
                                    <input type="password" class="form-control" id="api_secret" name="api_secret" value="{{ settings.api_secret }}">
                                    <button class="btn btn-outline-secondary" type="button" id="togglePassword">
                                        <i class="bi bi-eye"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mb-3 form-check">
                                <input type="checkbox" class="form-check-input" id="test_mode" name="test_mode" {% if settings.test_mode %}checked{% endif %}>
                                <label class="form-check-label" for="test_mode">מצב בדיקה (ללא מסחר אמיתי)</label>
                            </div>
                        </div>

                        <div class="col-lg-6">
                            <h6 class="mb-3">הגדרות מסחר</h6>
                            <div class="mb-3">
                                <label for="investment" class="form-label">סכום השקעה ($)</label>
                                <input type="number" class="form-control" id="investment" name="investment" value="{{ settings.investment }}" min="10" step="10">
                            </div>
                            <div class="mb-3">
                                <label for="trade_size" class="form-label">גודל עסקה ($)</label>
                                <input type="number" class="form-control" id="trade_size" name="trade_size" value="{{ settings.trade_size }}" min="1" step="1">
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="stop_loss" class="form-label">Stop Loss (%)</label>
                                        <input type="number" class="form-control" id="stop_loss" name="stop_loss" value="{{ settings.stop_loss }}" min="0.1" max="10" step="0.1">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="mb-3">
                                        <label for="take_profit" class="form-label">Take Profit (%)</label>
                                        <input type="number" class="form-control" id="take_profit" name="take_profit" value="{{ settings.take_profit }}" min="0.1" max="20" step="0.1">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="row mb-4">
                        <div class="col-12">
                            <h6 class="mb-3">הגדרות מסחר מרובה סימבולים</h6>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="max_watched" class="form-label">מספר מטבעות למעקב</label>
                                <input type="number" class="form-control" id="max_watched" name="max_watched" value="{{ settings.max_watched }}" min="1" max="20">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="max_positions" class="form-label">מספר פוזיציות מקסימלי</label>
                                <input type="number" class="form-control" id="max_positions" name="max_positions" value="{{ settings.max_positions }}" min="1" max="10">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="mb-3">
                                <label for="scan_interval" class="form-label">תדירות סריקת מטבעות (דקות)</label>
                                <input type="number" class="form-control" id="scan_interval" name="scan_interval" value="{{ settings.scan_interval }}" min="5" max="60">
                            </div>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between">
                        <div>
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-save"></i> שמור הגדרות
                            </button>
                            <button type="reset" class="btn btn-outline-secondary">
                                <i class="bi bi-arrow-counterclockwise"></i> אפס טופס
                            </button>
                        </div>
                        <button type="button" class="btn btn-danger" id="resetDefaultsBtn">
                            <i class="bi bi-exclamation-triangle"></i> אפס להגדרות ברירת מחדל
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- מודל אישור איפוס -->
    <div class="modal fade" id="resetModal" tabindex="-1" aria-labelledby="resetModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="resetModalLabel">אישור איפוס</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>האם אתה בטוח שברצונך לאפס את כל ההגדרות לברירת המחדל?</p>
                    <p class="text-danger">פעולה זו תמחק את כל ההגדרות הנוכחיות, כולל מפתחות ה-API!</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ביטול</button>
                    <button type="button" class="btn btn-danger" id="confirmResetBtn">אפס הגדרות</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // הצגת/הסתרת הסיסמה
        document.getElementById('togglePassword').addEventListener('click', function() {
            const apiSecretInput = document.getElementById('api_secret');
            const type = apiSecretInput.getAttribute('type');
            
            apiSecretInput.setAttribute('type', type === 'password' ? 'text' : 'password');
            this.querySelector('i').classList.toggle('bi-eye');
            this.querySelector('i').classList.toggle('bi-eye-slash');
        });

        // פתיחת מודל אישור איפוס
        document.getElementById('resetDefaultsBtn').addEventListener('click', function(e) {
            e.preventDefault();
            const resetModal = new bootstrap.Modal(document.getElementById('resetModal'));
            resetModal.show();
        });

        // איפוס להגדרות ברירת מחדל
        document.getElementById('confirmResetBtn').addEventListener('click', function() {
            // ערכי ברירת מחדל
            document.getElementById('api_key').value = '';
            document.getElementById('api_secret').value = '';
            document.getElementById('investment').value = '100';
            document.getElementById('trade_size').value = '10';
            document.getElementById('stop_loss').value = '1.5';
            document.getElementById('take_profit').value = '2.5';
            document.getElementById('max_watched').value = '5';
            document.getElementById('max_positions').value = '3';
            document.getElementById('scan_interval').value = '15';
            document.getElementById('test_mode').checked = true;
            
            // סגירת המודל
            bootstrap.Modal.getInstance(document.getElementById('resetModal')).hide();
            
            // שליחת הטופס
            document.querySelector('form').submit();
        });
    </script>
</body>
</html>
        ''',
        'positions.html': '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>פוזיציות פתוחות - בוט מסחר MEXC</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
        .profit {
            color: green;
        }
        .loss {
            color: red;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="card">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="card-title mb-0">פוזיציות פתוחות</h5>
                <span class="badge bg-light text-dark">{{ positions|length }} פוזיציות</span>
            </div>
            <div class="card-body">
                {% if positions %}
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>מטבע</th>
                                    <th>מחיר כניסה</th>
                                    <th>מחיר נוכחי</th>
                                    <th>כמות</th>
                                    <th>ערך ($)</th>
                                    <th>זמן כניסה</th>
                                    <th>Stop Loss</th>
                                    <th>Take Profit</th>
                                    <th>רווח/הפסד</th>
                                    <th>פעולות</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for symbol, position in positions.items() %}
                                    {% set current_price = position.current_price if position.current_price is defined else position.entry_price %}
                                    {% set profit_pct = (current_price - position.entry_price) / position.entry_price * 100 %}
                                    {% set profit_usd = (current_price - position.entry_price) * position.quantity %}
                                    {% set value = current_price * position.quantity %}
                                    <tr>
                                        <td>{{ symbol }}</td>
                                        <td>${{ "%.8f"|format(position.entry_price) }}</td>
                                        <td>${{ "%.8f"|format(current_price) }}</td>
                                        <td>{{ "%.6f"|format(position.quantity) }}</td>
                                        <td>${{ "%.2f"|format(value) }}</td>
                                        <td>{{ position.entry_time }}</td>
                                        <td>${{ "%.8f"|format(position.stop_loss) }}</td>
                                        <td>${{ "%.8f"|format(position.take_profit) }}</td>
                                        <td class="{% if profit_pct > 0 %}profit{% elif profit_pct < 0 %}loss{% endif %}">
                                            {{ "%.2f"|format(profit_pct) }}% (${{ "%.2f"|format(profit_usd) }})
                                        </td>
                                        <td>
                                            from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import threading
import queue
import time
import json
import os
import logging
from datetime import datetime
import importlib.util
import sys

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
app.secret_key = 'mexc_bot_secret_key'  # מפתח לשימוש ב-session ו-flash

# משתנים גלובליים לאחסון נתוני הבוט
bot = None
bot_thread = None
bot_running = False
bot_log_queue = queue.Queue()
watched_symbols = []
open_positions = {}
profit_history = []
total_profit = 0.0
start_time = None

# טעינת הגדרות מקובץ
def load_settings():
    if os.path.exists('bot_settings.json'):
        with open('bot_settings.json', 'r') as f:
            return json.load(f)
    else:
        # הגדרות ברירת מחדל
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

# שמירת הגדרות לקובץ
def save_settings(settings):
    with open('bot_settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

# טעינת מודול הבוט באופן דינמי
def load_bot_module():
    try:
        # בדיקה אם קובץ הבוט קיים
        if not os.path.exists('mexc_bot.py'):
            logger.error("קובץ הבוט mexc_bot.py לא נמצא!")
            return None
        
        # טעינת המודול באופן דינמי
        spec = importlib.util.spec_from_file_location("mexc_bot", "mexc_bot.py")
        mexc_bot = importlib.util.module_from_spec(spec)
        sys.modules["mexc_bot"] = mexc_bot
        spec.loader.exec_module(mexc_bot)
        
        return mexc_bot
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
    global bot, bot_running, start_time, total_profit, open_positions, watched_symbols
    
    mexc_bot_module = load_bot_module()
    if not mexc_bot_module:
        flash('שגיאה בטעינת מודול הבוט', 'danger')
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
        
        # התחלת תהליך עדכון נתונים
        data_thread = threading.Thread(target=update_bot_data)
        data_thread.daemon = True
        data_thread.start()
        
        # הפעלת הבוט
        bot.run()
        
        return True
    except Exception as e:
        logger.error(f"שגיאה בהפעלת הבוט: {str(e)}")
        return False

# פונקציה לעדכון נתוני הבוט
def update_bot_data():
    global bot, bot_running, open_positions, watched_symbols, total_profit
    
    while bot_running and bot:
        try:
            # עדכון נתונים מהבוט
            if hasattr(bot, 'open_positions'):
                open_positions = bot.open_positions
            
            if hasattr(bot, 'watched_symbols'):
                watched_symbols = bot.watched_symbols
            
            if hasattr(bot, 'profit_loss'):
                total_profit = bot.profit_loss
            
            # שינה של 2 שניות
            time.sleep(2)
        except Exception as e:
            logger.error(f"שגיאה בעדכון נתוני הבוט: {str(e)}")
            time.sleep(5)  # שינה ארוכה יותר במקרה של שגיאה

# עצירת הבוט
def stop_bot():
    global bot, bot_running
    
    if not bot_running:
        return True
    
    try:
        # עצירת הבוט
        bot_running = False
        
        # כאן יש לממש מנגנון עצירה בתוך הבוט עצמו אם קיים
        # למשל, אם הבוט יש לו דגל שמאפשר לעצור אותו
        if hasattr(bot, 'stop'):
            bot.stop()
        
        return True
    except Exception as e:
        logger.error(f"שגיאה בעצירת הבוט: {str(e)}")
        return False

# routes Flask

@app.route('/')
def index():
    """דף הבית של הממשק"""
    settings = load_settings()
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
    
    settings = load_settings()
    
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
    
    # שמירת ההגדרות
    save_settings(settings)
    
    # הפעלת הבוט בתהליך נפרד
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, args=(settings,))
    bot_thread.daemon = True
    bot_thread.start()
    
    flash('הבוט הופעל בהצלחה', 'success')
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
        settings = load_settings()
        
        # עדכון הגדרות
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
        
        # שמירת ההגדרות
        save_settings(settings)
        flash('ההגדרות נשמרו בהצלחה', 'success')
        return redirect(url_for('index'))
    
    # טעינת הגדרות עבור GET
    settings = load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/positions')
def positions_page():
    """דף פוזיציות פתוחות"""
    return render_template('positions.html', positions=open_positions)

@app.route('/watchlist')
def watchlist_page():
    """דף רשימת מעקב"""
    return render_template('watchlist.html', symbols=watched_symbols)

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
    
    global watched_symbols
    if symbol not in watched_symbols:
        watched_symbols.append(symbol)
        if hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = watched_symbols
    
    flash(f'הסימבול {symbol} נוסף בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/remove_symbol/<symbol>', methods=['POST'])
def remove_symbol(symbol):
    """הסרת סימבול מרשימת המעקב"""
    global watched_symbols
    
    if symbol in watched_symbols:
        watched_symbols.remove(symbol)
        if hasattr(bot, 'watched_symbols'):
            bot.watched_symbols = watched_symbols
    
    flash(f'הסימבול {symbol} הוסר בהצלחה', 'success')
    return redirect(url_for('watchlist_page'))

@app.route('/close_position/<symbol>', methods=['POST'])
def close_position(symbol):
    """סגירת פוזיציה פתוחה"""
    if not bot_running:
        flash('הבוט אינו רץ!', 'warning')
        return redirect(url_for('positions_page'))
    
    if symbol not in open_positions:
        flash(f'לא נמצאה פוזיציה פתוחה עבור {symbol}', 'warning')
        return redirect(url_for('positions_page'))
    
    try:
        # הפעלת פונקציית סגירת פוזיציה של הבוט
        # זה תלוי במימוש של הבוט שלך
        if hasattr(bot, 'close_position'):
            bot.close_position(symbol)
            flash(f'הפוזיציה ב-{symbol} נסגרה בהצלחה', 'success')
        else:
            flash('הבוט אינו תומך בסגירת פוזיציות ידנית', 'warning')
    except Exception as e:
        flash(f'שגיאה בסגירת הפוזיציה: {str(e)}', 'danger')
    
    return redirect(url_for('positions_page'))

@app.route('/api/data')
def get_data():
    """נקודת קצה API לקבלת נתונים עדכניים עבור עדכונים אוטומטיים"""
    data = {
        'bot_running': bot_running,
        'open_positions': [
            {
                'symbol': symbol,
                'entry_price': pos['entry_price'],
                'quantity': pos['quantity'],
                'stop_loss': pos['stop_loss'],
                'take_profit': pos['take_profit'],
                'entry_time': pos['entry_time'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(pos['entry_time'], datetime) else pos['entry_time'],
                'profit_pct': ((pos.get('current_price', pos['entry_price']) - pos['entry_price']) / pos['entry_price']) * 100,
                'profit_usd': (pos.get('current_price', pos['entry_price']) - pos['entry_price']) * pos['quantity']
            }
            for symbol, pos in open_positions.items()
        ],
        'watched_symbols': watched_symbols,
        'total_profit': total_profit
    }
    
    return jsonify(data)

# הפעלת השרת
if __name__ == '__main__':
    # בדיקה אם קיימת תיקיית templates
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # בדיקה אם קיימת תיקיית static
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # יצירת תבניות HTML אם אינן קיימות
    create_templates()
    
    # הפעלת השרת
    app.run(debug=True, host='0.0.0.0', port=5000)

# פונקציה ליצירת תבניות HTML
def create_templates():
    templates = {
        'index.html': '''
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>בוט מסחר MEXC - לוח בקרה</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        body {
            font-family: Arial, sans-serif;
            direction: rtl;
            text-align: right;
        }
        .card {
            margin-bottom: 20px;
        }
        .profit {
            color: green;
        }
        .loss {
            color: red;
        }
        .bot-status {
            font-weight: bold;
        }
        .status-running {
            color: green;
        }
        .status-stopped {
            color: red;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">בוט מסחר MEXC</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">בית</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/positions">פוזיציות</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/watchlist">רשימת מעקב</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/logs">לוגים</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/settings">הגדרות</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">סטטוס בוט</h5>
                    </div>
                    <div class="card-body">
                        <div class="row mb-3">
                            <div class="col-6">
                                <strong>סטטוס:</strong> 
                                <span class="bot-status {% if bot_running %}status-running{% else %}status-stopped{% endif %}">
                                    {% if bot_running %}פעיל{% else %}לא פעיל{% endif %}
                                </span>
                            </div>
                            <div class="col-6">
                                <strong>זמן פעילות:</strong> {{ uptime }}
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-6">
                                <strong>פוזיציות פתוחות:</strong> {{ open_positions|length }}
                            </div>
                            <div class="col-6">
                                <strong>סה״כ רווח:</strong> 
                                <span class="{% if total_profit > 0 %}profit{% elif total_profit < 0 %}loss{% endif %}">
                                    ${{ "%.2f"|format(total_profit) }}
                                </span>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-6">
                                <strong>מטבעות במעקב:</strong> {{ watched_symbols|length }}
                            </div>
                            <div class="col-6">
                                <strong>מצב:</strong> {% if settings.test_mode %}מצב בדיקה{% else %}מסחר אמיתי{% endif %}
                            </div>
                        </div>
                    </div>
                    <div class="card-footer">
                        {% if bot_running %}
                            <form action="/stop_bot" method="post" class="d-inline">
                                <button type="submit" class="btn btn-danger">
                                    <i class="bi bi-stop-circle"></i> עצור בוט
                                </button>
                            </form>
                        {% else %}
                            <button type="button" class="btn btn-success" data-bs-toggle="modal" data-bs-target="#startBotModal">
                                <i class="bi bi-play-circle"></i> הפעל בוט
                            </button>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">פוזיציות פתוחות</h5>
                    </div>
                    <div class="card-body">
                        {% if open_positions %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>מטבע</th>
                                            <th>מחיר כניסה</th>
                                            <th>רווח/הפסד</th>
                                            <th>פעולות</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for symbol, position in open_positions.items() %}
                                            {% set profit_pct = ((position.current_price if position.current_price is defined else position.entry_price) - position.entry_price) / position.entry_price * 100 %}
                                            {% set profit_usd = (position.current_price if position.current_price is defined else position.entry_price - position.entry_price) * position.quantity %}
                                            <tr>
                                                <td>{{ symbol }}</td>
                                                <td>${{ "%.8f"|format(position.entry_price) }}</td>
                                                <td class="{% if profit_pct > 0 %}profit{% elif profit_pct < 0 %}loss{% endif %}">
                                                    {{ "%.2f"|format(profit_pct) }}% (${{ "%.2f"|format(profit_usd) }})
                                                </td>
                                                <td>
                                                    <form action="/close_position/{{ symbol }}" method="post" class="d-inline">
                                                        <button type="submit" class="btn btn-sm btn-outline-danger">סגור</button>
                                                    </form>
                                                </td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="alert alert-info">אין פוזיציות פתוחות כרגע</div>
                        {% endif %}
                    </div>
                    <div class="card-footer">
                        <a href="/positions" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">מטבעות במעקב</h5>
                    </div>
                    <div class="card-body">
                        {% if watched_symbols %}
                            <div class="table-responsive">
                                <table class="table table-striped table-hover">
                                    <thead>
                                        <tr>
                                            <th>מטבע</th>
                                            <th>פעולות</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for symbol in watched_symbols %}
                                            <tr>
                                                <td>{{ symbol }}</td>
                                                <td>
                                                    <form action="/remove_symbol/{{ symbol }}" method="post" class="d-inline">
                                                        <button type="submit" class="btn btn-sm btn-outline-danger">הסר</button>
                                                    </form>
                                                </td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        {% else %}
                            <div class="alert alert-info">אין מטבעות במעקב כרגע</div>
                        {% endif %}
                    </div>
                    <div class="card-footer">
                        <a href="/watchlist" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>

            <div class="col-lg-6">
                <div class="card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="card-title mb-0">לוגים אחרונים</h5>
                    </div>
                    <div class="card-body">
                        <div style="max-height: 300px; overflow-y: auto;">
                            {% if logs %}
                                <div class="list-group">
                                    {% for log in logs[:10] %}
                                        <div class="list-group-item list-group-item-action">{{ log }}</div>
                                    {% endfor %}
                                </div>
                            {% else %}
                                <div class="alert alert-info">אין לוגים כרגע</div>
                            {% endif %}
                        </div>
                    </div>
                    <div class="card-footer">
                        <a href="/logs" class="btn btn-outline-primary">הצג הכל</a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- מודל הפעלת בוט -->
    <div class="modal fade" id="startBotModal" tabindex="-1" aria-labelledby="startBotModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="startBotModalLabel">הפעלת בוט</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <form action="/start_bot" method="post">
                    <div class="modal-body">
                        <div class="mb-3">