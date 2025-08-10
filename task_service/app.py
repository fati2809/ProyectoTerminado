import sys
import os
import datetime
from flask import Flask, jsonify, request
import pymongo
from functools import wraps
import jwt
from flask_cors import CORS
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

app = Flask(__name__)
CORS(app)
SECRET_KEY = os.getenv("SECRET_KEY", "a8f3c9d2f021ae6b8b76935b8e7f89ad28d76f9d29e3a1cf21e8b2c91566f51a")

# Configuración de MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://manuel:t9EXNA8qU7DOjUXI@cluster0.baf6uby.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]
tasks_collection = db["tasks"]

def validate_date(date_str: str) -> bool:
    """Valida formato de fecha (YYYY-MM-DD)."""
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Inicialización de la base de datos con datos de prueba
def init_db():
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

@app.route('/tasks', methods=['GET'])
@token_required
def tasks():
    """Lista todas las tareas."""
    tasks = list(tasks_collection.find())
    
    for task in tasks:
        task["_id"] = str(task["_id"])  # Convertir ObjectId a string
    return jsonify({
        "statusCode": 200,
        "intData": {
            "message": "Tasks retrieved successfully",
            "data": tasks
        }
    })

@app.route('/tasks/<string:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    """Obtiene información de una tarea por ID."""
    obj_id = ObjectId(task_id)
    task = tasks_collection.find_one({"_id": obj_id})
    if not task:
        return jsonify({
            "statusCode": 404,
            "intData": {
                "message": "Task not found",
                "data": None
            }
        })
    task["_id"] = str(task["_id"])  # Convertir ObjectId a string
    return jsonify({
        "statusCode": 200,
        "intData": {
            "message": "Task retrieved successfully",
            "data": task
        }
    })

@app.route('/tasks/user/<string:created_by>', methods=['GET'])
@token_required
def get_task_created_by(created_by):
    """Obtiene todas las tareas creadas por un usuario específico."""
    tasks = list(tasks_collection.find({"created_by": created_by}))
    if not tasks:
        return jsonify({
            "statusCode": 404,
            "intData": {
                "message": "No tasks found for this user",
                "data": []
            }
        })
    for task in tasks:
        task["_id"] = str(task["_id"])  # Convertir ObjectId a string
    return jsonify({
        "statusCode": 200,
        "intData": {
            "message": "Tasks retrieved successfully",
            "data": tasks
        }
    })

@app.route('/register_task', methods=['POST'])
@token_required
def register_task():
    """Registra una nueva tarea."""
    data = request.get_json()
    
    required_fields = ['name', 'description', 'created_at', 'dead_line', 'status', 'is_alive', 'created_by']
    if not all(field in data for field in required_fields):
        return jsonify({"message": "Todos los campos son requeridos", "status": "error"}), 400
    
    if not validate_date(data['created_at']) or not validate_date(data['dead_line']):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Invalid date format (YYYY-MM-DD)",
                "data": None
            }
        })
    
    tasks_collection.insert_one(data)
    return jsonify({
        "statusCode": 201,
        "intData": {
            "message": "Task registered successfully",
            "data": None
        }
    })

@app.route('/tasks/<string:task_id>/disable', methods=['PUT'])
@token_required
def disable_task(task_id):
    """Deshabilita una tarea."""
    obj_id = ObjectId(task_id)
    result = tasks_collection.update_one({"_id": obj_id}, {"$set": {"is_alive": False}})
    if result.matched_count == 0:
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
            "message": "Task disabled successfully",
            "data": None
        }
    })

@app.route('/tasks/<string:task_id>/enable', methods=['PUT'])
@token_required
def enable_task(task_id):
    """Habilita una tarea."""
    obj_id = ObjectId(task_id)
    result = tasks_collection.update_one({"_id": obj_id}, {"$set": {"is_alive": True}})
    if result.matched_count == 0:
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
            "message": "Task enabled successfully",
            "data": None
        }
    })

@app.route('/tasks/<string:task_id>', methods=['PUT'])
@token_required
def edit_task(task_id):
    """Edita información de una tarea."""
    data = request.get_json()
    obj_id = ObjectId(task_id)
    # Eliminar _id si viene en el payload
    if '_id' in data:
        del data['_id']
    required_fields = ['name', 'description', 'created_at', 'dead_line', 'status', 'is_alive', 'created_by']
    if not all(field in data for field in required_fields):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "All fields are required",
                "data": None
            }
        })
    
    if not validate_date(data['created_at']) or not validate_date(data['dead_line']):
        return jsonify({
            "statusCode": 400,
            "intData": {
                "message": "Invalid date format (YYYY-MM-DD)",
                "data": None
            }
        })
    
    result = tasks_collection.update_one({"_id": obj_id}, {"$set": data})
    if result.matched_count == 0:
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
            "message": "Task edited successfully",
            "data": None
        }
    })

@app.route('/tasks/<string:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
        """Elimina una tarea."""
        try:
            result = tasks_collection.delete_one({"_id": ObjectId(task_id)})
            if result.deleted_count == 0:
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
                    "message": "Task deleted successfully",
                    "data": None
                }
            })
        except ValueError:
            return jsonify({
                "statusCode": 400,
                "intData": {
                    "message": "Invalid task ID format",
                    "data": None
                }
            })

if __name__ == '__main__':
    init_db()
    app.run(port=5003, debug=True)