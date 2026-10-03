import math
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for


app = Flask(__name__)
DATABASE = Path(__file__).with_name("students.db")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_db():
    database = sqlite3.connect(DATABASE)
    try:
        database.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                course TEXT NOT NULL,
                semester INTEGER NOT NULL,
                marks REAL NOT NULL
            )
        """)
        database.commit()
    finally:
        database.close()


def student_form_data():
    name = request.form.get("name", "").strip()
    course = request.form.get("course", "").strip()
    try:
        semester = int(request.form.get("semester", ""))
        marks = float(request.form.get("marks", ""))
    except ValueError:
        return None

    if not name or not course or semester < 1 or not math.isfinite(marks):
        return None
    return name, course, semester, marks


@app.get("/")
def index():
    search = request.args.get("search", "").strip()
    database = get_db()
    if search:
        students = database.execute(
            "SELECT * FROM students WHERE name LIKE ? OR course LIKE ? ORDER BY name",
            (f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        students = database.execute(
            "SELECT * FROM students ORDER BY name"
        ).fetchall()

    editing_id = request.args.get("edit", type=int)
    editing = None
    if editing_id is not None:
        editing = database.execute(
            "SELECT * FROM students WHERE id = ?", (editing_id,)
        ).fetchone()

    count = database.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    return render_template(
        "index.html",
        students=students,
        editing=editing,
        search=search,
        count=count,
        notice=request.args.get("notice", ""),
    )


@app.post("/students")
def add_student():
    data = student_form_data()
    if data is None:
        return redirect(url_for("index", notice="Enter valid student details."))

    database = get_db()
    database.execute(
        "INSERT INTO students (name, course, semester, marks) VALUES (?, ?, ?, ?)",
        data,
    )
    database.commit()
    return redirect(url_for("index", notice="Student added."))


@app.post("/students/<int:student_id>/update")
def update_student(student_id):
    data = student_form_data()
    if data is None:
        return redirect(url_for("index", edit=student_id, notice="Enter valid student details."))

    database = get_db()
    result = database.execute(
        "UPDATE students SET name = ?, course = ?, semester = ?, marks = ? WHERE id = ?",
        (*data, student_id),
    )
    database.commit()
    notice = "Student updated." if result.rowcount else "Student not found."
    return redirect(url_for("index", notice=notice))


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id):
    database = get_db()
    result = database.execute(
        "DELETE FROM students WHERE id = ?", (student_id,)
    )
    database.commit()
    notice = "Student deleted." if result.rowcount else "Student not found."
    return redirect(url_for("index", notice=notice))


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)