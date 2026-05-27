import flask
from datetime import datetime, timezone
import flask_socketio

import random as rd

# email
import utils.argon_utils as argon



app = flask.Flask(__name__)

socketio = flask_socketio.SocketIO(app, cors_allowed_origins="*")


@app.route("/")
def root():
    return flask.redirect("/login")

@app.route("/login", methods=["POST", "GET"])
def login():
    # TODO:
    # add DB and verification syhstem
    if flask.request.method == "POST":
        print(flask.request.form)
        print(tuple(flask.request.form.items()))
        password = flask.request.form.get("password")
        if isinstance(password, str):
           print(argon.hash_password(password))
    return flask.render_template("login.html")


@app.route("/dashboard/teacher")
def dashboard_teacher():
    # TODO: pull real data from DB; stub data shown below
    # pass a precomputed data
    return flask.render_template(
        "dashboard-teacher.html",
        teacher_name="Ms. Reyes",
        section_id="s1",
        section_selections=[
            {"value": "s1", "content": "Grade 10 - Rizal"},
            {"value": "s2", "content": "Grade 10 - Bonifacio"},
        ],
        students=[
            [
                {"id": str(x + 1), "name": f"Juan dela Cruz ({x + 1})"},
                {"id": str(x + 1), "name": f"Maria Santos ({x + 1})"},
                {"id": str(x + 1), "name": f"Pedro Reyes ({x + 1})"},
            ][x % 3]
            for x in range(4)
        ],
        groups=["Quiz", "Activity", "Exam"],
        columns=[
            {"id": "q1", "name": "Quiz 1", "group": "Quiz", "max": 50},
            {"id": "q2", "name": "Quiz 2", "group": "Quiz", "max": 50},
            {"id": "a1", "name": "Act 1", "group": "Activity", "max": 100},
            {"id": "e1", "name": "Midterm", "group": "Exam", "max": 100},
        ],
        scores={
            "1": {"q1": 45, "q2": 38, "a1": 88, "e1": 79},
            "2": {"q1": 50, "q2": 47, "a1": 95, "e1": 91},
            "3": {"q1": 30, "q2": 28, "a1": 72, "e1": 65},
            "4": {"q1": 30, "q2": 28, "a1": 72, "e1": 65},
        },
        averages={str(x + 1): str(rd.randint(75,99)) for x in range(4)},
    )


@app.route("/dashboard/student")
def dashboard_student():
    # pass a precomputed data
    return flask.render_template(
        "dashboard-student.html",
        student={"name": "Juan dela Cruz"},
        classes=[
            {
                "name": "Mathematics",
                "published": True,
                "summary": {"average": "84.2%", "grade": "B", "passing": True},
                "groups": [
                    {
                        "name": "Quiz",
                        "average": "88.0%",
                        "columns": [
                            {"name": "Quiz 1", "score": 45, "max": 50, "pct": 90.0},
                            {"name": "Quiz 2", "score": 38, "max": 50, "pct": 76.0},
                        ],
                    },
                ],
            },
            {
                "name": "Science",
                "published": False,  # shows unpublished notice, hides groups
                "summary": {"average": "—", "grade": "—", "passing": False},
                "groups": [],
            },
        ],
    )


# WebSocket events
@socketio.on("sync")
def handle_sync(data):
    """
    Payload shape:
    {
        teacher_name: str
        section:  str,
        groups:   list[str],
        cols:     list[{id, name, group, max}],
        scores:   {student_id: {col_id: score}},
    }
    """
    teacher_name = data.get("teacher_name")
    section = data.get("section")
    groups = data.get("groups", [])
    cols = data.get("cols", [])
    scores = data.get("scores", {})
    print(f"synced, teacher_name: {teacher_name}\n\t{section, groups, cols, scores = }")

    # TODO: persist to DB here
    # save_grades_to_db(section, groups, cols, scores)

    saved_at = datetime.now(timezone.utc).isoformat()
    flask_socketio.emit("sync_ack", {"saved_at": saved_at})


@socketio.on("publish")
def handle_publish(data):
    """
    Same payload as sync — but also triggers email notifications
    to every student in the section.
    """
    teacher_name = data.get("teacher_name")
    section = data.get("section")
    groups = data.get("groups", [])
    cols = data.get("cols", [])
    scores = data.get("scores", {})
    print(f"a teacher submited a grades, teacher_name: {teacher_name}\n\t{section, groups, cols, scores}")

    # TODO: persist to DB
    # save_grades_to_db(section, groups, cols, scores)

    # TODO: send email notifications
    # notify_students(section, published=True)

    published_at = datetime.now(timezone.utc).isoformat()
    flask_socketio.emit("publish_ack", {"published_at": published_at})


if __name__ == "__main__":
    # use socketio.run instead of app.run to support WebSockets
    socketio.run(app, host="0.0.0.0", port=8008, debug=True)

'''

# sync/publish
teacher_name = data.get("teacher_name") # teacher's name
section = data.get("section")           # name of the selected section
groups = data.get("groups", [])         # groups like "activity, quiz"
cols = data.get("cols", [])             # specifics like activity1, project1 or final_exam in order
scores = data.get("scores", {})         # all the scores on order




DB structure

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
