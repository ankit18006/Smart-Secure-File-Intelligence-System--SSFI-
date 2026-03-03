import os
import shutil
import zipfile
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

# --- 1. Base Configuration (Render Optimized) ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ANKIT_ULTIMATE_SSFI_2026'

# Absolute Database Path
db_path = os.path.join(basedir, 'ssfi_enterprise.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Absolute Folder Paths
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'storage', 'uploads')
app.config['ENCRYPTED_FOLDER'] = os.path.join(basedir, 'storage', 'encrypted')
app.config['BACKUP_FOLDER'] = os.path.join(basedir, 'storage', 'backups')
app.config['VERSION_FOLDER'] = os.path.join(basedir, 'storage', 'versions')

db = SQLAlchemy(app)

# --- 2. Database Models ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- 3. System Initializer (Folders & Security) ---
def init_sys():
    """System folders aur security keys ensure karne ke liye."""
    folders = [
        os.path.join(basedir, 'storage'),
        app.config['UPLOAD_FOLDER'],
        app.config['ENCRYPTED_FOLDER'],
        app.config['BACKUP_FOLDER'],
        app.config['VERSION_FOLDER']
    ]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
            print(f"Verified Folder: {folder}")

# Security Setup
KEY_FILE = os.path.join(basedir, "secret.key")
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as kf:
        kf.write(Fernet.generate_key())

cipher = Fernet(open(KEY_FILE, "rb").read())

def add_audit(action, filename, category="System"):
    try:
        new_log = AuditLog(action=action, filename=filename, category=category)
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")

# --- 4. Routes ---

@app.route('/')
def index():
    # Application start hone par folders verify karo
    init_sys()
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Credentials from saved info
    if username == "admin" and password == "ankit123":
        session['user'] = "Ankit"
        add_audit("User Login", "N/A", "Security")
        return redirect(url_for('dashboard'))
    
    flash("Invalid Master Credentials!")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('index'))
    
    # Har render se pehle check karo ki folder delete toh nahi hua
    init_sys()
    
    try:
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        files = [f for f in files if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    except Exception as e:
        print(f"Error listing files: {e}")
        files = []
        
    return render_template('dashboard.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session: return redirect(url_for('index'))
    
    init_sys() # Storage check
    file = request.files.get('file')
    if file and file.filename != '':
        fname = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
        file.save(path)
        
        ext = fname.split('.')[-1].lower()
        add_audit(f"Uploaded & Classified ({ext})", fname, "AI Classifier")
        flash(f"File {fname} successfully secured!")
    return redirect(url_for('dashboard'))

@app.route('/encrypt/<filename>')
def encrypt_file(filename):
    if 'user' not in session: return redirect(url_for('index'))
    init_sys()
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(path):
        with open(path, "rb") as f: data = f.read()
        encrypted_data = cipher.encrypt(data)
        
        enc_fname = filename + ".enc"
        with open(os.path.join(app.config['ENCRYPTED_FOLDER'], enc_fname), "wb") as f:
            f.write(encrypted_data)
            
        add_audit("File Encrypted (AES)", filename, "Security")
        flash(f"AES Encryption applied to {filename}")
    return redirect(url_for('dashboard'))

@app.route('/save-version/<filename>')
def save_version(filename):
    if 'user' not in session: return redirect(url_for('index'))
    init_sys()
    
    source = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(source):
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        v_name = f"{ts}_{filename}"
        shutil.copy2(source, os.path.join(app.config['VERSION_FOLDER'], v_name))
        
        add_audit("Version Snapshot Created", filename, "Version Control")
        flash(f"Snapshot v_{ts} saved!")
    return redirect(url_for('dashboard'))

@app.route('/analyzer')
def analyzer():
    if 'user' not in session: return redirect(url_for('index'))
    init_sys()
    
    csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    stats_html, sel = None, request.args.get('file')
    
    if sel:
        try:
            df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], sel))
            stats_html = df.describe().to_html(classes='table')
            add_audit("CSV Deep Analysis", sel, "Analytics")
        except Exception as e:
            flash(f"Analysis Error: {str(e)}")
            
    return render_template('analyzer.html', csv_files=csv_files, stats=stats_html, selected_file=sel)

@app.route('/logs')
def logs():
    if 'user' not in session: return redirect(url_for('index'))
    try:
        audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    except:
        audits = []
    return render_template('logs.html', audits=audits, now=datetime.now().strftime('%H:%M:%S'))

@app.route('/backup-now')
def run_backup():
    if 'user' not in session: return redirect(url_for('index'))
    init_sys()
    
    b_name = f"Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    zip_path = os.path.join(app.config['BACKUP_FOLDER'], b_name)
    
    with zipfile.ZipFile(zip_path, 'w') as z:
        for root, _, files in os.walk(app.config['UPLOAD_FOLDER']):
            for f in files: z.write(os.path.join(root, f), f)
            
    add_audit("System Backup Generated", b_name, "System")
    flash("Full System Backup Created!")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 5. Execution Block ---
if __name__ == '__main__':
    # Initial startup preparation
    init_sys()
    with app.app_context():
        db.create_all()
    # Render port binding
    app.run(host='0.0.0.0', port=10000)
