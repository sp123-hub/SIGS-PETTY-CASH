import os
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from werkzeug.utils import secure_filename # Added for safe file saving

app = Flask(__name__)

# Configure a folder to save uploaded files
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    conn = sqlite3.connect('site_data.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            file TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM transactions ORDER BY date DESC').fetchall()
    
    # Calculate totals
    received = conn.execute('SELECT SUM(amount) FROM transactions WHERE type="Received"').fetchone()[0] or 0.0
    expenses = conn.execute('SELECT SUM(amount) FROM transactions WHERE type="Expense"').fetchone()[0] or 0.0
    balance = received - expenses
    
    conn.close()
    return render_template('index.html', transactions=transactions, received=received, expenses=expenses, balance=balance)

@app.route('/add', methods=('POST',))
def add():
    date = request.form['date']
    description = request.form['description']
    type = request.form['type']
    
    # Safely convert amount to float
    try:
        amount = float(request.form['amount'])
    except ValueError:
        amount = 0.0 
    
    # Handle the file upload properly
    file = request.files.get('file')
    filename = ""
    if file and file.filename:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = get_db_connection()
    conn.execute('INSERT INTO transactions (date, description, type, amount, file) VALUES (?, ?, ?, ?, ?)',
                 (date, description, type, amount, filename)) # Saving filename, not the object
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit(id):
    conn = get_db_connection()
    transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        date = request.form['date']
        description = request.form['description']
        type = request.form['type']
        
        try:
            amount = float(request.form['amount'])
        except ValueError:
            amount = 0.0

        file = request.files.get('file')
        
        # If a new file is uploaded, save it and update the DB
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            # Keep the old filename if no new file is uploaded
            filename = transaction['file']

        # FIXED: Added `id` at the end of the tuple!
        conn.execute('UPDATE transactions SET date = ?, description = ?, type = ?, amount = ?, file = ? WHERE id = ?',
                     (date, description, type, amount, filename, id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit.html', transaction=transaction)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)