#################################################
#                  ZID: z5360043                #   
#################################################
#                                               #
#               The Trader's Den                #
# A flask web application to provide traders    #
# with the tools to dig into social media stock #
# trends without having to manually do it       #
# themselves.                                   #
# Main APIS used:                               #                                               
# - PRAW  (reddit API wrapper)                  #
# - Plotly (graph/ tracing)                     #
# - Pandas (for getting the stock graph data pt)#                                             
# - yfinace (for stock market data)             #
#                                               #
#        The Code Structure (in this order)     #
#                                               #
#  1. CONSISTENT HASHING                        #
#  2. API STUFF                                 #
#  3. FORMS (used wtforms)                      #
#  4. FUNCTIONS                                 #
#  5. ROUTES AND CODE                           #       
#                                               #
#################################################

import os
import sys
import json
import praw  
import math
import datetime
import yfinance
import plotly.offline as po
import plotly.graph_objs as graphob
from flask_wtf import FlaskForm
from pandas_datareader import data as pr
from plotly.subplots import make_subplots
from wtforms import StringField, SubmitField, IntegerField, PasswordField
from flask import Flask, render_template, request, Markup, redirect, url_for, session

################################################
#             CONSISTENT HASHING               #
################################################

# Explicitely copied froom user582175's answer 
# https://stackoverflow.com/questions/30585108/disable-hash-randomization-from-within-python-program

# This is to ensure consistent hashing as the .hash method 
# has randomised offset for the hashing for security purposes 
# (This will always set the offset to 0)
hashseed = os.getenv('PYTHONHASHSEED')
if not hashseed:
    os.environ['PYTHONHASHSEED'] = '0'
    os.execv(sys.executable, [sys.executable] + sys.argv)

################################################
#                 API STUFF                    #
################################################

app = Flask(__name__)
MY_ID = 'mErvk0XmhCTXqPBKuv4eoA'
MY_KEY = 'zHwTAo9FAndhV8wFaYSmXPZxPOoJmw'

user = praw.Reddit(
            client_id = MY_ID,
            client_secret = MY_KEY,
            username = 'Projcomp1010',
            password = 'nAS9k9tc*p',
            user_agent = 'user_agent'
        )

app.config['SECRET_KEY'] = "password123"

#################################################


#################################################
#                     FORMS                     #
#################################################

class subreddit_form(FlaskForm): 
    subreddit_name = StringField("Write the subreddit name here")
    subreddit_n_post = IntegerField("Write the number of trending posts you want to see")
    submit_button = SubmitField("Search")

class stock_form(FlaskForm): 
    stock_name = StringField("Write the stock ticker name")
    submit_button = SubmitField("Search")

class login_f(FlaskForm):
    username = StringField("Username")
    password = PasswordField("Password")
    login_button = SubmitField("Login")

class sign_up(FlaskForm):
    username = StringField("Username")
    password = PasswordField("Password")
    submit_button = SubmitField("Sign Up")

#################################################


#################################################
#                  FUNCTIONS                    #
#################################################


# Calls pandas API to get stock graph data from yahoo
# All the tracing and graph styling was done with plotly
def get_stock_chart(ticker):

    # Timeframe for stock chart
    end = datetime.datetime.now()
    start = datetime.datetime(2018,1,1)

    # Call pandas API to get stock ticker pandas item
    graph = pr.get_data_yahoo(ticker, start, end)

    # Add volume subpgraph
    chart = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.3, 
                            subplot_titles=(ticker, 'Volume'), row_width=[0.3,0.8])

    # Add candlestick trace and stock information trace
    chart.add_trace(graphob.Candlestick(x=graph.index, open=graph['Open'], 
                                        high=graph['High'], close=graph['Close'], 
                                        low=graph['Low'],  name='Technicals'))
    chart.add_trace(graphob.Bar(x=graph.index, y=graph['Volume'], marker_color='yellow', 
                                showlegend=False), row=2, col=1)

    # Fix style and colouring
    chart.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    chart.update_xaxes(color='rgb(0, 179, 77)')
    chart.update_yaxes(color='rgb(0, 179, 77)')

    # Markup essential to preserve div component of the graph
    return Markup(po.plot(chart, include_plotlyjs=True, output_type='div'))


# Collects the top n-posts in a given subreddit using the PRAW API
def collect_top_posts(subreddit_name, n_post):
    current_subreddit = user.subreddit(subreddit_name)
    hot_post = current_subreddit.hot(limit=n_post)
    display = {}

    # Loop through submissions and add them to the display dictionary with respective link
    i = 1
    for submission in hot_post:
        string = str(i)+'. '+submission.title
        display[string] = "https://www.reddit.com" + submission.permalink
        i += 1

    return display


# Parses the comments to find the number of mentions for a given ticker using PRAW
def comment_parse(ticker):
    current_subreddit = user.subreddit('wallstreetbets')
    new_posts = current_subreddit.hot(limit=3)

    # Since comments on reddit are basically a tree, we'd normally have to 
    # DFS to read all, but PRAW has provided a .list() function which facilitates
    # that.
    # This loops through each post on the hot page and parses full strings of comments
    # to calculate how many mentions of a stock there are.
    occurances = 0
    for post in new_posts:
        post.comments.replace_more(limit=0)            # <---  This method was taken from 
        for single_comment in post.comments.list():    # https://praw.readthedocs.io/en/stable/tutorials/comments.html
            comment_body = single_comment.body
            string_list = comment_body.split()
            for word in string_list:
                if (ticker.lower() == word.lower()):
                    occurances += 1

    return occurances

