import os
from Msystem.Objects import User

import sqlite3

DB_NAME = "MAIN_DB.db"


_connection: sqlite3.Connection
_cursor    : sqlite3.Cursor

def _init_db():
    global _cursor, _connection
    db_exists = os.path.exists(DB_NAME)
    
    if not db_exists:
        _repopulate()
    else:
        _connection = sqlite3.connect(DB_NAME)
        _cursor     = _connection.cursor()

# connect to the server
def _repopulate():
    global _cursor, _connection
    _connection = sqlite3.connect(DB_NAME, timeout=10, check_same_thread=False)
    _connection.execute("PRAGMA journal_mode=WAL")
    _cursor     = _connection.cursor()
    # initialize users_table
    _cursor.execute("CREATE TABLE users ("
                    "  USER_ID         INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  user_name       TEXT    NOT NULL,"
                    "  login_user_name TEXT    NOT NULL,"
                    "  login_user_pass TEXT    NOT NULL,"
                    "  user_type       INTEGER)") # (0 = student, 1 = teacher, other = unknown)

    _cursor.execute("CREATE TABLE student_score_card ("
                    "  SCORE_ID   INTEGER PRIMARY KEY AUTOINCREMENT," #
                    "  owner      INTEGER NOT NULL,"    # USER_ID from users
                    "  class      INTEGER NOT NULL,"    # CLASS_DATA_ID from  class_data

                    "  group_name TEXT    NOT NULL,"    # (like "quiz", "activity")
                    "  test_name  TEXT    NOT NULL,"    # (like "quiz 1" or "project 1")
                    "  score      INTEGER,"
                    "  max_score  INTEGER)")

    _cursor.execute("CREATE TABLE class_data ("
                    "  CLASS_DATA_ID INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  teacher       INTEGER NOT NULL," # (USER_ID from users)

                    "  subject_name  TEXT    NOT NULL)")
    _connection.commit()


def get_user(user_name: str) -> User | None:
    row = _cursor.execute(
        "SELECT USER_ID, user_name, login_user_name, login_user_pass, user_type "
        "FROM users WHERE login_user_name = ?",
        (user_name,)
    ).fetchone()

    if row is None:
        return None

    user                  = User(row[2], row[3])
    user.user_id          = row[0]
    user.user_name        = row[1]
    user.user_type        = row[4]

    return user
def get_user_byID(user_id: int) -> User | None:
    row = _cursor.execute(
        "SELECT USER_ID, user_name, login_user_name, login_user_pass, user_type "
        "FROM users WHERE USER_ID = ?",
        (user_id,)
    ).fetchone()

    if row is None:
        return None

    user                  = User(row[2], row[3])
    user.user_id          = row[0]
    user.user_name        = row[1]
    user.user_type        = row[4]

    # if user.is_student():
    #     # fetch all score cards for this student across all classes
    #     user.data = _cursor.execute(
    #         "SELECT SCORE_ID, class, group_name, test_name, score, max_score "
    #         "FROM student_score_card WHERE owner = ?",
    #         (user.user_id,)
    #     ).fetchall()

    # elif user.is_teacher():
    #     # fetch all classes this teacher owns
    #     user.data = _cursor.execute(
    #         "SELECT CLASS_DATA_ID, subject_name "
    #         "FROM class_data WHERE teacher = ?",
    #         (user.user_id,)
    #     ).fetchall()

    return user

