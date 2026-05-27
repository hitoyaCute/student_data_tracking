from Objects import User

import sqlite3
import utils.argon_utils as argon

DB_NAME = "MAIN_DB.db"


# connect to the server
_connection = sqlite3.connect(DB_NAME)
_cursor     = _connection.cursor()

# when theres already a DB
if True:
    # initialize users_table
    _cursor.execute("CREATE TABLE users ("
                    "  USER_ID         INTIGER PRIMARY KEY,"
                    "  user_name       TEXT    NOT NULL,"
                    "  login_user_name TEXT    NOT NULL,"
                    "  login_user_pass TEXT    NOT NULL,"
                    "  user_type       INTIGER NOT NULL)")

    _cursor.execute("CREATE TABLE student_score_card ("
                    "  SCORE_ID        INTIGER PRIMARY KEY,"
                    "  owner           INTIGER NOT NULL,"
                    "  class           INTIGER NOT NULL,"
                    "  group_name      TEXT    NOT NULL,"
                    "  test_name       TEXT    NOT NULL,"
                    "  score           INTIGER,"
                    "  owner           INTIGER NOT NULL,"
                    "  )")

def get_user(user_nam:str) -> User | None:
    pass


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
    students      JSON BLOB # format ["USER_ID",...] # stores all the registered student
'''