#################################################


#################################################
#              ROUTES AND CODE                  #
#################################################

# Login Page
@app.route('/', methods=["GET", "POST"])
def welcome():
    error_message = "Wrong username or password"
    login_form = login_f()

    # Handles all logic to avoid logging into random accounts
    # The database format chosen was a jason file as no complex
    # structure is required
    if request.method == 'POST':
        f = open("database.json", "r")
        # Attemps to retreive data from database, if fail throw error
        try:
            data = json.loads(f.read())
        except:
            f.close()
            return render_template("login.html",form = login_form, error_msg = error_message)

        # If the username exist check for password
        if request.form['username'] in data:
            if data[request.form['username']] == hash(request.form['password']):
                f.close()
                return redirect(url_for('main'))
            else:   # If wrong password
                f.close()
                return render_template("login.html",form = login_form, error_msg = error_message)
        else:
            f.close()
            return render_template("login.html",form = login_form, error_msg = error_message)

    return render_template("login.html",form = login_form, error_msg ="")


# Signup page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    signup_form = sign_up() 

    # Handles cases where username is already taken or corrupted database
    if request.method == 'POST':
        error_msg = "Taken username"
        f = open("database.json", "r")

        # If database empty fill it up (It shouldn't since there is admin)
        try:
            data = json.loads(f.read())
        except:
            f.close()
            f = open("database.json", "w")
            data = {}
            f.write(json.dumps(data))
            f.close()
        f = open("database.json", "r")
        data = json.loads(f.read())
        f.close()

        # Username taken
        if request.form['username'] in data:
            return render_template('signup.html', signup = signup_form, error = error_msg)

        # Register new pass and username
        f = open("database.json", "w")
        data[request.form['username']] = hash(request.form['password'])
        f.write(json.dumps(data))
        f.close()

        return redirect(url_for('main'))
        
        
    return  render_template('signup.html', signup = signup_form, error = "")


# Subreddit search page
@app.route('/main', methods=["GET", "POST"])
def main():
    subreddit_f = subreddit_form()
    if request.method == 'POST':
        return render_template('main_page.html', sub_form=subreddit_f, error="Invalid subreddit or number")
    return render_template('main_page.html', sub_form=subreddit_f, error="")

# Stock search page
@app.route('/main-stock', methods=["GET", "POST"])
def main_stock():
    stock_f = stock_form()
    if request.method == 'POST':
        return render_template('main_page_stock.html', stock_form= stock_f, error="Invalid stock ticker")
    
    return render_template('main_page_stock.html', stock_form= stock_f, error="")

# Subreddit search results page
@app.route('/subreddit', methods=["GET", "POST"])
def subreddit_page():
    subreddit = request.form.get('subreddit_name')
    n_post = request.form.get('subreddit_n_post')

    # Handles user input negative number
    check_number = int(n_post)
    if check_number < 0:
        return redirect(url_for('main'), code=307)

    try:
        display = collect_top_posts(subreddit, int(n_post))
    except:
        return redirect(url_for('main'), code=307)

    # Color table for the subreddit listing (green to black shade reversely connected)
    color_list = ['#007500;', '#007000;', '#006600;', 
                  '#006100;', '#005c00;', '#005200;', 
                  '#004d00;', '#004700;', '#003d00;', 
                  '#003800;', '#003300;', '#002900;', 
                  '#002400;', '#001f00;', '#001400;']
    num_entry = len(display)
    multiplicative_factor = math.ceil(num_entry / len(color_list)) 

    # Reverse the color_list and add it to itself to create a feeling
    # of color connection between each 12 entry interval 
    i = 0
    final_color_list = []
    final_color_list.append(color_list)
    while(i < multiplicative_factor):
        color_list.reverse()
        final_color_list = final_color_list + color_list
        i += 1

    return render_template('subreddit.html', title=subreddit, display_list=display, n=n_post, color_l=final_color_list)


# Stock search information page
@app.route('/stock', methods=["GET", "POST"])
def stock_page():
    ticker = request.form.get('stock_name').upper()

    # Get market data for ticker from yfinance API
    try:
        ticker_info = yfinance.Ticker(ticker)    
        info = ticker_info.info
    except:
        return redirect(url_for('main-stock'), code=307)

    # Caching ticker for speed optimization
    try:
        if ticker not in session:
            occurance = str(comment_parse(ticker))
            session[ticker] = occurance
        else:
            occurance = session[ticker]
    except:
        return redirect(url_for('main-stock'), code=307)

    # Generates the div stock chart    
    try:
        stock_graph = get_stock_chart(ticker)
    except:
        return redirect(url_for('main_stock'), code=307)
    
    return render_template('stock.html', bar_chart_1=stock_graph, stock_name=ticker, information=info, occ=occurance)

# FAQ page
@app.route('/faq', methods=["GET", "POST"])
def faq_page():
    return render_template('faq.html')

if __name__ == "__main__":
    app.run(debug=True)



######################## END ###########################