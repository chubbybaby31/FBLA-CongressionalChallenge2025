from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import os
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
from google import genai
from firebase_integration import FBAgent

import json
import os
from datetime import datetime, date
from flask import request, jsonify 

import base64
import os
import datetime as dt
import json
import time
from datetime import date, timedelta
import uuid

from dotenv import load_dotenv
import plaid
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.api import plaid_api

load_dotenv()

PLAID_CLIENT_ID = os.getenv('PLAID_CLIENT_ID')
PLAID_SECRET = os.getenv('PLAID_SECRET')
PLAID_ENV = os.getenv('PLAID_ENV', 'sandbox')
PLAID_PRODUCTS = os.getenv('PLAID_PRODUCTS', 'transactions').split(',')
PLAID_COUNTRY_CODES = os.getenv('PLAID_COUNTRY_CODES', 'US').split(',')

def empty_to_none(field):
    value = os.getenv(field)
    if value is None or len(value) == 0:
        return None
    return value

host = plaid.Environment.Sandbox

if PLAID_ENV == 'sandbox':
    host = plaid.Environment.Sandbox

if PLAID_ENV == 'production':
    host = plaid.Environment.Production

PLAID_REDIRECT_URI = empty_to_none('PLAID_REDIRECT_URI')

configuration = plaid.Configuration(
    host=host,
    api_key={
        'clientId': PLAID_CLIENT_ID,
        'secret': PLAID_SECRET,
        'plaidVersion': '2020-09-14'
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

products = []
for product in PLAID_PRODUCTS:
    products.append(Products(product))

access_token = None
payment_id = None
transfer_id = None
user_token = None

item_id = None

# Initialize the Flask application
app = Flask(__name__)

global fb
fb = None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle form submission for regular login
        email = request.form['username']
        password = request.form['password']
        # Add your authentication logic here
        global fb
        fb = FBAgent(email)
        if fb.id == 0: return redirect(url_for('signup'))
        elif fb.contents["password"] != password: return redirect(url_for('login'))
        else: return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Handle form submission for signup
        email = request.form['username']
        password = request.form['password']
        name = request.form['name']
        # Add your user creation logic here
        if '@' in email and '.' in email:
            global fb
            fb = FBAgent(email, new_user=True, name=name, password=password)
        else: return redirect(url_for('signup'))


        return redirect(url_for('connect_bank'))
    return render_template('signup.html')

@app.route('/')
def home():
    if not fb: return redirect(url_for('login'))
    return render_template('index.html', balance=fb.balance, transactions=fb.transactions[::-1], name=fb.name)

@app.route('/add_transaction', methods=['GET', 'POST'])
def add_transaction():
    """Handle adding a new transaction."""
    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        category = request.form['category']
        trx_type = request.form['type']
        
        fb.addTransaction(trx_type, date, category, amount)

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
    transactions = fb.transactions
    df = pd.DataFrame(transactions)
    
    df['date'] = pd.to_datetime(df['date'])  # Convert date column to datetime
    
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]  # Filter transactions
    print(df)
    
    # Calculate summaries for total income and expenses within the filtered date range
    total_income = filtered_df[filtered_df['type'] == 'income']['value'].sum()
    total_expenses = filtered_df[filtered_df['type'] == 'expense']['value'].sum()
    
    net = total_income - total_expenses  # Calculate net 
    
    # Income by category and expenses by category summaries
    income_by_category = filtered_df[filtered_df['type'] == 'income'].groupby('description')['value'].sum().reset_index()
    expenses_by_category = filtered_df[filtered_df['type'] == 'expense'].groupby('description')['value'].sum().reset_index()
    
    # Create pie charts for income and expenses by category using Plotly
    if not income_by_category.empty:
        income_pie = px.pie(
            income_by_category,
            values='value',
            names='description',
            title=f'Income by Category ({start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")})'
        )
        income_pie_data = income_pie.to_json()
        
        expenses_pie_data = None  # Placeholder for expenses pie chart data
        
        if not expenses_by_category.empty:
            expenses_pie = px.pie(
                expenses_by_category,
                values='value',
                names='description',
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
    
    # Convert start_date and end_date to datetime objects if they're not already
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Get all transactions and convert to DataFrame if it's not already
    transactions_df = pd.DataFrame(fb.transactions)

    # Convert the date column to datetime
    transactions_df['date'] = pd.to_datetime(transactions_df['date'])

    # Filter transactions within the date range
    filtered_df = transactions_df[(transactions_df['date'] >= start_date) & (transactions_df['date'] <= end_date)]

    # Sort transactions by date
    filtered_df = filtered_df.sort_values('date')

    # Initialize the balance data
    balance_data = []
    current_balance = fb.balance

    # Generate daily balance data
    current_date = start_date
    while current_date <= end_date:
        # Filter transactions for the current date
        daily_transactions = filtered_df[filtered_df['date'].dt.date == current_date.date()]

        # Update balance based on daily transactions
        for _, transaction in daily_transactions.iterrows():
            if transaction['type'] == 'income':
                current_balance -= transaction['value']
            else:
                current_balance += transaction['value']   

        # Append the balance for the current date
        balance_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'balance': round(current_balance, 2)
        })

        # Move to the next day
        current_date += timedelta(days=1)
    print("HELLOOOO")
    return balance_data

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search for transactions based on a keyword."""
    
    keyword = request.args.get('keyword', '')  # Get search keyword from query parameters
    transactions = []
    
    if keyword:  
        all_transactions = fb.transactions 
        transactions = [t for t in all_transactions if keyword.lower() in t['description'].lower()]  
    
    return render_template('search_results.html', transactions=transactions, keyword=keyword)

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    fb.deleteTransaction(transaction_id)
    return redirect(url_for('home'))

@app.route('/edit_transaction/<int:transaction_id>', methods=['POST'])
def edit_transaction(transaction_id):
    etrx = request.get_json()
    fb.editTransaction(transaction_id, etrx["type"], etrx["date"], etrx["description"], etrx["value"])
    return jsonify({"success": True, "new_balance": fb.balance})


# Configure Google Generative AI API key (replace with your actual API key)
# genai.configure(api_key='AIzaSyBxRlte3PtiQNXQ6scrKG_MCf_miBr7DEs')
# model = genai.GenerativeModel('gemini-pro')

client_ai = genai.Client(api_key="AIzaSyBxRlte3PtiQNXQ6scrKG_MCf_miBr7DEs")

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
       balance = fb.balance
       transactions = fb.transactions

       df = pd.DataFrame(transactions) 
       df['date'] = pd.to_datetime(df['date']) 
       df['value'] = df['value'].astype(float) 

       today = datetime.now() 
       last_30_days = today - timedelta(days=30) 
       
       recent_df = df[df['date'] > last_30_days] 
       
       total_income = recent_df[recent_df['type'] == 'income']['value'].sum() 
       total_expenses = recent_df[recent_df['type'] == 'expense']['value'].sum() 
       
       top_expense_categories = recent_df[recent_df['type'] == 'expense'].groupby('description')['value'].sum().nlargest(3)

       context = f"""Current balance: **${balance:.2f}** Recent income (last 30 days): **${total_income:.2f}** Recent expenses (last 30 days): **${total_expenses:.2f}** Top 3 expense categories (last 30 days): {top_expense_categories.to_string()} Based on this information answer the following user query: {user_input}"""

       response = client_ai.models.generate_content(
            model="gemini-2.5-flash",
            contents=context,
        )
       
    #    response = model.generate_content(context) 

       formatted_response = format_response(response.text) 

       return jsonify({'response': formatted_response}) 

   return render_template('chatbot.html')

@app.route('/instructions')
def instructions():
   """Render the instructions page explaining how to use the application."""
   return render_template('instructions.html')

@app.route('/api/create_link_token', methods=['POST'])
def create_link_token():
    global user_token
    try:
        request = LinkTokenCreateRequest(
            products=products,
            client_name="Plaid Quickstart",
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(time.time())
            )
        )
        if PLAID_REDIRECT_URI!=None:
            request['redirect_uri']=PLAID_REDIRECT_URI
        if Products('statements') in products:
            statements=LinkTokenCreateRequestStatements(
                end_date=date.today(),
                start_date=date.today()-timedelta(days=30)
            )
            request['statements']=statements

        cra_products = ["cra_base_report", "cra_income_insights", "cra_partner_insights"]
        if any(product in cra_products for product in PLAID_PRODUCTS):
            request['user_token'] = user_token
            request['consumer_report_permissible_purpose'] = ConsumerReportPermissiblePurpose('ACCOUNT_REVIEW_CREDIT')
            request['cra_options'] = LinkTokenCreateRequestCraOptions(
                days_requested=60
            )
    # create link token
        response = client.link_token_create(request)
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        print(e)
        return json.loads(e.body)

@app.route('/connect_bank')
def connect_bank():
    return render_template('connect_bank.html')


if __name__ == '__main__':
   app.run(debug=True)  # Run the Flask application in debug mode