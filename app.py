import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "database" / "build_up.db"))
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-this-before-deploying")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "0") == "1", MAX_CONTENT_LENGTH=2 * 1024 * 1024)


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
          email TEXT UNIQUE NOT NULL COLLATE NOCASE, password TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS profiles (
          user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          goal TEXT NOT NULL DEFAULT 'Build muscle', weight REAL, height REAL,
          daily_calories INTEGER NOT NULL DEFAULT 2400, daily_protein INTEGER NOT NULL DEFAULT 150,
          daily_water REAL NOT NULL DEFAULT 3.0, units TEXT NOT NULL DEFAULT 'metric'
        );
        CREATE TABLE IF NOT EXISTS workouts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          title TEXT NOT NULL, workout_date TEXT NOT NULL, duration INTEGER NOT NULL DEFAULT 0,
          notes TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS exercises (
          id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
          name TEXT NOT NULL, sets INTEGER NOT NULL DEFAULT 3, reps INTEGER NOT NULL DEFAULT 10,
          weight REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS meals (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          meal_date TEXT NOT NULL, name TEXT NOT NULL, calories INTEGER NOT NULL DEFAULT 0,
          protein REAL NOT NULL DEFAULT 0, carbs REAL NOT NULL DEFAULT 0, fat REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS water_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          log_date TEXT NOT NULL, litres REAL NOT NULL CHECK(litres > 0)
        );
        CREATE TABLE IF NOT EXISTS recovery_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          log_date TEXT NOT NULL, sleep_hours REAL NOT NULL DEFAULT 0, mood INTEGER NOT NULL DEFAULT 3,
          notes TEXT DEFAULT '', UNIQUE(user_id, log_date)
        );
        CREATE TABLE IF NOT EXISTS body_metrics (
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          metric_date TEXT NOT NULL, weight REAL NOT NULL, notes TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, workout_date);
        CREATE INDEX IF NOT EXISTS idx_meals_user_date ON meals(user_id, meal_date);
        CREATE INDEX IF NOT EXISTS idx_water_user_date ON water_logs(user_id, log_date);
        """)

init_db()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def current_user():
    if not session.get("user_id"):
        return None
    if "_user" not in g:
        with connect_db() as db:
            g._user = db.execute("SELECT id, full_name, email FROM users WHERE id=?", (session["user_id"],)).fetchone()
    return g._user

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "today": date.today().isoformat()}

@app.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(name) < 2 or "@" not in email or len(password) < 8:
            flash("Enter your name, a valid email, and a password with at least 8 characters.", "error")
            return render_template("signup.html")
        try:
            with connect_db() as db:
                cur = db.execute("INSERT INTO users(full_name,email,password) VALUES(?,?,?)", (name, email, generate_password_hash(password)))
                db.execute("INSERT INTO profiles(user_id) VALUES(?)", (cur.lastrowid,))
            flash("Account created. Log in to start building your routine.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with connect_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = bool(request.form.get("remember"))
            flash("Welcome back. Let's get to work.", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.get("/dashboard")
@login_required
def dashboard():
    uid, today_s = session["user_id"], date.today().isoformat()
    week_start = (date.today() - timedelta(days=6)).isoformat()
    with connect_db() as db:
        profile = db.execute("SELECT * FROM profiles WHERE user_id=?", (uid,)).fetchone()
        workouts = db.execute("SELECT * FROM workouts WHERE user_id=? ORDER BY workout_date DESC,id DESC LIMIT 5", (uid,)).fetchall()
        workout_count = db.execute("SELECT COUNT(*) n FROM workouts WHERE user_id=? AND workout_date>=?", (uid, week_start)).fetchone()["n"]
        meals = db.execute("SELECT COALESCE(SUM(calories),0) calories, COALESCE(SUM(protein),0) protein FROM meals WHERE user_id=? AND meal_date=?", (uid,today_s)).fetchone()
        water = db.execute("SELECT COALESCE(SUM(litres),0) litres FROM water_logs WHERE user_id=? AND log_date=?", (uid,today_s)).fetchone()["litres"]
        recovery = db.execute("SELECT * FROM recovery_logs WHERE user_id=? AND log_date=?", (uid,today_s)).fetchone()
        metric = db.execute("SELECT weight FROM body_metrics WHERE user_id=? ORDER BY metric_date DESC,id DESC LIMIT 1", (uid,)).fetchone()
    return render_template("dashboard.html", profile=profile, workouts=workouts, workout_count=workout_count, meals=meals, water=water, recovery=recovery, current_weight=metric["weight"] if metric else profile["weight"])

@app.route("/workouts", methods=["GET", "POST"])
@login_required
def workouts_page():
    uid = session["user_id"]
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        workout_date = request.form.get("workout_date", date.today().isoformat())
        try:
            duration = max(0, min(600, int(request.form.get("duration", 0))))
        except ValueError:
            duration = 0
        notes = request.form.get("notes", "").strip()[:1000]
        names = request.form.getlist("exercise_name[]")
        sets_list, reps_list, weights = request.form.getlist("sets[]"), request.form.getlist("reps[]"), request.form.getlist("weight[]")
        if not title:
            flash("Give the workout a name.", "error")
        else:
            with connect_db() as db:
                cur = db.execute("INSERT INTO workouts(user_id,title,workout_date,duration,notes) VALUES(?,?,?,?,?)", (uid,title,workout_date,duration,notes))
                for i, name in enumerate(names):
                    name = name.strip()
                    if not name: continue
                    try:
                        sets = max(1,min(20,int(sets_list[i])))
                        reps = max(1,min(100,int(reps_list[i])))
                        weight = max(0,float(weights[i]))
                    except (ValueError, IndexError):
                        sets,reps,weight=3,10,0
                    db.execute("INSERT INTO exercises(workout_id,name,sets,reps,weight) VALUES(?,?,?,?,?)", (cur.lastrowid,name,sets,reps,weight))
            flash("Workout saved.", "success")
            return redirect(url_for("workouts_page"))
    with connect_db() as db:
        logs = db.execute("SELECT * FROM workouts WHERE user_id=? ORDER BY workout_date DESC,id DESC", (uid,)).fetchall()
        exercises = {w["id"]: db.execute("SELECT * FROM exercises WHERE workout_id=?",(w["id"],)).fetchall() for w in logs}
    return render_template("workouts.html", logs=logs, exercises=exercises)

@app.post("/workouts/<int:workout_id>/delete")
@login_required
def delete_workout(workout_id):
    with connect_db() as db:
        db.execute("DELETE FROM workouts WHERE id=? AND user_id=?", (workout_id,session["user_id"]))
    flash("Workout deleted.", "success")
    return redirect(url_for("workouts_page"))

@app.route("/nutrition", methods=["GET", "POST"])
@login_required
def nutrition_page():
    uid, today_s = session["user_id"], date.today().isoformat()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            vals = [int(request.form.get("calories",0)),float(request.form.get("protein",0)),float(request.form.get("carbs",0)),float(request.form.get("fat",0))]
            if not name or any(v < 0 for v in vals) or vals[0] > 10000: raise ValueError
        except ValueError:
            flash("Enter a meal name and valid non-negative nutrition values.", "error")
        else:
            with connect_db() as db:
                db.execute("INSERT INTO meals(user_id,meal_date,name,calories,protein,carbs,fat) VALUES(?,?,?,?,?,?,?)", (uid,request.form.get("meal_date") or today_s,name,*vals))
            flash("Meal logged.", "success")
            return redirect(url_for("nutrition_page"))
    selected = request.args.get("date", today_s)
    with connect_db() as db:
        meals = db.execute("SELECT * FROM meals WHERE user_id=? AND meal_date=? ORDER BY id DESC", (uid,selected)).fetchall()
        totals = db.execute("SELECT COALESCE(SUM(calories),0) calories,COALESCE(SUM(protein),0) protein,COALESCE(SUM(carbs),0) carbs,COALESCE(SUM(fat),0) fat FROM meals WHERE user_id=? AND meal_date=?",(uid,selected)).fetchone()
        profile = db.execute("SELECT * FROM profiles WHERE user_id=?",(uid,)).fetchone()
    return render_template("nutrition.html", meals=meals, totals=totals, profile=profile, selected=selected)

@app.post("/meals/<int:meal_id>/delete")
@login_required
def delete_meal(meal_id):
    with connect_db() as db: db.execute("DELETE FROM meals WHERE id=? AND user_id=?",(meal_id,session["user_id"]))
    flash("Meal removed.", "success")
    return redirect(url_for("nutrition_page"))

@app.route("/recovery", methods=["GET", "POST"])
@login_required
def recovery_page():
    uid, today_s = session["user_id"], date.today().isoformat()
    if request.method == "POST":
        try:
            sleep = float(request.form.get("sleep_hours",0)); mood=int(request.form.get("mood",3))
            if not 0 <= sleep <= 24 or not 1 <= mood <= 5: raise ValueError
        except ValueError:
            flash("Enter sleep between 0 and 24 hours and mood from 1 to 5.", "error")
        else:
            with connect_db() as db:
                db.execute("INSERT INTO recovery_logs(user_id,log_date,sleep_hours,mood,notes) VALUES(?,?,?,?,?) ON CONFLICT(user_id,log_date) DO UPDATE SET sleep_hours=excluded.sleep_hours,mood=excluded.mood,notes=excluded.notes", (uid,request.form.get("log_date") or today_s,sleep,mood,request.form.get("notes","").strip()[:1000]))
                db.execute("INSERT INTO water_logs(user_id,log_date,litres) SELECT ?,?,? WHERE ? > 0",(uid,request.form.get("log_date") or today_s,float(request.form.get("water",0)),float(request.form.get("water",0))))
            flash("Recovery log saved.", "success")
            return redirect(url_for("recovery_page"))
    with connect_db() as db:
        logs=db.execute("SELECT * FROM recovery_logs WHERE user_id=? ORDER BY log_date DESC LIMIT 14",(uid,)).fetchall()
        water_rows=db.execute("SELECT log_date,SUM(litres) litres FROM water_logs WHERE user_id=? GROUP BY log_date ORDER BY log_date DESC LIMIT 7",(uid,)).fetchall()
        today_water=db.execute("SELECT COALESCE(SUM(litres),0) n FROM water_logs WHERE user_id=? AND log_date=?",(uid,today_s)).fetchone()["n"]
        profile=db.execute("SELECT * FROM profiles WHERE user_id=?",(uid,)).fetchone()
    return render_template("recovery.html", logs=logs, water_rows=water_rows, today_water=today_water, profile=profile)

@app.post("/water/add")
@login_required
def add_water():
    try: litres=float(request.form.get("litres",0)); log_date=request.form.get("log_date") or date.today().isoformat()
    except ValueError: litres=0; log_date=date.today().isoformat()
    if 0 < litres <= 5:
        with connect_db() as db: db.execute("INSERT INTO water_logs(user_id,log_date,litres) VALUES(?,?,?)",(session["user_id"],log_date,litres))
        flash(f"Added {litres:g} L of water.", "success")
    else: flash("Enter a water amount between 0 and 5 litres.", "error")
    return redirect(url_for("recovery_page"))

@app.route("/progress", methods=["GET", "POST"])
@login_required
def progress_page():
    uid=session["user_id"]
    if request.method == "POST":
        try: weight=float(request.form.get("weight",0)); metric_date=request.form.get("metric_date") or date.today().isoformat()
        except ValueError: weight=0; metric_date=date.today().isoformat()
        if not 20 <= weight <= 500: flash("Enter a valid body weight.", "error")
        else:
            with connect_db() as db:
                db.execute("INSERT INTO body_metrics(user_id,metric_date,weight,notes) VALUES(?,?,?,?)",(uid,metric_date,weight,request.form.get("notes","").strip()[:500]))
                db.execute("UPDATE profiles SET weight=? WHERE user_id=?",(weight,uid))
            flash("Body measurement saved.", "success")
            return redirect(url_for("progress_page"))
    with connect_db() as db:
        metrics=db.execute("SELECT * FROM body_metrics WHERE user_id=? ORDER BY metric_date DESC,id DESC LIMIT 30",(uid,)).fetchall()
        workouts=db.execute("SELECT workout_date,COUNT(*) count FROM workouts WHERE user_id=? AND workout_date>=? GROUP BY workout_date ORDER BY workout_date",(uid,(date.today()-timedelta(days=29)).isoformat())).fetchall()
        totals=db.execute("SELECT COUNT(*) sessions,COALESCE(SUM(duration),0) minutes FROM workouts WHERE user_id=?",(uid,)).fetchone()
    chart=list(reversed(metrics))
    return render_template("progress.html", metrics=metrics, chart_labels=[m["metric_date"] for m in chart], chart_values=[m["weight"] for m in chart], workouts=workouts, totals=totals)

def built_in_coach_reply(message, equipment, goal, level):
    """Useful no-key fallback; configure OPENAI_API_KEY for the conversational AI."""
    text = message.lower()
    equipment_text = {
        "dumbbells": "Use dumbbell goblet squats, Romanian deadlifts, floor presses, one-arm rows, overhead presses, curls and farmer carries. Start with 2–3 sets of 8–12 controlled reps.",
        "bodyweight": "Use squats, reverse lunges, incline push-ups, glute bridges, calf raises, dead bugs and planks. Choose a variation you can perform with steady form for 2–3 sets.",
        "gym": "Build sessions around a squat or leg press, hip hinge, chest press, row, pulldown and core exercise. Ask gym staff to show you unfamiliar equipment and begin with a light load.",
        "mixed": "Combine bodyweight basics with your available dumbbells: squats, lunges, push-ups, rows, presses, hip hinges and core work."
    }.get(equipment, "Use a simple mix of bodyweight movements and the equipment you have available.")
    if any(word in text for word in ("plan", "routine", "workout", "start", "week")):
        answer = f"""A simple starter plan ({level}): train 3 non-consecutive days per week and alternate these sessions.

