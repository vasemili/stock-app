from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_pymongo import PyMongo
import plotly.graph_objs as go
import yfinance as yf
import datetime
import os
import openai
import requests
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import re
import uuid
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from transformers import BartTokenizer, BartForConditionalGeneration
import torch
load_dotenv()

# Access environment variables

app = Flask(__name__, static_folder="../public", template_folder="../templates")

openai_api_key = os.getenv('OpenAI_key')
mongodb_uri = os.getenv('MongoDB_URI')
fin_map_key = os.getenv('Fin_Map_key')

# MongoDB Configuration
app.config['OPENAI_API_KEY'] = openai_api_key

app.config['MONGO_URI'] = mongodb_uri

app.config['FIN_MAP_KEY'] = fin_map_key

app.secret_key = os.getenv('SECRET_KEY')

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))  # Convert to integer
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True  # Convert to boolean
app.config['MAIL_USE_SSL'] = False  # Convert to boolean

mail = Mail(app)

mongo = PyMongo(app)

openai.api_key = openai_api_key

def is_password_strong(password):
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    if not re.search("[_@$!%*?&]", password):
        return False
    return True

@app.route('/')
def home():
    return render_template('home.html')

bcrypt = Bcrypt(app)

@app.route('/check-availability')
def check_availability():
    type = request.args.get('type')
    value = request.args.get('value')

    if type == "username":
        existing_user = mongo.db.users.find_one({'username': value})
        return jsonify({'exists': bool(existing_user)})
    elif type == "email":
        existing_email = mongo.db.users.find_one({'email': value})
        return jsonify({'exists': bool(existing_email)})

    return jsonify({'exists': False})

@app.route('/flash-message')
def flash_message():
    message = request.args.get('message')
    if message:
        flash(message)
    return '', 204  # Return an empty response with a 204 status code

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        # Username and password validations
        if not (4 <= len(username) <= 12):
            flash('Username must be between 4 and 12 characters long.')
            return redirect(url_for('register'))
        if not is_password_strong(password):
            flash("Password must be at least 8 characters long and include lowercase, uppercase, numbers, and special characters.")
            return redirect(url_for('register'))
        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('register'))

        # Check for existing user or email
        if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
            flash('Username or Email already exists.')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        verification_token = str(uuid.uuid4())
        mongo.db.users.insert_one({'username': username, 'email': email, 'password': hashed_password, 'verification_token': verification_token, 'is_verified': False})

        verification_url = url_for('verify_email', token=verification_token, _external=True)
        msg = Message("Verify your email", sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Please click on the link to verify your email: {verification_url}"
        mail.send(msg)

        flash('A verification email has been sent. Please check your inbox.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/verify-email/<token>')
def verify_email(token):
    user = mongo.db.users.find_one({'verification_token': token})
    if user:
        mongo.db.users.update_one({'_id': user['_id']}, {'$set': {'is_verified': True}})
        flash('Your account has been verified. You may now login.')
        return redirect(url_for('login'))
    else:
        flash('Verification link is invalid or has expired.')
        return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = mongo.db.users.find_one({'username': username})
        if user and bcrypt.check_password_hash(user['password'], password):
            if not user.get('is_verified', False):
                flash('Your account is not verified. Please check your email to verify your account.', 'error')
                return render_template('login.html', username=username)
            
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            return render_template('login.html', username=username)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove the username from session
    return redirect(url_for('home'))

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    data = request.get_json()
    username = data.get('username')
    user = mongo.db.users.find_one({'username': username})
    if user and not user.get('is_verified', False):
        verification_token = str(uuid.uuid4())
        mongo.db.users.update_one({'_id': user['_id']}, {'$set': {'verification_token': verification_token}})
        
        verification_url = url_for('verify_email', token=verification_token, _external=True)
        msg = Message("Verify your email", sender=app.config['MAIL_USERNAME'], recipients=[user['email']])
        msg.body = f"Please click on the link to verify your email: {verification_url}"
        mail.send(msg)

        return jsonify({'message': 'Verification email resent. Please check your inbox.'})
    return jsonify({'message': 'Unable to resend verification email.'})

@app.route('/article_scraper', methods=['GET', 'POST'])
def article_scraper():
    summary = ""
    if request.method == 'POST':
        article_url = request.form.get('article_url')
        if article_url:
            existing_article = mongo.db.scraped_articles.find_one({'url': article_url})
            if existing_article:
                flash('Article already scraped. Using existing content.', 'info')
                article_text = existing_article['content']
            else:
                try:
                    article_text = scrape_msnbc_article(article_url)
                    mongo.db.scraped_articles.insert_one({'url': article_url, 'content': article_text})
                    flash('Article successfully scraped and stored.', 'info')
                except Exception as e:
                    flash(f'An error occurred while scraping: {str(e)}', 'error')
                    return render_template('article_scraper.html', summary=summary)

            # Generate summary
            summary = generate_summary(article_text)
        else:
            flash('No URL provided.', 'error')

    return render_template('article_scraper.html', summary=summary)

def scrape_msnbc_article(url):
    # Set up Selenium to work with headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize the webdriver with the specified options
    with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) as driver:
        driver.get(url)

        # Use BeautifulSoup to parse the page source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        article_content = soup.find_all('p')

        # Collect the text of each paragraph
        article_text = ''
        for p in article_content:
            # Add your logic to filter out unwanted text
            # For example, skipping empty paragraphs or specific elements
            if p.text.strip():
                article_text += p.get_text() + ' '

    return article_text.strip()

