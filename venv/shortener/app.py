import flask
from flask import Flask, request, redirect, render_template, url_for, session, flash
import string, random, re
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'
#test2
# Initialize the database
def init_db():
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS urls
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, original_url TEXT, short_url TEXT, user_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    conn.commit()
    conn.close()

def insert_url(original_url, short_url, user_id):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute('INSERT INTO urls (original_url, short_url, user_id) VALUES (?, ?, ?)', (original_url, short_url, user_id))
    conn.commit()
    conn.close()

def get_original_url(short_url):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute('SELECT original_url FROM urls WHERE short_url = ?', (short_url,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0]
    return None

def get_user_by_username(username):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    return result

def create_user(username, password):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

def create_cookie(username):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    new_cookie = "".join(random.choices(string.ascii_letters + string.digits, k=64))
    user_id = get_user_by_username(username)[0]
    c.execute('SELECT * FROM session_id WHERE key = ? OR user_id = ?', (new_cookie, user_id))
    row = c.fetchone()
    if row is not None:
        return row[0]
    c.execute('INSERT INTO session_id (user_id, key) VALUES (?, ?)', (user_id, new_cookie))
    conn.commit()
    return new_cookie


def check_cookie(cookie):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute("SELECT * FROM session_id WHERE key = ?", (cookie,))
    c.fetchone()
    if c.rowcount == 0:
        return False
    return True

def get_user_from_cookie(cookie):
    conn = sqlite3.connect('urls.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM session_id WHERE key = '?'", (cookie,))
    row = c.fetchone()
    if c.rowcount == 0:
        return None
    return row[0]

# Initialize the database
init_db()

# Regex pattern for validating URLs
url_regex = re.compile(
    r'^(https?|ftp)://[^\s/$.?#].[^\s]*$')

def generate_short_url(length=6):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/', methods=['GET', 'POST'])
def index():
    if "session_id" not in request.cookies or not check_cookie(request.cookies["session_id"]):
        return redirect(url_for('login'))

    if request.method == 'POST':
        original_url = request.form['original_url']
        if not re.match(r'^(https?|ftp)://', original_url):
            original_url = 'http://' + original_url
        if not re.match(url_regex, original_url):
            return render_template('index.html', error='Invalid URL. Please enter a valid URL.')
        short_url = generate_short_url()
        insert_url(original_url, short_url, get_user_from_cookie(request.cookies["session_id"]))
        return render_template('index.html', short_url=request.host_url + short_url)
    return render_template('index.html')

@app.route('/<short_url>')
def redirect_url(short_url):
    original_url = get_original_url(short_url)
    if original_url:
        return redirect(original_url)
    else:
        return '<h1>URL not found</h1>', 404

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        if user and check_password_hash(user[2], password):
            response = flask.make_response(redirect(url_for('index')))
            cookie = create_cookie(username)
            print(cookie)
            response.set_cookie("session_id", cookie)
            return response
        else:
            flash('Invalid username or password')

    if "session_id" in request.cookies:
        if check_cookie(request.cookies["session_id"]):
            return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if get_user_by_username(username):
            flash('Username already exists')
        else:
            create_user(username, password)
            flash('Registration successful, please log in', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    response = flask.make_response(redirect(url_for('login')))
    response.set_cookie("session_id", expires=0)
    return response

if __name__ == '__main__':
    app.run(debug=True)