Workout A: squat pattern, push, row, hip hinge and plank.
Workout B: lunge pattern, overhead press, row, glute bridge and dead bug.
Do 2–3 sets per movement, stop with 2–3 good reps left, and add a rep before adding weight.

Equipment ideas: {equipment_text}"""
    elif any(word in text for word in ("dumbbell", "equipment", "machine", "use", "form", "technique")):
        answer = f"""For your selected equipment ({equipment}), keep each rep controlled, use a comfortable range of motion and stop if you feel sharp pain.

{equipment_text}

Tell me the exact exercise and I can break down setup, movement, breathing and common mistakes."""
    elif any(word in text for word in ("food", "protein", "calorie", "meal", "nutrition")):
        answer = "Build meals around a protein source, vegetables or fruit, carbohydrates for training energy, and healthy fats. Use your app's nutrition log to track trends; calorie and protein needs depend on your body, activity and goal."
    elif any(word in text for word in ("pain", "injury", "hurt", "dizzy", "chest")):
        answer = "Stop the exercise if you have pain, dizziness or unusual symptoms. Do not train through sharp or worsening pain; seek advice from a qualified healthcare professional. Chest pain, fainting or severe breathing difficulty needs urgent medical help."
    else:
        answer = f"""Let's keep it practical for your goal ({goal}) and level ({level}). {equipment_text}

