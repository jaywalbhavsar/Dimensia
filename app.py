import os
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- 1. CONFIGURATION (READING SECRETS FROM ENVIRONMENT) ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL")

# --- 2. EMAIL FUNCTIONS ---
def send_login_notification(client_email, client_name):
    if not client_email or "@" not in client_email:
        return

    subject = "Welcome to DIMENSIA | Access Granted"
    body = f"Hello {client_name},\n\nYour access to the DIMENSIA Network has been granted.\n\n— DIMENSIA SYSTEMS"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = client_email
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, client_email, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"❌ Email failed: {e}")

# --- 3. OAUTH SETUP ---
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
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# --- 4. ROUTES ---
@app.route('/')
def home(): return render_template('index.html', user=session.get('user'))
@app.route('/team')
def team(): return render_template('team.html')
@app.route('/services')
def services(): return render_template('services.html')
@app.route('/contact')
def contact(): return render_template('contact.html')
@app.route('/login')
def login(): return render_template('login.html')
@app.route('/register')
def register(): return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user: return redirect('/login')
    if 'name' not in user: user['name'] = user.get('email', 'Agent')
    return render_template('dashboard.html', user=user)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

# --- 5. GOOGLE LOGIN START ---
@app.route('/login/google')
def login_google():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

# --- 6. GITHUB LOGIN START ---
@app.route('/login/github')
def login_github():
    redirect_uri = url_for('github_callback', _external=True)
    return github.authorize_redirect(redirect_uri)

# --- 7. CONTACT FORM LOGIC ---
@app.route('/send_email', methods=['POST'])
def send_email():
    name = request.form.get('name')
    client_email = request.form.get('email')
    message = request.form.get('message')

    msg_admin = MIMEMultipart()
    msg_admin['Subject'] = f"New Inquiry from {name}"
    msg_admin['From'] = SENDER_EMAIL
    msg_admin['To'] = RECEIVER_EMAIL
    msg_admin.attach(MIMEText(f"Name: {name}\nEmail: {client_email}\nMsg: {message}", 'plain'))

    msg_client = MIMEMultipart()
    msg_client['Subject'] = "Thank you for contacting Dimensia"
    msg_client['From'] = SENDER_EMAIL
    msg_client['To'] = client_email
    msg_client.attach(MIMEText(
        f"Dear {name},\n\nThank you for contacting Dimensia Freelancing. We received your inquiry.",
        'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg_admin.as_string())
        server.sendmail(SENDER_EMAIL, client_email, msg_client.as_string())
        server.quit()
        return redirect('/')
    except Exception as e:
        return f"Error sending email: {e}"

# --- 8. GOOGLE CALLBACK ---
@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('name'))
        return redirect('/dashboard')
    except Exception as e:
        return f"Google Login Failed: {e}"

# --- 9. GITHUB CALLBACK ---
@app.route('/login/github/callback')
def github_callback():
    try:
        token = github.authorize_access_token()
        user_info = github.get('user').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('login'))
        return redirect('/dashboard')
    except Exception as e:
        return f"GitHub Login Failed: {e}"

# --- 10. REMOVE localhost RUN ---
# No app.run() needed for Render – Gunicorn handles it
