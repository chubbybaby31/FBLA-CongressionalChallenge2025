from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import os
import plotly
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import google.generativeai as genai
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
from plaid.model.payment_amount import PaymentAmount
from plaid.model.payment_amount_currency import PaymentAmountCurrency
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.recipient_bacs_nullable import RecipientBACSNullable
from plaid.model.payment_initiation_address import PaymentInitiationAddress
from plaid.model.payment_initiation_recipient_create_request import PaymentInitiationRecipientCreateRequest
from plaid.model.payment_initiation_payment_create_request import PaymentInitiationPaymentCreateRequest
from plaid.model.payment_initiation_payment_get_request import PaymentInitiationPaymentGetRequest
from plaid.model.link_token_create_request_payment_initiation import LinkTokenCreateRequestPaymentInitiation
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.user_create_request import UserCreateRequest
from plaid.model.consumer_report_user_identity import ConsumerReportUserIdentity
from plaid.model.asset_report_create_request import AssetReportCreateRequest
from plaid.model.asset_report_create_request_options import AssetReportCreateRequestOptions
from plaid.model.asset_report_user import AssetReportUser
from plaid.model.asset_report_get_request import AssetReportGetRequest
from plaid.model.asset_report_pdf_get_request import AssetReportPDFGetRequest
from plaid.model.auth_get_request import AuthGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.identity_get_request import IdentityGetRequest
from plaid.model.investments_transactions_get_request_options import InvestmentsTransactionsGetRequestOptions
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_get_request import ItemGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.transfer_authorization_create_request import TransferAuthorizationCreateRequest
from plaid.model.transfer_create_request import TransferCreateRequest
from plaid.model.transfer_get_request import TransferGetRequest
from plaid.model.transfer_network import TransferNetwork
from plaid.model.transfer_type import TransferType
from plaid.model.transfer_authorization_user_in_request import TransferAuthorizationUserInRequest
from plaid.model.ach_class import ACHClass
from plaid.model.transfer_create_idempotency_key import TransferCreateIdempotencyKey
from plaid.model.transfer_user_address_in_request import TransferUserAddressInRequest
from plaid.model.signal_evaluate_request import SignalEvaluateRequest
from plaid.model.statements_list_request import StatementsListRequest
from plaid.model.link_token_create_request_statements import LinkTokenCreateRequestStatements
from plaid.model.link_token_create_request_cra_options import LinkTokenCreateRequestCraOptions
from plaid.model.statements_download_request import StatementsDownloadRequest
from plaid.model.consumer_report_permissible_purpose import ConsumerReportPermissiblePurpose
from plaid.model.cra_check_report_base_report_get_request import CraCheckReportBaseReportGetRequest
from plaid.model.cra_check_report_pdf_get_request import CraCheckReportPDFGetRequest
from plaid.model.cra_check_report_income_insights_get_request import CraCheckReportIncomeInsightsGetRequest
from plaid.model.cra_check_report_partner_insights_get_request import CraCheckReportPartnerInsightsGetRequest
from plaid.model.cra_pdf_add_ons import CraPDFAddOns
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


        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/')
def home():
    if not fb: return redirect(url_for('login'))
    return render_template('index.html', balance=fb.balance, transactions=fb.transactions, name=fb.name)

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
genai.configure(api_key='AIzaSyBxRlte3PtiQNXQ6scrKG_MCf_miBr7DEs')
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

       response = model.generate_content(context) 

       formatted_response = format_response(response.text) 

       return jsonify({'response': formatted_response}) 

   return render_template('chatbot.html')

@app.route('/instructions')
def instructions():
   """Render the instructions page explaining how to use the application."""
   return render_template('instructions.html')

@app.route('/api/info', methods=['POST'])
def info():
    global access_token
    global item_id
    return jsonify({
        'item_id': item_id,
        'access_token': access_token,
        'products': PLAID_PRODUCTS
    })


