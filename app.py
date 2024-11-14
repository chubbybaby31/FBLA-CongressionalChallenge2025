from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html', current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route('/about')
def about():
    return 'This is a basic Flask application.'

if __name__ == '__main__':
    app.run(debug=True)