from flask import Flask, render_template, request, session, redirect, url_for, flash, get_flashed_messages, g
from flask_bcrypt import Bcrypt 
from forms import SignUpForm, LoginForm, ForgotPasswordForm, ResetPasswordForm
import requests
import psycopg2
import psycopg2.extras
from urllib.parse import quote_plus
import secrets
from datetime import datetime, timedelta
from flask_mail import Mail, Message


app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

API_KEY = '9363b0c3'
TRAILER_API_KEY = 'c6c5b0e4790ec22c3baaf45460b1019b'
app.secret_key = 'a48a928d5a9f35f11114bba8'
password = quote_plus('Yvl_S@m@el25')
DATABASE_URL = os.environ.get('DATABASE_URL')
print(DATABASE_URL)
bcrypt = Bcrypt(app)
mail = Mail(app)


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

def get_trailer(title):
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={TRAILER_API_KEY}&query={title}'
    search_res = requests.get(search_url).json()
    
    results = search_res.get('results', [])
    if not results:
        return None
    
    movie_id = results[0]['id']
    
    videos_url = f'https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TRAILER_API_KEY}'
    videos_res = requests.get(videos_url).json()
    
    for video in videos_res.get('results', []):
        if video['type'] == 'Trailer' and video['site'] == 'YouTube':
            return video['key']
    return None

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    movie = None
    title_to_search = None
    alt = []
    trailer_key = None

    if request.method == 'GET':
        title_to_search = request.args.get("title")

    if request.method == 'POST':
        title_to_search = request.form.get('movie') 

    if title_to_search:
        url = f'https://www.omdbapi.com/?t={title_to_search}&plot=short&apikey={API_KEY}'
        response = requests.get(url)
        movie = response.json()
        
        data_url= f'https://www.omdbapi.com/?s={title_to_search}&apikey={API_KEY}'
        data_response = requests.get(data_url)
        data = data_response.json()
        
        trailer_key = None
        if movie.get("Response") == "True":
            trailer_key = get_trailer(title_to_search)
        
        alt = []
        
        if data.get("Response") == "True":
            for item in data.get("Search", []):
                alt.append({
                    "title": item.get("Title"),
                    "poster": item.get("Poster")
                })


        if movie.get("Response") == "True":
            if "recent" not in session:
                session['recent'] = []

            session['recent'] = [m for m in session['recent'] if m["title"] != movie.get("Title")]

            session["recent"].insert(0, {
                "title": movie.get("Title"),
                "poster": movie.get("Poster")
            })
            session["recent"] = session["recent"][:5] 


    return render_template('home.html', movie=movie, recent=session.get("recent", []), messages=get_flashed_messages(with_categories=True), alt=alt, trailer_key=trailer_key)

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
                "INSERT INTO Users (username, password_hash, email_address) VALUES (%s, %s, %s)",
                (username, password_hash, email_address)
            )
            conn.commit()

            cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
            user = cursor.fetchone()
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Account created!', category='success')
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
        cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
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

@app.route('/fullplot')
def fullplot():
    title = request.args.get('title')
    url = f'https://www.omdbapi.com/?t={title}&plot=full&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data.get('Plot', '')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
        form = ForgotPasswordForm()
        if form.validate_on_submit():
            email_address = form.email_address.data
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM USERS where email_address = %s ', (email_address,))
            user = cursor.fetchone()
            
            if user:
                token = secrets.token_urlsafe(32)
                expiry = datetime.now() + timedelta(hours=1)
                
                cursor.execute(
                    "Update users set reset_token = %s, reset_token_expiry = %s where email_address = %s",(token, expiry, email_address)
                )
                db.commit()
                
                reset_link = (url_for('reset_password', token=token, _external=True))
                
                msg = Message(
                    subject = 'MPz4 Password Reset',
                    sender = app.config['MAIL_USERNAME'],
                    recipients=[email_address],
                )
                msg.html = f""" Click the button below to reset your password for MPz4. If you did not request this, please ignore this email.
                <html>
                    <body style="font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px 20px; margin: 0;">
                        <div style="max-width: 500px; margin: 0 auto;">
                            <div style="text-align: center; background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); backdrop-filter: blur(10px);">
                                <h2 style="margin-bottom: 20px;">MPz4 Password Reset</h2>
                                <a href="{reset_link}" style="background: #119da4; color: white; padding: 10px 18px; border-radius: 8px; text-decoration: none; cursor: pointer; display: inline-block; transition: 0.2s; font-weight: bold; margin: 0 auto 20px auto;">Reset Password</a> <br>
                                <p style="margin: 0; font-size: 12px; color: #94a3b8;">This link expires in 1 hour</p>
                            </div>
                        </div>
                    </body>
                </html>
                """
                mail.send(msg)
                
                flash('Password reset link sent to your email.', category='success')
                return redirect(url_for('login'))
        
        return render_template('forgot-password.html', form=form, messages=get_flashed_messages(with_categories=True))
        
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        password1 = form.password1.data
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
                    "SELECT * FROM users WHERE reset_token = %s AND reset_token_expiry > %s", 
                    (token, datetime.now())
                    )
        user = cursor.fetchone()
        
        if not user:
            flash('Invalid or expired link.', category = 'danger')
            return redirect(url_for('forgot_password'))

        password_hash = bcrypt.generate_password_hash(password1).decode('utf-8')
        
        cursor.execute(
            "Update users set password_hash = %s , reset_token = NULL, reset_token_expiry = NULL where reset_token = %s",
            (password_hash, token)
        )
        db.commit()
        
        flash('Password reset successful! You can now log in.', category='success')
        return redirect(url_for('login'))
    return render_template('reset-password.html', form=form, token=token, messages=get_flashed_messages(with_categories=True))
if __name__ == '__main__':
    app.run(debug=True)
