import requests
from flask_cors import CORS
from flask import Flask, jsonify, request
from flask_limiter import Limiter, RateLimitExceeded
from flask_limiter.util import get_remote_address
import time
import logging
import jwt
import pymongo
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
# Habilitar CORS solo para frontend especificado (mejor que usar '*')
CORS(app)

# Configuración de MongoDB Atlas
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://lopezuribefatima:EfTdWf9y89LZn9j7@cluster0.x7tqlrq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]

# Definir colecciones
tasks_collection = db["tasks"]
users_collection = db["users"]
logs_collection = db["logs"]

# Crear índices para evitar duplicados (manejo de excepciones si ya existen)
try:
    users_collection.create_index("username", unique=True)
except Exception:
    pass

try:
    tasks_collection.create_index("name", unique=True)
except Exception:
    pass

# Configuración del logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('api_logger')

# URLs de servicios
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:5001")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:5002")
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://localhost:5003")
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a"
)

# Configuración de Flask-Limiter (memoria para pruebas)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "1 per hour"],
    storage_uri="memory://",
)

@app.errorhandler(RateLimitExceeded)
def rate_limit_exceeded(e):
    route_limits = {
        '/auth/': '30 peticiones por minuto',
        '/user/': '30 peticiones por minuto',
        '/task/': '30 peticiones por minuto',
    }
    route = request.path.split('/')[1] + '/' if request.path.startswith(('/auth/', '/user/', '/task/')) else None
    limit_message = route_limits.get(route, '1000 peticiones por día, 400 peticiones por hora, 30 peticiones por minuto')

    response = jsonify({
        'error': 'Límite de peticiones excedido',
        'message': f'Has alcanzado el límite de peticiones: {limit_message}. Por favor, intenta de nuevo más tarde.',
        'statusCode': 429
    })
    response.status_code = 429
    return response

# Inicializar base de datos con datos de prueba
def init_db():
    users = [
        {"username": "username1", "password": generate_password_hash("Hola.123"), "status": 1, "two_factor_enabled": False},
        {"username": "username2", "password": generate_password_hash("Hola.123"), "status": 1, "two_factor_enabled": False},
        {"username": "username3", "password": generate_password_hash("Hola.123"), "status": 1, "two_factor_enabled": False},
        {"username": "username4", "password": generate_password_hash("Hola.123"), "status": 1, "two_factor_enabled": False}
    ]
    for user in users:
        users_collection.update_one(
            {"username": user["username"]},
            {"$setOnInsert": user},
            upsert=True
        )

    tasks = [
        {
            "name": "name1",
            "description": "first task",
            "created_at": "2002-06-03",
            "dead_line": "2002-06-10",
            "status": "done",
            "is_alive": True,
            "created_by": "Manuel"
        },
        {
            "name": "name2",
            "description": "second task",
            "created_at": "2004-04-04",
            "dead_line": "2004-04-14",
            "status": "incomplete",
            "is_alive": True,
            "created_by": "Puga"
        }
    ]
    for task in tasks:
        tasks_collection.update_one(
            {"name": task["name"]},
            {"$setOnInsert": task},
            upsert=True
        )

# Función para registrar logs en MongoDB
def log_request(response):
    start_time = getattr(request, 'start_time', time.time())
    duration = time.time() - start_time
    
    user = 'anonymous'
    token = request.headers.get('Authorization')
    if token and token.startswith('Bearer '):
        try:
            decoded_token = jwt.decode(token.split(' ')[1], SECRET_KEY, algorithms=['HS256'])
            user = decoded_token.get('username', 'anonymous')
        except jwt.InvalidTokenError:
            user = 'invalid_token'

    service = {
        '/auth/': 'auth_service',
        '/user/': 'user_service',
        '/task/': 'task_service'
    }.get(request.path.split('/')[1] + '/', 'unknown_service')

    log_entry = {
        "route": request.path,
        "service": service,
        "method": request.method,
        "status": response.status_code,
        "response_time": round(duration, 2),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "user": user
    }
    logs_collection.insert_one(log_entry)

    log_message = (
        f"Route: {request.path} "
        f"Service: {service} "
        f"Method: {request.method} "
        f"Status: {response.status_code} "
        f"response_time: {duration:.2f}s "
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
        f"User: {user}"
    )
    if 200 <= response.status_code < 300:
        logger.info(log_message)
    elif 400 <= response.status_code < 500:
        logger.warning(log_message)
    else:
        logger.error(log_message)

