# 🔬 Race Condition Lab - TOCTOU Vulnerability Demonstration

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)


**A comprehensive security lab demonstrating Time-of-Check to Time-of-Use (TOCTOU) race condition vulnerabilities in web applications.**

[English](#english) | [עברית](#עברית)

</div>

---

## English

### 📋 Overview

This project demonstrates a **Race Condition** vulnerability (specifically TOCTOU - Time-of-Check to Time-of-Use) in a simulated SaaS platform. The lab shows how concurrent requests can bypass business logic constraints, allowing attackers to exploit timing gaps between validation and execution.

### 🎯 The Attack Scenario

- **Initial State**: Company wallet has $100, upgrade cost is $100
- **Expected Behavior**: Only 1 user can be upgraded to Premium
- **Vulnerability**: By sending 5 concurrent requests, ALL 5 users get upgraded
- **Impact**: $400 worth of services stolen (or negative balance)

### 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Attack Tool   │────▶│   Flask API     │────▶│   SQLite DB     │
│  (5 threads)    │     │   (vulnerable)  │     │   (WAL mode)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   Dashboard     │
                        │  (Real-time)    │
                        └─────────────────┘
```

### 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/race-condition-lab.git
cd race-condition-lab

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database.py

# Start the server
python app.py

# In another terminal, run the attack
python attack_tool.py
```

### 📁 Project Structure

```
race-condition-lab/
├── app.py              # Flask server with API endpoints
├── database.py         # SQLite database setup (WAL mode)
├── services.py         # Business logic (vulnerable + secure)
├── attack_tool.py      # Multi-threaded attack tool
├── requirements.txt    # Python dependencies
└── templates/
    └── dashboard.html  # Real-time visualization dashboard
```

### 🔴 Vulnerable Code (Check-Then-Act)

```python
# Step 1: CHECK - Read balance
balance = cursor.execute("SELECT balance FROM wallet").fetchone()

# Step 2: VALIDATE
if balance >= UPGRADE_COST:
    
    # ⚠️ CRITICAL WINDOW - Race condition here!
    time.sleep(0.3)  # Simulates external API call
    
    # Step 3: ACT - Deduct and upgrade
    cursor.execute("UPDATE wallet SET balance = ?", (balance - UPGRADE_COST,))
```

### 🟢 Secure Code (Atomic Update)

```python
# Atomic operation - Check and Act in one statement
cursor.execute("""
    UPDATE wallet 
    SET balance = balance - ? 
    WHERE balance >= ?
""", (UPGRADE_COST, UPGRADE_COST))

if cursor.rowcount == 0:
    return "Insufficient funds"
```

### 🛡️ Mitigation Strategies

1. **Atomic Database Operations** - Use `UPDATE ... WHERE` conditions
2. **Database Locks** - `SELECT ... FOR UPDATE`
3. **Optimistic Locking** - Version numbers/timestamps
4. **Distributed Locks** - Redis/Memcached for microservices

### 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard |
| `/api/stats` | GET | System statistics |
| `/api/upgrade` | POST | 🔴 Vulnerable upgrade |
| `/api/upgrade/secure` | POST | 🟢 Secure upgrade |
| `/api/reset` | POST | Reset system |

### 📚 References

- [OWASP Race Conditions](https://owasp.org/www-chapter-bangkok/slides/2024/2024-07-05_The-Race-is-On.pdf)
- [CWE-367: TOCTOU Race Condition](https://cwe.mitre.org/data/definitions/367.html)
- [CVE-2026-22820](https://www.cve.org/CVERecord?id=CVE-2026-22820)

---

## עברית

### 📋 סקירה כללית

פרויקט זה מדגים חולשת **Race Condition** (ספציפית TOCTOU - Time-of-Check to Time-of-Use) בפלטפורמת SaaS מדומה. המעבדה מראה כיצד בקשות מקביליות יכולות לעקוף מגבלות לוגיקה עסקית.

### 🎯 תרחיש המתקפה

- **מצב התחלתי**: ארנק החברה מכיל $100, עלות שדרוג $100
- **התנהגות צפויה**: רק משתמש אחד יכול להשתדרג לפרימיום
- **החולשה**: שליחת 5 בקשות במקביל - כל 5 המשתמשים משודרגים!
- **השפעה**: גניבת שירותים בשווי $400

### 🚀 התחלה מהירה

```bash
# התקנת תלויות
pip install -r requirements.txt

# אתחול מסד הנתונים
python database.py

# הפעלת השרת
python app.py

# בטרמינל נפרד - הרצת המתקפה
python attack_tool.py
```

### 🔧 פקודות כלי ההתקפה

```bash
# מתקפה על נקודת קצה פגיעה
python attack_tool.py

# מתקפה על נקודת קצה מאובטחת
python attack_tool.py --secure

# איפוס המערכת
python attack_tool.py --reset
```

</div>
