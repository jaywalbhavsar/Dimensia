import os
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- CRITICAL FIX: Determine the BASE URL securely ---
# If running on Render, use the secure URL from the environment (or a default).
# If running locally, use the unsecured 127.0.0.1.
if 'RENDER' in os.environ:
    # Use environment variable for the live domain (Render sets this)
    BASE_URL = 'https://' + os.environ.get('RENDER_EXTERNAL_HOSTNAME') 
    # Must explicitly allow unsecured transport during development/local test
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '0' 
else:
    BASE_URL = 'http://127.0.0.1:5000'
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# --- 1. CONFIGURATION (READING SECRETS FROM ENVIRONMENT) ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "701939588182-56qac914ughsp6iolqt5ff2o5tu9inbi.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "Ov23li4gpittcYAUFFkv")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "035226f2ac708cd48afa0767b7a955311e742f97")

# EMAIL CREDENTIALS
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "jaywal2509@gmail.com")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "bsky evfn ysun clyr")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "jaywal2509@gmail.com")

# --- 2. EMAIL FUNCTIONS (UNCHANGED) ---
def send_login_notification(client_email, client_name):
    """Sends an email TO THE CLIENT confirming their login/registration."""
    if not client_email or "@" not in client_email: return
    subject = "Welcome to DIMENSIA | Access Granted"
    body = f"Hello {client_name},\n\nThis is a confirmation that your access to the DIMENSIA Network has been granted."
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
        print(f"✅ Login Notification sent to: {client_email}")
    except Exception as e: print(f"❌ Email failed: {e}")


# --- 3. OAUTH SETUP (DYNAMIC REDIRECTS) ---
oauth = OAuth(app)

google = oauth.register(
    name='google', client_id=GOOGLE_CLIENT_ID, client_secret=GOOGLE_CLIENT_SECRET,
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'email profile'},
    # Use the dynamic BASE_URL for the final redirect
    redirect_uri=BASE_URL + '/login/google/callback'
)
github = oauth.register(
    name='github', client_id=GITHUB_CLIENT_ID, client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
    # Use the dynamic BASE_URL for the final redirect
    redirect_uri=BASE_URL + '/login/github/callback'
)

# --- 4. ROUTES (UNCHANGED) ---
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

# --- 5. CONTACT FORM LOGIC (UNCHANGED) ---
def send_contact_admin_notification(name, client_email, message):
    subject = f"New Inquiry from {name}"; body = f"Name: {name}\nEmail: {client_email}\nMsg: {message}"; msg = MIMEMultipart(); msg['Subject'] = subject; msg['From'] = SENDER_EMAIL; msg['To'] = RECEIVER_EMAIL; msg.attach(MIMEText(body, 'plain')); return msg

def send_contact_client_confirmation(name, client_email):
    subject = "Thank you for contacting Dimensia"; body = f"Dear {name},\n\nThank you for contacting Dimensia Freelancing. We received your inquiry and will review it shortly."; msg = MIMEMultipart(); msg['Subject'] = subject; msg['From'] = SENDER_EMAIL; msg['To'] = client_email; msg.attach(MIMEText(body, 'plain')); return msg

@app.route('/send_email', methods=['POST'])
def send_email():
    name = request.form.get('name')
    client_email = request.form.get('email')
    msg_admin = send_contact_admin_notification(name, client_email, request.form.get('message'))
    msg_client = send_contact_client_confirmation(name, client_email)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(SENDER_EMAIL, APP_PASSWORD);
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg_admin.as_string());
        server.sendmail(SENDER_EMAIL, client_email, msg_client.as_string());
        server.quit();
        return redirect('/')
    except Exception as e: return f"Error sending email: {e}"


# --- 6. OAUTH CALLBACKS (USES DYNAMIC BASE_URL) ---
@app.route('/login/google')
def google_login():
    # Pass the DYNAMIC redirect URI constructed above
    return google.authorize_redirect(BASE_URL + '/login/google/callback')

@app.route('/login/google/callback')
def google_callback():
    try:
        user_info = google.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('name'))
        return redirect('/dashboard')
    except Exception as e: return f"Google Login Failed: {e}"

@app.route('/login/github')
def github_login():
    # Pass the DYNAMIC redirect URI constructed above
    return github.authorize_redirect(BASE_URL + '/login/github/callback')

@app.route('/login/github/callback')
def github_callback():
    try:
        user_info = github.get('user').json()
        session['user'] = user_info
        send_login_notification(user_info.get('email'), user_info.get('login'))
        return redirect('/dashboard')
    except Exception as e: return f"GitHub Login Failed: {e}"

if __name__ == '__main__':
    # Run using the dynamic BASE_URL and port 5000
    # Note: Flask will prefer the host set in the OS environment if it exists.
    app.run(debug=True, host='0.0.0.0', port=5000)