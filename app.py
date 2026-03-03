import os
import shutil
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

# --- 1. Base Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ANKIT_ULTIMATE_SSFI_2026'

# Render par database write karne ke liye path fix
db_path = os.path.join(basedir, 'ssfi_enterprise.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Absolute Folder Paths
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'storage', 'uploads')
app.config['ENCRYPTED_FOLDER'] = os.path.join(basedir, 'storage', 'encrypted')

db = SQLAlchemy(app)

# --- 2. Database Model ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- 3. Robust System Initializer ---
def init_sys():
    # Saare folders ek saath create karna
    for folder in [app.config['UPLOAD_FOLDER'], app.config['ENCRYPTED_FOLDER']]:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
    
    # Database create karna agar nahi hai
    with app.app_context():
        db.create_all()

    # Security Key
    key_file = os.path.join(basedir, "secret.key")
    if not os.path.exists(key_file):
        with open(key_file, "wb") as kf:
            kf.write(Fernet.generate_key())
    return Fernet(open(key_file, "rb").read())

# Run initialization before any request
with app.app_context():
    cipher = init_sys()

def add_audit(action, filename, category="System"):
    try:
        new_log = AuditLog(action=action, filename=filename, category=category)
        db.session.add(new_log)
        db.session.commit()
    except:
        db.session.rollback()

# --- 4. Routes ---

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    if u == "admin" and p == "ankit123":
        session['user'] = "Ankit"
        add_audit("User Login", "N/A", "Security")
        return redirect(url_for('dashboard'))
    flash("Access Denied: Invalid Credentials")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('index'))
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
    except:
        files = []
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session: return redirect(url_for('index'))
    f = request.files.get('file')
    if f and f.filename != '':
        fname = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        add_audit("File Uploaded", fname, "AI Classifier")
    return redirect(url_for('dashboard'))

@app.route('/analyzer')
def analyzer():
    if 'user' not in session: return redirect(url_for('index'))
    csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    stats_html, sel = None, request.args.get('file')
    if sel:
        try:
            df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], sel))
            stats_html = df.describe().to_html(classes='table')
        except: pass
    return render_template('analyzer.html', csv_files=csv_files, stats=stats_html, selected_file=sel)

@app.route('/logs')
def logs():
    if 'user' not in session: return redirect(url_for('index'))
    audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('logs.html', audits=audits, now=datetime.now().strftime('%H:%M:%S'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
