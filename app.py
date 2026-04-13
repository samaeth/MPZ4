from flask import Flask, render_template, request, session, redirect, url_for, flash, get_flashed_messages, g
from flask_bcrypt import Bcrypt 
from forms import SignUpForm, LoginForm
import requests
import psycopg2
import psycopg2.extras
from urllib.parse import quote_plus

app = Flask(__name__)

API_KEY = '9363b0c3'
app.secret_key = 'a48a928d5a9f35f11114bba8'
password = quote_plus('Yvl_S@m@el25')
DATABASE_URL = f'postgresql://postgres:{password}@db.jpgomwjymnfqrnyhuafv.supabase.co:5432/postgres'
print(DATABASE_URL)
bcrypt = Bcrypt(app)

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL, sslmode='require')
        g.db.cursor_factory = psycopg2.extras.DictCursor
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    movie = None
    title_to_search = None

    if request.method == 'GET':
        title_to_search = request.args.get("title")

    if request.method == 'POST':
        title_to_search = request.form.get('movie') 

    if title_to_search:
        url = f'http://www.omdbapi.com/?t={title_to_search}&plot=full&apikey={API_KEY}'
        response = requests.get(url)
        movie = response.json()

        if movie.get("Response") == "True":
            if "recent" not in session:
                session['recent'] = []

            session['recent'] = [m for m in session['recent'] if m["title"] != movie.get("Title")]

            session["recent"].insert(0, {
                "title": movie.get("Title"),
                "poster": movie.get("Poster")
            })
            session["recent"] = session["recent"][:5] 


    return render_template('home.html', movie=movie, recent=session.get("recent", []), messages=get_flashed_messages(with_categories=True))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        username = form.username.data
        email_address = form.email_address.data
        password_hash = bcrypt.generate_password_hash(form.password1.data).decode('utf-8')
        
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash, email_address) VALUES (%s, %s, %s)",
                (username, password_hash, email_address)
            )
            conn.commit()

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Account created! Welcome to MPz4.', category='success')
            return redirect(url_for('home'))

        except Exception as e:
            flash('Sign up is unavailable on the live demo. Run locally to test auth.', category='danger')
            return redirect(url_for('home'))

    if form.errors:
        for err in form.errors.values():
            flash(err, category='danger')

    return render_template('signup.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', category='success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', category='danger')

    if form.errors:
        for err in form.errors.values():
            flash(err, category='danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', category='success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)