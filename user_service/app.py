import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, jsonify, request
import requests
import jwt
import sqlite3
import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from shared_db.db import get_db_connection, init_db

#! Creamos una instancia de la aplicación Flask
app = Flask(__name__)
# Clave secreta para JWT, se debe mantener en secreto y no exponer en el código fuente, pero para pruebas se queda así.
# El token debe llevar el id del usuario y el username
SECRET_KEY = "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a"

def validate_username(username: str) -> bool:
    """Valida longitud y caracteres del nombre de usuario."""
    return bool(username and 3 <= len(username) <= 50 and re.match(r'^[a-zA-Z0-9_]+$', username))

def validate_password(password: str) -> bool:
    """Valida que la contraseña tenga al menos 8 caracteres."""
    return bool(password and len(password) >= 8)

# ===================== DECORADOR JWT =====================

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

# ===================== Ruta para obtener todos los usuarios =====================

@app.route('/users', methods=['GET'])
@token_required
def list_users():
    """Lista todos los usuarios."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, status FROM users")
        users = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "users": [{
                "id": user["id"],
                "username": user["username"],
                "status": user["status"]
            } for user in users]
        }), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500
    
    

# ===================== Ruta para obtener usuario por id =====================

@app.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(user_id):
    """Obtiene información de un usuario por ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, status FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
        
        return jsonify({
            "status": "success",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "status": user["status"]
            }
        }), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500

# ===================== Ruta para deshabilitar usuarios =====================

@app.route('/users/<int:user_id>/disable', methods=['PUT'])
@token_required
def disable_user(user_id):
    """Deshabilita un usuario."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 0 WHERE id = ?", (user_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
        
        conn.close()
        return jsonify({"message": "Usuario deshabilitado correctamente", "status": "success"}), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500
    

# ===================== Ruta para habilitar usuarios =====================

@app.route('/users/<int:user_id>/enable', methods=['PUT'])
@token_required
def enable_user(user_id):
    """Habilita un usuario."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 1 WHERE id = ?", (user_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
        
        conn.close()
        return jsonify({"message": "Usuario habilitado correctamente", "status": "success"}), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500



# ===================== Ruta para editar usuarios =====================

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
    
    # Validaciones
    if not validate_username(username):
        return jsonify({"message": "Nombre de usuario inválido (3-50 caracteres, solo letras, números y guiones bajos)", "status": "error"}), 400
    if not validate_password(password):
        return jsonify({"message": "La contraseña debe tener al menos 8 caracteres", "status": "error"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si el username ya existe para otro usuario
        cursor.execute("SELECT 1 FROM users WHERE username = ? AND id != ?", (username, user_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({"message": "Nombre de usuario ya registrado", "status": "error"}), 400
        
        # Hash de la contraseña
        hashed_password = generate_password_hash(password)
        
        cursor.execute(
            """UPDATE users SET username = ?, password = ? WHERE id = ?""",
            (username, hashed_password, user_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"message": "Usuario no encontrado", "status": "error"}), 404
        
        conn.close()
        return jsonify({"message": "Usuario editado correctamente", "status": "success"}), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500

# Iniciamos el servidor en el puerto 5002 en modo debug
if __name__ == '__main__':
    init_db()
    app.run(port=5002, debug=True)