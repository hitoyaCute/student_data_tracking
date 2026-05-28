import os
import sqlite3
from Msystem.Objects import User

DB_NAME = "MAIN_DB.db"


def _conn() -> sqlite3.Connection:
    """Fresh connection per call — safe across threads."""
    c = sqlite3.connect(DB_NAME, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    if not os.path.exists(DB_NAME):
        with _conn() as c:
            c.executescript("""
                CREATE TABLE users (
                    USER_ID         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name       TEXT    NOT NULL,
                    login_user_name TEXT    NOT NULL,
                    login_user_pass TEXT    NOT NULL,
                    user_type       INTEGER
                );
                CREATE TABLE class_data (
                    CLASS_DATA_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher       INTEGER NOT NULL,
                    subject_name  TEXT    NOT NULL
                );
                CREATE TABLE student_score_card (
                    SCORE_ID   INTEGER PRIMARY KEY AUTOINCREMENT,
                    owner      INTEGER NOT NULL,
                    class      INTEGER NOT NULL,
                    group_name TEXT    NOT NULL,
                    test_name  TEXT    NOT NULL,
                    score      INTEGER,
                    max_score  INTEGER
                );
            """)


# ── users ─────────────────────────────────────────────────────────────────────

def get_user(user_name: str) -> User | None:
    with _conn() as c:
        row = c.execute(
            "SELECT USER_ID, user_name, login_user_name, login_user_pass, user_type "
            "FROM users WHERE login_user_name = ?",
            (user_name,)
        ).fetchone()
    if row is None:
        return None
    user                 = User(row[2], row[3])
    user.user_id         = row[0]
    user.user_name       = row[1]
    user.user_type       = row[4]
    return user


def get_user_byID(user_id: int) -> User | None:
    with _conn() as c:
        row = c.execute(
            "SELECT USER_ID, user_name, login_user_name, login_user_pass, user_type "
            "FROM users WHERE USER_ID = ?",
            (user_id,)
        ).fetchone()
    if row is None:
        return None
    user                 = User(row[2], row[3])
    user.user_id         = row[0]
    user.user_name       = row[1]
    user.user_type       = row[4]
    return user


# ── teacher dashboard ─────────────────────────────────────────────────────────

def fetch_teacher_data(teacher_id: int, class_id: int) -> dict:
    with _conn() as c:
        # section dropdown
        cls_rows = c.execute(
            "SELECT CLASS_DATA_ID, subject_name FROM class_data "
            "WHERE teacher = ? ORDER BY subject_name",
            (teacher_id,)
        ).fetchall()
        section_selections = [{"value": str(r[0]), "content": r[1]} for r in cls_rows]

        # students — derived from score cards (no enrollments table)
        student_rows = c.execute("""
            SELECT DISTINCT u.USER_ID, u.user_name FROM users u
            JOIN student_score_card sc ON sc.owner = u.USER_ID
            WHERE sc.class = ? ORDER BY u.user_name
        """, (class_id,)).fetchall()
        students = [{"id": str(r[0]), "name": r[1]} for r in student_rows]

        # column structure from score cards
        structure_rows = c.execute(
            "SELECT DISTINCT group_name, test_name, max_score "
            "FROM student_score_card WHERE class = ? ORDER BY SCORE_ID",
            (class_id,)
        ).fetchall()

        groups    = []
        seen_cols = {}
        for row in structure_rows:
            col_id = f"{row[0]}_{row[1]}".lower().replace(" ", "_")
            if row[0] not in groups:
                groups.append(row[0])
            if col_id not in seen_cols:
                seen_cols[col_id] = {"id": col_id, "name": row[1],
                                     "group": row[0], "max": row[2]}
        columns = list(seen_cols.values())

        # scores + averages per student
        scores   = {}
        averages = {}
        for s in students:
            sid     = int(s["id"])
            sid_str = s["id"]
            score_rows = c.execute(
                "SELECT group_name, test_name, score, max_score "
                "FROM student_score_card WHERE owner = ? AND class = ?",
                (sid, class_id)
            ).fetchall()
            flat          = {}
            earned, total = 0.0, 0.0
            for sc in score_rows:
                col_id = f"{sc[0]}_{sc[1]}".lower().replace(" ", "_")
                flat[col_id] = sc[2]
                if sc[2] is not None and sc[3]:
                    earned += sc[2]
                    total  += sc[3]
            scores[sid_str]   = flat
            averages[sid_str] = f"{earned / total * 100:.1f}" if total else "—"

    return {
        "section_selections": section_selections,
        "students":           students,
        "groups":             groups,
        "columns":            columns,
        "scores":             scores,
        "averages":           averages,
    }


# ── student dashboard ─────────────────────────────────────────────────────────

def fetch_student_data(student_id: int) -> dict:
    with _conn() as c:
        class_rows = c.execute(
            "SELECT DISTINCT c.CLASS_DATA_ID, c.subject_name FROM class_data c "
            "JOIN student_score_card sc ON sc.class = c.CLASS_DATA_ID "
            "WHERE sc.owner = ? ORDER BY c.subject_name",
            (student_id,)
        ).fetchall()

        classes = []
        for cls in class_rows:
            score_rows = c.execute(
                "SELECT group_name, test_name, score, max_score "
                "FROM student_score_card WHERE owner = ? AND class = ? ORDER BY SCORE_ID",
                (student_id, cls[0])
            ).fetchall()

            group_map: dict[str, list] = {}
            for sc in score_rows:
                pct = round(sc[2] / sc[3] * 100, 1) if (sc[2] is not None and sc[3]) else None
                group_map.setdefault(sc[0], []).append({
                    "name":  sc[1],
                    "score": sc[2],
                    "max":   sc[3],
                    "pct":   pct,
                })

            all_cols = [col for cols in group_map.values() for col in cols]
            earned   = sum(col["score"] for col in all_cols if col["score"] is not None)
            total    = sum(col["max"]   for col in all_cols if col["score"] is not None)
            avg      = earned / total * 100 if total else None

            def grade(p):
                if p is None: return "—"
                if p >= 90:   return "A"
                if p >= 80:   return "B"
                if p >= 75:   return "C"
                if p >= 70:   return "D"
                return "F"

            groups_out = []
            for g_name, cols in group_map.items():
                g_earned = sum(col["score"] for col in cols if col["score"] is not None)
                g_total  = sum(col["max"]   for col in cols if col["score"] is not None)
                groups_out.append({
                    "name":    g_name,
                    "average": f"{g_earned / g_total * 100:.1f}%" if g_total else "—",
                    "columns": cols,
                })

            classes.append({
                "name":      cls[1],
                "published": True,
                "summary": {
                    "average": f"{avg:.1f}%" if avg is not None else "—",
                    "grade":   grade(avg),
                    "passing": avg >= 75 if avg is not None else False,
                },
                "groups": groups_out,
            })

    return {"classes": classes}


# ── save grades (sync / publish) ──────────────────────────────────────────────

def save_grades(class_id: int, cols: list, scores: dict) -> None:
    col_map = {col["id"]: (col["group"], col["name"], col["max"]) for col in cols}

    with _conn() as c:
        for student_id_str, student_scores in scores.items():
            student_id = int(student_id_str)
            for col_id, score in student_scores.items():
                if col_id not in col_map:
                    continue
                group_name, test_name, max_score = col_map[col_id]
                existing = c.execute(
                    "SELECT SCORE_ID FROM student_score_card "
                    "WHERE owner = ? AND class = ? AND group_name = ? AND test_name = ?",
                    (student_id, class_id, group_name, test_name)
                ).fetchone()
                if existing:
                    c.execute(
                        "UPDATE student_score_card SET score = ?, max_score = ? WHERE SCORE_ID = ?",
                        (score, max_score, existing[0])
                    )
                else:
                    c.execute(
                        "INSERT INTO student_score_card "
                        "(owner, class, group_name, test_name, score, max_score) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (student_id, class_id, group_name, test_name, score, max_score)
                    )


# ── init on import ────────────────────────────────────────────────────────────

if __name__ != "__main__":
    init_db()

'''DB structure
# all of the user registered to the system
users:
    USER_ID unique int
    user_name       string[32]
    login_user_name string[32]
    login_user_pass string[256] (argon2 hashed)
    user_type       int  (0 = student, 1 = teacher, other = unknown)

    
# info about student's scores which can be used to compute grades
student_score_card:
    SCORE_ID   unique key int
    owner      int (USER_ID from users)
    class      int (CLASS_DATA_ID from class_data)
    
    group_name string[32] (like "quiz", "activity")
    test_name  string[32] (like "quiz 1" or "project 1")
    score      int
    max_score  int
    

# stores all the info about the class
class_data:
    CLASS_DATA_ID unique int
    teacher       int (USER_ID from users)
    
    subject_name  string[32]
'''
