import flask
from datetime import datetime, timezone
import flask_socketio

import random as rd

# email
from Msystem import DB
from Msystem.Objects import User

app = flask.Flask(__name__)
app.secret_key = "change-me-before-deploy"  # needed for session to work
 
socketio = flask_socketio.SocketIO(app, cors_allowed_origins="*")
 
 
# ── helpers ───────────────────────────────────────────────────────────────────
 
def get_current_user() -> User | None:
    """Fetch the logged-in user from DB using the ID stored in session."""
    user_id = flask.session.get("user_id")
    if user_id is None:
        return None
    return DB.get_user_byID(user_id)
 
 
# ── routes ────────────────────────────────────────────────────────────────────
 
@app.route("/")
def root():
    return flask.redirect("/login")
 
 
@app.route("/login", methods=["POST", "GET"])
def login():
    # already logged in — send them to dashboard
    if flask.session.get("user_id"):
        return flask.redirect("/dashboard")
 
    if flask.request.method == "POST":
        username = flask.request.form.get("user_name", "")
        password = flask.request.form.get("password", "")
 
        user = DB.get_user(username)
 
        if user and user.verify_password(password):
            flask.session["user_id"] = user.user_id  # persist across requests
            return flask.redirect("/dashboard")
        else:
            return flask.render_template(
                "login.html",
                error="Invalid username or password, please try again."
            )
 
    return flask.render_template("login.html")
 
 
@app.route("/logout")
def logout():
    flask.session.clear()
    return flask.redirect("/login")
 
 
@app.route("/dashboard")
def dashboard_root():
    user = get_current_user()
 
    if user is None:
        return flask.redirect("/login")
 
    if user.is_teacher():
        return dashboard_teacher(user)
    elif user.is_student():
        return dashboard_student(user)
    else:
        print("SessionError: unexpected user type")
        flask.session.clear()
        return flask.redirect("/login")

def dashboard_teacher(user: User):
    class_id = flask.request.args.get("class_id", -1,type=int)
    data     = DB.fetch_teacher_data(user.user_id, class_id)
    return flask.render_template("dashboard-teacher.html",
        teacher_name       = user.user_name,
        section_id         = class_id,
        section_selections = data["section_selections"],
        students           = data["students"],
        groups             = data["groups"],
        columns            = data["columns"],
        scores             = data["scores"],
        averages           = data["averages"],
    )

def dashboard_student(user: User):
    data = DB.fetch_student_data(user.user_id)
    return flask.render_template("dashboard-student.html",
        student = {"name": user.user_name},
        classes = data["classes"],
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
    class_id = int(data.get("section", -1))
    cols     = data.get("cols", [])
    scores   = data.get("scores", {})
 
    DB.save_grades(class_id, cols, scores)
    print(f"[sync] class_id={class_id} {len(cols)} cols, {len(scores)} students")
 
    saved_at = datetime.now(timezone.utc).isoformat()
    flask_socketio.emit("sync_ack", {"saved_at": saved_at})



@socketio.on("publish")
def handle_publish(data):
    """
    Same payload as sync — but also triggers email notifications
    to every student in the section.
    """
    class_id = int(data.get("section", -1))
    cols     = data.get("cols", [])
    scores   = data.get("scores", {})
 
    DB.save_grades(class_id, cols, scores)
    # TODO: notify_students(class_id)
    print(f"[publish] class_id={class_id} {len(cols)} cols, {len(scores)} students")
 
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
'''
