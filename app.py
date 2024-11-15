from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import os
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import google.generativeai as genai

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flashing messages

# Ensure data directory exists
if not os.path.exists('data'):
    os.makedirs('data')  # Create 'data' directory if it doesn't exist

# File paths for balance and transactions data
BALANCE_FILE = 'data/balance.txt'
TRANSACTIONS_FILE = 'data/transactions.txt'

def read_balance():
    """Read the current balance from the balance file."""
    if os.path.exists(BALANCE_FILE):
        with open(BALANCE_FILE, 'r') as f:
            return float(f.read().strip() or 0)  # Return balance as float
    return 0  # Return 0 if no balance file exists

def write_balance(balance):
    """Write the current balance to the balance file."""
    with open(BALANCE_FILE, 'w') as f:
        f.write(str(balance))  # Save balance as string

def read_transactions():
    """Read all transactions from the transactions file."""
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
                })  # Append transaction details to list
    return transactions

def write_transaction(date, amount, category, type):
    """Write a new transaction to the transactions file."""
    transactions = read_transactions()  # Read existing transactions
    new_id = max([t['id'] for t in transactions], default=0) + 1  # Generate new transaction ID
    with open(TRANSACTIONS_FILE, 'a') as f:
        f.write(f"{date},{amount},{category},{type},{new_id}\n")  # Append new transaction to file
    return new_id  # Return the new transaction ID

def update_balance(amount, type):
    """Update the balance based on income or expense."""
    balance = read_balance()  # Get current balance
    if type == 'income':
        balance += amount  # Increase balance for income
    else:
        balance -= amount  # Decrease balance for expense
    write_balance(balance)  # Save updated balance

@app.route('/')
def home():
    """Render the home page showing current balance and transactions."""
    balance = read_balance()  # Get current balance
    transactions = read_transactions()  # Get all transactions
    return render_template('index.html', balance=balance, transactions=transactions)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    """Handle adding a new transaction."""
    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        category = request.form['category']
        type = request.form['type']
        
        write_transaction(date, amount, category, type)  # Write new transaction to file
        update_balance(amount, type)  # Update the balance
        
        flash('Transaction added successfully!', 'success')  # Show success message
        return redirect(url_for('home'))  # Redirect to home page
    
    return render_template('add_transaction.html')  # Render form for adding transaction

@app.route('/summary', methods=['GET', 'POST'])
def summary():
    """Render a summary of income and expenses."""
    
    # Default to current month if no specific date is provided
    current_date = datetime.now()
    first_day_of_month = current_date.replace(day=1)  # First day of current month
    
    # Handle date filtering from query parameters
    start_date = request.args.get('start_date', first_day_of_month.strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', current_date.strftime('%Y-%m-%d'))
    
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        start_date = first_day_of_month  # Fallback to current month if date parsing fails
        end_date = current_date
    
    # Read and filter transactions based on specified date range
    transactions = read_transactions()
    df = pd.DataFrame(transactions)
    
    df['date'] = pd.to_datetime(df['date'])  # Convert date column to datetime
    
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]  # Filter transactions
    
    # Calculate summaries for total income and expenses within the filtered date range
    total_income = filtered_df[filtered_df['type'] == 'income']['amount'].sum()
    total_expenses = filtered_df[filtered_df['type'] == 'expense']['amount'].sum()
    
    net = total_income - total_expenses  # Calculate net income
    
    # Income by category and expenses by category summaries
    income_by_category = filtered_df[filtered_df['type'] == 'income'].groupby('category')['amount'].sum().reset_index()
    expenses_by_category = filtered_df[filtered_df['type'] == 'expense'].groupby('category')['amount'].sum().reset_index()
    
    # Create pie charts for income and expenses by category using Plotly
    if not income_by_category.empty:
        income_pie = px.pie(
            income_by_category,
            values='amount',
            names='category',
            title=f'Income by Category ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})'
        )
        income_pie_data = income_pie.to_json()
        
        expenses_pie_data = None  # Placeholder for expenses pie chart data
        
        if not expenses_by_category.empty:
            expenses_pie = px.pie(
                expenses_by_category,
                values='amount',
                names='category',
                title='Expenses by Category'
            )
            expenses_pie_data = expenses_pie.to_json()
        
        return render_template('summary.html', total_income=total_income,
                               total_expenses=total_expenses,
                               net=net,
                               income_pie_data=income_pie_data,
                               expenses_pie_data=expenses_pie_data,
                               start_date=start_date.strftime('%Y-%m-%d'),
                               end_date=end_date.strftime('%Y-%m-%d'),
                               transactions=transactions)
    
