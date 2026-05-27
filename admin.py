"""
manage.py — interactive terminal DB manager

Commands:
    add student        — add a new student
    add teacher        — add a new teacher
    add class          — add a new class under a teacher
    enroll             — enroll a student into a class
    add score          — add/update a score entry for a student in a class
    list users         — list all users
    list classes       — list all classes
    list enrollments   — list all enrollments
    list scores        — list scores for a student in a class
    remove user        — remove a user by ID
    remove class       — remove a class by ID
    quit               — exit
"""

import sqlite3
import sys
import os

import utils.argon_utils as argon
def hash_password(pw: str) -> str:
    return argon.hash_password(pw)
HASHING = "argon2"

DB_NAME = "MAIN_DB.db"

# ── db connection ─────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    if not os.path.exists(DB_NAME):
        print(f"[error] '{DB_NAME}' not found. Run the app first to initialize the DB.")
        sys.exit(1)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ── helpers ───────────────────────────────────────────────────────────────────

ROLE_LABEL = {0: "student", 1: "teacher"}

def _prompt(label: str, required: bool = True) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val or not required:
            return val
        print("  [!] this field is required.")

def _prompt_int(label: str) -> int | None:
    try:
        return int(_prompt(label))
    except ValueError:
        print("  [!] must be a number.")
        return None

def _confirm(msg: str) -> bool:
    return input(f"  {msg} [y/N]: ").strip().lower() == "y"

def _divider():
    print("─" * 52)

# ── list helpers ──────────────────────────────────────────────────────────────

def _print_users(rows):
    if not rows:
        print("  (none)")
        return
    for r in rows:
        role = ROLE_LABEL.get(r["user_type"], "?")
        print(f"  [{r['USER_ID']:>3}]  {r['user_name']:<24}  @{r['login_user_name']:<20}  {role}")

def _print_classes(rows):
    if not rows:
        print("  (none)")
        return
    for r in rows:
        print(f"  [{r['CLASS_DATA_ID']:>3}]  {r['subject_name']:<28}  teacher ID: {r['teacher']}")

# ── commands: users ───────────────────────────────────────────────────────────

def cmd_add_user(user_type: int):
    role = ROLE_LABEL[user_type]
    print(f"\n  Add {role}")
    _divider()

    user_name  = _prompt("Display name")
    login_name = _prompt("Login username")

    with _connect() as conn:
        if conn.execute(
            "SELECT 1 FROM users WHERE login_user_name = ?", (login_name,)
        ).fetchone():
            print(f"  [!] Username '{login_name}' is already taken.")
            return

    password = _prompt("Password")
    pw_hash  = hash_password(password)

    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (user_name, login_user_name, login_user_pass, user_type) "
            "VALUES (?, ?, ?, ?)",
            (user_name, login_name, pw_hash, user_type),
        )
        uid = cur.lastrowid

    print(f"\n   {role.capitalize()} '{user_name}' added  (ID: {uid})")


def cmd_remove_user():
    print("\n  Remove user")
    _divider()
    cmd_list_users()

    uid = _prompt_int("USER_ID to remove")
    if uid is None:
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

        conn.execute("DELETE FROM enrollments        WHERE student_id = ?", (uid,))
        conn.execute("DELETE FROM student_score_card WHERE owner      = ?", (uid,))
        conn.execute("DELETE FROM class_data         WHERE teacher    = ?", (uid,))
        conn.execute("DELETE FROM users              WHERE USER_ID    = ?", (uid,))

    print(f"   User {uid} removed.")


def cmd_list_users():
    print("\n  Users")
    _divider()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT USER_ID, user_name, login_user_name, user_type "
            "FROM users ORDER BY user_type, user_name"
        ).fetchall()
    _print_users(rows)
    _divider()

# ── commands: classes ─────────────────────────────────────────────────────────