@app.route('/api/create_link_token_for_payment', methods=['POST'])
def create_link_token_for_payment():
    global payment_id
    try:
        request = PaymentInitiationRecipientCreateRequest(
            name='John Doe',
            bacs=RecipientBACSNullable(account='26207729', sort_code='560029'),
            address=PaymentInitiationAddress(
                street=['street name 999'],
                city='city',
                postal_code='99999',
                country='GB'
            )
        )
        response = client.payment_initiation_recipient_create(
            request)
        recipient_id = response['recipient_id']

        request = PaymentInitiationPaymentCreateRequest(
            recipient_id=recipient_id,
            reference='TestPayment',
            amount=PaymentAmount(
                PaymentAmountCurrency('GBP'),
                value=100.00
            )
        )
        response = client.payment_initiation_payment_create(
            request
        )
        pretty_print_response(response.to_dict())
        
        # We store the payment_id in memory for demo purposes - in production, store it in a secure
        # persistent data store along with the Payment metadata, such as userId.
        payment_id = response['payment_id']
        
        linkRequest = LinkTokenCreateRequest(
            # The 'payment_initiation' product has to be the only element in the 'products' list.
            products=[Products('payment_initiation')],
            client_name='Plaid Test',
            # Institutions from all listed countries will be shown.
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES)),
            language='en',
            user=LinkTokenCreateRequestUser(
                # This should correspond to a unique id for the current user.
                # Typically, this will be a user ID number from your application.
                # Personally identifiable information, such as an email address or phone number, should not be used here.
                client_user_id=str(time.time())
            ),
            payment_initiation=LinkTokenCreateRequestPaymentInitiation(
                payment_id=payment_id
            )
        )

        if PLAID_REDIRECT_URI!=None:
            linkRequest['redirect_uri']=PLAID_REDIRECT_URI
        linkResponse = client.link_token_create(linkRequest)
        pretty_print_response(linkResponse.to_dict())
        return jsonify(linkResponse.to_dict())
    except plaid.ApiException as e:
        return json.loads(e.body)


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

# Create a user token which can be used for Plaid Check, Income, or Multi-Item link flows
# https://plaid.com/docs/api/users/#usercreate
@app.route('/api/create_user_token', methods=['POST'])
def create_user_token():
    global user_token
    try:
        consumer_report_user_identity = None
        user_create_request = UserCreateRequest(
            # Typically this will be a user ID number from your application. 
            client_user_id="user_" + str(uuid.uuid4())
        )

        cra_products = ["cra_base_report", "cra_income_insights", "cra_partner_insights"]
        if any(product in cra_products for product in PLAID_PRODUCTS):
            consumer_report_user_identity = ConsumerReportUserIdentity(
                first_name="Harry",
                last_name="Potter",
                phone_numbers= ['+16174567890'],
                emails= ['harrypotter@example.com'],
                primary_address= {
                    "city": 'New York',
                    "region": 'NY',
                    "street": '4 Privet Drive',
                    "postal_code": '11111',
                    "country": 'US'
                }
            )
            user_create_request["consumer_report_user_identity"] = consumer_report_user_identity

        user_response = client.user_create(user_create_request)
        user_token = user_response['user_token']
        return jsonify(user_response.to_dict())
    except plaid.ApiException as e:
        print(e)
        return jsonify(json.loads(e.body)), e.status


# Exchange token flow - exchange a Link public_token for
# an API access_token
# https://plaid.com/docs/#exchange-token-flow


@app.route('/api/set_access_token', methods=['POST'])
def get_access_token():
    global access_token
    global item_id
    try:
        data = request.get_json()  # ✅ Correctly get JSON data
        public_token = data.get('public_token')  # ✅ Extract public_token safely

        if not public_token:
            return jsonify({'error': 'Missing public_token'}), 400  # Return error if missing

        # Exchange the public_token for an access_token
        exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
        exchange_response = client.item_public_token_exchange(exchange_request)
        
        access_token = exchange_response.access_token  # ✅ Store access_token
        item_id = exchange_response.item_id  # ✅ Store item_id

        return jsonify(exchange_response.to_dict())  # ✅ Return success response

    except plaid.ApiException as e:
        return json.loads(e.body)

# Retrieve ACH or ETF account numbers for an Item
# https://plaid.com/docs/#auth


@app.route('/api/auth', methods=['GET'])
def get_auth():
    try:
       request = AuthGetRequest(
            access_token=access_token
        )
       response = client.auth_get(request)
       pretty_print_response(response.to_dict())
       return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve Transactions for an Item
