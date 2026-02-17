"""
services.py - Business Logic
============================
Contains two versions of the upgrade function:
1. vulnerable_upgrade - Vulnerable version (TOCTOU)
2. secure_upgrade - Secure version (Atomic)

Demonstrates the race condition exploit and its fix.
"""

import time
import threading
from datetime import datetime
from database import get_connection, add_audit_log, UPGRADE_COST

# Global counter for unique request IDs
request_counter = 0
counter_lock = threading.Lock()


def get_request_id():
    """Generate unique ID for each request"""
    global request_counter
    with counter_lock:
        request_counter += 1
        return f"REQ-{request_counter:03d}"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                        VULNERABLE UPGRADE FUNCTION                          ║
# ║                                                                            ║
# ║  This function is vulnerable! It uses the wrong Check-Then-Act pattern:    ║
# ║  1. Read balance (SELECT)                                                 ║
# ║  2. Check if enough funds                                                 ║
# ║  3. ⚠️ Artificial delay - vulnerability window! ⚠️                        ║
# ║  4. Update balance (UPDATE)                                               ║
# ║                                                                            ║
# ║  Between step 2 and 4, other requests can "win the race"                  ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def vulnerable_upgrade(user_id: int) -> dict:
    """
    Vulnerable function - TOCTOU Race Condition
    
    Issue: Gap between Check and Act phases.
    In real scenarios, the delay could be:
    - External payment gateway call (Stripe, PayPal)
    - Permission verification from external service
    - Server load/network latency
    
    Args:
        user_id: ID of user to upgrade
        
    Returns:
        dict with operation result
    """
    request_id = get_request_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: CHECK - Read current balance
        # ═══════════════════════════════════════════════════════════════
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_before = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 📖 Reading balance: ${balance_before}")
        
        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: VALIDATE - Check if enough funds
        # ═══════════════════════════════════════════════════════════════
        if balance_before < UPGRADE_COST:
            add_audit_log(
                action="UPGRADE_ATTEMPT",
                user_id=user_id,
                balance_before=balance_before,
                balance_after=balance_before,
                status="REJECTED - Insufficient funds",
                thread_id=request_id
            )
            return {
                "success": False,
                "error": "Insufficient funds in wallet",
                "balance": balance_before,
                "request_id": request_id
            }
        
        print(f"[{request_id}] ✅ Check passed: ${balance_before} >= ${UPGRADE_COST}")
        
        # ╔══════════════════════════════════════════════════════════════╗
        # ║  ⚠️⚠️⚠️ CRITICAL SECTION - VULNERABILITY WINDOW! ⚠️⚠️⚠️     ║
        # ║                                                              ║
        # ║  This delay simulates:                                      ║
        # ║  - External payment gateway call (100-500ms)                ║
        # ║  - Authorization check with external service               ║
        # ║  - Server load/network latency                              ║
        # ║                                                              ║
        # ║  During this time, other requests can:                      ║
        # ║  1. Read the same balance ($100)                            ║
        # ║  2. Pass the check                                          ║
        # ║  3. Proceed to update phase                                 ║
        # ╚══════════════════════════════════════════════════════════════╝
        
        print(f"[{request_id}] ⏳ Processing payment... (0.5s delay)")
        time.sleep(0.5)  # 500ms - sufficient for race condition
        
        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: ACT - Update balance and upgrade user
        # ⚠️ VULNERABILITY: We use the old value we read earlier!
        # ═══════════════════════════════════════════════════════════════
        
        # Read current balance (actual)
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        current_balance = cursor.fetchone()['balance']
        
        # Calculate new balance using the OLD value we read (not current!)
        # This is the vulnerability - we update with a pre-calculated value
        new_balance = balance_before - UPGRADE_COST
        
        cursor.execute(
            "UPDATE wallet SET balance = ?, last_updated = ? WHERE id = 1",
            (new_balance, datetime.now())
        )
        
        cursor.execute(
            "UPDATE users SET is_premium = 1, upgraded_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        
        print(f"[{request_id}] 💰 Balance updated: ${balance_before} → ${new_balance}")
        print(f"[{request_id}] 👑 User {user_id} upgraded to premium!")
        
        # Log transaction
        add_audit_log(
            action="UPGRADE_SUCCESS",
            user_id=user_id,
            balance_before=balance_before,
            balance_after=new_balance,
            status="SUCCESS",
            thread_id=request_id
        )
        
        return {
            "success": True,
            "message": f"User {user_id} upgraded successfully!",
            "balance_before": balance_before,
            "balance_after": new_balance,
            "request_id": request_id
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[{request_id}] ❌ Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "request_id": request_id
        }
    finally:
        conn.close()


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                        SECURE UPGRADE FUNCTION                              ║
# ║                                                                            ║
# ║  This function is secure! Uses Atomic Update:                             ║
# ║  UPDATE ... WHERE balance >= cost                                         ║
# ║                                                                            ║
# ║  Check and Act execute as a SINGLE atomic operation,                      ║
# ║  eliminating the race condition window.                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def secure_upgrade(user_id: int) -> dict:
    """
    Secure function - Atomic Transaction
    
    Solution: Use atomic update with WHERE condition.
    Database ensures check and update happen as single operation.
    
    SQL: UPDATE wallet SET balance = balance - 100 
         WHERE id = 1 AND balance >= 100
         
    If condition fails (insufficient funds), no rows are updated.
    
    Args:
        user_id: ID of user to upgrade
        
    Returns:
        dict with operation result
    """
    request_id = get_request_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Read balance before (for audit log only)
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_before = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 📖 Current balance: ${balance_before}")
        
        # ═══════════════════════════════════════════════════════════════
        # ⚡ ATOMIC UPDATE - Check and Act in ONE operation!
        # ═══════════════════════════════════════════════════════════════
        # 
        # The WHERE balance >= ? condition ensures update only happens
        # if sufficient funds exist AT THE TIME of execution.
        # 
        # Database locks the row during check and update,
        # making concurrent requests wait in queue.
        #
        cursor.execute("""
            UPDATE wallet 
            SET balance = balance - ?, last_updated = ?
            WHERE id = 1 AND balance >= ?
        """, (UPGRADE_COST, datetime.now(), UPGRADE_COST))
        
        # Check if update succeeded (was any row updated?)
        if cursor.rowcount == 0:
            # No row updated = insufficient funds
            add_audit_log(
                action="SECURE_UPGRADE_ATTEMPT",
                user_id=user_id,
                balance_before=balance_before,
                balance_after=balance_before,
                status="REJECTED - Atomic check failed",
                thread_id=request_id
            )
            print(f"[{request_id}] 🛡️ Blocked! Insufficient funds (atomic check)")
            return {
                "success": False,
                "error": "Insufficient funds (atomic transaction)",
                "balance": balance_before,
                "request_id": request_id
            }
        
        # Update succeeded - upgrade user
        cursor.execute(
            "UPDATE users SET is_premium = 1, upgraded_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        
        # Read balance after
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_after = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 🟢 Secure upgrade successful!")
        print(f"[{request_id}] 💰 Balance: ${balance_before} → ${balance_after}")
        
        add_audit_log(
            action="SECURE_UPGRADE_SUCCESS",
            user_id=user_id,
            balance_before=balance_before,
            balance_after=balance_after,
            status="SUCCESS",
            thread_id=request_id
        )
        
        return {
            "success": True,
            "message": f"User {user_id} upgraded successfully! (secure)",
            "balance_before": balance_before,
            "balance_after": balance_after,
            "request_id": request_id
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[{request_id}] ❌ Error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "request_id": request_id
        }
    finally:
        conn.close()