def cmd_add_class():
    print("\n  Add class")
    _divider()

    # show teachers to pick from
    with _connect() as conn:
        teachers = conn.execute(
            "SELECT USER_ID, user_name FROM users WHERE user_type = 1 ORDER BY user_name"
        ).fetchall()

    if not teachers:
        print("  [!] No teachers found. Add a teacher first.")
        return

    print("  Teachers:")
    for t in teachers:
        print(f"    [{t['USER_ID']:>3}]  {t['user_name']}")

    teacher_id = _prompt_int("Teacher ID")
    if teacher_id is None:
        return

    with _connect() as conn:
        if not conn.execute(
            "SELECT 1 FROM users WHERE USER_ID = ? AND user_type = 1", (teacher_id,)
        ).fetchone():
            print("  [!] Teacher not found.")
            return

    subject = _prompt("Subject / class name")

    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO class_data (teacher, subject_name) VALUES (?, ?)",
            (teacher_id, subject),
        )
        cid = cur.lastrowid

    print(f"\n  Class '{subject}' added  (CLASS_DATA_ID: {cid})")


def cmd_remove_class():
    print("\n  Remove class")
    _divider()
    cmd_list_classes()

    cid = _prompt_int("CLASS_DATA_ID to remove")
    if cid is None:
        return

    with _connect() as conn:
        row = conn.execute(
            "SELECT subject_name FROM class_data WHERE CLASS_DATA_ID = ?", (cid,)
        ).fetchone()
        if not row:
            print(f"  [!] No class with ID {cid}.")
            return

        print(f"\n  About to remove: [{cid}] {row['subject_name']}")
        print("  [!] Warning: also removes all enrollments and score cards for this class.")

        if not _confirm("Are you sure?"):
            print("  Cancelled.")
            return

        conn.execute("DELETE FROM student_score_card WHERE class      = ?", (cid,))
        conn.execute("DELETE FROM enrollments        WHERE class_id   = ?", (cid,))
        conn.execute("DELETE FROM class_data         WHERE CLASS_DATA_ID = ?", (cid,))

    print(f"   Class {cid} removed.")


def cmd_list_classes():
    print("\n  Classes")
    _divider()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT CLASS_DATA_ID, subject_name, teacher FROM class_data ORDER BY subject_name"
        ).fetchall()
    _print_classes(rows)
    _divider()

# ── commands: enrollments ─────────────────────────────────────────────────────

def cmd_enroll():
    print("\n  Enroll student into class")
    _divider()

    cmd_list_users()
    student_id = _prompt_int("Student USER_ID")
    if student_id is None:
        return

    with _connect() as conn:
        if not conn.execute(
            "SELECT 1 FROM users WHERE USER_ID = ? AND user_type = 0", (student_id,)
        ).fetchone():
            print("  [!] Student not found.")
            return

    cmd_list_classes()
    class_id = _prompt_int("CLASS_DATA_ID")
    if class_id is None:
        return

    with _connect() as conn:
        if not conn.execute(
            "SELECT 1 FROM class_data WHERE CLASS_DATA_ID = ?", (class_id,)
        ).fetchone():
            print("  [!] Class not found.")
            return

        if conn.execute(
            "SELECT 1 FROM enrollments WHERE student_id = ? AND class_id = ?",
            (student_id, class_id)
        ).fetchone():
            print("  [!] Student is already enrolled in that class.")
            return

        conn.execute(
            "INSERT INTO enrollments (student_id, class_id) VALUES (?, ?)",
            (student_id, class_id),
        )

    print(f"\n   Student {student_id} enrolled in class {class_id}.")


def cmd_list_enrollments():
    print("\n  Enrollments")
    _divider()
    with _connect() as conn:
        rows = conn.execute("""
            SELECT e.student_id, u.user_name, e.class_id, c.subject_name
            FROM enrollments e
            JOIN users      u ON u.USER_ID       = e.student_id
            JOIN class_data c ON c.CLASS_DATA_ID = e.class_id
            ORDER BY c.subject_name, u.user_name
        """).fetchall()

    if not rows:
        print("  (none)")
    else:
        cur_class = None
        for r in rows:
            if r["subject_name"] != cur_class:
                cur_class = r["subject_name"]
                print(f"\n  [{r['class_id']}] {cur_class}")
            print(f"       student [{r['student_id']:>3}]  {r['user_name']}")
    _divider()

