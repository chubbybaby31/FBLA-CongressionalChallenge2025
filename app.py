from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import os
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import google.generativeai as genai


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
                date, amount, category, type, id = line.strip().split(',')
                transactions.append({
                    'date': date,
                    'amount': float(amount),
                    'category': category,
                    'type': type,
                    'id': int(id)
                })
    return transactions

def write_transaction(date, amount, category, type):
    transactions = read_transactions()
    new_id = max([t['id'] for t in transactions], default=0) + 1
    with open(TRANSACTIONS_FILE, 'a') as f:
        f.write(f"{date},{amount},{category},{type},{new_id}\n")
    return new_id

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

@app.route('/summary', methods=['GET', 'POST'])
def summary():
    # Default to current month if no specific date is provided
    from datetime import datetime, timedelta
    
    # Get current date and first day of current month
    current_date = datetime.now()
    first_day_of_month = current_date.replace(day=1)
    
    # Handle date filtering
    start_date = request.args.get('start_date', first_day_of_month.strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', current_date.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        # Fallback to current month if date parsing fails
        start_date = first_day_of_month
        end_date = current_date
    
    # Read and filter transactions
    transactions = read_transactions()
    df = pd.DataFrame(transactions)
    
    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter transactions within the specified date range
    filtered_df = df[
        (df['date'] >= start_date) & 
        (df['date'] <= end_date)
    ]
    
    # Calculate summaries
    total_income = filtered_df[filtered_df['type'] == 'income']['amount'].sum()
    total_expenses = filtered_df[filtered_df['type'] == 'expense']['amount'].sum()
    net = total_income - total_expenses

    # Income by category
    income_by_category = filtered_df[filtered_df['type'] == 'income'].groupby('category')['amount'].sum().reset_index()
    
    # Expenses by category
    expenses_by_category = filtered_df[filtered_df['type'] == 'expense'].groupby('category')['amount'].sum().reset_index()
    
    # Create pie charts
    # Income Pie Chart
    if not income_by_category.empty:
        income_pie = px.pie(
            income_by_category, 
            values='amount', 
            names='category', 
            title=f'Income by Category ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})'
        )
        income_pie_json = json.dumps(income_pie, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        income_pie_json = None

    # Create pie charts
    if not income_by_category.empty:
        income_pie = px.pie(
            income_by_category, 
            values='amount', 
            names='category', 
            title='Income by Category'
        )
        income_pie_data = income_pie.to_json()
    else:
        income_pie_data = None

    # Expenses Pie Chart
    if not expenses_by_category.empty:
        expenses_pie = px.pie(
            expenses_by_category, 
            values='amount', 
            names='category', 
            title='Expenses by Category'
        )
        expenses_pie_data = expenses_pie.to_json()
    else:
        expenses_pie_data = None

    return render_template('summary.html', 
                           total_income=total_income, 
                           total_expenses=total_expenses, 
                           net=net,
                           income_pie_data=income_pie_data,
                           expenses_pie_data=expenses_pie_data,
                           start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'),
                           transactions=transactions)

@app.route('/search', methods=['GET', 'POST'])
def search():
    keyword = request.args.get('keyword', '')
    transactions = []
    if keyword:
        all_transactions = read_transactions()
        transactions = [t for t in all_transactions if keyword.lower() in t['category'].lower()]
    return render_template('search_results.html', transactions=transactions, keyword=keyword)


@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    try:
        transactions = read_transactions()
        transaction_found = False
        current_balance = read_balance()
        
        for i, transaction in enumerate(transactions):
            if transaction.get('id') == transaction_id:
                deleted_transaction = transactions.pop(i)
                transaction_found = True
                
                # Adjust balance
                if deleted_transaction['type'] == 'income':
                    new_balance = current_balance - deleted_transaction['amount']
                else:  # expense
                    new_balance = current_balance + deleted_transaction['amount']
                
                # Update balance in file
                write_balance(new_balance)
                
                # Write updated transactions back to file
                with open(TRANSACTIONS_FILE, 'w') as f:
                    for t in transactions:
                        f.write(f"{t['date']},{t['amount']},{t['category']},{t['type']},{t['id']}\n")
                
                break
        
        if transaction_found:
            return jsonify({"success": True, "new_balance": new_balance})
        else:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
    except Exception as e:
        app.logger.error(f"Error deleting transaction: {str(e)}")
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500

@app.route('/edit_transaction/<int:transaction_id>', methods=['POST'])
def edit_transaction(transaction_id):
    try:
        transactions = read_transactions()
        edited_transaction = request.get_json()
        if edited_transaction is None:
            return jsonify({"success": False, "error": "Invalid JSON data"}), 400
        transaction_found = False
        current_balance = read_balance()
        
        for i, transaction in enumerate(transactions):
            if transaction.get('id') == transaction_id:
                old_transaction = transaction.copy()
                transactions[i] = {**transaction, **edited_transaction}
                transaction_found = True
                
                # Adjust balance
                if old_transaction['type'] == 'income':
                    current_balance -= old_transaction['amount']
                else:  # expense
                    current_balance += old_transaction['amount']
                
                if edited_transaction['type'] == 'income':
                    current_balance += edited_transaction['amount']
                else:  # expense
                    current_balance -= edited_transaction['amount']
                
                # Update balance in file
                write_balance(current_balance)
                
                # Write updated transactions back to file
                with open(TRANSACTIONS_FILE, 'w') as f:
                    for t in transactions:
                        f.write(f"{t['date']},{t['amount']},{t['category']},{t['type']},{t['id']}\n")
                
                break
        
        if transaction_found:
            return jsonify({"success": True, "new_balance": current_balance})
        else:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
    except Exception as e:
        app.logger.error(f"Error editing transaction: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

genai.configure(api_key='AIzaSyBzu_nG7KLLyJykyMwG3-T8xxHDJttV72o')  # Replace with your actual API key
model = genai.GenerativeModel('gemini-pro')

# ... (keep all the existing code)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        user_input = request.form['user_input']
        
        # Generate response using Gemini API
        response = model.generate_content(user_input)
        
        return jsonify({'response': response.text})
    
    return render_template('chatbot.html')

if __name__ == '__main__':
    app.run(debug=True)