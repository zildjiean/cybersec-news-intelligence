#!/usr/bin/env python3
"""
Reset admin password utility
รันเมื่อ Flask หยุดทำงานแล้วเท่านั้น (ไม่งั้น SQLite จะ lock)

Usage:
    python reset_admin_password.py
    python reset_admin_password.py --username admin --password MyNewPass@123
"""
import sys, os, sqlite3, getpass, argparse

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt not installed. Run: pip install bcrypt")
    sys.exit(1)

DB_PATHS = [
    os.path.join(os.path.dirname(__file__), 'cybersec_news.db'),
    os.path.expanduser('~/cybersec_news.db'),
    '/var/lib/cybersec-intel/cybersec_news.db',
]

def find_db():
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    return None

def main():
    parser = argparse.ArgumentParser(description='Reset user password')
    parser.add_argument('--username', default='admin', help='Username to reset (default: admin)')
    parser.add_argument('--password', default=None, help='New password (prompt if not given)')
    args = parser.parse_args()

    db_path = find_db()
    if not db_path:
        print("ERROR: Database not found. Make sure you run this from the project directory.")
        sys.exit(1)
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    user = conn.execute('SELECT id, username, role FROM users WHERE username=?', (args.username,)).fetchone()
    if not user:
        print(f"ERROR: User '{args.username}' not found.")
        conn.close()
        sys.exit(1)

    print(f"User found: id={user['id']} username={user['username']} role={user['role']}")

    new_password = args.password
    if not new_password:
        while True:
            new_password = getpass.getpass("New password (≥ 8 chars): ")
            confirm = getpass.getpass("Confirm password: ")
            if new_password != confirm:
                print("Passwords do not match. Try again.")
            elif len(new_password) < 8:
                print("Password must be at least 8 characters.")
            else:
                break

    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn.execute('UPDATE users SET password_hash=? WHERE username=?', (pw_hash, args.username))
    conn.commit()
    conn.close()

    print(f"\n✓ Password for '{args.username}' reset successfully.")
    print("  Restart Flask/Gunicorn for changes to take effect if needed.")

if __name__ == '__main__':
    main()
