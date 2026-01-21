"""
services.py - לוגיקה עסקית
============================
מכיל שתי גרסאות של פונקציית השדרוג:
1. vulnerable_upgrade - הגרסה הפגיעה (TOCTOU)
2. secure_upgrade - הגרסה המאובטחת (Atomic)

This module contains the business logic with both vulnerable
and secure implementations of the upgrade function.
"""

import time
import threading
from datetime import datetime
from database import get_connection, add_audit_log, UPGRADE_COST

# משתנה גלובלי לזיהוי thread (להדגמה)
request_counter = 0
counter_lock = threading.Lock()


def get_request_id():
    """יצירת מזהה ייחודי לבקשה"""
    global request_counter
    with counter_lock:
        request_counter += 1
        return f"REQ-{request_counter:03d}"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                        🔴 VULNERABLE UPGRADE FUNCTION                       ║
# ║                                                                            ║
# ║  זוהי הפונקציה הפגיעה! היא משתמשת בדפוס Check-Then-Act שגוי:              ║
# ║  1. קוראת את היתרה (SELECT)                                               ║
# ║  2. בודקת אם יש מספיק כסף                                                 ║
# ║  3. ⚠️ השהייה מלאכותית - כאן חלון הפגיעות! ⚠️                            ║
# ║  4. מעדכנת את היתרה (UPDATE)                                              ║
# ║                                                                            ║
# ║  בין שלב 2 ל-4, בקשות אחרות יכולות "לנצח במרוץ"                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def vulnerable_upgrade(user_id: int) -> dict:
    """
    🔴 פונקציית שדרוג פגיעה - TOCTOU Race Condition
    
    הבעיה: יש הפרדה בין הבדיקה (Check) לבין הפעולה (Act).
    בתרחיש אמיתי, ההשהייה יכולה להיות:
    - קריאה לשער תשלומים חיצוני (Stripe, PayPal)
    - בדיקת הרשאות מול שירות חיצוני
    - עומס על השרת
    
    Args:
        user_id: מזהה המשתמש לשדרוג
        
    Returns:
        dict עם תוצאת הפעולה
    """
    request_id = get_request_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # ═══════════════════════════════════════════════════════════════
        # שלב 1: CHECK - קריאת היתרה הנוכחית
        # ═══════════════════════════════════════════════════════════════
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_before = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 📖 קריאת יתרה: ${balance_before}")
        
        # ═══════════════════════════════════════════════════════════════
        # שלב 2: VALIDATE - בדיקה אם יש מספיק כסף
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
                "error": "אין מספיק כסף בארנק",
                "balance": balance_before,
                "request_id": request_id
            }
        
        print(f"[{request_id}] ✅ בדיקה עברה: ${balance_before} >= ${UPGRADE_COST}")
        
        # ╔══════════════════════════════════════════════════════════════╗
        # ║  ⚠️⚠️⚠️ CRITICAL SECTION - חלון הפגיעות! ⚠️⚠️⚠️              ║
        # ║                                                              ║
        # ║  ההשהייה הזו מדמה:                                          ║
        # ║  - קריאה לשער תשלומים (100-500ms)                           ║
        # ║  - אימות מול שירות חיצוני                                   ║
        # ║  - עומס על השרת                                             ║
        # ║                                                              ║
        # ║  בזמן הזה, בקשות אחרות יכולות:                              ║
        # ║  1. לקרוא את אותה יתרה ($100)                               ║
        # ║  2. לעבור את הבדיקה                                         ║
        # ║  3. להמשיך לשלב העדכון                                      ║
        # ╚══════════════════════════════════════════════════════════════╝
        
        print(f"[{request_id}] ⏳ מעבד תשלום... (השהייה 0.5 שניות)")
        time.sleep(0.5)  # 500ms - מספיק זמן למרוץ
        
        # ═══════════════════════════════════════════════════════════════
        # שלב 3: ACT - עדכון היתרה ושדרוג המשתמש
        # ⚠️ הבעיה: אנחנו משתמשים בערך הישן שקראנו קודם!
        # ═══════════════════════════════════════════════════════════════
        
        # קריאה מחדש של היתרה הנוכחית (אמיתית)
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        current_balance = cursor.fetchone()['balance']
        
        # מחשבים את היתרה החדשה על בסיס מה שקראנו בהתחלה (לא הנוכחית!)
        # זו הפגיעות - אנחנו מעדכנים לערך מחושב מראש
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
        
        print(f"[{request_id}] 💰 יתרה עודכנה: ${balance_before} → ${new_balance}")
        print(f"[{request_id}] 👑 משתמש {user_id} שודרג לפרימיום!")
        
        # רישום ללוג
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
            "message": f"משתמש {user_id} שודרג בהצלחה!",
            "balance_before": balance_before,
            "balance_after": new_balance,
            "request_id": request_id
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[{request_id}] ❌ שגיאה: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "request_id": request_id
        }
    finally:
        conn.close()


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                        🟢 SECURE UPGRADE FUNCTION                          ║
# ║                                                                            ║
# ║  זוהי הפונקציה המאובטחת! היא משתמשת ב-Atomic Update:                      ║
# ║  UPDATE ... WHERE balance >= cost                                         ║
# ║                                                                            ║
# ║  הבדיקה והעדכון מתבצעים באותה פעולה אטומית,                               ║
# ║  כך שאין חלון לתנאי מרוץ.                                                 ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def secure_upgrade(user_id: int) -> dict:
    """
    🟢 פונקציית שדרוג מאובטחת - Atomic Transaction
    
    הפתרון: שימוש בעדכון אטומי עם תנאי WHERE.
    מסד הנתונים מבטיח שהבדיקה והעדכון מתבצעים כפעולה אחת.
    
    SQL: UPDATE wallet SET balance = balance - 100 
         WHERE id = 1 AND balance >= 100
         
    אם התנאי לא מתקיים (אין מספיק כסף), אף שורה לא מתעדכנת.
    
    Args:
        user_id: מזהה המשתמש לשדרוג
        
    Returns:
        dict עם תוצאת הפעולה
    """
    request_id = get_request_id()
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # קריאת יתרה לפני (לצורך הלוג בלבד)
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_before = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 📖 יתרה נוכחית: ${balance_before}")
        
        # ═══════════════════════════════════════════════════════════════
        # ⚡ ATOMIC UPDATE - הבדיקה והעדכון באותה פעולה!
        # ═══════════════════════════════════════════════════════════════
        # 
        # הקסם כאן: התנאי WHERE balance >= ? מבטיח שהעדכון יתבצע
        # רק אם יש מספיק כסף ברגע הביצוע בפועל.
        # 
        # מסד הנתונים נועל את השורה בזמן הבדיקה והעדכון,
        # כך שבקשות מקביליות יחכו בתור.
        #
        cursor.execute("""
            UPDATE wallet 
            SET balance = balance - ?, last_updated = ?
            WHERE id = 1 AND balance >= ?
        """, (UPGRADE_COST, datetime.now(), UPGRADE_COST))
        
        # בדיקה אם העדכון הצליח (האם שורה עודכנה?)
        if cursor.rowcount == 0:
            # לא עודכנה שורה = לא היה מספיק כסף
            add_audit_log(
                action="SECURE_UPGRADE_ATTEMPT",
                user_id=user_id,
                balance_before=balance_before,
                balance_after=balance_before,
                status="REJECTED - Atomic check failed",
                thread_id=request_id
            )
            print(f"[{request_id}] 🛡️ נחסם! אין מספיק כסף (בדיקה אטומית)")
            return {
                "success": False,
                "error": "אין מספיק כסף בארנק (בדיקה אטומית)",
                "balance": balance_before,
                "request_id": request_id
            }
        
        # העדכון הצליח - משדרגים את המשתמש
        cursor.execute(
            "UPDATE users SET is_premium = 1, upgraded_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        
        # קריאת יתרה אחרי
        cursor.execute("SELECT balance FROM wallet WHERE id = 1")
        balance_after = cursor.fetchone()['balance']
        
        print(f"[{request_id}] 🟢 שדרוג מאובטח הצליח!")
        print(f"[{request_id}] 💰 יתרה: ${balance_before} → ${balance_after}")
        
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
            "message": f"משתמש {user_id} שודרג בהצלחה! (מאובטח)",
            "balance_before": balance_before,
            "balance_after": balance_after,
            "request_id": request_id
        }
        
    except Exception as e:
        conn.rollback()
        print(f"[{request_id}] ❌ שגיאה: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "request_id": request_id
        }
    finally:
        conn.close()
