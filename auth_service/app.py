import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify, request
import pyotp
import qrcode
from io import BytesIO
import base64
import jwt
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
SECRET_KEY = os.getenv("SECRET_KEY", "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a")

# Configuración de MongoDB Atlas
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://lopezuribefatima:EfTdWf9y89LZn9j7@cluster0.x7tqlrq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]
users_collection = db["users"]
logs_collection = db["logs"]

def validate_username(username: str) -> bool:
    """Valida longitud y caracteres del nombre de usuario."""
    return bool(username and 3 <= len(username) <= 50 and re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_password(password: str) -> bool:
    """Valida que la contraseña tenga al menos 8 caracteres."""
    return bool(password and len(password) >= 8)

# Inicialización de la base de datos con usuarios de prueba
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

@app.route('/register_user', methods=['POST'])
def register_user():
    """Registra un nuevo usuario y genera un código QR para MFA."""
    data = request.get_json()

    required_fields = ['username', 'password', 'status']
    if not data or not all(field in data for field in required_fields):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Todos los campos son requeridos",
                "data": None
            }
        }), 400

    username = data['username']
    password = data['password']
    status = data['status']

    if not validate_username(username):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Nombre de usuario inválido (3-50 caracteres, solo letras, números y guiones bajos)",
                "data": None
            }
        }), 400

    if not validate_password(password):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "La contraseña debe tener al menos 8 caracteres",
                "data": None
            }
        }), 400

    if users_collection.find_one({"username": username}):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Nombre de usuario ya registrado",
                "data": None
            }
        }), 400

    # Generar secreto TOTP
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name='MFA-App')

    # Generar código QR
    qr = qrcode.QRCode()
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    qr_code = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # Hash de la contraseña
    hashed_password = generate_password_hash(password)

    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "status": status,
        "two_factor_secret": secret,
        "two_factor_enabled": True
    })

    return jsonify({
        "statusCode": 201,
        "intData": {
            "message": "Usuario registrado exitosamente",
            "data": {
                "qr_code": f"data:image/png;base64,{qr_code}",
                "secret": secret
            }
        }
    }), 201

@app.route('/login', methods=['POST'])
def login():
    """Autentica usuarios, verifica OTP y genera token JWT."""
    data = request.get_json()
    username = data.get('username') if data else None
    password = data.get('password') if data else None
    otp = data.get('otp') if data else None

    if not username or not password or not otp:
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Usuario, contraseña y OTP son requeridos",
                "data": None
            }
        }), 400

    user = users_collection.find_one({"username": username})

    if not user or not check_password_hash(user["password"], password):
        return jsonify({
            "statusCode": 401,
            "intData": {
                "message": "Credenciales incorrectas",
                "data": None
            }
        }), 401

    if user.get("two_factor_enabled", False):
        totp = pyotp.TOTP(user["two_factor_secret"])
        if not totp.verify(otp, valid_window=1):
            return jsonify({
                "statusCode": 401,
                "intData": {
                    "message": "Código OTP inválido",
                    "data": None
                }
            }), 401

    payload = {
        'user_id': str(user["_id"]),  # Convertir ObjectId a string
        'username': user["username"],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    return jsonify({
        "statusCode": 200,
        "intData": {
            "message": "Login exitoso",
            "token": token
        }
    }), 200

@app.route('/logs', methods=['GET'])
def get_logs():
    """Recupera los logs de MongoDB con filtros opcionales."""
    try:
        # Filtros opcionales desde los parámetros de la solicitud
        user = request.args.get('user')
        route = request.args.get('route')
        status = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        query = {}
        if user:
            query['user'] = user
        if route:
            query['route'] = route
        if status:
            try:
                query['status'] = int(status)
            except ValueError:
                return jsonify({
                    "statusCode": 400,
                    "intData": {
                        "message": "El status debe ser un número entero",
                        "data": None
                    }
                }), 400
        if start_date and end_date:
            # Asume que timestamp está almacenado como string con formato ISO, convertir a datetime para consulta correcta
            try:
                start_dt = datetime.datetime.fromisoformat(start_date)
                end_dt = datetime.datetime.fromisoformat(end_date)
                query['timestamp'] = {"$gte": start_dt.strftime('%Y-%m-%d %H:%M:%S'), "$lte": end_dt.strftime('%Y-%m-%d %H:%M:%S')}
            except ValueError:
                return jsonify({
                    "statusCode": 400,
                    "intData": {
                        "message": "Formato de fecha incorrecto. Use YYYY-MM-DD o ISO 8601.",
                        "data": None
                    }
                }), 400

        logs = list(logs_collection.find(query).sort("timestamp", -1))
        for log in logs:
            log['_id'] = str(log['_id'])  # Convierte ObjectId a string para JSON

        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Logs recuperados exitosamente",
                "data": logs
            }
        }), 200
    except Exception as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": "Error al recuperar los logs",
                "error": str(e)
            }
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(port=5001, debug=True)
