import os
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
# Reading from environment variables for security (Render)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# This allows OAuth to run unsecured locally (on http://127.0.0.1)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

oauth = OAuth(app)

# ---------------- OAUTH SETUP ----------------
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

# --- EMAIL FUNCTION (For Login/Registration Confirmation) ---
def send_login_notification(client_email, client_name):
    """Sends an email TO THE CLIENT confirming their login/registration."""
    
    if not client_email or "@" not in client_email: return

    subject = "Welcome to DIMENSIA | Access Granted"
    body = f"Hello {client_name},\n\nThis is a confirmation that your access to the DIMENSIA Network has been granted."
    
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = os.environ.get("SENDER_EMAIL")
    msg['To'] = client_email
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD"))
        server.sendmail(os.environ.get("SENDER_EMAIL"), client_email, msg.as_string())
        server.quit()
        print(f"✅ Login Notification sent to: {client_email}")
    except Exception as e:
        print(f"❌ Email failed: {e}")

# ---------------- CORE WEBSITE ROUTES (ALL PAGES ADDED) ----------------
@app.route('/')
def home():
    return render_template("index.html", user=session.get("user"))

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/services')
def services():
    return render_template("services.html")

@app.route('/team')
def team():
    return render_template("team.html")

@app.route('/socials')
def socials():
    return render_template("socials.html")

@app.route('/register')
def register():
    return render_template("register.html")

@app.route('/dashboard')
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")


# ---------------- GOOGLE LOGIN (FIXED REDIRECT) ----------------
@app.route('/login/google')
def login_google():
    # Use request.url_root to dynamically get HTTPS/HTTP and domain
    # This fixes the Internal Server Error on Render deployment
    callback_url = request.url_root.replace('http://', 'https://') + 'login/google/callback'
    
    # Authorize Redirect now uses the dynamically generated HTTPS URL
    return google.authorize_redirect(callback_url)

@app.route('/login/google/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = google.get('userinfo').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('name'))
        return redirect('/dashboard')
    except Exception as e:
        # Returning a clear error message here helps debugging the Google Console setup
        return f"Google Login Failed (Check Google Console Redirect URIs): {e}"

# ---------------- GITHUB LOGIN (FIXED REDIRECT) ----------------
@app.route('/login/github')
def login_github():
    # Use request.url_root for dynamic HTTPS/HTTP and domain
    callback_url = request.url_root.replace('http://', 'https://') + 'login/github/callback'
    
    # Authorize Redirect now uses the dynamically generated HTTPS URL
    return github.authorize_redirect(callback_url)

@app.route('/login/github/callback')
def github_callback():
    try:
        token = github.authorize_access_token()
        user_info = github.get('user').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('login'))
        return redirect('/dashboard')
    except Exception as e:
        # Returning a clear error message here helps debugging the GitHub Console setup
        return f"GitHub Login Failed (Check GitHub Console Redirect URIs): {e}"

# ---------------- CONTACT FORM LOGIC ----------------
@app.route('/send_email', methods=['POST'])
def send_email():
    name = request.form.get('name')
    client_email = request.form.get('email')
    message = request.form.get('message')

    # 1. Admin Notification
    msg_admin = MIMEMultipart()
    msg_admin['Subject'] = f"New Inquiry from {name}"
    msg_admin['From'] = os.environ.get("SENDER_EMAIL")
    msg_admin['To'] = os.environ.get("RECEIVER_EMAIL")
    msg_admin.attach(MIMEText(f"Name: {name}\nEmail: {client_email}\nMsg: {message}", 'plain'))

    # 2. Client Confirmation
    msg_client = MIMEMultipart()
    msg_client['Subject'] = "Thank you for contacting Dimensia"
    msg_client['From'] = os.environ.get("SENDER_EMAIL")
    msg_client['To'] = client_email
    msg_client.attach(MIMEText(f"Dear {name},\n\nThank you for contacting Dimensia Freelancing. We received your inquiry and will review it shortly.", 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(os.environ.get("SENDER_EMAIL"), os.environ.get("APP_PASSWORD"))
        server.sendmail(os.environ.get("SENDER_EMAIL"), os.environ.get("RECEIVER_EMAIL"), msg_admin.as_string())  # To Admin
        server.sendmail(os.environ.get("SENDER_EMAIL"), client_email, msg_client.as_string())  # To Client
        server.quit()
        return redirect('/')
    except Exception as e: return f"Error sending email: {e}"


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')