from flask import Flask, request, jsonify, render_template_string
import sqlite3
import json
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)
DB_PATH = 'sales.db'
MASTER_DATA_PATH = 'master_data.json'

# Card types list
CARD_TYPES = ['SBI', 'ICICI', 'HDFC', 'KOTAK', 'AXIS', 'IDFC', 'INDUSIND', 'RBL', 'YES', 'BOB', 'FEDERAL']

# Load Master Data
def load_master_data():
    if os.path.exists(MASTER_DATA_PATH):
        with open(MASTER_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "cards": [],
        "machines": [],
        "vendors": [],
        "models": []
    }

# Save Master Data
def save_master_data(data):
    with open(MASTER_DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

master_data = load_master_data()

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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            type TEXT
        )
    ''')
    
    # Load cards from master data only if inventory is empty
    c.execute('SELECT COUNT(*) FROM inventory')
    if c.fetchone()[0] == 0 and master_data.get('cards'):
        default_cards = [(card['number'], card['type']) for card in master_data['cards']]
        c.executemany('INSERT INTO inventory (number, type) VALUES (?,?)', default_cards)
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                machines=master_data.get('machines', []),
                                vendors=master_data.get('vendors', []),
                                models=master_data.get('models', []))

@app.route('/master-data-editor')
def master_data_editor():
    return render_template_string(MASTER_EDITOR_TEMPLATE, card_types=CARD_TYPES)

@app.route('/api/master-data', methods=['GET'])
def get_master_data():
    return jsonify({'success': True, 'data': master_data})

@app.route('/api/master-data', methods=['POST'])
def update_master_data():
    global master_data
    data = request.json
    
    # Validate data structure
    if not all(key in data for key in ['cards', 'machines', 'vendors', 'models']):
        return jsonify({'success': False, 'error': 'Invalid data structure'}), 400
    
    # Save to file
    save_master_data(data)
    master_data = data
    
    # Update inventory - clear and reload all cards
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Clear existing inventory
    c.execute('DELETE FROM inventory')
    
    # Insert all cards from master data (allows complete duplicates)
    if data['cards']:
        all_cards = [(card['number'], card['type']) for card in data['cards']]
        c.executemany('INSERT INTO inventory (number, type) VALUES (?,?)', all_cards)
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Master data updated successfully'})

@app.route('/api/validate-card/<number>', methods=['GET'])
def validate_card(number):
    # Get all cards with this number from inventory
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT DISTINCT type FROM inventory WHERE number = ?', (number,))
    types = [row[0] for row in c.fetchall()]
    conn.close()
    
    return jsonify({
        'success': True,
        'exists': len(types) > 0,
        'types': types
    })

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
    
    # Validate card exists in master data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM inventory WHERE number = ? AND type = ?', 
              (data['cardNumber'], data['cardType']))
    count = c.fetchone()[0]
    conn.close()
    
    if count == 0:
        return jsonify({'success': False, 'error': 'Card not found in master data'}), 400
    
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
    
    # Validate card exists in master data
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM inventory WHERE number = ? AND type = ?', 
              (data['cardNumber'], data['cardType']))
    count = c.fetchone()[0]
    conn.close()
    
    if count == 0:
        return jsonify({'success': False, 'error': 'Card not found in master data'}), 400
    
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
    c.execute('SELECT number, type FROM inventory ORDER BY type, number')
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

MASTER_EDITOR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Data Editor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            min-height: 100vh; 
            padding: 20px; 
        }
        .container { 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 20px; 
            box-shadow: 0 20px 60px rgba(0,0,0,0.3); 
            overflow: hidden; 
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            text-align: center; 
            position: relative; 
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .back-btn { 
            position: absolute; 
            left: 20px; 
            top: 50%; 
            transform: translateY(-50%); 
            background: rgba(255,255,255,0.2); 
            color: white; 
            padding: 10px 20px; 
            border-radius: 8px; 
            text-decoration: none; 
            font-weight: 600;
            transition: all 0.3s;
        }
        .back-btn:hover { background: rgba(255,255,255,0.3); }
        .content { padding: 30px; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
            gap: 30px; 
        }
        .section { 
            background: #f8f9fa; 
            border-radius: 12px; 
            padding: 25px; 
            border: 2px solid #e9ecef;
        }
        .section h2 { 
            color: #333; 
            margin-bottom: 20px; 
            display: flex; 
            align-items: center; 
            gap: 10px;
            font-size: 1.3em;
        }
        .section-icon { font-size: 1.5em; }
        .form-group { margin-bottom: 15px; }
        .form-group label { 
            display: block; 
            font-weight: 600; 
            margin-bottom: 5px; 
            color: #555; 
            font-size: 0.9em;
        }
        .form-group input, .form-group select { 
            width: 100%; 
            padding: 10px; 
            border: 2px solid #e0e0e0; 
            border-radius: 6px; 
            font-size: 14px;
        }
        .form-group input:focus, .form-group select:focus { 
            outline: none; 
            border-color: #667eea; 
        }
        .btn { 
            padding: 10px 20px; 
            border: none; 
            border-radius: 6px; 
            font-size: 14px; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s; 
            margin-right: 5px;
        }
        .btn-primary { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
        .item-list { 
            max-height: 300px; 
            overflow-y: auto; 
            border: 1px solid #dee2e6; 
            border-radius: 6px; 
            background: white;
            margin-top: 10px;
        }
        .item { 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            padding: 10px 15px; 
            border-bottom: 1px solid #f0f0f0;
        }
        .item:last-child { border-bottom: none; }
        .item:hover { background: #f8f9fa; }
        .item-info { font-weight: 500; color: #333; }
        .item-sub { font-size: 0.85em; color: #666; }
        .item-actions { display: flex; gap: 5px; }
        .btn-small { padding: 5px 10px; font-size: 12px; }
        .add-form { 
            display: flex; 
            gap: 10px; 
            margin-bottom: 15px; 
            flex-wrap: wrap;
        }
        .add-form input { flex: 1; min-width: 120px; }
        .save-all-btn { 
            position: fixed; 
            bottom: 30px; 
            right: 30px; 
            padding: 15px 30px; 
            font-size: 16px; 
            border-radius: 50px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            z-index: 1000;
        }
        .alert { 
            padding: 15px; 
            border-radius: 8px; 
            margin-bottom: 20px; 
            display: none; 
        }
        .alert-success { 
            background: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
            display: block; 
        }
        .alert-error { 
            background: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
            display: block; 
        }
        .stats { 
            display: flex; 
            gap: 20px; 
            margin-bottom: 20px; 
            flex-wrap: wrap;
        }
        .stat-item { 
            background: white; 
            padding: 15px 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value { 
            font-size: 1.5em; 
            font-weight: bold; 
            color: #667eea; 
        }
        .stat-label { 
            font-size: 0.85em; 
            color: #666; 
            text-transform: uppercase;
        }
        .info-message { 
            background: #d1ecf1; 
            color: #0c5460; 
            padding: 8px 12px; 
            border-radius: 4px; 
            font-size: 0.85em; 
            margin-bottom: 10px;
            border: 1px solid #bee5eb;
        }
        @media (max-width: 768px) { 
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 1.5em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <a href="/" class="back-btn">← Back to Tracker</a>
            <h1>⚙️ Master Data Editor</h1>
            <p>Manage Cards, Machines, Vendors, and Models</p>
        </div>

        <div class="content">
            <div class="alert" id="alertBox"></div>
            
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value" id="statCards">0</div>
                    <div class="stat-label">Cards</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statMachines">0</div>
                    <div class="stat-label">Machines</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statVendors">0</div>
                    <div class="stat-label">Vendors</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value" id="statModels">0</div>
                    <div class="stat-label">Models</div>
                </div>
            </div>

            <div class="grid">
                <!-- Cards Section -->
                <div class="section">
                    <h2><span class="section-icon">💳</span> Cards</h2>
                    <div class="info-message">
                        ℹ️ Duplicate card numbers are allowed (same number with same type)
                    </div>
                    <div class="add-form">
                        <input type="text" id="newCardNumber" placeholder="Card Number">
                        <select id="newCardType">
                            <option value="">Select Type</option>
                            {% for type in card_types %}
                            <option value="{{ type }}">{{ type }}</option>
                            {% endfor %}
                        </select>
                        <button class="btn btn-success" onclick="addCard()">Add</button>
                    </div>
                    <div class="item-list" id="cardsList"></div>
                </div>

                <!-- Machines Section -->
                <div class="section">
                    <h2><span class="section-icon">⚙️</span> Machines</h2>
                    <div class="add-form">
                        <input type="text" id="newMachine" placeholder="Machine Name">
                        <button class="btn btn-success" onclick="addMachine()">Add</button>
                    </div>
                    <div class="item-list" id="machinesList"></div>
                </div>

                <!-- Vendors Section -->
                <div class="section">
                    <h2><span class="section-icon">🏪</span> Vendors</h2>
                    <div class="add-form">
                        <input type="text" id="newVendor" placeholder="Vendor Name">
                        <button class="btn btn-success" onclick="addVendor()">Add</button>
                    </div>
                    <div class="item-list" id="vendorsList"></div>
                </div>

                <!-- Models Section -->
                <div class="section">
                    <h2><span class="section-icon">📱</span> Models</h2>
                    <div class="add-form">
                        <input type="text" id="newModel" placeholder="Model Name">
                        <button class="btn btn-success" onclick="addModel()">Add</button>
                    </div>
                    <div class="item-list" id="modelsList"></div>
                </div>
            </div>
        </div>
    </div>

    <button class="btn btn-primary save-all-btn" onclick="saveAllData()">💾 Save All Changes</button>

    <script>
        let masterData = {
            cards: [],
            machines: [],
            vendors: [],
            models: []
        };

        document.addEventListener('DOMContentLoaded', function() {
            loadMasterData();
        });

        async function loadMasterData() {
            try {
                const response = await fetch('/api/master-data');
                const result = await response.json();
                masterData = result.data;
                renderAll();
                updateStats();
            } catch (error) {
                showAlert('Failed to load master data: ' + error.message, 'error');
            }
        }

        function renderAll() {
            renderCards();
            renderMachines();
            renderVendors();
            renderModels();
        }

        function updateStats() {
            document.getElementById('statCards').textContent = masterData.cards.length;
            document.getElementById('statMachines').textContent = masterData.machines.length;
            document.getElementById('statVendors').textContent = masterData.vendors.length;
            document.getElementById('statModels').textContent = masterData.models.length;
        }

        function renderCards() {
            const container = document.getElementById('cardsList');
            container.innerHTML = '';
            
            masterData.cards.forEach((card, index) => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div>
                        <div class="item-info">${card.number}</div>
                        <div class="item-sub">${card.type}</div>
                    </div>
                    <div class="item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteCard(${index})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function renderMachines() {
            const container = document.getElementById('machinesList');
            container.innerHTML = '';
            
            masterData.machines.forEach((machine, index) => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div class="item-info">${machine}</div>
                    <div class="item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteMachine(${index})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function renderVendors() {
            const container = document.getElementById('vendorsList');
            container.innerHTML = '';
            
            masterData.vendors.forEach((vendor, index) => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div class="item-info">${vendor}</div>
                    <div class="item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteVendor(${index})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function renderModels() {
            const container = document.getElementById('modelsList');
            container.innerHTML = '';
            
            masterData.models.forEach((model, index) => {
                const div = document.createElement('div');
                div.className = 'item';
                div.innerHTML = `
                    <div class="item-info">${model}</div>
                    <div class="item-actions">
                        <button class="btn btn-danger btn-small" onclick="deleteModel(${index})">Delete</button>
                    </div>
                `;
                container.appendChild(div);
            });
        }

        function addCard() {
            const number = document.getElementById('newCardNumber').value.trim();
            const type = document.getElementById('newCardType').value;
            
            if (!number || !type) {
                showAlert('Please enter both card number and type', 'error');
                return;
            }
            
            // No duplicate check - allow same number with same type
            masterData.cards.push({ number, type });
            masterData.cards.sort((a, b) => {
                if (a.number !== b.number) return a.number.localeCompare(b.number);
                return a.type.localeCompare(b.type);
            });
            
            document.getElementById('newCardNumber').value = '';
            document.getElementById('newCardType').value = '';
            
            renderCards();
            updateStats();
            showAlert('Card added! Click "Save All Changes" to persist.', 'success');
        }

        function addMachine() {
            const name = document.getElementById('newMachine').value.trim();
            if (!name) return;
            
            if (masterData.machines.includes(name)) {
                showAlert('Machine already exists', 'error');
                return;
            }
            
            masterData.machines.push(name);
            masterData.machines.sort();
            
            document.getElementById('newMachine').value = '';
            renderMachines();
            updateStats();
            showAlert('Machine added! Click "Save All Changes" to persist.', 'success');
        }

        function addVendor() {
            const name = document.getElementById('newVendor').value.trim();
            if (!name) return;
            
            if (masterData.vendors.includes(name)) {
                showAlert('Vendor already exists', 'error');
                return;
            }
            
            masterData.vendors.push(name);
            masterData.vendors.sort();
            
            document.getElementById('newVendor').value = '';
            renderVendors();
            updateStats();
            showAlert('Vendor added! Click "Save All Changes" to persist.', 'success');
        }

        function addModel() {
            const name = document.getElementById('newModel').value.trim();
            if (!name) return;
            
            if (masterData.models.includes(name)) {
                showAlert('Model already exists', 'error');
                return;
            }
            
            masterData.models.push(name);
            masterData.models.sort();
            
            document.getElementById('newModel').value = '';
            renderModels();
            updateStats();
            showAlert('Model added! Click "Save All Changes" to persist.', 'success');
        }

        function deleteCard(index) {
            if (!confirm('Delete this card?')) return;
            masterData.cards.splice(index, 1);
            renderCards();
            updateStats();
            showAlert('Card deleted! Click "Save All Changes" to persist.', 'success');
        }

        function deleteMachine(index) {
            if (!confirm('Delete this machine?')) return;
            masterData.machines.splice(index, 1);
            renderMachines();
            updateStats();
            showAlert('Machine deleted! Click "Save All Changes" to persist.', 'success');
        }

        function deleteVendor(index) {
            if (!confirm('Delete this vendor?')) return;
            masterData.vendors.splice(index, 1);
            renderVendors();
            updateStats();
            showAlert('Vendor deleted! Click "Save All Changes" to persist.', 'success');
        }

        function deleteModel(index) {
            if (!confirm('Delete this model?')) return;
            masterData.models.splice(index, 1);
            renderModels();
            updateStats();
            showAlert('Model deleted! Click "Save All Changes" to persist.', 'success');
        }

        async function saveAllData() {
            try {
                const response = await fetch('/api/master-data', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(masterData)
                });
                
                const result = await response.json();
                if (result.success) {
                    showAlert('All changes saved successfully! Redirecting...', 'success');
                    setTimeout(() => window.location.href = '/', 1500);
                } else {
                    showAlert('Error saving data: ' + result.error, 'error');
                }
            } catch (error) {
                showAlert('Save failed: ' + error.message, 'error');
            }
        }

        function showAlert(message, type) {
            const alert = document.getElementById('alertBox');
            alert.textContent = message;
            alert.className = 'alert alert-' + type;
            setTimeout(() => alert.className = 'alert', 5000);
        }
    </script>
</body>
</html>
'''

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
        .master-data-btn { 
            position: absolute; 
            right: 20px; 
            top: 50%; 
            transform: translateY(-50%); 
            background: rgba(255,255,255,0.9); 
            color: #667eea; 
            padding: 10px 20px; 
            border-radius: 8px; 
            text-decoration: none; 
            font-weight: 600;
            transition: all 0.3s;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .master-data-btn:hover { 
            background: white; 
            transform: translateY(-50%) scale(1.05); 
        }
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
        .card-invalid { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .card-used { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .btn { padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; text-transform: uppercase; letter-spacing: 0.5px; margin-right: 10px; margin-bottom: 10px; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-warning { background: #ffc107; color: #000; }
        .btn-secondary { background: #6c757d; color: white; }
        .btn-info { background: #17a2b8; color: white; }
        .btn:disabled { background: #ccc; cursor: not-allowed; }
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
        .validation-error { color: #dc3545; font-size: 0.85em; margin-top: 5px; display: none; }
        @media (max-width: 768px) { 
            .form-grid { grid-template-columns: 1fr; } 
            .header h1 { font-size: 1.8em; } 
            .master-data-btn { position: static; transform: none; margin-top: 15px; display: inline-block; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 Mobile Sales Tracker</h1>
            <p>Server: <span id="serverStatus" style="color: #d4edda;">Online</span> | <span id="lastSync">Never synced</span></p>
            <a href="/master-data-editor" class="master-data-btn">⚙️ Master Data</a>
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
                        <div id="cardError" class="validation-error">Card not found in master data</div>
                    </div>
                    <div class="form-group">
                        <label>Card Type *</label>
                        <select id="cardType" required onchange="validateCardType()">
                            <option value="">Select</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Machine *</label>
                        <select id="machine" required>
                            <option value="">Select</option>
                            {% for machine in machines %}
                            <option value="{{ machine }}">{{ machine }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Vendor *</label>
                        <select id="vendor" required>
                            <option value="">Select</option>
                            {% for vendor in vendors %}
                            <option value="{{ vendor }}">{{ vendor }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Model *</label>
                        <select id="model" required>
                            <option value="">Select</option>
                            {% for model in models %}
                            <option value="{{ model }}">{{ model }}</option>
                            {% endfor %}
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

                <button type="submit" class="btn btn-primary" id="submitBtn" disabled>Submit Sale</button>
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
                        <input type="text" id="editCardNumber" required oninput="checkEditCard()">
                        <span id="editCardValidationBadge" class="card-status-badge"></span>
                    </div>
                    <div class="form-group">
                        <label>Card Type *</label>
                        <select id="editCardType" required>
                            <option value="">Select</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Machine *</label>
                        <select id="editMachine" required>
                            <option value="">Select</option>
                            {% for machine in machines %}
                            <option value="{{ machine }}">{{ machine }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Vendor *</label>
                        <select id="editVendor" required>
                            <option value="">Select</option>
                            {% for vendor in vendors %}
                            <option value="{{ vendor }}">{{ vendor }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Model *</label>
                        <select id="editModel" required>
                            <option value="">Select</option>
                            {% for model in models %}
                            <option value="{{ model }}">{{ model }}</option>
                            {% endfor %}
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
                <button type="submit" class="btn btn-primary" id="editSubmitBtn">Update Record</button>
                <button type="button" class="btn btn-secondary" onclick="closeEditModal()">Cancel</button>
            </form>
        </div>
    </div>

    <script>
        let salesData = [];
        let inventoryData = [];
        let comparisonData = [];
        let masterData = {};
        let currentCardTypes = [];

        document.addEventListener('DOMContentLoaded', function() {
            setCurrentDateTime();
            setInterval(setCurrentDateTime, 60000);
            loadMasterData();
            syncData();
            
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('endDate').value = today;
            
            const currentMonth = new Date().toISOString().slice(0, 7);
            document.getElementById('exportMonth').value = currentMonth;
        });

        async function loadMasterData() {
            try {
                const response = await fetch('/api/master-data');
                const result = await response.json();
                masterData = result.data;
                populateCardTypeDropdown();
            } catch (error) {
                console.error('Failed to load master data:', error);
            }
        }

        function populateCardTypeDropdown() {
            const cardTypeSelect = document.getElementById('cardType');
            const editCardTypeSelect = document.getElementById('editCardType');
            
            // Get unique card types from master data
            const cardTypes = [...new Set(masterData.cards.map(c => c.type))].sort();
            
            const options = cardTypes.map(type => `<option value="${type}">${type}</option>`).join('');
            
            cardTypeSelect.innerHTML = '<option value="">Select</option>' + options;
            editCardTypeSelect.innerHTML = '<option value="">Select</option>' + options;
        }

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

        async function checkCard() {
            const num = document.getElementById('cardNumber').value.trim();
            const badge = document.getElementById('cardValidationBadge');
            const cardError = document.getElementById('cardError');
            const cardTypeSelect = document.getElementById('cardType');
            const submitBtn = document.getElementById('submitBtn');
            
            if (!num) {
                badge.style.display = 'none';
                cardError.style.display = 'none';
                submitBtn.disabled = true;
                return;
            }
            
            try {
                const response = await fetch(`/api/validate-card/${encodeURIComponent(num)}`);
                const result = await response.json();
                
                if (result.exists) {
                    currentCardTypes = result.types;
                    
                    // Populate card type dropdown with available types for this card
                    const options = result.types.map(type => `<option value="${type}">${type}</option>`).join('');
                    cardTypeSelect.innerHTML = '<option value="">Select</option>' + options;
                    
                    // Check if used
                    const used = salesData.find(s => s.cardNumber === num);
                    
                    badge.style.display = 'inline-block';
                    badge.className = 'card-status-badge card-valid';
                    badge.textContent = used ? 'USED' : 'VALID';
                    
                    cardError.style.display = 'none';
                    
                    // Enable submit only if card type is selected
                    validateForm();
                } else {
                    currentCardTypes = [];
                    cardTypeSelect.innerHTML = '<option value="">Select</option>';
                    
                    badge.style.display = 'inline-block';
                    badge.className = 'card-status-badge card-invalid';
                    badge.textContent = 'INVALID';
                    
                    cardError.style.display = 'block';
                    submitBtn.disabled = true;
                }
            } catch (error) {
                console.error('Card validation error:', error);
            }
        }

        function validateCardType() {
            validateForm();
        }

        function validateForm() {
            const cardNumber = document.getElementById('cardNumber').value.trim();
            const cardType = document.getElementById('cardType').value;
            const submitBtn = document.getElementById('submitBtn');
            
            // Check if card number exists in master data and type matches
            const isValid = cardNumber && cardType && currentCardTypes.includes(cardType);
            submitBtn.disabled = !isValid;
        }

        async function checkEditCard() {
            const num = document.getElementById('editCardNumber').value.trim();
            const badge = document.getElementById('editCardValidationBadge');
            const cardTypeSelect = document.getElementById('editCardType');
            
            if (!num) {
                badge.style.display = 'none';
                return;
            }
            
            try {
                const response = await fetch(`/api/validate-card/${encodeURIComponent(num)}`);
                const result = await response.json();
                
                if (result.exists) {
                    const options = result.types.map(type => `<option value="${type}">${type}</option>`).join('');
                    cardTypeSelect.innerHTML = '<option value="">Select</option>' + options;
                    
                    badge.style.display = 'inline-block';
                    badge.className = 'card-status-badge card-valid';
                    badge.textContent = 'VALID';
                } else {
                    cardTypeSelect.innerHTML = '<option value="">Select</option>';
                    badge.style.display = 'inline-block';
                    badge.className = 'card-status-badge card-invalid';
                    badge.textContent = 'NOT FOUND';
                }
            } catch (error) {
                console.error('Card validation error:', error);
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
                const url = editId ? `/api/sales/${editId}` : '/api/sales';
                const method = editId ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(record)
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    showAlert(result.error || 'Failed to save', 'error');
                    return;
                }
                
                if (editId) {
                    const idx = salesData.findIndex(s => s.id === editId);
                    if (idx !== -1) salesData[idx] = record;
                    showAlert('Record updated!', 'success');
                } else {
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
            document.getElementById('cardValidationBadge').style.display = 'none';
            document.getElementById('cardError').style.display = 'none';
            document.getElementById('submitBtn').disabled = true;
            currentCardTypes = [];
            populateCardTypeDropdown();
            setCurrentDateTime();
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

        async function editRecord(id) {
            const record = salesData.find(s => s.id === id);
            if (!record) return;
            
            document.getElementById('editModalId').value = record.id;
            document.getElementById('editDateTime').value = record.dateTime.slice(0, 16);
            document.getElementById('editCardNumber').value = record.cardNumber;
            
            // Validate and populate card types
            await checkEditCard();
            
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
                const response = await fetch(`/api/sales/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(record)
                });
                
                const result = await response.json();
                
                if (!result.success) {
                    showAlert(result.error || 'Failed to update', 'error');
                    return;
                }
                
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
