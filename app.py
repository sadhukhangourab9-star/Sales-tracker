from flask import Flask, request, jsonify, render_template_string
import sqlite3
import json
from datetime import datetime
import csv
import io

app = Flask(__name__)
DB_PATH = 'sales.db'

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id TEXT PRIMARY KEY,
            dateTime TEXT,
            cardNumber TEXT,
            cardType TEXT,
            machine TEXT,
            vendor TEXT,
            model TEXT,
            amount REAL,
            type TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            number TEXT PRIMARY KEY,
            type TEXT
        )
    ''')
    
    c.execute('SELECT COUNT(*) FROM inventory')
    if c.fetchone()[0] == 0:
        default_cards = [
            ("7340", "SBI"), ("7357", "SBI"), ("7373", "SBI"), ("7365", "SBI"),
            ("2448", "SBI"), ("9207", "SBI"), ("0359", "SBI"), ("8431", "SBI"),
            ("0618", "SBI"), ("1285", "SBI"), ("1277", "SBI"), ("1293", "SBI"),
            ("7524", "SBI"), ("0358", "SBI"), ("0341", "SBI"), ("7261", "SBI"),
            ("7056", "SBI"), ("1914", "SBI"), ("1906", "SBI"), ("9920", "SBI"),
            ("2748", "SBI"), ("6184", "SBI"), ("5994", "SBI"), ("5986", "SBI"),
            ("4544", "SBI"), ("5152", "SBI"), ("5160", "SBI"), ("5178", "SBI"),
            ("7005", "ICICI"), ("7104", "ICICI"), ("4001", "ICICI"), ("4100", "ICICI"),
            ("0000", "ICICI"), ("0109", "ICICI"), ("1006", "ICICI"), ("1105", "ICICI"),
            ("3007", "ICICI"), ("3106", "ICICI"), ("9002", "ICICI"), ("9101", "ICICI"),
            ("70103", "ICICI"), ("70004", "ICICI"), ("60007", "ICICI"), ("7003", "ICICI"),
            ("7102", "ICICI"), ("0003", "ICICI"), ("8001", "ICICI"), ("9003", "ICICI"),
            ("9009", "ICICI"), ("9108", "ICICI"), ("6004", "ICICI"), ("6103", "ICICI"),
            ("7004", "ICICI"), ("0006", "ICICI"), ("8003", "ICICI"), ("8201", "ICICI"),
            ("9000", "ICICI"), ("9109", "ICICI"), ("9208", "ICICI"), ("4007", "ICICI"),
            ("4106", "ICICI"), ("8209", "ICICI"), ("8100", "ICICI"), ("4205", "ICICI"),
            ("6001", "ICICI"), ("7009", "ICICI"), ("7900", "HDFC"), ("9662", "HDFC"),
            ("0033", "HDFC"), ("5025", "HDFC"), ("7719", "HDFC"), ("3599", "HDFC"),
            ("7342", "HDFC"), ("6368", "HDFC"), ("1533", "HDFC"), ("4405", "HDFC"),
            ("0989", "HDFC"), ("5521", "HDFC"), ("8122", "HDFC"), ("6837", "HDFC"),
            ("9255", "KOTAK"), ("9248", "KOTAK"), ("2057", "KOTAK"), ("2874", "KOTAK"),
            ("3375", "KOTAK"), ("4668", "AXIS"), ("8230", "AXIS"), ("5058", "AXIS"),
            ("5790", "AXIS"), ("9873", "AXIS"), ("0861", "AXIS"), ("1227", "AXIS"),
            ("5808", "AXIS"), ("6988", "AXIS"), ("0853", "AXIS"), ("3158", "AXIS"),
            ("4570", "AXIS"), ("8821", "AXIS"), ("4477", "AXIS"), ("3258", "IDFC"),
            ("6853", "IDFC"), ("9112", "IDFC"), ("7775", "IDFC"), ("0027", "IDFC"),
            ("6486", "IDFC"), ("4245", "IDFC"), ("3875", "IDFC"), ("4557", "IDFC"),
            ("1047", "IDFC"), ("2134", "IDFC"), ("7907", "IDFC"), ("5139", "INDUSIND"),
            ("8156", "INDUSIND"), ("2941", "INDUSIND"), ("0081", "INDUSIND"),
            ("1413", "INDUSIND"), ("2897", "INDUSIND"), ("6669", "INDUSIND"),
            ("6289", "INDUSIND"), ("5205", "INDUSIND"), ("8600", "INDUSIND"),
            ("4247", "INDUSIND"), ("6655", "INDUSIND"), ("9031", "INDUSIND"),
            ("4831", "INDUSIND"), ("3197", "INDUSIND"), ("7145", "INDUSIND"),
            ("1324", "INDUSIND"), ("1314", "INDUSIND"), ("9575", "INDUSIND"),
            ("7172", "INDUSIND"), ("8834", "INDUSIND"), ("9436", "RBL"),
            ("1015", "RBL"), ("6809", "RBL"), ("0026", "RBL"), ("3160", "RBL"),
            ("3885", "RBL"), ("9820", "RBL"), ("1083", "RBL"), ("1924", "RBL"),
            ("9794", "RBL"), ("4907", "RBL"), ("3402", "RBL"), ("3477", "RBL"),
            ("0276", "RBL"), ("0344", "RBL"), ("9991", "RBL"), ("3860", "RBL"),
            ("8458", "YES"), ("7676", "YES"), ("2709", "YES"), ("2337", "YES"),
            ("8508", "BOB"), ("6509", "BOB"), ("4805", "BOB"), ("0870", "BOB"),
            ("6118", "BOB"), ("5397", "BOB"), ("2023", "BOB"), ("7613", "BOB"),
            ("6395", "BOB"), ("1401", "BOB"), ("0041", "BOB")
        ]
        c.executemany('INSERT OR IGNORE INTO inventory VALUES (?,?)', default_cards)
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/sales', methods=['GET'])
def get_sales():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM sales ORDER BY dateTime DESC')
    rows = c.fetchall()
    conn.close()
    
    sales = []
    for row in rows:
        sales.append({
            'id': row[0], 'dateTime': row[1], 'cardNumber': row[2],
            'cardType': row[3], 'machine': row[4], 'vendor': row[5],
            'model': row[6], 'amount': row[7], 'type': row[8]
        })
    return jsonify({'success': True, 'data': sales})

@app.route('/api/sales', methods=['POST'])
def add_sale():
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO sales VALUES (?,?,?,?,?,?,?,?,?)', (
        str(data['id']), data['dateTime'], data['cardNumber'],
        data['cardType'], data['machine'], data['vendor'],
        data['model'], data['amount'], data['type']
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/sales/<id>', methods=['PUT'])
def update_sale(id):
    data = request.json
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE sales SET 
        dateTime=?, cardNumber=?, cardType=?, machine=?, 
        vendor=?, model=?, amount=?, type=? WHERE id=?''', (
        data['dateTime'], data['cardNumber'], data['cardType'],
        data['machine'], data['vendor'], data['model'],
        data['amount'], data['type'], id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/sales/<id>', methods=['DELETE'])
def delete_sale(id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM sales WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM inventory ORDER BY type, number')
    rows = c.fetchall()
    conn.close()
    
    inventory = [{'number': row[0], 'type': row[1]} for row in rows]
    return jsonify({'success': True, 'data': inventory})

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    data = request.json
    filters = data.get('filters', {})
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = 'SELECT * FROM sales WHERE 1=1'
    params = []
    
    if filters.get('startDate'):
        query += ' AND dateTime >= ?'
        params.append(filters['startDate'] + 'T00:00:00')
    if filters.get('endDate'):
        query += ' AND dateTime <= ?'
        params.append(filters['endDate'] + 'T23:59:59')
    if filters.get('month'):
        query += ' AND strftime("%Y-%m", dateTime) = ?'
        params.append(filters['month'])
    
    query += ' ORDER BY dateTime DESC'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date Time', 'Card Number', 'Card Type', 'Machine', 'Vendor', 'Model', 'Amount', 'Type'])
    
    for row in rows:
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=sales_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    }

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile Sales Tracker</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1600px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; position: relative; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .tabs { display: flex; background: #f8f9fa; border-bottom: 2px solid #dee2e6; flex-wrap: wrap; }
        .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; transition: all 0.3s; font-weight: 600; color: #666; min-width: 120px; }
        .tab.active { background: white; color: #667eea; border-bottom: 3px solid #667eea; }
        .tab:hover:not(.active) { background: #e9ecef; }
        .content { padding: 30px; display: none; }
        .content.active { display: block; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .form-group { display: flex; flex-direction: column; position: relative; }
        .form-group label { font-weight: 600; margin-bottom: 8px; color: #333; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }
        .form-group input, .form-group select { padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; transition: all 0.3s; }
        .form-group input:focus, .form-group select:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1); }
        .card-status-badge { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); padding: 4px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold; display: none; }
        .card-valid { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .card-used { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .btn { padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 10px; margin-bottom: 10px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .table-container { overflow-x: auto; margin-top: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; background: white; }
        th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; text-align: left; font-weight: 600; text-transform: uppercase; font-size: 0.85em; letter-spacing: 0.5px; }
        td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; }
        tr:hover { background: #f8f9fa; }
        tr.card-group-start { border-top: 2px solid #667eea; }
        tr.transaction-row { background: #fafbfc; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 4px solid #667eea; }
        .stat-card h3 { color: #666; font-size: 0.9em; text-transform: uppercase; margin-bottom: 10px; }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #333; }
        .card-status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }
        .status-used { background: #dc3545; color: white; }
        .status-available { background: #28a745; color: white; }
        .alert { padding: 15px; border-radius: 8px; margin-bottom: 20px; display: none; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; display: block; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; display: block; }
        .filter-box { margin-bottom: 15px; padding: 15px; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #667eea; }
        .filter-row { background: #f8f9fa; }
        .filter-row td { padding: 8px; border-bottom: 2px solid #dee2e6; }
        .column-filter { width: 100%; padding: 6px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.85em; background: white; }
        .filter-label { font-size: 0.75em; color: #666; margin-bottom: 2px; display: block; }
        .search-box { margin-bottom: 20px; display: flex; gap: 10px; flex-wrap: wrap; }
        .search-box input { flex: 1; min-width: 200px; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 16px; }
        .date-filter { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }
        .inventory-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; margin-right: 5px; font-weight: 600; background: #e3f2fd; color: #1976d2; }
        .clear-filters-btn { margin-bottom: 15px; padding: 8px 16px; font-size: 14px; }
        .export-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 2px solid #dee2e6; }
        .export-section h3 { margin-bottom: 15px; color: #333; }
        .export-options { display: flex; gap: 15px; flex-wrap: wrap; align-items: end; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 5% auto; padding: 30px; border-radius: 12px; width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #dee2e6; }
        .modal-header h2 { margin: 0; color: #333; }
        .close { color: #aaa; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: #000; }
        .action-btns { display: flex; gap: 5px; }
        .action-btns .btn { padding: 6px 12px; font-size: 12px; margin: 0; }
        @media (max-width: 768px) { .form-grid { grid-template-columns: 1fr; } .header h1 { font-size: 1.8em; } .export-options { flex-direction: column; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Mobile Sales Tracker</h1>
            <p>Server: <span id="serverStatus" style="color: #d4edda;">Online</span> | <span id="lastSync">Never synced</span></p>
        </div>

        <div class="tabs">
            <div class="tab active" onclick="showTab('entry')">New Sale</div>
            <div class="tab" onclick="showTab('records')">Sales Records</div>
            <div class="tab" onclick="showTab('inventory')">Card Inventory</div>
            <div class="tab" onclick="showTab('reports')">Reports</div>
        </div>

        <!-- Entry Tab -->
        <div id="entry" class="content active">
            <div class="alert" id="alertBox"></div>
            <div style="margin-bottom: 20px;">
                <button class="btn btn-success" onclick="syncData()">🔄 Sync Data</button>
            </div>
            
            <form id="saleForm">
                <input type="hidden" id="editId" value="">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Date & Time</label>
                        <input type="datetime-local" id="dateTime" readonly>
                    </div>
                    <div class="form-group">
                        <label>Card Number *</label>
                        <input type="text" id="cardNumber" placeholder="Enter card number" required oninput="checkCard()">
                        <span id="cardValidationBadge" class="card-status-badge"></span>
                    </div>
                    <div class="form-group">
                        <label>Card Type *</label>
                        <select id="cardType" required>
                            <option value="">Select</option>
                            <option value="SBI">SBI</option>
                            <option value="ICICI">ICICI</option>
                            <option value="HDFC">HDFC</option>
                            <option value="KOTAK">KOTAK</option>
                            <option value="AXIS">AXIS</option>
                            <option value="IDFC">IDFC</option>
                            <option value="INDUSIND">INDUSIND</option>
                            <option value="RBL">RBL</option>
                            <option value="YES">YES</option>
                            <option value="BOB">BOB</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Machine *</label>
                        <select id="machine" required>
                            <option value="">Select</option>
                            <option value="PINELAB">PINELAB</option>
                            <option value="BENOW">BENOW</option>
                            <option value="PAYTM">PAYTM</option>
                            <option value="RAZORPAY">RAZORPAY</option>
                            <option value="INNOVITI">INNOVITI</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Vendor *</label>
                        <select id="vendor" required>
                            <option value="">Select</option>
                            <option value="LIMPTON">LIMPTON</option>
                            <option value="R G CELLULLARS">R G CELLULLARS</option>
                            <option value="VELOCITY">VELOCITY</option>
                            <option value="LETS CONNECT">LETS CONNECT</option>
                            <option value="THE PRIME">THE PRIME</option>
                            <option value="LOGICA">LOGICA</option>
                            <option value="BHAJANLAL">BHAJANLAL</option>
                            <option value="NATIONAL RADIO PRODUCT">NATIONAL RADIO PRODUCT</option>
                            <option value="DISHA">DISHA</option>
                            <option value="D P ELECTRONICS">D P ELECTRONICS</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Model *</label>
                        <select id="model" required>
                            <option value="">Select</option>
                            <option value="NOTHING">NOTHING</option>
                            <option value="VIVO">VIVO</option>
                            <option value="CMF">CMF</option>
                            <option value="MOTOROLA">MOTOROLA</option>
                            <option value="OPPO">OPPO</option>
                            <option value="REDMI">REDMI</option>
                            <option value="APPLE">APPLE</option>
                            <option value="SAMSUNG">SAMSUNG</option>
                            <option value="ONEPLUS">ONEPLUS</option>
                            <option value="REALME">REALME</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Amount (₹) *</label>
                        <input type="number" id="amount" placeholder="Enter amount" required min="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Type *</label>
                        <select id="type" required>
                            <option value="">Select</option>
                            <option value="INSTANT">INSTANT</option>
                            <option value="EMI">EMI</option>
                        </select>
                    </div>
                </div>

                <button type="submit" class="btn btn-primary" id="submitBtn">Submit Sale</button>
                <button type="button" class="btn btn-warning" onclick="clearForm()">Clear Form</button>
                <button type="button" class="btn btn-success" onclick="exportToExcel()">Export to Excel</button>
            </form>
        </div>

        <!-- Records Tab -->
        <div id="records" class="content">
            <div class="export-section">
                <h3>📥 Export/Backup Data</h3>
                <div class="export-options">
                    <div class="form-group" style="flex: 1; min-width: 150px;">
                        <label>Start Date</label>
                        <input type="date" id="exportStartDate">
                    </div>
                    <div class="form-group" style="flex: 1; min-width: 150px;">
                        <label>End Date</label>
                        <input type="date" id="exportEndDate">
                    </div>
                    <div class="form-group" style="flex: 1; min-width: 150px;">
                        <label>Month Filter</label>
                        <input type="month" id="exportMonth">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-success" onclick="exportToCSV()">📄 Export CSV</button>
                        <button class="btn btn-primary" onclick="exportToExcelFiltered()">📊 Export Excel</button>
                    </div>
                </div>
            </div>

            <div class="date-filter">
                <label><strong>Filter by Date:</strong></label>
                <input type="date" id="startDate" onchange="filterRecords()">
                <span>to</span>
                <input type="date" id="endDate" onchange="filterRecords()">
                <div class="form-group" style="margin: 0;">
                    <label style="font-size: 0.8em; margin-bottom: 2px;">Month</label>
                    <input type="month" id="recordMonthFilter" onchange="filterRecordsByMonth()" style="padding: 6px;">
                </div>
                <button class="btn btn-secondary" onclick="clearDateFilter()" style="padding: 8px 15px; font-size: 14px;">Clear</button>
            </div>
            <div class="search-box">
                <input type="text" id="searchRecords" placeholder="Search by card number, vendor, model..." onkeyup="searchRecords()">
            </div>
            <button class="btn btn-success" onclick="loadSales()">🔄 Refresh Data</button>
            
            <div class="table-container">
                <table id="recordsTable">
                    <thead>
                        <tr>
                            <th>Date & Time</th>
                            <th>Card Number</th>
                            <th>Card Type</th>
                            <th>Machine</th>
                            <th>Vendor</th>
                            <th>Model</th>
                            <th>Amount</th>
                            <th>Type</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="recordsBody"></tbody>
                </table>
            </div>
        </div>

        <!-- Inventory Tab -->
        <div id="inventory" class="content">
            <div class="stats-grid" id="cardStats"></div>
            
            <button class="btn btn-secondary clear-filters-btn" onclick="clearInventoryFilters()">Clear All Filters</button>
            
            <div class="filter-box">
                <div style="display: flex; gap: 15px; flex-wrap: wrap; align-items: end; margin-bottom: 15px;">
                    <div class="form-group" style="flex: 1; min-width: 200px; margin: 0;">
                        <label>Filter by Month</label>
                        <input type="month" id="inventoryMonthFilter" onchange="applyInventoryFilters()" style="padding: 8px;">
                    </div>
                    <button class="btn btn-secondary" onclick="clearInventoryMonthFilter()" style="margin-bottom: 0;">Clear Month</button>
                </div>
                
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600;">
                    <input type="checkbox" id="showRemainingForModel" onchange="applyInventoryFilters()" style="width: 18px; height: 18px;">
                    <span>🎯 Show Remaining Cards Only (Not Used for Selected Model)</span>
                </label>
                <small style="display: block; margin-top: 5px; color: #666; margin-left: 28px;">
                    When Model is selected, shows cards available or used for other models (excluding selected model).
                </small>
                <div id="remainingStats" style="display: none; margin-top: 10px; padding: 8px; background: white; border-radius: 4px; color: #155724; border: 1px solid #c3e6cb;"></div>
            </div>

            <div class="search-box">
                <input type="text" id="searchCards" placeholder="Search card number, vendor, model..." onkeyup="searchInventoryTable()">
            </div>

            <div class="table-container">
                <table id="inventoryTable">
                    <thead>
                        <tr>
                            <th>Card Number</th>
                            <th>Card Type</th>
                            <th>Status</th>
                            <th>Date & Time</th>
                            <th>Vendor</th>
                            <th>Model</th>
                            <th>Amount</th>
                        </tr>
                        <tr class="filter-row">
                            <td>
                                <span class="filter-label">Filter:</span>
                                <select class="column-filter" id="filterCardNumber" onchange="applyInventoryFilters()"><option value="">All</option></select>
                            </td>
                            <td>
                                <span class="filter-label">Filter:</span>
                                <select class="column-filter" id="filterCardType" onchange="applyInventoryFilters()"><option value="">All</option></select>
                            </td>
                            <td>
                                <span class="filter-label">Filter:</span>
                                <select class="column-filter" id="filterStatus" onchange="applyInventoryFilters()">
                                    <option value="">All</option>
                                    <option value="Used">Used</option>
                                    <option value="Available">Available</option>
                                </select>
                            </td>
                            <td></td>
                            <td>
                                <span class="filter-label">Filter:</span>
                                <select class="column-filter" id="filterVendor" onchange="applyInventoryFilters()"><option value="">All</option></select>
                            </td>
                            <td>
                                <span class="filter-label">Filter:</span>
                                <select class="column-filter" id="filterModel" onchange="applyInventoryFilters()"><option value="">All</option></select>
                            </td>
                            <td></td>
                        </tr>
                    </thead>
                    <tbody id="inventoryBody"></tbody>
                </table>
            </div>
        </div>

        <!-- Reports Tab -->
        <div id="reports" class="content">
            <div class="stats-grid" id="reportStats"></div>
            <div class="table-container" id="reportTables"></div>
        </div>
    </div>

    <!-- Edit Modal -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>✏️ Edit Sale Record</h2>
                <span class="close" onclick="closeEditModal()">&times;</span>
            </div>
            <form id="editForm">
                <input type="hidden" id="editModalId">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Date & Time</label>
                        <input type="datetime-local" id="editDateTime" required>
                    </div>
                    <div class="form-group">
                        <label>Card Number *</label>
                        <input type="text" id="editCardNumber" required>
                    </div>
                    <div class="form-group">
                        <label>Card Type *</label>
                        <select id="editCardType" required>
                            <option value="">Select</option>
                            <option value="SBI">SBI</option>
                            <option value="ICICI">ICICI</option>
                            <option value="HDFC">HDFC</option>
                            <option value="KOTAK">KOTAK</option>
                            <option value="AXIS">AXIS</option>
                            <option value="IDFC">IDFC</option>
                            <option value="INDUSIND">INDUSIND</option>
                            <option value="RBL">RBL</option>
                            <option value="YES">YES</option>
                            <option value="BOB">BOB</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Machine *</label>
                        <select id="editMachine" required>
                            <option value="">Select</option>
                            <option value="PINELAB">PINELAB</option>
                            <option value="BENOW">BENOW</option>
                            <option value="PAYTM">PAYTM</option>
                            <option value="RAZORPAY">RAZORPAY</option>
                            <option value="INNOVITI">INNOVITI</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Vendor *</label>
                        <select id="editVendor" required>
                            <option value="">Select</option>
                            <option value="LIMPTON">LIMPTON</option>
                            <option value="R G CELLULLARS">R G CELLULLARS</option>
                            <option value="VELOCITY">VELOCITY</option>
                            <option value="LETS CONNECT">LETS CONNECT</option>
                            <option value="THE PRIME">THE PRIME</option>
                            <option value="LOGICA">LOGICA</option>
                            <option value="BHAJANLAL">BHAJANLAL</option>
                            <option value="NATIONAL RADIO PRODUCT">NATIONAL RADIO PRODUCT</option>
                            <option value="DISHA">DISHA</option>
                            <option value="D P ELECTRONICS">D P ELECTRONICS</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Model *</label>
                        <select id="editModel" required>
                            <option value="">Select</option>
                            <option value="NOTHING">NOTHING</option>
                            <option value="VIVO">VIVO</option>
                            <option value="CMF">CMF</option>
                            <option value="MOTOROLA">MOTOROLA</option>
                            <option value="OPPO">OPPO</option>
                            <option value="REDMI">REDMI</option>
                            <option value="APPLE">APPLE</option>
                            <option value="SAMSUNG">SAMSUNG</option>
                            <option value="ONEPLUS">ONEPLUS</option>
                            <option value="REALME">REALME</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Amount (₹) *</label>
                        <input type="number" id="editAmount" required min="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Type *</label>
                        <select id="editType" required>
                            <option value="">Select</option>
                            <option value="INSTANT">INSTANT</option>
                            <option value="EMI">EMI</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">Update Record</button>
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
            </form>
        </div>
    </div>

    <script>
        let salesData = [];
        let inventoryData = [];
        let comparisonData = [];

        document.addEventListener('DOMContentLoaded', function() {
            setCurrentDateTime();
            setInterval(setCurrentDateTime, 60000);
            syncData();
            
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('endDate').value = today;
            
            // Set current month as default for month filters
            const currentMonth = new Date().toISOString().slice(0, 7);
            document.getElementById('exportMonth').value = currentMonth;
        });

        function setCurrentDateTime() {
            const now = new Date();
            document.getElementById('dateTime').value = now.toISOString().slice(0, 16);
        }

        async function syncData() {
            try {
                const [salesRes, invRes] = await Promise.all([
                    fetch('/api/sales'),
                    fetch('/api/inventory')
                ]);
                
                const salesResult = await salesRes.json();
                const invResult = await invRes.json();
                
                salesData = salesResult.data;
                inventoryData = invResult.data;
                
                document.getElementById('lastSync').textContent = 'Last sync: ' + new Date().toLocaleTimeString();
                showAlert('Data synced!', 'success');
                
                if (document.getElementById('records').classList.contains('active')) loadSales();
                if (document.getElementById('inventory').classList.contains('active')) loadInventory();
                if (document.getElementById('reports').classList.contains('active')) loadReports();
                
            } catch (error) {
                showAlert('Sync failed: ' + error.message, 'error');
            }
        }

        function showTab(tabName) {
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            if (tabName === 'records') loadSales();
            if (tabName === 'inventory') loadInventory();
            if (tabName === 'reports') loadReports();
        }

        function checkCard() {
            const num = document.getElementById('cardNumber').value.trim();
            const badge = document.getElementById('cardValidationBadge');
            const card = inventoryData.find(c => c.number === num);
            
            if (card) {
                document.getElementById('cardType').value = card.type;
                const used = salesData.find(s => s.cardNumber === num);
                
                badge.style.display = 'inline-block';
                if (used) {
                    badge.className = 'card-status-badge card-used';
                    badge.textContent = 'USED';
                } else {
                    badge.className = 'card-status-badge card-valid';
                    badge.textContent = 'VALID';
                }
            } else {
                badge.style.display = 'none';
            }
        }

        document.getElementById('saleForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const editId = document.getElementById('editId').value;
            const record = {
                id: editId || Date.now().toString(),
                dateTime: document.getElementById('dateTime').value,
                cardNumber: document.getElementById('cardNumber').value.trim(),
                cardType: document.getElementById('cardType').value,
                machine: document.getElementById('machine').value,
                vendor: document.getElementById('vendor').value,
                model: document.getElementById('model').value,
                amount: parseFloat(document.getElementById('amount').value),
                type: document.getElementById('type').value
            };
            
            try {
                if (editId) {
                    // Update existing
                    await fetch(`/api/sales/${editId}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(record)
                    });
                    const idx = salesData.findIndex(s => s.id === editId);
                    if (idx !== -1) salesData[idx] = record;
                    showAlert('Record updated!', 'success');
                } else {
                    // Add new
                    await fetch('/api/sales', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(record)
                    });
                    salesData.unshift(record);
                    showAlert('Sale saved!', 'success');
                }
                clearForm();
            } catch (error) {
                showAlert('Save failed: ' + error.message, 'error');
            }
        });

        function clearForm() {
            document.getElementById('saleForm').reset();
            document.getElementById('editId').value = '';
            document.getElementById('submitBtn').textContent = 'Submit Sale';
            setCurrentDateTime();
            document.getElementById('cardValidationBadge').style.display = 'none';
        }

        function showAlert(message, type) {
            const alert = document.getElementById('alertBox');
            alert.textContent = message;
            alert.className = 'alert alert-' + type;
            setTimeout(() => alert.className = 'alert', 5000);
        }

        function loadSales() {
            const tbody = document.getElementById('recordsBody');
            tbody.innerHTML = '';
            
            salesData.forEach(record => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${new Date(record.dateTime).toLocaleString()}</td>
                    <td>${record.cardNumber}</td>
                    <td>${record.cardType}</td>
                    <td>${record.machine}</td>
                    <td>${record.vendor}</td>
                    <td>${record.model}</td>
                    <td>₹${record.amount.toLocaleString()}</td>
                    <td>${record.type}</td>
                    <td>
                        <div class="action-btns">
                            <button class="btn btn-info" onclick="editRecord('${record.id}')">Edit</button>
                            <button class="btn btn-danger" onclick="deleteRecord('${record.id}')">Delete</button>
                        </div>
                    </td>
                `;
            });
        }

        function editRecord(id) {
            const record = salesData.find(s => s.id === id);
            if (!record) return;
            
            document.getElementById('editModalId').value = record.id;
            document.getElementById('editDateTime').value = record.dateTime.slice(0, 16);
            document.getElementById('editCardNumber').value = record.cardNumber;
            document.getElementById('editCardType').value = record.cardType;
            document.getElementById('editMachine').value = record.machine;
            document.getElementById('editVendor').value = record.vendor;
            document.getElementById('editModel').value = record.model;
            document.getElementById('editAmount').value = record.amount;
            document.getElementById('editType').value = record.type;
            
            document.getElementById('editModal').style.display = 'block';
        }

        function closeEditModal() {
            document.getElementById('editModal').style.display = 'none';
        }

        document.getElementById('editForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const id = document.getElementById('editModalId').value;
            const record = {
                dateTime: document.getElementById('editDateTime').value,
                cardNumber: document.getElementById('editCardNumber').value.trim(),
                cardType: document.getElementById('editCardType').value,
                machine: document.getElementById('editMachine').value,
                vendor: document.getElementById('editVendor').value,
                model: document.getElementById('editModel').value,
                amount: parseFloat(document.getElementById('editAmount').value),
                type: document.getElementById('editType').value
            };
            
            try {
                await fetch(`/api/sales/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(record)
                });
                
                const idx = salesData.findIndex(s => s.id === id);
                if (idx !== -1) {
                    salesData[idx] = { ...record, id };
                }
                
                closeEditModal();
                loadSales();
                showAlert('Record updated successfully!', 'success');
            } catch (error) {
                showAlert('Update failed: ' + error.message, 'error');
            }
        });

        async function deleteRecord(id) {
            if (!confirm('Delete this record?')) return;
            try {
                await fetch(`/api/sales/${id}`, {method: 'DELETE'});
                salesData = salesData.filter(r => r.id !== id);
                loadSales();
                showAlert('Deleted', 'success');
            } catch (error) {
                showAlert('Delete failed', 'error');
            }
        }

        function filterRecords() {
            const start = document.getElementById('startDate').value;
            const end = document.getElementById('endDate').value;
            if (!start || !end) return;
            
            const rows = document.getElementById('recordsBody').getElementsByTagName('tr');
            const startDate = new Date(start);
            const endDate = new Date(end);
            endDate.setHours(23, 59, 59);
            
            Array.from(rows).forEach(row => {
                const dateText = row.cells[0].textContent;
                const rowDate = new Date(dateText);
                row.style.display = (rowDate >= startDate && rowDate <= endDate) ? '' : 'none';
            });
        }

        function filterRecordsByMonth() {
            const month = document.getElementById('recordMonthFilter').value;
            if (!month) return;
            
            const rows = document.getElementById('recordsBody').getElementsByTagName('tr');
            
            Array.from(rows).forEach(row => {
                const dateText = row.cells[0].textContent;
                const rowDate = new Date(dateText);
                const rowMonth = rowDate.toISOString().slice(0, 7);
                row.style.display = (rowMonth === month) ? '' : 'none';
            });
        }

        function clearDateFilter() {
            document.getElementById('startDate').value = '';
            document.getElementById('endDate').value = '';
            document.getElementById('recordMonthFilter').value = '';
            loadSales();
        }

        function searchRecords() {
            const term = document.getElementById('searchRecords').value.toLowerCase();
            const rows = document.getElementById('recordsBody').getElementsByTagName('tr');
            Array.from(rows).forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
            });
        }

        async function exportToCSV() {
            const filters = {
                startDate: document.getElementById('exportStartDate').value,
                endDate: document.getElementById('exportEndDate').value,
                month: document.getElementById('exportMonth').value
            };
            
            try {
                const response = await fetch('/api/export/csv', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({filters})
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `sales_export_${new Date().toISOString().slice(0,10)}.csv`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    showAlert('CSV exported successfully!', 'success');
                }
            } catch (error) {
                showAlert('Export failed: ' + error.message, 'error');
            }
        }

        function exportToExcelFiltered() {
            const startDate = document.getElementById('exportStartDate').value;
            const endDate = document.getElementById('exportEndDate').value;
            const month = document.getElementById('exportMonth').value;
            
            let filteredData = [...salesData];
            
            if (startDate) {
                filteredData = filteredData.filter(s => s.dateTime >= startDate + 'T00:00:00');
            }
            if (endDate) {
                filteredData = filteredData.filter(s => s.dateTime <= endDate + 'T23:59:59');
            }
            if (month) {
                filteredData = filteredData.filter(s => s.dateTime.slice(0, 7) === month);
            }
            
            const ws = XLSX.utils.json_to_sheet(filteredData);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Sales');
            XLSX.writeFile(wb, `sales_export_${new Date().toISOString().split('T')[0]}.xlsx`);
            showAlert('Excel exported successfully!', 'success');
        }

        function loadInventory() {
            comparisonData = [];
            const usedCards = new Set(salesData.map(s => s.cardNumber));
            
            inventoryData.forEach(card => {
                const cardSales = salesData.filter(s => s.cardNumber === card.number);
                
                if (cardSales.length === 0) {
                    comparisonData.push({
                        cardNumber: card.number,
                        cardType: card.type,
                        status: 'Available',
                        dateTime: '-',
                        vendor: '-',
                        model: '-',
                        amount: '-'
                    });
                } else {
                    cardSales.forEach(sale => {
                        comparisonData.push({
                            cardNumber: card.number,
                            cardType: card.type,
                            status: 'Used',
                            dateTime: sale.dateTime,
                            vendor: sale.vendor,
                            model: sale.model,
                            amount: sale.amount
                        });
                    });
                }
            });
            
            comparisonData.sort((a, b) => {
                if (a.cardNumber !== b.cardNumber) return a.cardNumber.localeCompare(b.cardNumber);
                if (a.dateTime === '-') return 1;
                if (b.dateTime === '-') return -1;
                return new Date(a.dateTime) - new Date(b.dateTime);
            });
            
            populateFilters();
            applyInventoryFilters();
            updateInventoryStats();
        }

        function populateFilters() {
            const cardNumbers = [...new Set(comparisonData.map(c => c.cardNumber))].sort();
            const cardTypes = [...new Set(comparisonData.map(c => c.cardType))].sort();
            const vendors = [...new Set(comparisonData.map(c => c.vendor).filter(v => v !== '-'))].sort();
            const models = [...new Set(comparisonData.map(c => c.model).filter(m => m !== '-'))].sort();
            
            populateSelect('filterCardNumber', cardNumbers);
            populateSelect('filterCardType', cardTypes);
            populateSelect('filterVendor', vendors);
            populateSelect('filterModel', models);
        }

        function populateSelect(id, values) {
            const select = document.getElementById(id);
            while (select.options.length > 1) select.remove(1);
            values.forEach(val => {
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = val;
                select.appendChild(opt);
            });
        }

        function applyInventoryFilters() {
            const filters = {
                cardNumber: document.getElementById('filterCardNumber').value,
                cardType: document.getElementById('filterCardType').value,
                status: document.getElementById('filterStatus').value,
                vendor: document.getElementById('filterVendor').value,
                model: document.getElementById('filterModel').value
            };
            
            const monthFilter = document.getElementById('inventoryMonthFilter').value;
            const showRemaining = document.getElementById('showRemainingForModel').checked;
            const remainingStats = document.getElementById('remainingStats');
            let filtered = [...comparisonData];
            
            // Apply month filter
            if (monthFilter) {
                filtered = filtered.filter(item => {
                    if (item.dateTime === '-') return false;
                    return item.dateTime.slice(0, 7) === monthFilter;
                });
            }
            
            if (showRemaining && filters.model) {
                let usedForModel = comparisonData.filter(c => c.model === filters.model && c.status === 'Used');
                if (filters.cardType) usedForModel = usedForModel.filter(c => c.cardType === filters.cardType);
                const cardsUsedForModel = new Set(usedForModel.map(c => c.cardNumber));
                let eligible = filters.cardType ? comparisonData.filter(c => c.cardType === filters.cardType) : [...comparisonData];
                filtered = eligible.filter(item => !cardsUsedForModel.has(item.cardNumber));
                
                if (filters.cardNumber) filtered = filtered.filter(i => i.cardNumber === filters.cardNumber);
                if (filters.status) filtered = filtered.filter(i => i.status === filters.status);
                if (filters.vendor) filtered = filtered.filter(i => i.vendor === filters.vendor);
                
                const totalEligible = new Set(eligible.map(c => c.cardNumber)).size;
                const remaining = totalEligible - cardsUsedForModel.size;
                const pct = totalEligible > 0 ? Math.round((remaining / totalEligible) * 100) : 0;
                remainingStats.style.display = 'block';
                remainingStats.innerHTML = `<strong>📊 Remaining:</strong> ${remaining} of ${totalEligible} cards available (${pct}%)`;
            } else {
                remainingStats.style.display = 'none';
                if (filters.cardNumber) filtered = filtered.filter(i => i.cardNumber === filters.cardNumber);
                if (filters.cardType) filtered = filtered.filter(i => i.cardType === filters.cardType);
                if (filters.status) filtered = filtered.filter(i => i.status === filters.status);
                if (filters.vendor) filtered = filtered.filter(i => i.vendor === filters.vendor);
                if (filters.model) filtered = filtered.filter(i => i.model === filters.model);
            }
            
            renderInventoryTable(filtered);
        }

        function renderInventoryTable(data) {
            const tbody = document.getElementById('inventoryBody');
            tbody.innerHTML = '';
            let lastCard = '';
            
            data.forEach(item => {
                const row = tbody.insertRow();
                if (item.cardNumber === lastCard) row.classList.add('transaction-row');
                else row.classList.add('card-group-start');
                lastCard = item.cardNumber;
                
                const statusClass = item.status === 'Used' ? 'status-used' : 'status-available';
                row.innerHTML = `
                    <td>${item.cardNumber}</td>
                    <td><span class="inventory-tag">${item.cardType}</span></td>
                    <td><span class="card-status ${statusClass}">${item.status}</span></td>
                    <td>${item.dateTime !== '-' ? new Date(item.dateTime).toLocaleString() : '-'}</td>
                    <td>${item.vendor}</td>
                    <td>${item.model}</td>
                    <td>${item.amount !== '-' ? '₹' + item.amount.toLocaleString() : '-'}</td>
                `;
            });
        }

        function clearInventoryFilters() {
            ['filterCardNumber', 'filterCardType', 'filterStatus', 'filterVendor', 'filterModel'].forEach(id => {
                document.getElementById(id).value = '';
            });
            document.getElementById('showRemainingForModel').checked = false;
            document.getElementById('remainingStats').style.display = 'none';
            document.getElementById('inventoryMonthFilter').value = '';
            applyInventoryFilters();
        }

        function clearInventoryMonthFilter() {
            document.getElementById('inventoryMonthFilter').value = '';
            applyInventoryFilters();
        }

        function searchInventoryTable() {
            const term = document.getElementById('searchCards').value.toLowerCase();
            const rows = document.getElementById('inventoryBody').getElementsByTagName('tr');
            Array.from(rows).forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
            });
        }

        function updateInventoryStats() {
            const usedCards = new Set(salesData.map(s => s.cardNumber));
            const total = inventoryData.length;
            const used = usedCards.size;
            
            document.getElementById('cardStats').innerHTML = `
                <div class="stat-card"><h3>Total Cards</h3><div class="stat-number">${total}</div></div>
                <div class="stat-card"><h3>Used</h3><div class="stat-number">${used}</div></div>
                <div class="stat-card"><h3>Available</h3><div class="stat-number">${total - used}</div></div>
                <div class="stat-card"><h3>Transactions</h3><div class="stat-number">${salesData.length}</div></div>
            `;
        }

        function loadReports() {
            const totalAmount = salesData.reduce((sum, r) => sum + r.amount, 0);
            
            const byType = {};
            const byVendor = {};
            const byModel = {};
            
            salesData.forEach(r => {
                byType[r.cardType] = (byType[r.cardType] || 0) + r.amount;
                byVendor[r.vendor] = (byVendor[r.vendor] || 0) + r.amount;
                byModel[r.model] = (byModel[r.model] || 0) + r.amount;
            });
            
            document.getElementById('reportStats').innerHTML = `
                <div class="stat-card"><h3>Total Sales</h3><div class="stat-number">₹${totalAmount.toLocaleString()}</div></div>
                <div class="stat-card"><h3>Transactions</h3><div class="stat-number">${salesData.length}</div></div>
            `;
            
            let html = '<h3 style="margin-top: 30px;">By Card Type</h3><table><tr><th>Type</th><th>Amount</th></tr>';
            Object.entries(byType).sort((a,b) => b[1]-a[1]).forEach(([type, amt]) => {
                html += `<tr><td>${type}</td><td>₹${amt.toLocaleString()}</td></tr>`;
            });
            html += '</table>';
            
            html += '<h3 style="margin-top: 30px;">By Vendor</h3><table><tr><th>Vendor</th><th>Amount</th></tr>';
            Object.entries(byVendor).sort((a,b) => b[1]-a[1]).forEach(([v, amt]) => {
                html += `<tr><td>${v}</td><td>₹${amt.toLocaleString()}</td></tr>`;
            });
            html += '</table>';
            
            document.getElementById('reportTables').innerHTML = html;
        }

        function exportToExcel() {
            const ws = XLSX.utils.json_to_sheet(salesData);
            const wb = XLSX.utils.book_new();
            XLSX.utils.book_append_sheet(wb, ws, 'Sales');
            XLSX.writeFile(wb, `sales_${new Date().toISOString().split('T')[0]}.xlsx`);
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('editModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
