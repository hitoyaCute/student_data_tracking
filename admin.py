"""

Connects to the same MAIN_DB.db as the running server.
WAL mode allows both to access the file at the same time safely.

Commands:
    add student       add a new student
    add teacher       add a new teacher
    add class         add a new class under a teacher
    add score         add or update a score for a student in a class
    list users        list all users
    list classes      list all classes
    list scores       show scores for a student in a class
    remove user       remove a user by ID
    remove class      remove a class by ID
    quit
"""

import sqlite3
import sys
import os

import utils.argon_utils as argon
def hash_password(pw: str) -> str: return argon.hash_password(pw)
HASHING = "argon2"

DB_NAME = "MAIN_DB.db"


# ── connection ────────────────────────────────────────────────────────────────
# timeout=10  — wait up to 10s if the server holds a write lock
# WAL mode    — allows concurrent reads from server + writes from this tool

def _conn() -> sqlite3.Connection:
    if not os.path.exists(DB_NAME):
        print(f"[error] '{DB_NAME}' not found. Run the app first.")
        sys.exit(1)
    c = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


# ── tiny helpers ──────────────────────────────────────────────────────────────

ROLE = {0: "student", 1: "teacher"}

def ask(label: str) -> str:
    while True:
        v = input(f"  {label}: ").strip()
        if v:
            return v
        print("  required.")

def ask_int(label: str) -> int | None:
    try:
        return int(ask(label))
    except Exception:
        print("  must be a number.")
        return None

def confirm(msg: str) -> bool:
    return input(f"  {msg} [y/N]: ").strip().lower() == "y"

def div(): print("─" * 48)


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_add_user(user_type: int):
    print(f"\n  Add {ROLE[user_type]}")
    div()
    name       = ask("Display name")
    login_name = ask("Login username")

    with _conn() as c:
        if c.execute("SELECT 1 FROM users WHERE login_user_name=?", (login_name,)).fetchone():
            print(f"  [!] '{login_name}' already taken.")
            return
        password = ask("Password")
        cur = c.execute(
            "INSERT INTO users (user_name, login_user_name, login_user_pass, user_type) VALUES (?,?,?,?)",
            (name, login_name, hash_password(password), user_type)
        )
    print(f"\n  ✓ {ROLE[user_type].capitalize()} '{name}' added  (ID: {cur.lastrowid})")


def cmd_add_class():
    print("\n  Add class")
    div()
    cmd_list_users(user_type=1)

    teacher_id = ask_int("Teacher ID")
    if teacher_id is None:
        return

    with _conn() as c:
        if not c.execute("SELECT 1 FROM users WHERE USER_ID=? AND user_type=1", (teacher_id,)).fetchone():
            print("  [!] Teacher not found.")
            return
        subject = ask("Subject / class name")
        cur = c.execute(
            "INSERT INTO class_data (teacher, subject_name) VALUES (?,?)",
            (teacher_id, subject)
        )
    print(f"\n  ✓ Class '{subject}' added  (CLASS_DATA_ID: {cur.lastrowid})")


def cmd_add_score():
    print("\n  Add / update score")
    div()
    cmd_list_users(user_type=0)
    student_id = ask_int("Student USER_ID")
    if student_id is None:
        return

    cmd_list_classes()
    class_id = ask_int("CLASS_DATA_ID")
    if class_id is None:
        return

    group_name = ask("Group name  (e.g. Quiz)")
    test_name  = ask("Test name   (e.g. Quiz 1)")
    try:
        score     = int(ask("Score"))
        max_score = int(ask("Max score"))
    except Exception:
        print("  [!] Score must be a number.")
        return

    with _conn() as c:
        row = c.execute(
            "SELECT SCORE_ID FROM student_score_card "
            "WHERE owner=? AND class=? AND group_name=? AND test_name=?",
            (student_id, class_id, group_name, test_name)
        ).fetchone()
        if row:
            c.execute("UPDATE student_score_card SET score=?, max_score=? WHERE SCORE_ID=?",
                      (score, max_score, row["SCORE_ID"]))
            print("\n  ✓ Score updated.")
        else:
            c.execute(
                "INSERT INTO student_score_card (owner, class, group_name, test_name, score, max_score) "
                "VALUES (?,?,?,?,?,?)",
                (student_id, class_id, group_name, test_name, score, max_score)
            )
            print("\n  ✓ Score added.")


