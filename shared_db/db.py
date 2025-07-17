import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_connection() -> sqlite3.Connection:
    """Creates a connection to the shared database with row_factory."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'shared_db', 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the shared database schema and adds MFA fields if needed."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'shared_db', 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Crear tabla users si no existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                status INTEGER DEFAULT 1,
                two_factor_secret TEXT,
                two_factor_enabled BOOLEAN DEFAULT FALSE
            )
        """)
        # Insertar usuarios de prueba
        users = [
            ('username1', 'Hola.123', 1),
            ('username2', 'Hola.123', 1),
            ('username3', 'Hola.123', 1),
            ('username4', 'Hola.123', 1)
        ]
        for user in users:
            username, password, status = user
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password, status, two_factor_enabled) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), status, False)
            )
    else:
        # Verificar y agregar columnas solo si no existen
        cursor.execute("PRAGMA table_info(users)")
        columns = {info[1] for info in cursor.fetchall()}  # Conjunto de nombres de columnas
        if 'two_factor_secret' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN two_factor_secret TEXT")
        if 'two_factor_enabled' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN DEFAULT FALSE")

    conn.commit()
    conn.close()