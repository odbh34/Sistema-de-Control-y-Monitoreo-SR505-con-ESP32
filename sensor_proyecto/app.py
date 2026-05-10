from flask import Flask, request, jsonify, render_template
import psycopg2
import json
import os
from datetime import datetime

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'sensordb',
    'user': 'sensoruser',
    'password': '123456789'
}

ultimo_registro = None
sensor_activo = True

def get_db():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS detecciones (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            movimiento BOOLEAN NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

@app.route('/sensor', methods=['POST'])
def recibir_sensor():
    global ultimo_registro, sensor_activo
    if not sensor_activo:
        return 'IGNORADO', 200
    movimiento = request.form.get('movimiento', '0') == '1'
    ahora = datetime.now()
    estado = {'movimiento': movimiento, 'timestamp': ahora.strftime('%Y-%m-%d %H:%M:%S')}
    with open('estado.json', 'w') as f:
        json.dump(estado, f)
    if movimiento:
        if ultimo_registro is None or (ahora - ultimo_registro).total_seconds() >= 5:
            ultimo_registro = ahora
            conn = get_db()
            cur = conn.cursor()
            cur.execute('INSERT INTO detecciones (timestamp, movimiento) VALUES (%s, %s)', (ahora, True))
            conn.commit()
            cur.close()
            conn.close()
    return 'OK', 200

@app.route('/estado')
def estado():
    if not os.path.exists('estado.json'):
        return jsonify({'movimiento': False, 'timestamp': 'Sin datos aún'})
    with open('estado.json') as f:
        return jsonify(json.load(f))

@app.route('/historial_json')
def historial_json():
    fecha = request.args.get('fecha')
    conn = get_db()
    cur = conn.cursor()
    if fecha:
        cur.execute('SELECT timestamp FROM detecciones WHERE timestamp::date = %s ORDER BY timestamp DESC LIMIT 50', (fecha,))
    else:
        cur.execute('SELECT timestamp FROM detecciones ORDER BY timestamp DESC LIMIT 50')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{'timestamp': r[0].strftime('%Y-%m-%d %H:%M:%S')} for r in rows])

@app.route('/conteo_hoy')
def conteo_hoy():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM detecciones WHERE timestamp::date = CURRENT_DATE")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return jsonify({'total': count})

@app.route('/control', methods=['POST'])
def control():
    global sensor_activo
    accion = request.form.get('accion')
    if accion == 'apagar':
        sensor_activo = False
    elif accion == 'encender':
        sensor_activo = True
    return jsonify({'sensor_activo': sensor_activo})

@app.route('/estado_control')
def estado_control():
    return jsonify({'sensor_activo': sensor_activo})

@app.route('/señal')
def senal():
    fecha = request.args.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT timestamp FROM detecciones
        WHERE timestamp::date = %s
        ORDER BY timestamp ASC
    ''', (fecha,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([r[0].strftime('%Y-%m-%d %H:%M:%S') for r in rows])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/historial')
def historial():
    return render_template('historial.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)