def cmd_remove_user():
    print("\n  Remove user")
    div()
    cmd_list_users()
    uid = ask_int("USER_ID to remove")
    if uid is None:
        return

    with _conn() as c:
        row = c.execute("SELECT user_name, user_type FROM users WHERE USER_ID=?", (uid,)).fetchone()
        if not row:
            print(f"  [!] No user with ID {uid}.")
            return

        print(f"\n  [{uid}] {row['user_name']} ({ROLE.get(row['user_type'], '?')})")
        if row["user_type"] == 1:
            print("  [!] Warning: also removes all their classes and score cards.")
        if not confirm("Remove?"):
            print("  Cancelled.")
            return

        c.execute("DELETE FROM student_score_card WHERE owner=?",   (uid,))
        c.execute("DELETE FROM class_data         WHERE teacher=?", (uid,))
        c.execute("DELETE FROM users              WHERE USER_ID=?", (uid,))
    print(f"  ✓ User {uid} removed.")


def cmd_remove_class():
    print("\n  Remove class")
    div()
    cmd_list_classes()
    cid = ask_int("CLASS_DATA_ID to remove")
    if cid is None:
        return

    with _conn() as c:
        row = c.execute("SELECT subject_name FROM class_data WHERE CLASS_DATA_ID=?", (cid,)).fetchone()
        if not row:
            print(f"  [!] No class with ID {cid}.")
            return

        print(f"\n  [{cid}] {row['subject_name']}")
        print("  [!] Warning: also removes all score cards for this class.")
        if not confirm("Remove?"):
            print("  Cancelled.")
            return

        c.execute("DELETE FROM student_score_card WHERE class=?",         (cid,))
        c.execute("DELETE FROM class_data         WHERE CLASS_DATA_ID=?", (cid,))
    print(f"  ✓ Class {cid} removed.")


def cmd_list_users(user_type: int | None = None):
    with _conn() as c:
        if user_type is not None:
            rows = c.execute(
                "SELECT USER_ID, user_name, login_user_name, user_type FROM users "
                "WHERE user_type=? ORDER BY user_name", (user_type,)
            ).fetchall()
        else:
            rows = c.execute(
                "SELECT USER_ID, user_name, login_user_name, user_type FROM users "
                "ORDER BY user_type, user_name"
            ).fetchall()
    label = "Users" if user_type is None else ROLE.get(user_type, "Users").capitalize() + "s"
    print(f"\n  {label}")
    div()
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  [{r['USER_ID']:>3}]  {r['user_name']:<24}  @{r['login_user_name']:<20}  {ROLE.get(r['user_type'],'?')}")
    div()


def cmd_list_classes():
    with _conn() as c:
        rows = c.execute(
            "SELECT CLASS_DATA_ID, subject_name, teacher FROM class_data ORDER BY subject_name"
        ).fetchall()
    print("\n  Classes")
    div()
    if not rows:
        print("  (none)")
    for r in rows:
        print(f"  [{r['CLASS_DATA_ID']:>3}]  {r['subject_name']:<28}  teacher ID: {r['teacher']}")
    div()


def cmd_list_scores():
    print("\n  List scores")
    div()
    cmd_list_users(user_type=0)
    student_id = ask_int("Student USER_ID")
    if student_id is None:
        return

    cmd_list_classes()
    class_id = ask_int("CLASS_DATA_ID")
    if class_id is None:
        return

    with _conn() as c:
        rows = c.execute(
            "SELECT group_name, test_name, score, max_score FROM student_score_card "
            "WHERE owner=? AND class=? ORDER BY group_name, SCORE_ID",
            (student_id, class_id)
        ).fetchall()

    if not rows:
        print("  (no scores)")
        return
    cur_group = None
    for r in rows:
        if r["group_name"] != cur_group:
            cur_group = r["group_name"]
            print(f"\n  {cur_group}")
        score_str = str(r["score"]) if r["score"] is not None else "—"
        print(f"    {r['test_name']:<24}  {score_str} / {r['max_score']}")
    div()


# ── main ──────────────────────────────────────────────────────────────────────

COMMANDS = {
    "add student":  lambda: cmd_add_user(0),
    "add teacher":  lambda: cmd_add_user(1),
    "add class":    cmd_add_class,
    "add score":    cmd_add_score,
    "list users":   cmd_list_users,
    "list classes": cmd_list_classes,
    "list scores":  cmd_list_scores,
    "remove user":  cmd_remove_user,
    "remove class": cmd_remove_class,
}

HELP = """
  add student      add teacher      add class      add score
  list users       list classes     list scores
  remove user      remove class
  quit
"""

def main():
    print(f"\n  DB Manager  —  {DB_NAME}  ({HASHING})")
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
        elif cmd in ("help", "?"):
            print(HELP)
        elif cmd == "":
            pass
        elif cmd in COMMANDS:
            COMMANDS[cmd]()
        else:
            print("  [!] Unknown command. Type 'help'.")

if __name__ == "__main__":
    main()
