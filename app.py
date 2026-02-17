"""
app.py - Flask Server
====================
Web server providing API endpoints and web dashboard.
"""

from flask import Flask, render_template, jsonify, request
from database import (
    init_database, reset_database, get_wallet_balance,
    get_all_users, get_audit_log, INITIAL_BALANCE, UPGRADE_COST
)
from services import vulnerable_upgrade, secure_upgrade
import os

app = Flask(__name__)

# Initialize database if not exists
if not os.path.exists('saas_platform.db'):
    init_database()


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    """Landing page"""
    return render_template('index.html')


@app.route('/login')
def login_page():
    """Login page"""
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    """Dashboard - Admin panel"""
    return render_template('dashboard.html')


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES - DATA
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/stats')
def get_stats():
    """
    Fetch real-time system statistics.
    Used by dashboard to update platform data.
    """
    balance = get_wallet_balance()
    users = get_all_users()
    logs = get_audit_log()
    
    premium_count = sum(1 for u in users if u['is_premium'])
    free_count = len(users) - premium_count
    
    return jsonify({
        "wallet": {
            "balance": balance,
            "initial": INITIAL_BALANCE,
            "is_negative": balance < 0
        },
        "users": users,
        "stats": {
            "total": len(users),
            "premium": premium_count,
            "free": free_count
        },
        "logs": logs,
        "config": {
            "upgrade_cost": UPGRADE_COST
        }
    })


@app.route('/api/logs')
def get_logs():
    """Fetch audit log entries"""
    return jsonify(get_audit_log())


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES - VULNERABLE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/upgrade', methods=['POST'])
def upgrade_endpoint():
    """
    Vulnerable endpoint for user premium upgrade.
    
    This is the endpoint targeted by the race condition attack!
    Calls vulnerable_upgrade() which contains the security flaw.
    
    Request Body:
        {"user_id": 1}
    """
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "error": "Missing user_id"}), 400
    
    result = vulnerable_upgrade(user_id)
    
    # Returns 200 OK even on failure (for demonstration purposes)
    # In production, proper HTTP status codes would be used
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES - SECURE ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/upgrade/secure', methods=['POST'])
def secure_upgrade_endpoint():
    """
    Secure endpoint for user premium upgrade.
    
    This is the fixed endpoint using atomic transaction!
    Calls secure_upgrade() which prevents race conditions.
    
    Request Body:
        {"user_id": 1}
    """
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "error": "Missing user_id"}), 400
    
    result = secure_upgrade(user_id)
    return jsonify(result)


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES - MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/reset', methods=['POST'])
def reset_endpoint():
    """
    Reset system to initial state.
    Used for rerunning the demonstration.
    """
    reset_database()
    return jsonify({
        "success": True,
        "message": "System reset successfully",
        "balance": INITIAL_BALANCE
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ☁️  NexusCloud - Team Collaboration Platform                    ║
║                                                                   ║
║   Website:   http://localhost:5000                                ║
║   Dashboard: http://localhost:5000/dashboard                      ║
║                                                                   ║
║   API Endpoints:                                                  ║
║   • GET  /api/stats          - Platform statistics                ║
║   • POST /api/upgrade        - Upgrade user to Pro                ║
║   • POST /api/upgrade/secure - Secure upgrade endpoint            ║
║   • POST /api/reset          - Reset platform data                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Start server with threaded mode for concurrent request handling
    app.run(debug=True, threaded=True, port=5000)
