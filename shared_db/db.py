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
    """Initializes the shared database schema only if needed."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    db_path = os.path.join(base_dir, 'shared_db', 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                status INTEGER DEFAULT 1
            )
        """)
        users = [
            ('username1', 'Hola.123', 1),
            ('username2', 'Hola.123', 1),
            ('username3', 'Hola.123', 1),
            ('username4', 'Hola.123', 1)
        ]
        for user in users:
            username, password, status = user
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password, status) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), status)
            )
    conn.commit()
    conn.close()