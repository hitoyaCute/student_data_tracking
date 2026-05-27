from Objects import User

import sqlite3
import utils.argon_utils as argon

DB_NAME = "MAIN_DB.db"


# connect to the server
_connection = sqlite3.connect(DB_NAME)
_cursor     = _connection.cursor()

# if DB is empty
if _cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    # initialize users_table
    _cursor.execute("CREATE TABLE users ("
                    "  USER_ID         INTIGER PRIMARY KEY NOT NULL,"
                    "  user_name       TEXT    NOT NULL,"
                    "  login_user_name TEXT    NOT NULL,"
                    "  login_user_pass TEXT    NOT NULL,"
                    "  user_type       INTIGER NOT NULL)") # (0 = student, 1 = teacher, other = unknown)

    _cursor.execute("CREATE TABLE student_score_card ("
                    "  SCORE_ID   INTIGER PRIMARY KEY NOT NULL," #
                    "  owner      INTIGER NOT NULL,"    # USER_ID from users
                    "  class      INTIGER NOT NULL,"    # CLASS_DATA_ID from  class_data

                    "  group_name TEXT    NOT NULL,"    # (like "quiz", "activity")
                    "  test_name  TEXT    NOT NULL,"    # (like "quiz 1" or "project 1")
                    "  score      INTIGER,"
                    "  max_score  INTIGER)")

    _cursor.execute("CREATE TABLE class_data ("
                    "  CLASS_DATA_ID INTIGER PRIMARY KEY NOT NULL,"
                    "  teacher       INTIGER NOT NULL," # (USER_ID from users)

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
