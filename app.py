import os
import shutil
import zipfile
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

# Absolute Database Path
db_path = os.path.join(basedir, 'ssfi_enterprise.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Folder Paths
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'storage', 'uploads')
app.config['ENCRYPTED_FOLDER'] = os.path.join(basedir, 'storage', 'encrypted')
app.config['BACKUP_FOLDER'] = os.path.join(basedir, 'storage', 'backups')
app.config['VERSION_FOLDER'] = os.path.join(basedir, 'storage', 'versions')

db = SQLAlchemy(app)

# --- 2. Database Model ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(200))
    filename = db.Column(db.String(100))
    category = db.Column(db.String(50)) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- 3. Initializer Function ---
def init_sys():
    # Create all required folders
    folders = [
        os.path.join(basedir, 'storage'),
        app.config['UPLOAD_FOLDER'],
        app.config['ENCRYPTED_FOLDER'],
        app.config['BACKUP_FOLDER'],
        app.config['VERSION_FOLDER']
    ]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

    # Database creation
    with app.app_context():
        db.create_all()

    # Security Key Setup
    key_file = os.path.join(basedir, "secret.key")
    if not os.path.exists(key_file):
        with open(key_file, "wb") as kf:
            kf.write(Fernet.generate_key())
    return Fernet(open(key_file, "rb").read())

# Initialize once
cipher = init_sys()

def add_audit(action, filename, category="System"):
    try:
        new_log = AuditLog(action=action, filename=filename, category=category)
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Audit Error: {e}")

# --- 4. Routes ---

@app.route('/')
def index():
    if 'user' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Master Credentials
    if username == "admin" and password == "ankit123":
        session.clear() # Purani session clear karo
        session['user'] = "Ankit"
        add_audit("User Login", "N/A", "Security")
        return redirect(url_for('dashboard'))
    
    flash("Invalid Master Credentials!")
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
    file = request.files.get('file')
    if file and file.filename != '':
        fname = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        add_audit("File Uploaded", fname, "AI Classifier")
        flash(f"File {fname} Secured!")
    return redirect(url_for('dashboard'))

@app.route('/analyzer')
def analyzer():
    if 'user' not in session: return redirect(url_for('index'))
    csv_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    stats_html, sel = None, request.args.get('file')
    if sel:
        try:
            df = pd.read_csv(os.path.join(app.config['UPLOAD_FOLDER'], sel))
            stats_html = df.describe().to_html(classes='table table-dark')
            add_audit("Deep Analysis", sel, "Analytics")
        except Exception as e:
            flash(f"Error: {str(e)}")
    return render_template('analyzer.html', csv_files=csv_files, stats=stats_html, selected_file=sel)

@app.route('/logs')
def logs():
    if 'user' not in session: return redirect(url_for('index'))
    try:
        audits = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    except:
        audits = []
    return render_template('logs.html', audits=audits, now=datetime.now().strftime('%H:%M:%S'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Render port binding
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
