#!/usr/bin/env python3
"""
manage.py — interactive terminal DB manager

Commands:
    add student   — add a new student
    add teacher   — add a new teacher
    remove        — remove a user by ID
    list          — list all users
    quit          — exit
"""

import sqlite3
import sys
import os

import utils.argon_utils as argon
def hash_password(pw: str) -> str:
    return argon.hash_password(pw)
HASHING = "argon2"


DB_NAME = "MAIN_DB.db"

# ── db ────────────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    if not os.path.exists(DB_NAME):
        print(f"[error] '{DB_NAME}' not found. Run the app first to initialize the DB.")
        sys.exit(1)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def _add_user(user_name: str, login_name: str,
              password_hash: str, user_type: int) -> int | None:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (user_name, login_user_name, login_user_pass, user_type) "
            "VALUES (?, ?, ?, ?)",
            (user_name, login_name, password_hash, user_type),
        )
        return cur.lastrowid


def _remove_user(user_id: int) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT user_name, user_type FROM users WHERE USER_ID = ?", (user_id,)
        ).fetchone()
        if not row:
            return False
        # also clean up enrollments and class ownership
        conn.execute("DELETE FROM enrollments WHERE student_id = ?",  (user_id,))
        conn.execute("DELETE FROM class_data   WHERE teacher   = ?",  (user_id,))
        conn.execute("DELETE FROM users        WHERE USER_ID   = ?",  (user_id,))
    return True


def _list_users() -> list:
    with _connect() as conn:
        return conn.execute(
            "SELECT USER_ID, user_name, login_user_name, user_type FROM users ORDER BY user_type, user_name"
        ).fetchall()


# ── helpers ───────────────────────────────────────────────────────────────────

ROLE_LABEL = {0: "student", 1: "teacher"}

def _prompt(label: str, required: bool = True) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val or not required:
            return val
        print("  [!] this field is required.")

def _confirm(msg: str) -> bool:
    return input(f"  {msg} [y/N]: ").strip().lower() == "y"

def _divider():
    print("─" * 42)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_add(user_type: int):
    role = ROLE_LABEL[user_type]
    print(f"\n  Add {role}")
    _divider()

    user_name  = _prompt("Display name")
    login_name = _prompt("Login username")

    # check username not taken
    with _connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE login_user_name = ?", (login_name,)
        ).fetchone()
    if exists:
        print(f"  [!] Username '{login_name}' is already taken.")
        return

    password = _prompt("Password")
    pw_hash  = hash_password(password)

    uid = _add_user(user_name, login_name, pw_hash, user_type)
    print(f"\n  ✓ {role.capitalize()} '{user_name}' added (ID: {uid})")


def cmd_remove():
    print("\n  Remove user")
    _divider()
    cmd_list()

    try:
        uid = int(_prompt("Enter USER_ID to remove"))
    except ValueError:
        print("  [!] Invalid ID.")
        return

    with _connect() as conn:
        row = conn.execute(
            "SELECT user_name, user_type FROM users WHERE USER_ID = ?", (uid,)
        ).fetchone()

    if not row:
        print(f"  [!] No user with ID {uid}.")
        return

    role = ROLE_LABEL.get(row["user_type"], "unknown")
    print(f"\n  About to remove: [{uid}] {row['user_name']} ({role})")

    if row["user_type"] == 1:
        print("  [!] Warning: removing a teacher also deletes all their classes.")

    if not _confirm("Are you sure?"):
        print("  Cancelled.")
        return

    _remove_user(uid)
    print(f"  ✓ User {uid} removed.")


def cmd_list():
    print("\n  Users")
    _divider()
    rows = _list_users()
    if not rows:
        print("  (no users)")
        return
    for r in rows:
        role = ROLE_LABEL.get(r["user_type"], "unknown")
        print(f"  [{r['USER_ID']:>3}]  {r['user_name']:<24}  @{r['login_user_name']:<20}  {role}")
    _divider()


# ── main loop ─────────────────────────────────────────────────────────────────

HELP = """
  Commands:
    add student   — add a new student
    add teacher   — add a new teacher
    remove        — remove a user by ID
    list          — list all users
    quit          — exit
"""

def main():
    print(f"\n  DB Manager — {DB_NAME}")
    print(f"  Password hashing: {HASHING}")
    print(HELP)

    while True:
        try:
            cmd = input(">> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye.")
            break

        if cmd in ("quit", "exit", "q"):
            print("  Bye.")
            break

        elif cmd == "add student":
            cmd_add(user_type=0)

        elif cmd == "add teacher":
            cmd_add(user_type=1)

        elif cmd == "remove":
            cmd_remove()

        elif cmd == "list":
            cmd_list()

        elif cmd in ("help", "?"):
            print(HELP)

        elif cmd == "":
            pass

        else:
            print(f"  [!] Unknown command '{cmd}'. Type 'help' to see available commands.")


if __name__ == "__main__":
    main()