# https://plaid.com/docs/#transactions


 

TRANSACTIONS_FILE = "transactions.json"  # JSON file to store transactions

def parse_transaction(transaction):
    """Convert transaction data into a clean format."""
    transaction_date = transaction["date"]
    
  
    if isinstance(transaction_date, date):
        formatted_date = transaction_date.strftime("%m-%d-%Y")
    else:
        
        formatted_date = datetime.strptime(transaction_date, "%Y-%m-%d").strftime("%m-%d-%Y")

    return {
        "date": formatted_date,  
        "amount": round(transaction["amount"], 2),  
        "type": "income" if transaction["amount"] > 0 else "expense", 
        "category": transaction.get("merchant_name", transaction.get("name", "Unknown")) 
    }


@app.route('/api/transactions', methods=['GET', 'POST']) 
def get_transactions():
    global access_token

    if not access_token:
        return jsonify({'error': 'No access_token found. Please connect a bank first.'}), 400

    if request.method == 'GET': 
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r') as file:
                try:
                    existing_transactions = json.load(file)
                    return jsonify({'transactions': existing_transactions})
                except json.JSONDecodeError:
                    return jsonify({'error': 'Failed to load transactions'}), 500
        return jsonify({'transactions': []})

   
    cursor = ''
    added = []
    has_more = True

    try:
        while has_more:
            plaid_request = TransactionsSyncRequest(  
                access_token=access_token,  
                cursor=cursor,
            )
            response = client.transactions_sync(plaid_request).to_dict()
            cursor = response['next_cursor']
            added.extend(response['added'])
            has_more = response['has_more']

        # Read existing transactions
        if os.path.exists(TRANSACTIONS_FILE):
            with open(TRANSACTIONS_FILE, 'r') as file:
                try:
                    existing_transactions = json.load(file)
                except json.JSONDecodeError:
                    existing_transactions = []  
        else:
            existing_transactions = []

        # Append new transactions while avoiding duplicates
        existing_transaction_ids = {t['transaction_id'] for t in existing_transactions}
        new_transactions = [parse_transaction(t) for t in added if t['transaction_id'] not in existing_transaction_ids]
        existing_transactions.extend(new_transactions)

        # Save back to the file
        with open(TRANSACTIONS_FILE, 'w') as file:
            json.dump(existing_transactions, file, indent=2)  

        return jsonify({'message': 'Transactions updated successfully', 'transactions': existing_transactions})

    except plaid.ApiException as e:
        return jsonify({'error': 'Failed to fetch transactions', 'details': json.loads(e.body)}), 500



@app.route('/api/identity', methods=['GET'])
def get_identity():
    try:
        request = IdentityGetRequest(
            access_token=access_token
        )
        response = client.identity_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(
            {'error': None, 'identity': response.to_dict()['accounts']})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve real-time balance data for each of an Item's accounts
# https://plaid.com/docs/#balance


@app.route('/api/balance', methods=['GET'])
def get_balance():
    try:
        request = AccountsBalanceGetRequest(
            access_token=access_token
        )
        response = client.accounts_balance_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve an Item's accounts
