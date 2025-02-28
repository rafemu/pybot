
def get_templates_part1():
    return {
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
                            <label for="api_key" class="form-label">API Key</label>
                            <input type="text" class="form-control" id="api_key" name="api_key" value="{{ settings.api_key }}" required>
                        </div>
                        <div class="mb-3">
                            <label for="api_secret" class="form-label">API Secret</label>
                            <input type="password" class="form-control" id="api_secret" name="api_secret" value="{{ settings.api_secret }}" required>
                        </div>
                        <div class="mb-3 form-check">
                            <input type="checkbox" class="form-check-input" id="test_mode" name="test_mode" {% if settings.test_mode %}checked{% endif %}>
                            <label class="form-check-label" for="test_mode">מצב בדיקה (ללא מסחר אמיתי)</label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">ביטול</button>
                        <button type="submit" class="btn btn-success">הפעל בוט</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // עדכון נתונים אוטומטי
        function updateData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // עדכון לוגיקה כאן אם נדרש
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        // עדכון כל 5 שניות
        setInterval(updateData, 5000);
    </script>
</body>
</html>
        ''',
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
        '''
    }