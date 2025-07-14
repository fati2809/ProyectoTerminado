import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Habilitamos CORS para permitir peticiones desde otros dominios

AUTH_SERVICE_URL = 'http://localhost:5001'
USER_SERVICE_URL = 'http://localhost:5002'
TASK_SERVICE_URL = 'http://localhost:5003'

# Esta ruta redirige a la ruta de autenticación (auth service)
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_auth(path):
    method = request.method
    url = f'{AUTH_SERVICE_URL}/{path}'

    resp = requests.request(
        method=method,
        url=url,
        json=request.get_json(silent=True),
        headers={key: value for key, value in request.headers if key.lower() != 'host'}
    )

    return jsonify(resp.json()), resp.status_code

# Esta ruta redirige a la ruta del usuario (user service)
@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_user(path):
    method = request.method
    url = f'{USER_SERVICE_URL}/{path}'

    resp = requests.request(
        method=method,
        url=url,
        json=request.get_json(silent=True),
        headers={key: value for key, value in request.headers if key.lower() != 'host'}
    )

    return jsonify(resp.json()), resp.status_code

# Esta ruta redirige a la ruta de tareas (task service)
@app.route('/task/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_task(path):
    method = request.method
    url = f'{TASK_SERVICE_URL}/{path}'

    resp = requests.request(
        method=method,
        url=url,
        json=request.get_json(silent=True),
        headers={key: value for key, value in request.headers if key.lower() != 'host'}
    )

    return jsonify(resp.json()), resp.status_code

if __name__ == '__main__': app.run(port=5000, debug=True)