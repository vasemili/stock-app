from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_pymongo import PyMongo
import plotly.graph_objs as go
import yfinance as yf
import datetime
import os
import openai
from dotenv import load_dotenv
load_dotenv()

# Access environment variables

app = Flask(__name__, static_folder="../public", template_folder="../templates")

openai_api_key = os.getenv('OpenAI_key')
mongodb_uri = os.getenv('MongoDB_URI')

# MongoDB Configuration
app.config['OPENAI_API_KEY'] = openai_api_key

app.config['MONGO_URI'] = mongodb_uri

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

@app.route('/interactive-analysis')
def interactive_analysis():
    companies = ["NVDA", "TSLA", "FDX", "ABNB", "AAPL", "GOOG", "ORCL", "IBM", "MSFT"]
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=180)
    all_candlestick_charts = {}

    for company in companies:
        df_main, _, candlestick_chart = fetch_stock_data(company, start_date, end_date)
        all_candlestick_charts[company] = candlestick_chart

    return render_template("interactive-analysis.html", candlestick_charts=all_candlestick_charts)

if __name__ == "__main__":
    db.create_all()  # This will create the required tables in the database.
    app.run(debug=True)