@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for transactions based on a keyword."""
    
    keyword = request.args.get('keyword', '')  # Get search keyword from query parameters
    transactions = []
    
    if keyword:  
        all_transactions = read_transactions()  
        transactions = [t for t in all_transactions if keyword.lower() in t['category'].lower()]  
    
    return render_template('search_results.html', transactions=transactions, keyword=keyword)

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    """Delete a specified transaction by its ID."""
    
    try:
       transactions = read_transactions()  
       transaction_found = False  
       current_balance = read_balance()  
       
       for i, transaction in enumerate(transactions):  
           if transaction.get('id') == transaction_id:  
               deleted_transaction = transactions.pop(i)  
               transaction_found = True  
               
               # Adjust balance based on deleted transaction type
               if deleted_transaction['type'] == 'income':  
                   new_balance = current_balance - deleted_transaction['amount']  
               else:  
                   new_balance = current_balance + deleted_transaction['amount']  
               
               write_balance(new_balance)  # Update balance in file  

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
   """Edit an existing transaction by its ID."""
   
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

               # Adjust balance based on old and edited transaction types
               if old_transaction['type'] == 'income':  
                   current_balance -= old_transaction['amount']  
               else: 
                   current_balance += old_transaction['amount']  

               if edited_transaction['type'] == 'income': 
                   current_balance += edited_transaction['amount']  
               else: 
                   current_balance -= edited_transaction['amount']  

               write_balance(current_balance)  

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

# Configure Google Generative AI API key (replace with your actual API key)
genai.configure(api_key='AIzaSyBzu_nG7KLLyJykyMwG3-T8xxHDJttV72o')
model = genai.GenerativeModel('gemini-pro')

def format_response(response_text):
   """Format response text from AI model."""
   
   formatted_text = response_text.replace('*', '<strong>') 
   formatted_text = formatted_text.replace('<strong>', '<strong>', 1).replace('</strong>', '</strong>', 1) 

   paragraphs = formatted_text.split('\n\n') 
   formatted_paragraphs = ''.join(f'<p>{para.strip()}</p>' for para in paragraphs if para.strip()) 

   return formatted_paragraphs 

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
   """Handle chatbot interactions and provide financial advice based on user input."""
   
   if request.method == 'POST':
       user_input = request.form['user_input']

       # Get client's financial information
       balance = read_balance() 
       transactions = read_transactions() 

       df = pd.DataFrame(transactions) 
       df['date'] = pd.to_datetime(df['date']) 
       df['amount'] = df['amount'].astype(float) 

       today = datetime.now() 
       last_30_days = today - timedelta(days=30) 
       
       recent_df = df[df['date'] > last_30_days] 
       
       total_income = recent_df[recent_df['type'] == 'income']['amount'].sum() 
       total_expenses = recent_df[recent_df['type'] == 'expense']['amount'].sum() 
       
       top_expense_categories = recent_df[recent_df['type'] == 'expense'].groupby('category')['amount'].sum().nlargest(3)

       context = f"""Current balance: **${balance:.2f}** Recent income (last 30 days): **${total_income:.2f}** Recent expenses (last 30 days): **${total_expenses:.2f}** Top 3 expense categories (last 30 days): {top_expense_categories.to_string()} Based on this information answer the following user query: {user_input}"""

       response = model.generate_content(context) 

       formatted_response = format_response(response.text) 

       return jsonify({'response': formatted_response}) 

   return render_template('chatbot.html')

@app.route('/instructions')
def instructions():
   """Render the instructions page explaining how to use the application."""
   return render_template('instructions.html')

if __name__ == '__main__':
   app.run(debug=True)  # Run the Flask application in debug mode.