# ── commands: scores ──────────────────────────────────────────────────────────

def cmd_add_score():
    print("\n  Add / update score")
    _divider()

    cmd_list_enrollments()

    student_id = _prompt_int("Student USER_ID")
    if student_id is None:
        return

    class_id = _prompt_int("CLASS_DATA_ID")
    if class_id is None:
        return

    with _connect() as conn:
        if not conn.execute(
            "SELECT 1 FROM enrollments WHERE student_id = ? AND class_id = ?",
            (student_id, class_id)
        ).fetchone():
            print("  [!] That student is not enrolled in that class.")
            return

    group_name = _prompt("Group name  (e.g. Quiz, Activity, Exam)")
    test_name  = _prompt("Test name   (e.g. Quiz 1, Midterm)")

    try:
        score     = int(_prompt("Score"))
        max_score = int(_prompt("Max score"))
    except ValueError:
        print("  [!] Score and max score must be numbers.")
        return

    with _connect() as conn:
        existing = conn.execute(
            "SELECT SCORE_ID FROM student_score_card "
            "WHERE owner = ? AND class = ? AND group_name = ? AND test_name = ?",
            (student_id, class_id, group_name, test_name)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE student_score_card SET score = ?, max_score = ? WHERE SCORE_ID = ?",
                (score, max_score, existing["SCORE_ID"])
            )
            print("\n   Score updated.")
        else:
            conn.execute(
                "INSERT INTO student_score_card "
                "(owner, class, group_name, test_name, score, max_score) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (student_id, class_id, group_name, test_name, score, max_score)
            )
            print("\n   Score added.")


def cmd_list_scores():
    print("\n  List scores")
    _divider()

    cmd_list_enrollments()

    student_id = _prompt_int("Student USER_ID")
    if student_id is None:
        return
    class_id = _prompt_int("CLASS_DATA_ID")
    if class_id is None:
        return

    with _connect() as conn:
        rows = conn.execute(
            "SELECT group_name, test_name, score, max_score "
            "FROM student_score_card WHERE owner = ? AND class = ? "
            "ORDER BY group_name, SCORE_ID",
            (student_id, class_id)
        ).fetchall()

    if not rows:
        print("  (no scores yet)")
        return

    cur_group = None
    for r in rows:
        if r["group_name"] != cur_group:
            cur_group = r["group_name"]
            print(f"\n  {cur_group}")
        score_str = str(r["score"]) if r["score"] is not None else "—"
        print(f"    {r['test_name']:<24}  {score_str} / {r['max_score']}")
    _divider()

# ── main loop ─────────────────────────────────────────────────────────────────

COMMANDS = {
    "add student":       lambda: cmd_add_user(0),
    "add teacher":       lambda: cmd_add_user(1),
    "add class":         cmd_add_class,
    "enroll":            cmd_enroll,
    "add score":         cmd_add_score,
    "list users":        cmd_list_users,
    "list classes":      cmd_list_classes,
    "list enrollments":  cmd_list_enrollments,
    "list scores":       cmd_list_scores,
    "remove user":       cmd_remove_user,
    "remove class":      cmd_remove_class,
}

HELP = """
  Commands:
    add student        add a new student
    add teacher        add a new teacher
    add class          add a new class under a teacher
    enroll             enroll a student into a class
    add score          add or update a score for a student
    list users         list all users
    list classes       list all classes
    list enrollments   show who is in which class
    list scores        show scores for a student in a class
    remove user        remove a user by ID
    remove class       remove a class by ID
    quit               exit
"""

def main():
    print(f"\n  DB Manager  —  {DB_NAME}")
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
        elif cmd in ("help", "?"):
            print(HELP)
        elif cmd == "":
            pass
        elif cmd in COMMANDS:
            COMMANDS[cmd]()
        else:
            print("  [!] Unknown command. Type 'help' to see available commands.")

if __name__ == "__main__":
    main()
