# database.py (Final version for Render's default filesystem)
import sqlite3
import os

# Create the database in the project's source directory
DB_FILE = "tournament.db"

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Creates the necessary tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            ff_username TEXT,
            ff_userid TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    # Tournaments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            date_time TEXT NOT NULL,
            fee INTEGER NOT NULL,
            max_players INTEGER NOT NULL,
            status TEXT DEFAULT 'OPEN',
            room_id TEXT,
            room_password TEXT
        )
    ''')
    # Registrations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            telegram_id INTEGER,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database setup complete.")

# --- (The rest of the functions in this file are correct and do not need changes) ---
# --- (add_or_update_user, get_user, etc. are all fine) ---

def add_or_update_user(telegram_id, ff_username=None, ff_userid=None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    if user:
        if ff_username and ff_userid:
            c.execute("UPDATE users SET ff_username = ?, ff_userid = ? WHERE telegram_id = ?",
                      (ff_username, ff_userid, telegram_id))
    else:
        c.execute("INSERT INTO users (telegram_id, ff_username, ff_userid) VALUES (?, ?, ?)",
                  (telegram_id, ff_username, ff_userid))
    conn.commit()
    conn.close()

def get_user(telegram_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def get_all_user_ids():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT telegram_id FROM users")
    user_ids = [row['telegram_id'] for row in c.fetchall()]
    conn.close()
    return user_ids

def is_admin(telegram_id):
    user = get_user(telegram_id)
    return user and user['is_admin'] == 1

def add_tournament(mode, date_time, fee, max_players):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO tournaments (mode, date_time, fee, max_players) VALUES (?, ?, ?, ?)",
              (mode, date_time, fee, max_players))
    conn.commit()
    conn.close()

def get_open_tournaments():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE status = 'OPEN'")
    tournaments = c.fetchall()
    conn.close()
    return tournaments

def get_tournament_details(tournament_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
    tournament = c.fetchone()
    conn.close()
    return tournament

def register_user_for_tournament(tournament_id, telegram_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM registrations WHERE tournament_id = ? AND telegram_id = ?", (tournament_id, telegram_id))
    if c.fetchone():
        conn.close()
        return "ALREADY_REGISTERED"

    c.execute("INSERT INTO registrations (tournament_id, telegram_id) VALUES (?, ?)", (tournament_id, telegram_id))
    conn.commit()
    
    c.execute("SELECT COUNT(*) as count FROM registrations WHERE tournament_id = ?", (tournament_id,))
    registration_count = c.fetchone()['count']
    tournament = get_tournament_details(tournament_id)
    if registration_count >= tournament['max_players']:
        c.execute("UPDATE tournaments SET status = 'FULL' WHERE id = ?", (tournament_id,))
        conn.commit()

    conn.close()
    return "SUCCESS"

def get_registrations_for_tournament(tournament_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT u.telegram_id, u.ff_username, u.ff_userid
        FROM registrations r
        JOIN users u ON r.telegram_id = u.telegram_id
        WHERE r.tournament_id = ?
    ''', (tournament_id,))
    registrations = c.fetchall()
    conn.close()
    return registrations