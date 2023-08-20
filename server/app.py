from flask import Flask, render_template

app = Flask(__name__, static_folder="../public", template_folder="../templates")

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

@app.route('/user-feedback-and-review')
def user_feedback_and_review():
    return render_template('user-feedback-and-review.html')

@app.route('/interactive-analysis')
def interactive_analysis():
    return render_template("interactive-analysis.html")

if __name__ == "__main__":
    app.run(debug=True)