"""
database.py - מודול מסד הנתונים
================================
מסד נתונים SQLite עם WAL Mode לאפשר כתיבות מקביליות.
זה קריטי להדגמת Race Condition - בלי WAL, הקובץ היה ננעל.

Database module with SQLite WAL Mode to allow concurrent writes.
This is critical for demonstrating Race Conditions.
"""

import sqlite3
import os
from datetime import datetime

# נתיב מסד הנתונים
DB_PATH = os.path.join(os.path.dirname(__file__), 'saas_platform.db')

# קבועים
INITIAL_BALANCE = 100  # יתרה התחלתית בארנק
UPGRADE_COST = 100     # עלות שדרוג לפרימיום
NUM_USERS = 5          # מספר משתמשים במערכת


def get_connection():
    """
    יצירת חיבור למסד הנתונים עם WAL Mode.
    WAL (Write-Ahead Logging) מאפשר קריאות וכתיבות מקביליות.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row  # גישה לעמודות לפי שם
    conn.execute("PRAGMA journal_mode=WAL")  # מצב WAL קריטי!
    return conn


def init_database():
    """
    אתחול מסד הנתונים - יצירת טבלאות ונתונים התחלתיים.
    
    טבלאות:
    - users: משתמשי המערכת (id, name, is_premium)
    - wallet: ארנק החברה (id, balance)
    - audit_log: לוג פעולות להוכחת המתקפה
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # מחיקת טבלאות קיימות (לאיפוס)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS wallet")
    cursor.execute("DROP TABLE IF EXISTS audit_log")
    
    # טבלת משתמשים
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'Member',
            avatar_color TEXT DEFAULT '#6366f1',
            is_premium INTEGER DEFAULT 0,
            upgraded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # טבלת ארנק (שורה אחת בלבד)
    cursor.execute("""
        CREATE TABLE wallet (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            balance REAL NOT NULL,
            last_updated TIMESTAMP
        )
    """)
    
    # טבלת לוג פעולות - קריטית להוכחת המתקפה!
    cursor.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            action TEXT NOT NULL,
            user_id INTEGER,
            balance_before REAL,
            balance_after REAL,
            status TEXT,
            thread_id TEXT
        )
    """)
    
    # הכנסת משתמשים התחלתיים
    users = [
        (1, 'Alice Johnson', 'alice@techcorp.io', 'Frontend Developer', '#6366f1'),
        (2, 'Bob Cohen', 'bob@techcorp.io', 'UI/UX Designer', '#06b6d4'),
        (3, 'Charlie Levy', 'charlie@techcorp.io', 'Product Manager', '#f59e0b'),
        (4, 'Dana Mizrahi', 'dana@techcorp.io', 'DevOps Engineer', '#10b981'),
        (5, 'Avi Ben-David', 'avi@techcorp.io', 'Team Lead', '#ef4444')
    ]
    cursor.executemany("INSERT INTO users (id, name, email, role, avatar_color) VALUES (?, ?, ?, ?, ?)", users)
    
    # הכנסת יתרה התחלתית לארנק
    cursor.execute(
        "INSERT INTO wallet (id, balance, last_updated) VALUES (1, ?, ?)",
        (INITIAL_BALANCE, datetime.now())
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ מסד הנתונים אותחל בהצלחה!")
    print(f"   📊 {NUM_USERS} משתמשים נוצרו")
    print(f"   💰 יתרת ארנק: ${INITIAL_BALANCE}")
    print(f"   💵 עלות שדרוג: ${UPGRADE_COST}")


def reset_database():
    """איפוס מסד הנתונים למצב התחלתי"""
    init_database()


def get_wallet_balance():
    """קבלת יתרת הארנק הנוכחית"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result['balance'] if result else 0


def get_all_users():
    """קבלת כל המשתמשים"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_audit_log():
    """קבלת לוג הפעולות"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50")
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def add_audit_log(action, user_id, balance_before, balance_after, status, thread_id=""):
    """הוספת רשומה ללוג"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (action, user_id, balance_before, balance_after, status, thread_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (action, user_id, balance_before, balance_after, status, thread_id))
    conn.commit()
    conn.close()


# אתחול אוטומטי אם הקובץ לא קיים
if __name__ == "__main__":
    init_database()
