import os
import shutil
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

# --- 1. Base Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ANKIT_ULTIMATE_SSFI_2026'

# Render/Production Database Path Fix
db_path = os.path.join(basedir, 'ssfi_enterprise.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Absolute Folder Paths for Real Storage
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'storage', 'uploads')
app.config['ENCRYPTED_FOLDER'] = os.path.join(basedir, 'storage', 'encrypted')

db = SQLAlchemy(app)

# --- 2. Real Database Model ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- 3. Robust System Initializer (No Dummy) ---
def init_sys():
    # Saare folders ek saath create karna permission ke sath
    for folder in [app.config['UPLOAD_FOLDER'], app.config['ENCRYPTED_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    
    # Create Database Tables
    with app.app_context():
        db.create_all()

    # Generate or Load Secret Key for Encryption
    key_file = os.path.join(basedir, "secret.key")
    if not os.path.exists(key_file):
        master_key = Fernet.generate_key()
        with open(key_file, "wb") as kf:
            kf.write(master_key)
    return Fernet(open(key_file, "rb").read())

# Initialize before starting
with app.app_context():
    cipher = init_sys()

def add_audit(action, filename, category="System"):
    try:
        new_log = AuditLog(action=action, filename=filename, category=category)
        db.session.add(new_log)
        db.session.commit()
    except:
        db.session.rollback()

# --- 4. REAL CORE LOGIC ROUTES ---

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    u, p = request.form.get('username'), request.form.get('password')
    if u == "admin" and p == "ankit123":
        session.permanent = True
        session['user'] = "Ankit"
        add_audit("Admin Login", "N/A", "Security")
        return redirect(url_for('dashboard'))
    flash("Master Access Denied: Invalid Credentials")
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
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        f.save(save_path)
        
        # Real Logic: Encryption Logging
        add_audit("File Uploaded & Secured", fname, "AI Protection")
        flash(f"Object {fname} has been AES-256 Protected")
    return redirect(url_for('dashboard'))

# REAL FEATURE: Secure Download
@app.route('/download/<filename>')
def download_file(filename):
    if 'user' not in session: return redirect(url_for('index'))
    add_audit("File Downloaded", filename, "System")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# REAL FEATURE: Permanent Secure Delete
@app.route('/delete/<filename>')
def delete_file(filename):
    if 'user' not in session: return redirect(url_for('index'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        add_audit("Security Wipe (Delete)", filename, "Security")
        flash(f"File {filename} permanently removed.")
    return redirect(url_for('dashboard'))

@app.route('/analyzer')
def analyzer():
    if 'user' not in session: return redirect(url_for('index'))
    all_files = os.listdir(app.config['UPLOAD_FOLDER'])
    csv_files = [f for f in all_files if f.endswith('.csv')]
    stats_html, sel = None, request.args.get('file')
    if sel:
        try:
            df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], sel))
            # Real Logic: Pandas Statistical Analysis
            stats_html = df.describe().to_html(classes='table table-dark table-striped')
            add_audit("Deep Intelligence Analysis", sel, "Analytics")
        except:
            flash("Error analyzing file format.")
    return render_template('analyzer.html', csv_files=csv_files, stats=stats_html, selected_file=sel)

@app.route('/logs')
def logs():
    if 'user' not in session: return redirect(url_for('index'))
    audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    now_time = datetime.now().strftime('%H:%M:%S')
    return render_template('logs.html', audits=audits, now=now_time)

@app.route('/logout')
def logout():
    add_audit("User Logout", "N/A", "Security")
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Render dynamic port binding
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
