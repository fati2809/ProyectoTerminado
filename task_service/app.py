import sys
import os
import datetime
from venv import logger
from flask import Flask, jsonify, request
import requests
import sqlite3
from functools import wraps
import jwt
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# Clave secreta para JWT, se debe mantener en secreto y no exponer en el código fuente, pero para pruebas se queda así.
# El token debe llevar el id del usuario y el username
SECRET_KEY = "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a"

def validate_date(date_str: str) -> bool:
    """Valida formato de fecha (YYYY-MM-DD)."""
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Conexión a la base de datos
def get_db_connection() -> sqlite3.Connection:
    """Crea conexión a la base de datos con row_factory."""
    db_path = os.path.join(os.path.dirname(__file__), "database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Inicialización de la base de datos
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), "database.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at DATE NOT NULL,
            dead_line DATE NOT NULL,                   
            status TEXT NOT NULL,
            is_alive boolean TEXT NOT NULL,
            created_by INTEGER NOT NULL
        )
    """)


# Insertar tareas de prueba
    tasks = [
        ('name1', 'first task', '2002-06-03', '2002-06-10', 'done', 1, 'Manuel'),
        ('name2', 'second task', '2004-04-04', '2004-04-14', 'incomplete', 1, 'Puga')
    ]
    
    for task in tasks:
        name, description, created_at, dead_line, status, is_alive, created_by = task
        cursor.execute(
            """INSERT INTO tasks (name, description, created_at, dead_line, status, is_alive, created_by)
               SELECT ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE name = ?)""",
            (name, description, created_at, dead_line, status, is_alive, created_by, name)
        )
    
    conn.commit()
    conn.close()

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

# ===================== Ruta para obtener todas las tareas =====================

@app.route('/tasks', methods=['GET'])
@token_required
def tasks():
    """Lista todas las tareas."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, created_at, dead_line, status, is_alive, created_by FROM tasks")
        tasks = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Tasks retrieved successfully",
                "data": [{
                    "id": task["id"],
                    "name": task["name"],
                    "description": task["description"],
                    "created_at": task["created_at"],
                    "dead_line": task["dead_line"],
                    "status": task["status"],
                    "is_alive": task["is_alive"],
                    "created_by": task["created_by"]
                } for task in tasks]
            }
        })
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500

# ===================== Ruta para obtener la tarea por id =====================

@app.route('/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    """Obtiene información de una tarea por ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, created_at, dead_line, status, is_alive, created_by FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return jsonify({
                "statusCode": 404,
                "intData": {
                    "message": "Task not found",
                    "data": None
                }
            })
        
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Task retrieved successfully",
                "data": {
                    "id": task["id"],
                    "name": task["name"],
                    "description": task["description"],
                    "created_at": task["created_at"],
                    "dead_line": task["dead_line"],
                    "status": task["status"],
                    "is_alive": task["is_alive"],
                    "created_by": task["created_by"]
                }
            }
        })
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}), 500
    
# ===================== Ruta para obtener la tarea por created_by =====================

@app.route('/tasks/<string:created_by>', methods=['GET'])
@token_required
def get_task_created_by(created_by):
    """Obtiene todas las tareas creadas por un usuario específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, description, created_at, dead_line, status, is_alive, created_by FROM tasks WHERE created_by = ?",
            (created_by,)
        )
        tasks = cursor.fetchall()
        conn.close()
        
        if not tasks:
            return jsonify({
                "statusCode": 404,
                "intData": {
                    "message": "No tasks found for this user",
                    "data": []
                }
            })
        
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Tasks retrieved successfully",
                "data": [{
                    "id": task["id"],
                    "name": task["name"],
                    "description": task["description"],
                    "created_at": task["created_at"],
                    "dead_line": task["dead_line"],
                    "status": task["status"],
                    "is_alive": task["is_alive"],
                    "created_by": task["created_by"]
                } for task in tasks]
            }
        })
    except sqlite3.Error as e:
        return jsonify({"message": f"Error en la base de datos: {str(e)}", "status": "error"}),

# ===================== Ruta para registrar tareas =====================

@app.route('/register_task', methods=['POST'])
@token_required
def register_task():
    """Registra una nueva tarea."""
    data = request.get_json()
    
    required_fields = ['name', 'description', 'created_at', 'dead_line', 'status', 'is_alive', 'created_by']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Todos los campos son requeridos", "status": "error"}), 400
    
    name = data['name']
    description = data['description']
    created_at = data['created_at']
    dead_line = data['dead_line']
    status = data['status']
    is_alive = data['is_alive']
    created_by = data['created_by']
    
    if not validate_date(created_at) or not validate_date(dead_line):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Invalid date format (YYYY-MM-DD)",
                "data": None
            }
        })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO tasks (name, description, created_at, dead_line, status, is_alive, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, description, created_at, dead_line, status, is_alive, created_by)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "statusCode": 201,
            "intData": {
                "message": "Task registered successfully",
                "data": None
            }
        })
    
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Database error: {str(e)}",
                "data": None
            }
        })
    
    # ===================== Ruta para deshabilitar tareas =====================

@app.route('/tasks/<int:task_id>/disable', methods=['PUT'])
@token_required
def disable_task(task_id):
    """Deshabilita una tarea."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET is_alive = 0 WHERE id = ?", (task_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                "statusCode": 404,
                "intData": {
                    "message": "Task not found",
                    "data": None
                }
            })
        
        conn.close()
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Task disabled successfully",
                "data": None
            }
        })
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Database error: {str(e)}",
                "data": None
            }
        })
    

# ===================== Ruta para habilitar tareas =====================

@app.route('/tasks/<int:task_id>/enable', methods=['PUT'])
@token_required
def enable_task(task_id):
    """Habilita una tarea."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET is_alive = 1 WHERE id = ?", (task_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                "statusCode": 404,
                "intData": {
                    "message": "Task not found",
                    "data": None
                }
            })
        
        conn.close()
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Task enabled successfully",
                "data": None
            }
        })
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Database error: {str(e)}",
                "data": None
            }
        })

# ===================== Ruta para editar tareas =====================

@app.route('/tasks/<int:task_id>', methods=['PUT'])
@token_required
def edit_task(task_id):
    """Edita información de una tarea."""
    data = request.get_json()
    
    required_fields = ['name', 'description', 'created_at', 'dead_line', 'status', 'is_alive', 'created_by']
    if not all(field in data for field in required_fields):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "All fields are required",
                "data": None
            }
        })
    
    name = data['name']
    description = data['description']
    created_at = data['created_at']
    dead_line = data['dead_line']
    status = data['status']
    is_alive = data['is_alive']
    created_by = data['created_by']
    
    if not validate_date(created_at) or not validate_date(dead_line):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Invalid date format (YYYY-MM-DD)",
                "data": None
            }
        })
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """UPDATE tasks SET name = ?, description = ?, created_at = ?, dead_line = ?, status = ?, 
               is_alive = ?, created_by = ? WHERE id = ?""",
            (name, description, created_at, dead_line, status, is_alive, created_by, task_id)
        )
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                "statusCode": 404,
                "intData": {
                    "message": "Task not found",
                    "data": None
                }
            })
        
        conn.close()
        return jsonify({
            "statusCode": 200,
            "intData": {
                "message": "Task edited successfully",
                "data": None
            }
        })
    except sqlite3.Error as e:
        return jsonify({
            "statusCode": 500,
            "intData": {
                "message": f"Database error: {str(e)}",
                "data": None
            }
        })

#! Iniciamos el servidor en el puerto 5003 en modo debug
if __name__ == '__main__':
    init_db()
    app.run(port=5003, debug=True,)