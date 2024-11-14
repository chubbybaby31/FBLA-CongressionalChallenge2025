from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')

# File paths
BALANCE_FILE = 'data/balance.txt'
TRANSACTIONS_FILE = 'data/transactions.txt'

def read_balance():
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, 'r') as f:
            return float(f.read().strip() or 0)
    return 0

def write_balance(balance):
    with open(BALANCE_FILE, 'w') as f:
        f.write(str(balance))

def read_transactions():
    transactions = []
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE, 'r') as f:
            for line in f:
                date, amount, category, type = line.strip().split(',')
                transactions.append({
                    'date': date,
                    'amount': float(amount),
                    'category': category,
                    'type': type
                })
    return transactions

def write_transaction(date, amount, category, type):
    with open(TRANSACTIONS_FILE, 'a') as f:
        f.write(f"{date},{amount},{category},{type}\n")

def update_balance(amount, type):
    balance = read_balance()
    if type == 'income':
        balance += amount
    else:
        balance -= amount
    write_balance(balance)

@app.route('/')
def home():
    balance = read_balance()
    transactions = read_transactions()
    return render_template('index.html', balance=balance, transactions=transactions)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        category = request.form['category']
        type = request.form['type']
        
        write_transaction(date, amount, category, type)
        update_balance(amount, type)
        
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('home'))
    
    return render_template('add_transaction.html')

@app.route('/summary')
def summary():
    transactions = read_transactions()
    # Calculate summaries (you can expand this based on your needs)
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    
    return render_template('summary.html', total_income=total_income, total_expenses=total_expenses)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        keyword = request.form['keyword']
        transactions = read_transactions()
        filtered_transactions = [t for t in transactions if keyword.lower() in t['category'].lower()]
        return render_template('search_results.html', transactions=filtered_transactions)
    
    return render_template('search.html')

if __name__ == '__main__':
    app.run(debug=True)