import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify, request
import pymongo
import jwt
import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
SECRET_KEY = os.getenv("SECRET_KEY", "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a")

# Configuración de MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://lopezuribefatima:EfTdWf9y89LZn9j7@cluster0.x7tqlrq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")


client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]
users_collection = db["users"]

def validate_username(username: str) -> bool:
    """Valida longitud y caracteres del nombre de usuario."""
    return bool(username and 3 <= len(username) <= 50 and re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_password(password: str) -> bool:
    """Valida que la contraseña tenga al menos 8 caracteres."""
    return bool(password and len(password) >= 8)

# DECORADOR JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token requerido', 'status': 'error'}), 401
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = decoded
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado', 'status': 'error'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido', 'status': 'error'}), 401
        return f(*args, **kwargs)
    return decorated

# Inicialización de la base de datos con datos de prueba
def init_db():
    users = [
        {"username": "username1", "password": generate_password_hash("Hola.123"), "status": 1},
        {"username": "username2", "password": generate_password_hash("Hola.123"), "status": 1},
        {"username": "username3", "password": generate_password_hash("Hola.123"), "status": 1},
        {"username": "username4", "password": generate_password_hash("Hola.123"), "status": 1}
    ]
    for user in users:
        users_collection.update_one(
            {"username": user["username"]},
            {"$setOnInsert": user},
            upsert=True
        )

@app.route('/users', methods=['GET'])
@token_required
def list_users():
    """Lista todos los usuarios."""
    users = list(users_collection.find({}, {"password": 0}))  # Excluir contraseña
    for user in users:
        user["_id"] = str(user["_id"])  # Convertir ObjectId a string
    return jsonify({
        "status": "success",
        "users": users
    }), 200

@app.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(user_id):
    """Obtiene información de un usuario por ID."""
    user = users_collection.find_one({"_id": user_id}, {"password": 0})  # Excluir contraseña
    if not user:
        return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
    user["_id"] = str(user["_id"])  # Convertir ObjectId a string
    return jsonify({
        "status": "success",
        "user": user
    }), 200

@app.route('/users/<int:user_id>/disable', methods=['PUT'])
@token_required
def disable_user(user_id):
    """Deshabilita un usuario."""
    result = users_collection.update_one({"_id": user_id}, {"$set": {"status": 0}})
    if result.matched_count == 0:
        return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
    return jsonify({"message": "Usuario deshabilitado correctamente", "status": "success"}), 200

@app.route('/users/<int:user_id>/enable', methods=['PUT'])
@token_required
def enable_user(user_id):
    """Habilita un usuario."""
    result = users_collection.update_one({"_id": user_id}, {"$set": {"status": 1}})
    if result.matched_count == 0:
        return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
    return jsonify({"message": "Usuario habilitado correctamente", "status": "success"}), 200

@app.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def edit_user(user_id):
    """Edita información de un usuario."""
    data = request.get_json()
    
    required_fields = ['username', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Todos los campos son requeridos", "status": "error"}), 400
    
    username = data['username']
    password = data['password']
    
    if not validate_username(username):
        return jsonify({"message": "Nombre de usuario inválido (3-50 caracteres, solo letras, números y guiones bajos)", "status": "error"}), 400
    if not validate_password(password):
        return jsonify({"message": "La contraseña debe tener al menos 8 caracteres", "status": "error"}), 400
    
    # Verificar si el username ya existe para otro usuario
    existing_user = users_collection.find_one({"username": username, "_id": {"$ne": user_id}})
    if existing_user:
        return jsonify({"message": "Nombre de usuario ya registrado", "status": "error"}), 400
    
    hashed_password = generate_password_hash(password)
    result = users_collection.update_one({"_id": user_id}, {"$set": {"username": username, "password": hashed_password}})
    if result.matched_count == 0:
        return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
    return jsonify({"message": "Usuario editado correctamente", "status": "success"}), 200

if __name__ == '__main__':
    init_db()
    app.run(port=5002, debug=True)