model_name = "facebook/bart-large-cnn"
model = BartForConditionalGeneration.from_pretrained(model_name)
tokenizer = BartTokenizer.from_pretrained(model_name)

def generate_summary(article):
    model.eval()
    inputs = tokenizer.encode("summarize: " + article, return_tensors="pt", max_length=1024, truncation=True)
    outputs = model.generate(inputs, max_length=200)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"Generated Summary: {summary}")  # Log the summary for debugging
    return summary

@app.route('/history-of-stocks')
def history_of_stocks():
    return render_template('history-of-stocks.html')

@app.route('/glossary')
def glossary():
    return render_template('glossary.html')

@app.route('/educational-resources')
def educational_resources():
    return render_template('educational-resources.html')

@app.route('/user-feedback-and-review', methods=['GET', 'POST'])
def user_feedback_and_review():
    if request.method == 'POST':
        user_name = request.form.get('userName')
        user_email = request.form.get('userEmail')
        feedback_content = request.form.get('userFeedback')
        
        feedback_data = {
            'user_name': user_name,
            'user_email': user_email,
            'feedback': feedback_content
        }
        mongo.db.feedback.insert_one(feedback_data)

        return redirect(url_for('feedback_thank_you'))

    return render_template('user-feedback-and-review.html') # Display the feedback form for GET requests

@app.route('/feedback-thank-you')
def feedback_thank_you():
    return render_template('feedback-thank-you.html') 

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        user_message = request.json.get('user_message')
        print(f"Received message: {user_message}")  # Debugging

        if 'conversation_history' not in session:
            print("Initializing new session.")  # Debugging
            session['conversation_history'] = ""

        print(f"Previous conversation history: {session['conversation_history']}")  # Debugging

        session['conversation_history'] += f"User: {user_message}\n"

        # Prepare the prompt for OpenAI API
        prompt = session['conversation_history'] + "Chatbot:"
        print(f"Sending prompt to API: {prompt}")  # Debugging

        response = openai.Completion.create(
            engine="text-davinci-003",  # or another appropriate model
            prompt=prompt,
            max_tokens=50,
            temperature=0.7,  # Adjust as needed
            stop=["User:", "Chatbot:"]
        )

        chatbot_response = response.choices[0].text.strip()
        session['conversation_history'] += f"Chatbot: {chatbot_response}\n"

        print(f"Chatbot response: {chatbot_response}")  # Debugging

        return jsonify({'chatbot_response': chatbot_response})

    return render_template('chatbot.html')

def fetch_stock_data(ticker_symbol, start_date, end_date):
    stock_data = yf.download(ticker_symbol, start=start_date, end=end_date)
    stock_data = stock_data[['Open', 'High', 'Low', 'Close', 'Volume']]
    df_main = stock_data.iloc[:-4]
    df_future = stock_data.iloc[-5:]

    # Create a Plotly candlestick chart
    candlestick_chart = go.Figure(data=[go.Candlestick(x=df_main.index,
                                                       open=df_main['Open'],
                                                       high=df_main['High'],
                                                       low=df_main['Low'],
                                                       close=df_main['Close'])])
    candlestick_chart.update_layout(title=f'Candlestick Chart for {ticker_symbol}')
    
    return df_main, df_future, candlestick_chart

def get_ticker_symbol(company_name, api_key):
    url = f'https://financialmodelingprep.com/api/v3/search?query={company_name}&limit=1&exchange=NASDAQ&apikey={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data:
            return data[0]['symbol']  # Assuming the first result is the most relevant
    return None

@app.route('/interactive-analysis', methods=['GET', 'POST'])
def interactive_analysis():
    candlestick_chart = None
    api_key = fin_map_key

    if request.method == 'POST':
        input_value = request.form.get('company_name').strip()

        # Convert company name to ticker symbol using FMP API
        ticker_symbol = get_ticker_symbol(input_value, api_key)
        if ticker_symbol is None:
            flash('Unable to find ticker for the given company name.', 'error')
            return render_template("interactive-analysis.html", candlestick_chart=None)

        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=180)
        try:
            df_main, _, candlestick_chart = fetch_stock_data(ticker_symbol, start_date, end_date)
        except Exception as e:
            flash(f'Error fetching data for {ticker_symbol}: {str(e)}', 'error')

    return render_template("interactive-analysis.html", candlestick_chart=candlestick_chart)

@app.route('/session_clear')
def session_clear():
    session.clear()
    flash('Session has been cleared.')
    return redirect(url_for('home'))

if __name__ == "__main__":
    #db.create_all()  # This will create the required tables in the database.
    app.run(debug=True, port=3000)
