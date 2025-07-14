import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify, request
import requests
import jwt
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import re
from shared_db.db import get_db_connection, init_db
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
SECRET_KEY = "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a"

def validate_username(username: str) -> bool:
    """Valida longitud y caracteres del nombre de usuario."""
    return bool(username and 3 <= len(username) <= 50 and re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_password(password: str) -> bool:
    """Valida que la contraseña tenga al menos 8 caracteres."""
    return bool(password and len(password) >= 8)

# ===================== Ruta para registrar usuarios =====================

@app.route('/register_user', methods=['POST'])
def register_user():
    """Registra un nuevo usuario."""
    data = request.get_json()
    
    required_fields = ['username', 'password', 'status']
    if not all(field in data for field in required_fields):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Todos los campos son requeridos",
                "data": None
            }
        })
    
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
        })
    if not validate_password(password):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "La contraseña debe tener al menos 8 caracteres",
                "data": None
            }
        })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el username ya existe
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return jsonify({
                "statusCode": 400,
                "intData": {
                    "message": "Nombre de usuario ya registrado",
                    "data": None
                }
            })
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            """INSERT INTO users (username, password, status)
               VALUES (?, ?, ?)""",
            (username, hashed_password, status)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "statusCode": 201,
            "intData": {
                "message": "Usuario registrado exitosamente",
                "data": None
            }
        })
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Error en la base de datos: {str(e)}",
                "data": None
            }
        })

# ===================== Ruta para iniciar sesión =====================
@app.route('/login', methods=['POST'])
def login():
    """Autentica usuarios y genera token JWT con 5 minutos de vida."""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    status = data.get('status')
    
    if not username or not password:
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Usuario y contraseña son requeridos",
                "data": None
            }
        })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, status FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or not check_password_hash(user["password"], password):
            return jsonify({
                "statusCode": 401,
                "intData": {
                    "message": "Credenciales incorrectas",
                    "data": None
                }
            })
        
        payload = {
            'user_id': user["id"],
            'username': user["username"],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Login exitoso",
                "token": token
            }
        })
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Error en la base de datos: {str(e)}",
                "data": None
            }
        })

#! Iniciamos el servidor en el puerto 5001 en modo debug
if __name__ == '__main__':
    init_db()
    app.run(port=5001, debug=True,)
    