# database.py (Updated with functions for new features)

import sqlite3

DB_FILE = "tournament.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
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
            status TEXT DEFAULT 'OPEN'
        )
    ''')
    # Registrations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER,
            telegram_id INTEGER,
            FOREIGN KEY (tournament_id) REFERENCES tournaments (id) ON DELETE CASCADE,
            FOREIGN KEY (telegram_id) REFERENCES users (telegram_id)
        )
    ''')
    # Enable foreign key support
    c.execute("PRAGMA foreign_keys = ON;")
    conn.commit()
    conn.close()
    print("Database setup complete.")

# --- New Functions for New Features ---
def unregister_user_from_tournament(tournament_id, telegram_id):
    """Removes a user's registration from a tournament."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM registrations WHERE tournament_id = ? AND telegram_id = ?", (tournament_id, telegram_id))
    conn.commit()
    conn.close()

def get_user_registrations(telegram_id):
    """Gets all tournaments a user is registered for."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT t.id, t.mode, t.date_time
        FROM registrations r
        JOIN tournaments t ON r.tournament_id = t.id
        WHERE r.telegram_id = ? AND t.status != 'FINISHED'
    ''', (telegram_id,))
    registrations = c.fetchall()
    conn.close()
    return registrations

def delete_tournament(tournament_id):
    """Deletes a tournament and all its associated registrations."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    c.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
    conn.commit()
    conn.close()

def kick_player(tournament_id, ff_userid):
    """Kicks a player from a tournament using their Free Fire ID."""
    conn = get_db_connection()
    c = conn.cursor()
    # Find the telegram_id for the given ff_userid
    c.execute("SELECT telegram_id FROM users WHERE ff_userid = ?", (ff_userid,))
    user_row = c.fetchone()
    if not user_row:
        conn.close()
        return False # User not found in the bot's database

    telegram_id_to_kick = user_row['telegram_id']
    
    # Delete the registration
    c.execute("DELETE FROM registrations WHERE tournament_id = ? AND telegram_id = ?", (tournament_id, telegram_id_to_kick))
    changes = conn.total_changes
    conn.commit()
    conn.close()
    return changes > 0 # Return True if a row was deleted, False otherwise

# --- (The rest of your original database functions are below and are correct) ---
# ... (add_or_update_user, get_user, add_tournament, etc.)
# --- The complete code is included in the final block ---