# Middleware para medir tiempos de petición
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    log_request(response)
    return response

# Endpoint para obtener logs con filtros
@app.route('/auth/logs', methods=['GET'])
@limiter.exempt  # <---- Aquí quitamos el límite
def get_logs():
    # Parámetros opcionales
    user = request.args.get('user')
    route = request.args.get('route')
    status = request.args.get('status')
    start_date_str = request.args.get('start_date')  # yyyy-mm-dd
    end_date_str = request.args.get('end_date')      # yyyy-mm-dd

    query = {}

    if user:
        query['user'] = user
    if route:
        query['route'] = route
    if status:
        try:
            query['status'] = int(status)
        except ValueError:
            return jsonify({'error': 'El parámetro status debe ser un número'}), 400

    # Fecha inicio y fin convertidas a objetos datetime para consulta
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            query['timestamp'] = {"$gte": start_date.strftime('%Y-%m-%d %H:%M:%S')}
        except ValueError:
            return jsonify({'error': 'Formato incorrecto para start_date, debe ser yyyy-mm-dd'}), 400

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            if 'timestamp' in query:
                query['timestamp']['$lte'] = end_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                query['timestamp'] = {"$lte": end_date.strftime('%Y-%m-%d %H:%M:%S')}
        except ValueError:
            return jsonify({'error': 'Formato incorrecto para end_date, debe ser yyyy-mm-dd'}), 400

    logs_cursor = logs_collection.find(query).sort('timestamp', -1)
    logs = list(logs_cursor)

    # Convertir ObjectId a string y devolver sólo campos que quieres exponer
    def clean_log(log):
        log['_id'] = str(log['_id'])
        return log

    cleaned_logs = [clean_log(log) for log in logs]

    return jsonify({
        "intData": {
            "data": cleaned_logs,
            "message": "Logs recuperados exitosamente"
        },
        "statusCode": 200
    })

# Helper para manejar requests en proxy (evita json=None en GET, pasa params)
def forward_request(service_url):
    method = request.method
    url = f'{service_url}/{request.view_args["path"]}'

    headers = {key: value for key, value in request.headers if key.lower() != 'host'}

    # En GET, pasar params; en otros métodos pasar json
    if method == 'GET':
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=request.args
        )
    else:
        # Para POST, PUT, PATCH, DELETE
        json_body = request.get_json(silent=True)
        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_body
        )

    try:
        resp_json = resp.json()
    except Exception:
        # Si no es JSON, devuelve texto plano
        return (resp.text, resp.status_code, resp.headers.items())

    return (jsonify(resp_json), resp.status_code)

# Proxy a servicio Auth con límite 30/minuto
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@limiter.limit("30 per minute")
def proxy_auth(path):
    return forward_request(AUTH_SERVICE_URL)

# Proxy a servicio User con límite 30/minuto
@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@limiter.limit("30 per minute")
def proxy_user(path):
    return forward_request(USER_SERVICE_URL)

# Proxy a servicio Task con límite 30/minuto
@app.route('/task/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@limiter.limit("30 per minute")
def proxy_task(path):
    return forward_request(TASK_SERVICE_URL)

if __name__ == '__main__':
    init_db()  # Inicializar la base de datos con datos de prueba
port = int(os.environ.get("PORT", 5000))  # 5000 solo para correr localmente
    app.run(host="0.0.0.0", port=port)



