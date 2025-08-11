import os
import sqlite3
import pymongo
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

# Conexión MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://lopezuribefatima:EfTdWf9y89LZn9j7@cluster0.x7tqlrq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = pymongo.MongoClient(MONGO_URI)
db = client["task_db"]
users_collection = db["users"]

def get_db_connection() -> sqlite3.Connection:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'shared_db', 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def sync_sqlite_users_to_mongo():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    
    for user in users:
        user_doc = {
            "username": user["username"],
            "password": user["password"],  # Ya hash de SQLite
            "status": user["status"],
            "two_factor_secret": user["two_factor_secret"],
            "two_factor_enabled": user["two_factor_enabled"]
        }
        users_collection.update_one(
            {"username": user_doc["username"]},
            {"$set": user_doc},
            upsert=True
        )
    conn.close()
    print(f"Sincronizados {len(users)} usuarios de SQLite a MongoDB")

# Ejecutar sincronización justo después de iniciar SQLite
def init_db_and_sync():
    # Aquí iría tu función init_db() para crear tablas e insertar datos
    init_db()
    sync_sqlite_users_to_mongo()

if __name__ == '__main__':
    init_db_and_sync()
