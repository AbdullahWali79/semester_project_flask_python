"""Flask + Supabase authentication starter application."""
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from werkzeug.security import check_password_hash, generate_password_hash

from flask import Flask, flash, redirect, render_template, request, session, url_for
try:
    from supabase import create_client
except ImportError:  # Supabase is optional when running the SQLite demo mode.
    create_client = None

from config import Config

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    session_cipher = None
    if Config.SECRET_KEY:
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(Config.SECRET_KEY.encode()).digest())
        session_cipher = Fernet(derived_key)

    def save_auth_tokens(access_token, refresh_token):
        if not session_cipher or not access_token or not refresh_token:
            return
        encrypted = session_cipher.encrypt(json.dumps({
            "access_token": access_token,
            "refresh_token": refresh_token,
        }).encode()).decode()
        session["auth_tokens"] = encrypted

    def local_db():
        connection = sqlite3.connect(Config.LOCAL_DB_PATH)
        connection.row_factory = sqlite3.Row
        return connection

    if Config.USE_LOCAL_DB:
        with local_db() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        app.extensions["supabase"] = None
    else:
        try:
            Config.validate()
            app.extensions["supabase"] = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
        except Exception as exc:
            # Keep the app importable for health checks and friendly setup errors.
            logger.error("Supabase configuration is unavailable: %s", exc)
            app.extensions["supabase"] = None
            app.config["SETUP_ERROR"] = str(exc)

    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_forms():
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected, supplied):
                flash("Your form expired. Please try again.", "error")
                return redirect(request.referrer or url_for("login"))

    def supabase_or_error():
        client = app.extensions.get("supabase")
        if client is None:
            raise RuntimeError(app.config.get("SETUP_ERROR", "Supabase is not configured."))
        return client

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user"):
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.get("/")
    def index():
        return redirect(url_for("dashboard" if session.get("user") else "login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not email or not password:
                flash("Enter your email and password.", "error")
                return render_template("login.html", email=email)
            try:
                if Config.USE_LOCAL_DB:
                    with local_db() as connection:
                        user = connection.execute(
                            "SELECT * FROM users WHERE email = ?", (email,)
                        ).fetchone()
                    if not user or not check_password_hash(user["password_hash"], password):
                        raise ValueError("Invalid local credentials")
                    session.clear()
                    session["user"] = {
                        "id": user["id"],
                        "email": user["email"],
                        "user_metadata": {"full_name": user["full_name"]},
                    }
                    session.permanent = True
                    flash("Welcome back.", "success")
                    return redirect(url_for("dashboard"))
                response = supabase_or_error().auth.sign_in_with_password({"email": email, "password": password})
                session.clear()
                session["user"] = response.user.model_dump() if hasattr(response.user, "model_dump") else response.user
                save_auth_tokens(response.session.access_token, response.session.refresh_token)
                session.permanent = True
                flash("Welcome back.", "success")
                return redirect(url_for("dashboard"))
            except Exception:
                logger.warning("Sign-in failed for %s", email, exc_info=True)
                flash("We could not sign you in. Check your details and try again.", "error")
        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            full_name = " ".join(request.form.get("full_name", "").split())
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if not full_name or len(full_name) > 100:
                flash("Enter your full name (up to 100 characters).", "error")
            elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
                flash("Enter a valid email address.", "error")
            elif len(password) < 8:
                flash("Password must be at least 8 characters.", "error")
            elif password != confirm:
                flash("Passwords do not match.", "error")
            else:
                try:
                    if Config.USE_LOCAL_DB:
                        with local_db() as connection:
                            connection.execute(
                                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                                (full_name, email, generate_password_hash(password)),
                            )
                            connection.commit()
                        flash("Account created. You can now sign in.", "success")
                        return redirect(url_for("login"))
                    result = supabase_or_error().auth.sign_up({
                        "email": email,
                        "password": password,
                        "options": {"data": {"full_name": full_name}},
                    })
                    if result.session:
                        session["user"] = result.user.model_dump() if hasattr(result.user, "model_dump") else result.user
                        save_auth_tokens(result.session.access_token, result.session.refresh_token)
                        session.permanent = True
                        return redirect(url_for("dashboard"))
                    flash("Check your email to confirm your account, then sign in.", "success")
                    return redirect(url_for("login"))
                except Exception:
                    logger.warning("Sign-up failed for %s", email, exc_info=True)
                    flash("We could not create that account. It may already exist.", "error")
            return render_template("signup.html", email=email, full_name=full_name)
        return render_template("signup.html")

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            if "@" not in email:
                flash("Enter a valid email address.", "error")
            else:
                try:
                    redirect_url = url_for("reset_password", _external=True)
                    supabase_or_error().auth.reset_password_email(email, options={"redirect_to": redirect_url})
                except Exception:
                    logger.warning("Password reset request failed", exc_info=True)
                # Do not disclose whether an account exists.
                flash("If an account exists, you will receive a reset email shortly.", "success")
                return redirect(url_for("login"))
        return render_template("forgot_password.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        if request.method == "GET":
            try:
                # Support Supabase's server-friendly token-hash template as well as
                # PKCE authorization-code redirects.
                if request.args.get("token_hash"):
                    response = supabase_or_error().auth.verify_otp({
                        "token_hash": request.args["token_hash"],
                        "type": request.args.get("type", "recovery"),
                    })
                    if response.session:
                        save_auth_tokens(response.session.access_token, response.session.refresh_token)
                elif request.args.get("code"):
                    response = supabase_or_error().auth.exchange_code_for_session(request.args["code"])
                    if response.session:
                        save_auth_tokens(response.session.access_token, response.session.refresh_token)
                elif request.args.get("access_token") and request.args.get("refresh_token"):
                    save_auth_tokens(request.args["access_token"], request.args["refresh_token"])

                tokens = load_auth_tokens()
                if tokens:
                    supabase_or_error().auth.set_session(
                        tokens["access_token"], tokens["refresh_token"]
                    )
            except Exception:
                logger.warning("Password reset link could not be established", exc_info=True)
                session.pop("auth_tokens", None)
                flash("That reset link is invalid or expired.", "error")
        if request.method == "POST":
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if len(password) < 8 or password != confirm:
                flash("Use matching passwords of at least 8 characters.", "error")
            else:
                try:
                    tokens = load_auth_tokens()
                    if not tokens:
                        raise RuntimeError("Reset session is missing or expired")
                    supabase_or_error().auth.set_session(tokens["access_token"], tokens["refresh_token"])
                    supabase_or_error().auth.update_user({"password": password})
                    session.clear()
                    flash("Password updated. You can now sign in.", "success")
                    return redirect(url_for("login"))
                except Exception:
                    logger.warning("Password update failed", exc_info=True)
                    flash("That reset link is invalid or expired.", "error")
        return render_template("forgot_password.html", reset=True)

    @app.get("/dashboard")
    @login_required
    def dashboard():
        user = session.get("user", {})
        metadata = user.get("user_metadata", {}) if isinstance(user, dict) else {}
        name = metadata.get("full_name") or user.get("email", "Member")
        return render_template("dashboard.html", user=user, name=name)

    @app.post("/logout")
    def logout():
        if load_auth_tokens():
            try:
                supabase_or_error().auth.sign_out()
            except Exception:
                logger.info("Remote sign-out failed; clearing local session.", exc_info=True)
        session.clear()
        flash("You have been signed out.", "success")
        return redirect(url_for("login"))

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("base.html", content="Page not found."), 404

    @app.errorhandler(500)
    def server_error(_error):
        logger.exception("Unhandled application error")
        return render_template("base.html", content="Something went wrong. Please try again."), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
