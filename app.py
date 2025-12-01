import os
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile'},
)

github = oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

@app.route('/')
def home():
    return render_template("index.html", user=session.get("user"))

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

# ---------------- GOOGLE LOGIN ----------------
@app.route('/login/google')
def login_google():
    return google.authorize_redirect(
        'https://dimensia-81ua.onrender.com/login/google/callback'
    )

@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        print("TOKEN:", token)
        user_info = google.get('userinfo').json()
        print("USER:", user_info)
        session['user'] = user_info
        return redirect('/dashboard')
    except Exception as e:
        return f"Google Login Failed: {e}"

# ---------------- GITHUB LOGIN ----------------
@app.route('/login/github')
def login_github():
    return github.authorize_redirect(
        'https://dimensia-81ua.onrender.com/login/github/callback'
    )

@app.route('/login/github/callback')
def github_callback():
    try:
        token = github.authorize_access_token()
        user_info = github.get('user').json()
        session['user'] = user_info
        return redirect('/dashboard')
    except Exception as e:
        return f"GitHub Login Failed: {e}"

if __name__ == "__main__":
    app.run()