For a good next step, tell me your goal, available time, equipment and which exercise or body area you want help with."""
    return answer + "\n\nGeneral fitness guidance only; use safe technique and progress gradually."


@app.route("/coach", methods=["GET", "POST"])
@login_required
def coach_page():
    history = session.get("coach_history", [])
    ai_enabled = bool(os.getenv("OPENAI_API_KEY"))
    if request.method == "POST":
        message = request.form.get("message", "").strip()[:500]
        equipment = request.form.get("equipment", "dumbbells")
        if equipment not in {"dumbbells", "bodyweight", "gym", "mixed"}:
            equipment = "dumbbells"
        goal = request.form.get("goal", "Build muscle")[:50]
        level = request.form.get("level", "Beginner")
        if level not in {"Beginner", "Intermediate", "Advanced"}:
            level = "Beginner"
        if not message:
            flash("Ask the Coach a question first.", "error")
        else:
            user_entry = {"role": "user", "content": message}
            answer = None
            if ai_enabled:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
                    with connect_db() as db:
                        uid = session["user_id"]
                        week = (date.today() - timedelta(days=6)).isoformat()
                        count = db.execute("SELECT COUNT(*) n FROM workouts WHERE user_id=? AND workout_date>=?", (uid, week)).fetchone()["n"]
                        profile = db.execute("SELECT * FROM profiles WHERE user_id=?", (uid,)).fetchone()
                    system_prompt = ("You are Build Up Coach, a supportive, practical fitness assistant. Give clear, step-by-step instructions in plain language. "
                        "Tailor advice to the user's stated goal, experience and equipment. If they have only dumbbells or no equipment, suggest safe home alternatives. "
                        "Explain setup, execution, breathing, sets/reps, progression and common mistakes when relevant. Keep answers structured and not overly long. "
                        "Ask one clarifying question if essential information is missing. Never claim to monitor the user live; use only the supplied app summary. "
                        "Do not diagnose injuries or encourage training through pain. For concerning symptoms, advise stopping and seeking qualified medical care. "
                        f"User goal: {goal}. Experience: {level}. Available equipment: {equipment}. Workouts logged in the last 7 days: {count}. "
                        f"Daily protein target saved in app: {profile['daily_protein']} g. Give general fitness information, not medical advice.")
                    prior = [{"role": item["role"], "content": item["content"]} for item in history[-3:] if item.get("role") in {"user", "assistant"}]
                    response = client.responses.create(model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), input=[{"role": "system", "content": system_prompt}, *prior, {"role": "user", "content": message}])
                    answer = response.output_text.strip()
                except Exception:
                    app.logger.exception("Build Up Coach AI request failed")
                    answer = built_in_coach_reply(message, equipment, goal, level)
                    flash("AI service was unavailable, so the built-in Coach gave you a fallback answer.", "error")
            else:
                answer = built_in_coach_reply(message, equipment, goal, level)
                flash("Built-in Coach is active. Add OPENAI_API_KEY to enable conversational AI.", "success")
            answer = answer[:900]
            history = (history + [user_entry, {"role": "assistant", "content": answer}])[-4:]
            session["coach_history"] = history
            session.modified = True
    return render_template("coach.html", history=history, ai_enabled=ai_enabled)

@app.post("/coach/clear")
@login_required
def clear_coach_history():
    session.pop("coach_history", None)
    return redirect(url_for("coach_page"))

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings_page():
    uid=session["user_id"]
    with connect_db() as db: profile=db.execute("SELECT * FROM profiles WHERE user_id=?",(uid,)).fetchone()
    if request.method == "POST":
        try:
            calories=max(500,min(10000,int(request.form.get("daily_calories",2400))))
            protein=max(0,min(500,int(request.form.get("daily_protein",150))))
            water=max(0.5,min(10,float(request.form.get("daily_water",3))))
            weight=request.form.get("weight","").strip(); height=request.form.get("height","").strip()
            weight=float(weight) if weight else None; height=float(height) if height else None
            if weight is not None and not 20 <= weight <= 500: raise ValueError
            if height is not None and not 80 <= height <= 250: raise ValueError
        except ValueError:
            flash("Check your targets and measurements.", "error")
        else:
            with connect_db() as db:
                db.execute("UPDATE profiles SET goal=?,daily_calories=?,daily_protein=?,daily_water=?,weight=?,height=? WHERE user_id=?",(request.form.get("goal","Build muscle"),calories,protein,water,weight,height,uid))
                db.execute("UPDATE users SET full_name=? WHERE id=?",(request.form.get("full_name","").strip()[:100] or current_user()["full_name"],uid))
            flash("Settings saved.", "success")
            return redirect(url_for("settings_page"))
    return render_template("settings.html", profile=profile)

@app.get("/health")
def health():
    return {"status":"ok", "app":"Build Up"}

@app.errorhandler(404)
def not_found(_):
    return render_template("message.html", title="Page not found", message="That page does not exist."), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG", "0") == "1")
