from flask import Flask, render_template, request, redirect, url_for, session, flash,  jsonify
import sqlite3 as sql
import os
import uuid
from werkzeug.utils import secure_filename

# ---------------- APP SETUP ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"   # session key

DB_PATH = "database.db"
con = sql.connect(DB_PATH)
# Folder untuk upload foto
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- FUNGSI ----------------
def save_photo(photo_file):
    """Simpan foto dengan nama unik UUID"""
    if not photo_file or photo_file.filename == "":
        return None

    filename = secure_filename(photo_file.filename)
    ext = os.path.splitext(filename)[1]
    new_filename = f"{uuid.uuid4().hex}{ext}"
    photo_path = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
    photo_file.save(photo_path)
    return new_filename

# Inject user (bisa dipakai di semua template, misalnya navbar)
@app.context_processor
def inject_user():
    user = session.get("user")
    return dict(user=user)

# ---------------- DATABASE ----------------
# Buat tabel jika belum ada
print("Opened database successfully")

con.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        city TEXT,
        username TEXT UNIQUE,
        pin TEXT,
        photo TEXT
    )
''')
print("Table students created successfully")

con.execute('''CREATE TABLE IF NOT EXISTS sensor_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    temperature REAL,
                    humidity REAL,
                    light INTEGER,
                    gas INTEGER,
                    water REAL,
                    mode TEXT,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
print("Table sensors created successfully")
con.close()

@app.route('/api/data/save', methods=['POST'])
def save_data():
    data = request.json
    con = sql.connect(DB_PATH)
    c = con.cursor()
    c.execute('''INSERT INTO sensor_log 
                 (temperature, humidity, light, gas, water, mode, status) 
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (data['temperature'], data['humidity'], data['valueldr'], data['valuegas'],
               data['distance'], data['mode'], data['status']))
    con.commit()
    con.close()
    return jsonify({"message": "Data berhasil disimpan"}), 201

# Get semua tanaman
@app.route('/api/user', methods=['GET'])
def get_student():
    with sql.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students")
        items = cursor.fetchall()
    students_list = [
        {
            'id': item[0],
            'name': item[1],
            'address': item[2],
            'city': item[3],
            'username': item[4],
            'pin': item[5],
            'photo': item[6],
        } for item in items
    ]
    return jsonify(students_list)

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('indexsql.html')

@app.route('/about')
def about():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('about.html')

@app.route('/response')
def contact():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('response.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form["username"]
        pin = request.form["pin"]

        con = sql.connect(DB_PATH)
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM students WHERE username=? AND pin=?", (username, pin))
        user = cur.fetchone()
        con.close()

        if user:
            session["user"] = dict(user)  # simpan seluruh data user ke session
            flash("Login berhasil!", "success")
            return redirect(url_for("home"))
        else:
            flash("Username atau PIN salah!", "danger")

    return render_template("loginsql.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Anda sudah logout.", "info")
    return redirect(url_for("login"))

# ---------------- CRUD ----------------
# Form input data baru
@app.route('/enternew')
def new_student():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('studentsql.html')

# Tambah data
@app.route('/addrec', methods=['POST'])
def addrec():
    try:
        name = request.form['name']
        address = request.form['address']
        city = request.form['city']
        username = request.form["username"]
        pin = request.form['pin']
        photo_file = request.files["photo"]

        photo_filename = save_photo(photo_file)

        with sql.connect(DB_PATH) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO students (name, address, city, username, pin, photo) VALUES (?, ?, ?, ?, ?, ?)",
                (name, address, city, username, pin, photo_filename),
            )
            con.commit()
            msg = "Record successfully added"
    except Exception as e:
        con.rollback()
        msg = f"Error in insert operation: {e}"
    finally:
        con.close()
        return render_template("resultsql.html", msg=msg)

# List semua data
@app.route('/list')
def list_records():
    if "user" not in session:
        return redirect(url_for("login"))

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM students")
    rows = cur.fetchall()
    con.close()
    return render_template("listsql.html", rows=rows)

# Edit form
@app.route("/edit/<int:id>")
def edit(id):
    if "user" not in session:
        return redirect(url_for("login"))

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    student = con.execute("SELECT * FROM students WHERE id = ?", (id,)).fetchone()
    con.close()
    return render_template("editsql.html", student=student)

# Update data
@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    if "user" not in session:
        return redirect(url_for("login"))

    name = request.form["name"]
    address = request.form["address"]
    city = request.form["city"]
    username = request.form["username"]
    pin = request.form["pin"]

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    old_student = con.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()

    photo_file = request.files["photo"]
    photo_filename = old_student["photo"]

    if photo_file and photo_file.filename != "":
        if old_student["photo"]:
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], old_student["photo"])
            if os.path.exists(old_path):
                os.remove(old_path)
        photo_filename = save_photo(photo_file)

    con.execute(
        "UPDATE students SET name=?, address=?, city=?, username=?, pin=?, photo=? WHERE id=?",
        (name, address, city, username, pin, photo_filename, id)
    )
    con.commit()
    con.close()
    return redirect(url_for("list_records"))

# Delete confirm
@app.route("/delete/<int:id>")
def delete_confirm(id):
    if "user" not in session:
        return redirect(url_for("login"))

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    student = con.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    con.close()
    return render_template("deletesql.html", student=student)

# Delete action
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    if "user" not in session:
        return redirect(url_for("login"))

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    student = con.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()

    if student["photo"]:
        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], student["photo"])
        if os.path.exists(photo_path):
            os.remove(photo_path)

    con.execute("DELETE FROM students WHERE id=?", (id,))
    con.commit()
    con.close()

    return redirect(url_for("list_records"))

@app.route("/sensors")
def list_sensors():
    if "user" not in session:
        return redirect(url_for("login"))

    con = sql.connect(DB_PATH)
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM sensor_log ORDER BY timestamp DESC")
    rows = cur.fetchall()
    con.close()

    return render_template("listsensor.html", rows=rows)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5050)
