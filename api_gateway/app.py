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
from datetime import datetime
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuración de MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manuel:t9EXNA8qU7DOjUXI@cluster0.baf6uby.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]

# Definir colecciones
tasks_collection = db["tasks"]
users_collection = db["users"]
logs_collection = db["logs"]

# Crear índices para evitar duplicados
users_collection.create_index("username", unique=True)
tasks_collection.create_index("name", unique=True)

# Configuración del logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('api_logger')

# Configuración de servicios
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:5001")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:5002")
TASK_SERVICE_URL = os.getenv("TASK_SERVICE_URL", "http://localhost:5003")
SECRET_KEY = os.getenv("SECRET_KEY", "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a")

# Configuración de Flask-Limiter (almacenamiento en memoria para pruebas)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Usa la IP del cliente para identificar solicitudes
    default_limits=["200 per day", "1 per hour"],  # Límites globales
    storage_uri="memory://",  # Almacenamiento en memoria (cambia a Redis en producción)
)

# Para Redis (en producción), descomenta y configura:
# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# limiter = Limiter(
#     app=app,
#     key_func=get_remote_address,
#     default_limits=["200 per day", "50 per hour"],
#     storage_uri=REDIS_URL
# )

@app.errorhandler(RateLimitExceeded)
def rate_limit_exceeded(e):
    # Extraer detalles del límite desde la excepción
    limit = e.description if e.description else "límite desconocido"
    
    # Definir mensajes de límites según la ruta
    route_limits = {
        '/auth/': '30 peticiones por minuto',
        '/user/': '30 peticiones por minuto',
        '/task/': '30 peticiones por minuto',
    }
    default_limits = '1000 peticiones por día, 400 peticiones por hora, 30 peticiones por minuto'
    
    # Determinar el límite específico de la ruta
    route = request.path.split('/')[1] + '/' if request.path.startswith(('/auth/', '/user/', '/task/')) else None
    limit_message = route_limits.get(route, default_limits)
    
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

# Middleware para logear solicitudes y respuestas
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    log_request(response)
    return response

# Rutas con límites específicos
@app.route('/auth/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("30 per minute")  # Límite específico para autenticación
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

@app.route('/user/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("30 per minute")  # Límite específico para rutas de usuario
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

@app.route('/task/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("30 per minute")  # Límite específico para rutas de tareas
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

if __name__ == '__main__':
    init_db()  # Inicializar la base de datos con datos de prueba
    app.run(port=5000, debug=True)