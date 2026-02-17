"""
database.py - Database Module
=============================
SQLite database with WAL mode for concurrent write support.
Critical for demonstrating race conditions effectively.
"""

import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), 'saas_platform.db')

# Constants
INITIAL_BALANCE = 100  # Initial wallet balance
UPGRADE_COST = 100     # Premium upgrade cost
NUM_USERS = 5          # Number of users in system


def get_connection():
    """
    Create database connection with WAL mode enabled.
    WAL (Write-Ahead Logging) allows concurrent reads and writes.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # Critical for race condition demo!
    return conn


def init_database():
    """
    Initialize database - create tables and initial data.
    
    Tables:
    - users: System users (id, name, is_premium)
    - wallet: Company wallet (id, balance)
    - audit_log: Action log for proving the attack
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Drop existing tables (for reset)
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS wallet")
    cursor.execute("DROP TABLE IF EXISTS audit_log")
    
    # Users table
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
    
    # Wallet table (single row)
    cursor.execute("""
        CREATE TABLE wallet (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            balance REAL NOT NULL,
            last_updated TIMESTAMP
        )
    """)
    
    # Audit log table - critical for proving the attack!
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
    
    # Insert initial users
    users = [
        (1, 'Alice Johnson', 'alice@techcorp.io', 'Frontend Developer', '#6366f1'),
        (2, 'Bob Cohen', 'bob@techcorp.io', 'UI/UX Designer', '#06b6d4'),
        (3, 'Charlie Levy', 'charlie@techcorp.io', 'Product Manager', '#f59e0b'),
        (4, 'Dana Mizrahi', 'dana@techcorp.io', 'DevOps Engineer', '#10b981'),
        (5, 'Avi Ben-David', 'avi@techcorp.io', 'Team Lead', '#ef4444')
    ]
    cursor.executemany("INSERT INTO users (id, name, email, role, avatar_color) VALUES (?, ?, ?, ?, ?)", users)
    
    # Insert initial wallet balance
    cursor.execute(
        "INSERT INTO wallet (id, balance, last_updated) VALUES (1, ?, ?)",
        (INITIAL_BALANCE, datetime.now())
    )
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized successfully!")
    print(f"   📊 {NUM_USERS} users created")
    print(f"   💰 Wallet balance: ${INITIAL_BALANCE}")
    print(f"   💵 Upgrade cost: ${UPGRADE_COST}")


def reset_database():
    """Reset database to initial state"""
    init_database()


def get_wallet_balance():
    """Fetch current wallet balance"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result['balance'] if result else 0


def get_all_users():
    """Fetch all users"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY id")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users


def get_audit_log():
    """Fetch audit log entries"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50")
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs


def add_audit_log(action, user_id, balance_before, balance_after, status, thread_id=""):
    """Add entry to audit log"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (action, user_id, balance_before, balance_after, status, thread_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (action, user_id, balance_before, balance_after, status, thread_id))
    conn.commit()
    conn.close()


# Auto-initialize if file doesn't exist
if __name__ == "__main__":
    init_database()