# https://plaid.com/docs/#accounts


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    try:
        request = AccountsGetRequest(
            access_token=access_token
        )
        response = client.accounts_get(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Create and then retrieve an Asset Report for one or more Items. Note that an
# Asset Report can contain up to 100 items, but for simplicity we're only
# including one Item here.
# https://plaid.com/docs/#assets


@app.route('/api/assets', methods=['GET'])
def get_assets():
    try:
        request = AssetReportCreateRequest(
            access_tokens=[access_token],
            days_requested=60,
            options=AssetReportCreateRequestOptions(
                webhook='https://www.example.com',
                client_report_id='123',
                user=AssetReportUser(
                    client_user_id='789',
                    first_name='Jane',
                    middle_name='Leah',
                    last_name='Doe',
                    ssn='123-45-6789',
                    phone_number='(555) 123-4567',
                    email='jane.doe@example.com',
                )
            )
        )

        response = client.asset_report_create(request)
        pretty_print_response(response.to_dict())
        asset_report_token = response['asset_report_token']

        # Poll for the completion of the Asset Report.
        request = AssetReportGetRequest(
            asset_report_token=asset_report_token,
        )
        response = poll_with_retries(lambda: client.asset_report_get(request))
        asset_report_json = response['report']

        request = AssetReportPDFGetRequest(
            asset_report_token=asset_report_token,
        )
        pdf = client.asset_report_pdf_get(request)
        return jsonify({
            'error': None,
            'json': asset_report_json.to_dict(),
            'pdf': base64.b64encode(pdf.read()).decode('utf-8'),
        })
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve investment holdings data for an Item
# https://plaid.com/docs/#investments


@app.route('/api/holdings', methods=['GET'])
def get_holdings():
    try:
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = client.investments_holdings_get(request)
        pretty_print_response(response.to_dict())
        return jsonify({'error': None, 'holdings': response.to_dict()})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve Investment Transactions for an Item
# https://plaid.com/docs/#investments


@app.route('/api/investments_transactions', methods=['GET'])
def get_investments_transactions():
    # Pull transactions for the last 30 days

    start_date = (dt.datetime.now() - dt.timedelta(days=(30)))
    end_date = dt.datetime.now()
    try:
        options = InvestmentsTransactionsGetRequestOptions()
        request = InvestmentsTransactionsGetRequest(
            access_token=access_token,
            start_date=start_date.date(),
            end_date=end_date.date(),
            options=options
        )
        response = client.investments_transactions_get(
            request)
        pretty_print_response(response.to_dict())
        return jsonify(
            {'error': None, 'investments_transactions': response.to_dict()})

    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# This functionality is only relevant for the ACH Transfer product.
# Authorize a transfer

@app.route('/api/transfer_authorize', methods=['GET'])
def transfer_authorization():
    global authorization_id 
    global account_id
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    account_id = response['accounts'][0]['account_id']
    try:
        request = TransferAuthorizationCreateRequest(
            access_token=access_token,
            account_id=account_id,
            type=TransferType('debit'),
            network=TransferNetwork('ach'),
            amount='1.00',
            ach_class=ACHClass('ppd'),
            user=TransferAuthorizationUserInRequest(
                legal_name='FirstName LastName',
                email_address='foobar@email.com',
                address=TransferUserAddressInRequest(
                    street='123 Main St.',
                    city='San Francisco',
                    region='CA',
                    postal_code='94053',
                    country='US'
                ),
            ),
        )
        response = client.transfer_authorization_create(request)
        pretty_print_response(response.to_dict())
        authorization_id = response['authorization']['id']
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# Create Transfer for a specified Transfer ID

@app.route('/api/transfer_create', methods=['GET'])
def transfer():
    try:
        request = TransferCreateRequest(
            access_token=access_token,
            account_id=account_id,
            authorization_id=authorization_id,
            description='Debit')
        response = client.transfer_create(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

@app.route('/api/statements', methods=['GET'])
def statements():
    try:
        request = StatementsListRequest(access_token=access_token)
        response = client.statements_list(request)
        pretty_print_response(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)
    try:
        request = StatementsDownloadRequest(
            access_token=access_token,
            statement_id=response['accounts'][0]['statements'][0]['statement_id']
        )
        pdf = client.statements_download(request)
        return jsonify({
            'error': None,
            'json': response.to_dict(),
            'pdf': base64.b64encode(pdf.read()).decode('utf-8'),
        })
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)




@app.route('/api/signal_evaluate', methods=['GET'])
def signal():
    global account_id
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    account_id = response['accounts'][0]['account_id']
    try:
        request = SignalEvaluateRequest(
            access_token=access_token,
            account_id=account_id,
            client_transaction_id='txn1234',
            amount=100.00)
        response = client.signal_evaluate(request)
        pretty_print_response(response.to_dict())
        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# This functionality is only relevant for the UK Payment Initiation product.
# Retrieve Payment for a specified Payment ID


@app.route('/api/payment', methods=['GET'])
def payment():
    global payment_id
    try:
        request = PaymentInitiationPaymentGetRequest(payment_id=payment_id)
        response = client.payment_initiation_payment_get(request)
        pretty_print_response(response.to_dict())
        return jsonify({'error': None, 'payment': response.to_dict()})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)