def fetch_teacher_data(teacher_id: int, class_id: int) -> dict:
    """
    Returns data shaped exactly for the teacher dashboard template.
 
    {
        section_selections: [{"value": class_id, "content": subject_name}],
        students:           [{"id": str, "name": str}],
        groups:             [str],
        columns:            [{"id": str, "name": str, "group": str, "max": int}],
        scores:             {student_id_str: {col_id: score}},
        averages:           {student_id_str: str},
    }
 
    col_id is built as  "<group_initial><test_name>" slugified,
    e.g. group="Quiz" test_name="Quiz 1"  ->  id="quiz_quiz_1"
    The same id is stored in student_score_card so teacher JS can match them.
    """
    # all classes for the section dropdown
    cls_rows = _cursor.execute(
        "SELECT CLASS_DATA_ID, subject_name FROM class_data WHERE teacher = ? ORDER BY subject_name",
        (teacher_id,)
    ).fetchall()
    section_selections = [{"value": str(r[0]), "content": r[1]} for r in cls_rows]
 
    # students enrolled in the selected class
    student_rows = _cursor.execute("""
        SELECT u.USER_ID, u.user_name FROM users u
        JOIN enrollments e ON e.student_id = u.USER_ID
        WHERE e.class_id = ? ORDER BY u.user_name
    """, (class_id,)).fetchall()
    students = [{"id": str(r[0]), "name": r[1]} for r in student_rows]
 
    # derive groups + columns from the score cards in this class
    # we read all score cards for this class to discover structure
    structure_rows = _cursor.execute(
        "SELECT DISTINCT group_name, test_name, max_score "
        "FROM student_score_card WHERE class = ? ORDER BY SCORE_ID",
        (class_id,)
    ).fetchall()

    seen_cols = {}   # col_id -> col dict, ordered
    groups    = []   # ordered, deduplicated group names

    for row in structure_rows:
        group_name = row[0]
        test_name  = row[1]
        max_score  = row[2]
        col_id     = f"{group_name}_{test_name}".lower().replace(" ", "_")

        if group_name not in groups:
            groups.append(group_name)

        if col_id not in seen_cols:
            seen_cols[col_id] = {
                "id":    col_id,
                "name":  test_name,
                "group": group_name,
                "max":   max_score,
            }

    columns = list(seen_cols.values())

    # scores per student
    scores   = {}
    averages = {}

    for s in students:
        sid     = int(s["id"])
        sid_str = s["id"]

        score_rows = _cursor.execute(
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

def fetch_student_data(student_id: int) -> dict:
    """
    Returns data shaped exactly for the student dashboard template.
 
    {
        classes: [
            {
                name:      str,
                published: bool,        (always True — only published scores are stored)
                summary:   {average, grade, passing},
                groups: [
                    {
                        name:    str,
                        average: str,
                        columns: [{"name", "score", "max", "pct"}],
                    }
                ],
            }
        ]
    }
    """
    class_rows = _cursor.execute("""
        SELECT c.CLASS_DATA_ID, c.subject_name FROM class_data c
        JOIN enrollments e ON e.class_id = c.CLASS_DATA_ID
        WHERE e.student_id = ? ORDER BY c.subject_name
    """, (student_id,)).fetchall()
 
    classes = []
 
    for cls_row in class_rows:
        class_id     = cls_row[0]
        subject_name = cls_row[1]

        score_rows = _cursor.execute(
            "SELECT group_name, test_name, score, max_score "
            "FROM student_score_card WHERE owner = ? AND class = ? ORDER BY SCORE_ID",
            (student_id, class_id)
        ).fetchall()

        # build groups with columns
        group_map: dict[str, list] = {}
        for sc in score_rows:
            score     = sc[2]
            max_score = sc[3]
            pct       = round(score / max_score * 100, 1) if (score is not None and max_score) else None
            group_map.setdefault(sc[0], []).append({
                "name":  sc[1],
                "score": score,
                "max":   max_score,
                "pct":   pct,
            })

        # compute overall average and grade
        all_scores = [col for cols in group_map.values() for col in cols]
        earned = sum(c["score"] for c in all_scores if c["score"] is not None)
        total  = sum(c["max"]   for c in all_scores if c["score"] is not None)
        avg    = earned / total * 100 if total else None

        def grade(p):
            if p is None:
                return "—"
            if p >= 90:
                return "A"
            if p >= 80:
                return "B"
            if p >= 75:
                return "C"
            if p >= 70:
                return "D"
            return "F"

        # per-group averages
        groups_out = []
        for group_name, cols in group_map.items():
            g_earned = sum(c["score"] for c in cols if c["score"] is not None)
            g_total  = sum(c["max"]   for c in cols if c["score"] is not None)
            groups_out.append({
                "name":    group_name,
                "average": f"{g_earned / g_total * 100:.1f}%" if g_total else "—",
                "columns": cols,
            })

        classes.append({
            "name":      subject_name,
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
    """
    Upserts scores from the teacher dashboard into student_score_card.
 
    cols   — list of {id, name, group, max}
    scores — {student_id_str: {col_id: score_or_null}}
 
    Each col maps to one group_name + test_name pair.
    For each student + col we either INSERT a new row or UPDATE the existing one.
    """
    # build a lookup: col_id -> (group_name, test_name, max_score)
    col_map = {
        col["id"]: (col["group"], col["name"], col["max"])
        for col in cols
    }
 
    for student_id_str, student_scores in scores.items():
        student_id = int(student_id_str)
 
        for col_id, score in student_scores.items():
            if col_id not in col_map:
                continue  # unknown col, skip
 
            group_name, test_name, max_score = col_map[col_id]
 
            # check if a row already exists for this student + class + test
            existing = _cursor.execute(
                "SELECT SCORE_ID FROM student_score_card "
                "WHERE owner = ? AND class = ? AND group_name = ? AND test_name = ?",
                (student_id, class_id, group_name, test_name)
            ).fetchone()
 
            if existing:
                _cursor.execute(
                    "UPDATE student_score_card SET score = ?, max_score = ? "
                    "WHERE SCORE_ID = ?",
                    (score, max_score, existing[0])
                )
            else:
                _cursor.execute(
                    "INSERT INTO student_score_card "
                    "(owner, class, group_name, test_name, score, max_score) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (student_id, class_id, group_name, test_name, score, max_score)
                )
 
    _connection.commit()


if __name__ == "__main__":
    exit()
else:
    _init_db()

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
