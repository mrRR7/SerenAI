import os
import sqlite3
import datetime

DB_PATH = 'data/user_history.db'

def create_connection():
    """Create an sqlite3 connection. If the existing file is not a valid SQLite DB,
    back it up and create a fresh database file.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        # Quick sanity-check: try a simple query against sqlite_master
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            _ = cursor.fetchall()
        except sqlite3.DatabaseError:
            # The file exists but is not a valid database
            conn.close()
            raise sqlite3.DatabaseError("Existing file is not a valid SQLite database")
        return conn
    except sqlite3.DatabaseError as e:
        print(f"Existing DB file appears invalid: {e}")
        # Attempt to back up the corrupt file and create a new one
        try:
            if os.path.exists(DB_PATH):
                backup_name = DB_PATH + ".corrupt." + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                os.rename(DB_PATH, backup_name)
                print(f"Backed up invalid DB to: {backup_name}")
        except Exception as be:
            print(f"Failed to back up invalid DB file: {be}")
        try:
            conn = sqlite3.connect(DB_PATH)
            return conn
        except sqlite3.Error as e2:
            print(f"Database connection error after recreating DB: {e2}")
            return None
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def setup_database():
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_logs (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    transcript_summary TEXT,
                    mood_score REAL,
                    anxiety_score REAL,
                    risk_level INTEGER,
                    jitter_score REAL,
                    loudness_mean REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profile (
                    trait_key TEXT PRIMARY KEY,
                    trait_value TEXT,
                    last_updated TEXT
                )
            ''')
            conn.commit()
            print("Database setup complete: daily_logs and user_profile tables ready.")
        except sqlite3.Error as e:
            print(f"Error setting up database tables: {e}")
        finally:
            conn.close()

def save_daily_log(log_data):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO daily_logs (
                    timestamp, session_id, transcript_summary, mood_score, anxiety_score, 
                    risk_level, jitter_score, loudness_mean
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_data.get('timestamp'), log_data.get('session_id'), 
                log_data.get('transcript_summary'), log_data.get('mood_score'), 
                log_data.get('anxiety_score'), log_data.get('risk_level'), 
                log_data.get('jitter_score'), log_data.get('loudness_mean')
            ))
            conn.commit()
            print(f"Daily Log saved for session {log_data.get('session_id')}.")
        except sqlite3.Error as e:
            print(f"Error saving daily log: {e}")
        finally:
            conn.close()

def update_user_profile(trait_key, trait_value):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute('''
                REPLACE INTO user_profile (trait_key, trait_value, last_updated)
                VALUES (?, ?, ?)
            ''', (trait_key, trait_value, timestamp))
            conn.commit()
            print(f"User Profile updated for key: {trait_key}.")
        except sqlite3.Error as e:
            print(f"Error updating user profile: {e}")
        finally:
            conn.close()

def get_recent_history(days=7):
    conn = create_connection()
    logs = []
    if conn is not None:
        try:
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM daily_logs 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC
            ''', (cutoff.isoformat(),))
            logs = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error retrieving history: {e}")
        finally:
            conn.close()
    return logs

def get_user_profile():
    conn = create_connection()
    profile = {}
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT trait_key, trait_value FROM user_profile')
            profile = {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            print(f"Error retrieving profile: {e}")
        finally:
            conn.close()
    return profile