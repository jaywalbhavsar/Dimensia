import os
import threading
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import requests, json  # required for SendGrid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key_for_local_dev")

# --- 1. SMART CONFIGURATION ---
if 'RENDER' in os.environ:
    BASE_URL = "https://dimensia-81ua.onrender.com"
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0'
else:
    BASE_URL = "http://127.0.0.1:5000"
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Load Keys from Environment
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "jaywal2509@gmail.com")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

# --- 2. OAUTH SETUP ---
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

# --- 3. EMAIL LOGIC (SendGrid final) ---
def send_email_notification(subject, body, recipient):
    def send():
        if not SENDGRID_API_KEY:
            print("❌ ERROR: SENDGRID_API_KEY missing")
            return

        if not recipient:
            print("❌ ERROR: Email recipient missing")
            return

        data = {
            "personalizations": [{
                "to": [{"email": recipient}],
                "subject": subject
            }],
            "from": {"email": SENDER_EMAIL},
            "content": [{"type": "text/plain", "value": body}]
        }

        r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps(data)
        )
        print("📨 SENDGRID RESPONSE:", r.status_code, r.text)

    threading.Thread(target=send).start()

# --- 4. ROUTES ---
@app.route('/')
def home(): return render_template('index.html', user=session.get('user'))

@app.route('/services')
def services(): return render_template('services.html')

@app.route('/team')
def team(): return render_template('team.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/login')
def login(): return render_template('login.html')

@app.route('/register')
def register(): return render_template('register.html')

@app.route('/socials')
def socials(): return render_template('socials.html')

@app.route('/dashboard')
def dashboard():
    if "user" not in session: return redirect("/login")
    return render_template('dashboard.html', user=session['user'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- 5. LOGIN FLOWS ---

# GOOGLE LOGIN — unchanged (works)
@app.route('/login/google')
def google_login():
    redirect_uri = f"{BASE_URL}/login/google/callback"
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        session['user'] = user_info

        send_email_notification(
            "Welcome to Dimensia",
            f"Hello {user_info['name']}, welcome to Dimensia!",
            user_info['email']
        )
        return redirect('/dashboard')
    except Exception as e:
        return f"Google Login Error: {e}"

# ✔✔✔ GITHUB LOGIN — FINAL FIX ✔✔✔
@app.route('/login/github')
def github_login():
    redirect_uri = f"{BASE_URL}/login/github/callback"
    return github.authorize_redirect(redirect_uri)

@app.route('/login/github/callback')
def github_callback():
    try:
        token = github.authorize_access_token()

        # Get basic user info
        user_info = github.get('user').json()

        # Request email list
        emails = github.get('user/emails').json()

        primary_email = None
        for e in emails:
            if e.get("primary"):
                primary_email = e.get("email")

        email = primary_email or user_info.get('email')
        print("🔥 GITHUB RESOLVED EMAIL =", email)

        session['user'] = user_info

        if email:
            send_email_notification(
                "Welcome to Dimensia",
                f"Hello {user_info['login']}, welcome to Dimensia!",
                email
            )
        else:
            print("⚠️ WARNING: GitHub returned NO email")

        return redirect('/dashboard')
    except Exception as e:
        return f"GitHub Login Error: {e}"

# --- 6. CONTACT FORM ---
@app.route('/send_email', methods=['POST'])
def handle_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    send_email_notification(
        f"New Client: {name}",
        f"Name: {name}\nEmail: {email}\nMessage: {message}",
        SENDER_EMAIL
    )
    send_email_notification(
        "We received your message",
        f"Dear {name},\n\nThank you for contacting us!\n\n— Dimensia Team",
        email
    )
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
