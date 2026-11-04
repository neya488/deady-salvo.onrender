import os
import sqlite3
from functools import wraps
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "deady_salvo.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "CHANGE-ME-before-public-launch")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 7
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
CSRFProtect(app)

TEAM = [
    {"name": "DEADY", "handle": "1deady", "url": "https://www.tiktok.com/@1deady", "number": "01"},
    {"name": "KUZEY", "handle": "lifevolkxey", "url": "https://www.tiktok.com/@lifevolkxey", "number": "02"},
    {"name": "APOLON", "handle": "dream_lord11", "url": "https://www.tiktok.com/@dream_lord11", "number": "03"},
    {"name": "SHAZDY", "handle": "shazdyweb", "url": "https://www.tiktok.com/@shazdyweb", "number": "04"},
]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        bio TEXT NOT NULL DEFAULT '',
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS likes (
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        PRIMARY KEY(user_id, post_id)
    );
    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)
    admin_username = os.environ.get("ADMIN_USERNAME", "").strip()
    if admin_username:
        conn.execute(
            "UPDATE users SET is_admin = 1 WHERE username = ?",
            (admin_username,)
        )
    conn.commit()
    conn.close()

init_db()


def current_user():
    if "user" not in g:
        uid = session.get("user_id")
        g.user = db().execute("SELECT id, username, bio, is_admin FROM users WHERE id=?", (uid,)).fetchone() if uid else None
        g.user_loaded = True
    return g.get("user")

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "team": TEAM}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Bu işlem için giriş yapmalısın.", "warning")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or not user["is_admin"]:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    announcements = db().execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 3").fetchall()
    return render_template("index.html", announcements=announcements)

@app.route("/community")
def community():
    posts = db().execute("""
        SELECT p.*, u.username,
        (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS like_count,
        (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comment_count
        FROM posts p JOIN users u ON u.id=p.user_id
        ORDER BY p.id DESC LIMIT 50
    """).fetchall()
    liked = set()
    if current_user():
        liked = {r["post_id"] for r in db().execute("SELECT post_id FROM likes WHERE user_id=?", (current_user()["id"],))}
    return render_template("community.html", posts=posts, liked=liked)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not (3 <= len(username) <= 24) or not username.replace("_", "").isalnum():
            flash("Kullanıcı adı 3-24 karakter olmalı; harf, rakam ve _ kullanabilirsin.", "error")
        elif len(password) < 10:
            flash("Şifre en az 10 karakter olmalı.", "error")
        else:
            try:
                db().execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                             (username, generate_password_hash(password), datetime.now(timezone.utc).isoformat()))
                db().commit()
                flash("Hesabın oluşturuldu. Şimdi giriş yapabilirsin.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Bu kullanıcı adı zaten alınmış.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash("Hoş geldin, " + user["username"] + "!", "success")
            target = request.args.get("next", "")
            if target.startswith("/") and not target.startswith("//"):
                return redirect(target)
            return redirect(url_for("community"))
        flash("Kullanıcı adı veya şifre hatalı.", "error")
    return render_template("auth.html", mode="login")

@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("Çıkış yaptın.", "success")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        bio = request.form.get("bio", "").strip()[:180]
        db().execute("UPDATE users SET bio=? WHERE id=?", (bio, user["id"]))
        db().commit()
        flash("Profilin güncellendi.", "success")
        return redirect(url_for("profile"))
    user = db().execute("SELECT id,username,bio,is_admin,created_at FROM users WHERE id=?", (user["id"],)).fetchone()
    return render_template("profile.html", user=user)

@app.post("/post")
@login_required
def create_post():
    body = request.form.get("body", "").strip()
    if not body or len(body) > 1000:
        flash("Gönderi 1-1000 karakter arasında olmalı.", "error")
    else:
        db().execute("INSERT INTO posts(user_id,body,created_at) VALUES(?,?,?)",
                     (current_user()["id"], body, datetime.now(timezone.utc).isoformat()))
        db().commit()
        flash("Gönderin yayınlandı.", "success")
    return redirect(url_for("community"))

@app.post("/like/<int:post_id>")
@login_required
def like(post_id):
    exists = db().execute("SELECT 1 FROM likes WHERE user_id=? AND post_id=?", (current_user()["id"], post_id)).fetchone()
    if exists:
        db().execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (current_user()["id"], post_id))
    else:
        db().execute("INSERT OR IGNORE INTO likes(user_id,post_id) VALUES(?,?)", (current_user()["id"], post_id))
    db().commit()
    return redirect(url_for("community"))

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    post = db().execute("""
        SELECT p.*,u.username,(SELECT COUNT(*) FROM likes WHERE post_id=p.id) AS like_count
        FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?
    """, (post_id,)).fetchone()
    if not post:
        abort(404)
    if request.method == "POST":
        if not current_user():
            flash("Yorum yazmak için giriş yapmalısın.", "warning")
            return redirect(url_for("login"))
        body = request.form.get("body", "").strip()
        if body and len(body) <= 500:
            db().execute("INSERT INTO comments(post_id,user_id,body,created_at) VALUES(?,?,?,?)",
                         (post_id, current_user()["id"], body, datetime.now(timezone.utc).isoformat()))
            db().commit()
            flash("Yorum eklendi.", "success")
            return redirect(url_for("post_detail", post_id=post_id))
        flash("Yorum 1-500 karakter arasında olmalı.", "error")
    comments = db().execute("""
        SELECT c.*,u.username FROM comments c JOIN users u ON u.id=c.user_id
        WHERE c.post_id=? ORDER BY c.id ASC
    """, (post_id,)).fetchall()
    return render_template("post.html", post=post, comments=comments)

@app.route("/admin", methods=["GET", "POST"])
@admin_required
def admin():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:100]
        body = request.form.get("body", "").strip()[:1000]
        if title and body:
            db().execute("INSERT INTO announcements(title,body,created_at) VALUES(?,?,?)",
                         (title, body, datetime.now(timezone.utc).isoformat()))
            db().commit()
            flash("Duyuru yayınlandı.", "success")
        return redirect(url_for("admin"))
    users = db().execute("SELECT id,username,is_admin,created_at FROM users ORDER BY id DESC LIMIT 100").fetchall()
    announcements = db().execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 20").fetchall()
    posts = db().execute("SELECT p.id,p.body,u.username FROM posts p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC LIMIT 20").fetchall()
    return render_template("admin.html", users=users, announcements=announcements, posts=posts)

@app.post("/admin/delete-post/<int:post_id>")
@admin_required
def admin_delete_post(post_id):
    db().execute("DELETE FROM posts WHERE id=?", (post_id,))
    db().commit()
    flash("Gönderi silindi.", "success")
    return redirect(url_for("admin"))

@app.post("/admin/delete-announcement/<int:announcement_id>")
@admin_required
def admin_delete_announcement(announcement_id):
    db().execute("DELETE FROM announcements WHERE id=?", (announcement_id,))
    db().commit()
    flash("Duyuru silindi.", "success")
    return redirect(url_for("admin"))

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, message="Bu alana erişim iznin yok."), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Aradığın sayfa bulunamadı."), 404

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'"
    return response

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