# Retrieve high-level information about an Item
# https://plaid.com/docs/#retrieve-item


@app.route('/api/item', methods=['GET'])
def item():
    try:
        request = ItemGetRequest(access_token=access_token)
        response = client.item_get(request)
        request = InstitutionsGetByIdRequest(
            institution_id=response['item']['institution_id'],
            country_codes=list(map(lambda x: CountryCode(x), PLAID_COUNTRY_CODES))
        )
        institution_response = client.institutions_get_by_id(request)
        pretty_print_response(response.to_dict())
        pretty_print_response(institution_response.to_dict())
        return jsonify({'error': None, 'item': response.to_dict()[
            'item'], 'institution': institution_response.to_dict()['institution']})
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# Retrieve CRA Base Report and PDF
# Base report: https://plaid.com/docs/check/api/#cracheck_reportbase_reportget
# PDF: https://plaid.com/docs/check/api/#cracheck_reportpdfget
@app.route('/api/cra/get_base_report', methods=['GET'])
def cra_check_report():
    try:
        get_response = poll_with_retries(lambda: client.cra_check_report_base_report_get(
            CraCheckReportBaseReportGetRequest(user_token=user_token, item_ids=[])
        ))
        pretty_print_response(get_response.to_dict())

        pdf_response = client.cra_check_report_pdf_get(
            CraCheckReportPDFGetRequest(user_token=user_token)
        )
        return jsonify({
            'report': get_response.to_dict()['report'],
            'pdf': base64.b64encode(pdf_response.read()).decode('utf-8')
        })
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# Retrieve CRA Income Insights and PDF with Insights
# Income insights: https://plaid.com/docs/check/api/#cracheck_reportincome_insightsget
# PDF w/ income insights: https://plaid.com/docs/check/api/#cracheck_reportpdfget
@app.route('/api/cra/get_income_insights', methods=['GET'])
def cra_income_insights():
    try:
        get_response = poll_with_retries(lambda: client.cra_check_report_income_insights_get(
            CraCheckReportIncomeInsightsGetRequest(user_token=user_token))
        )
        pretty_print_response(get_response.to_dict())

        pdf_response = client.cra_check_report_pdf_get(
            CraCheckReportPDFGetRequest(user_token=user_token, add_ons=[CraPDFAddOns('cra_income_insights')]),
        )

        return jsonify({
            'report': get_response.to_dict()['report'],
            'pdf': base64.b64encode(pdf_response.read()).decode('utf-8')
        })
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# Retrieve CRA Partner Insights
# https://plaid.com/docs/check/api/#cracheck_reportpartner_insightsget
@app.route('/api/cra/get_partner_insights', methods=['GET'])
def cra_partner_insights():
    try:
        response = poll_with_retries(lambda: client.cra_check_report_partner_insights_get(
            CraCheckReportPartnerInsightsGetRequest(user_token=user_token)
        ))
        pretty_print_response(response.to_dict())

        return jsonify(response.to_dict())
    except plaid.ApiException as e:
        error_response = format_error(e)
        return jsonify(error_response)

# Since this quickstart does not support webhooks, this function can be used to poll
# an API that would otherwise be triggered by a webhook.
# For a webhook example, see
# https://github.com/plaid/tutorial-resources or
# https://github.com/plaid/pattern
def poll_with_retries(request_callback, ms=1000, retries_left=20):
    while retries_left > 0:
        try:
            return request_callback()
        except plaid.ApiException as e:
            response = json.loads(e.body)
            if response['error_code'] != 'PRODUCT_NOT_READY':
                raise e
            elif retries_left == 0:
                raise Exception('Ran out of retries while polling') from e
            else:
                retries_left -= 1
                time.sleep(ms / 1000)

def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True, default=str))

def format_error(e):
    response = json.loads(e.body)
    return {'error': {'status_code': e.status, 'display_message':
                      response['error_message'], 'error_code': response['error_code'], 'error_type': response['error_type']}}

if __name__ == '__main__':
   app.run(debug=True)  # Run the Flask application in debug mode.