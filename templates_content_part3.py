def get_templates_part3():
    return {
        'positions_html_continued': '''
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