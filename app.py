import os
import shutil
import zipfile
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ANKIT_ULTIMATE_SSFI_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ssfi_enterprise.db'
app.config['UPLOAD_FOLDER'] = 'storage/uploads'
app.config['ENCRYPTED_FOLDER'] = 'storage/encrypted'
app.config['BACKUP_FOLDER'] = 'storage/backups'
app.config['VERSION_FOLDER'] = 'storage/versions'

db = SQLAlchemy(app)

# --- Database Models ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Security Setup ---
KEY_FILE = "secret.key"
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as kf:
        kf.write(Fernet.generate_key())

cipher = Fernet(open(KEY_FILE, "rb").read())

def init_sys():
    for p in [app.config['UPLOAD_FOLDER'], app.config['ENCRYPTED_FOLDER'], 
              app.config['BACKUP_FOLDER'], app.config['VERSION_FOLDER']]:
        os.makedirs(p, exist_ok=True)

def add_audit(action, filename, category="System"):
    db.session.add(AuditLog(action=action, filename=filename, category=category))
    db.session.commit()

# --- Routes ---
@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('username') == "admin" and request.form.get('password') == "ankit123":
        session['user'] = "Ankit"
        add_audit("User Login", "N/A", "Security")
        return redirect(url_for('dashboard'))
    flash("Invalid Master Credentials!")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('index'))
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    # Filter only files (not directories)
    files = [f for f in files if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if file and file.filename != '':
        fname = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(path)
        
        # Feature 2: Smart Organizer (Move to ext folder)
        ext = fname.split('.')[-1].lower()
        ext_path = os.path.join(app.config['UPLOAD_FOLDER'], ext)
        os.makedirs(ext_path, exist_ok=True)
        # shutil.copy(path, os.path.join(ext_path, fname)) # Optional auto-sort copy
        
        add_audit(f"Uploaded & Classified ({ext})", fname, "AI Classifier")
        flash(f"File {fname} successfully secured!")
    return redirect(url_for('dashboard'))

@app.route('/encrypt/<filename>')
def encrypt_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(path, "rb") as f: data = f.read()
    encrypted_data = cipher.encrypt(data)
    with open(os.path.join(app.config['ENCRYPTED_FOLDER'], filename + ".enc"), "wb") as f:
        f.write(encrypted_data)
    add_audit("File Encrypted (AES)", filename, "Security")
    flash(f"AES Encryption applied to {filename}")
    return redirect(url_for('dashboard'))

@app.route('/save-version/<filename>')
def save_version(filename):
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    v_name = f"{ts}_{filename}"
    shutil.copy2(os.path.join(app.config['UPLOAD_FOLDER'], filename), 
                 os.path.join(app.config['VERSION_FOLDER'], v_name))
    add_audit("Version Snapshot Created", filename, "Version Control")
    flash(f"Snapshot v_{ts} saved!")
    return redirect(url_for('dashboard'))

@app.route('/analyzer')
def analyzer():
    csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    stats_html, sel = None, request.args.get('file')
    if sel:
        df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], sel))
        stats_html = df.describe().to_html(classes='table')
        add_audit("CSV Deep Analysis", sel, "Analytics")
    return render_template('analyzer.html', csv_files=csv_files, stats=stats_html, selected_file=sel)

@app.route('/logs')
def logs():
    audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('logs.html', audits=audits, now=datetime.now().strftime('%H:%M:%S'))

@app.route('/backup-now')
def run_backup():
    b_name = f"Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    with zipfile.ZipFile(os.path.join(app.config['BACKUP_FOLDER'], b_name), 'w') as z:
        for root, _, files in os.walk(app.config['UPLOAD_FOLDER']):
            for f in files: z.write(os.path.join(root, f), f)
    add_audit("System Backup Generated", b_name, "System")
    flash("Full System Backup Created!")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_sys()
    with app.app_context(): db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)