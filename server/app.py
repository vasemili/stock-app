from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_pymongo import PyMongo
import plotly.graph_objs as go
import yfinance as yf
import datetime
import os
import openai
import requests
from dotenv import load_dotenv
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

mongo = PyMongo(app)

openai.api_key = openai_api_key

@app.route('/')
def home():
    return render_template('home.html')

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

        # Call OpenAI's API to generate a response
        response = openai.Completion.create(
            engine="davinci",
            prompt=f"User: {user_message}\nChatbot:",
            max_tokens=50,  # Adjust as needed
            stop=None  # You can set a list of stop words to limit the response
        )

        chatbot_response = response.choices[0].text.strip()

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

if __name__ == "__main__":
    db.create_all()  # This will create the required tables in the database.
    app.run(debug=True)
