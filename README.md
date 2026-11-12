# Flask + Supabase Auth

A beginner-friendly Flask + Supabase authentication application designed for Vercel's Python serverless runtime. It includes sign up, sign in, sign out, password reset, a protected dashboard, CSRF protection, secure signed cookies, and friendly setup errors.

## Features

- Full-name, email, password, and password-confirmation signup form
- Supabase Auth handles password hashing and account authentication
- Email confirmation and password-reset email workflows
- Protected dashboard with the user's name and registered email
- Encrypted, signed, HTTP-only, SameSite cookies suitable for serverless requests
- Session-bound CSRF protection on every POST form
- Vercel-ready Python serverless entry point (`api/index.py` and `vercel.json`)
- Responsive accessible templates, password visibility toggles, and submit loading states
- Render-ready Gunicorn configuration and `/health` endpoint
- No SQLite and no hardcoded credentials

## Project layout

```text
flask-auth-app/
├── app.py
├── config.py
├── requirements.txt
├── api/index.py
├── vercel.json
├── Procfile
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html
│   └── forgot_password.html
└── static/
    ├── css/style.css
    └── js/app.js
```

## 1. Install and run locally

Install Python 3.10 or newer, then create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows Command Prompt
.venv\Scripts\activate.bat
# macOS/Linux
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the values:

```bash
# macOS/Linux
cp .env.example .env
# Windows PowerShell
Copy-Item .env.example .env
```

Generate a strong Flask secret, for example with Python:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put the generated value in `SECRET_KEY`. Never commit `.env` or a Supabase service-role key.

## Local client demo with SQLite

For a local demonstration without a Supabase project, copy `.env.example` to `.env` and set:

```env
USE_LOCAL_DB=true
SECRET_KEY=local-demo-secret-change-me
SESSION_COOKIE_SECURE=false
```

Then run `python app.py`. The app creates `local_auth.db` automatically and supports local signup, login, dashboard protection, and logout. This SQLite mode is only for offline demos; production deployment should use Supabase Auth and `USE_LOCAL_DB=false`.


1. Open [supabase.com](https://supabase.com), create an account, and create a new project.
2. Wait for the project to finish provisioning.
3. Open **Project Settings → API**.
4. Copy **Project URL** into `SUPABASE_URL`.
5. Copy the public **anon** key into `SUPABASE_ANON_KEY`. Do not use or expose the `service_role` key.
6. Open **Authentication → Providers → Email** and enable Email if it is not already enabled.
7. Decide whether **Confirm email** should be enabled. When it is enabled, a new user must click the confirmation email before signing in.
8. Open **Authentication → URL Configuration** and add these allowed redirect URLs during local development:
   - `http://127.0.0.1:5000/reset-password`
   - `http://localhost:5000/reset-password`
9. For the most reliable server-rendered password reset flow, open **Authentication → Email Templates → Reset Password** and make the link point to your app using the token hash:
   `{{ .SiteURL }}/reset-password?token_hash={{ .TokenHash }}&type=recovery`

The full name is stored as Supabase Auth user metadata (`user_metadata.full_name`), while Supabase Auth stores the user identity and password data in the project's PostgreSQL-backed auth database. This app never stores plain-text passwords.

## 3. Start and test locally

```bash
python app.py
```

Open <http://127.0.0.1:5000>. Test these flows:

1. Create an account with a full name, valid email, and an eight-character-or-longer password.
2. If email confirmation is enabled, click the Supabase confirmation link, then sign in.
3. Confirm the dashboard shows the name and email.
4. Open `/dashboard` in a private window while signed out; it must redirect to login.
5. Try an incorrect password; it must be rejected without exposing provider details.
6. Use **Forgot your password?**, follow the email, and set a new password.
7. Sign out and confirm that the dashboard is no longer accessible.
8. Check <http://127.0.0.1:5000/health> returns `{"status":"ok"}`.

## 4. Upload the project to GitHub

From the project directory:

```bash
git init
git add .
git commit -m "Build Flask Supabase authentication app"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

If this repository already has a remote, use `git remote -v` to inspect it and skip `git init`/`git remote add`. Before pushing, verify that `.env` is ignored:

```bash
git status
```

Only `.env.example` belongs in GitHub. Never upload passwords, `SECRET_KEY`, Supabase service-role keys, or session files.

## 5. Deploy to Vercel

1. Push the project to GitHub.
2. Sign in at [vercel.com](https://vercel.com) and choose **Add New → Project**.
3. Import the GitHub repository.
4. Vercel will detect `vercel.json` and the Python function in `api/index.py`.
5. In **Project Settings → Environment Variables**, add:
   - `SECRET_KEY` — a new long random value
   - `SUPABASE_URL` — your Supabase Project URL
   - `SUPABASE_ANON_KEY` — your Supabase public anon key
   - `SESSION_COOKIE_SECURE` — `true`
6. Deploy the project.
7. Copy the Vercel URL, then add `https://YOUR-PROJECT.vercel.app/reset-password` to Supabase **Authentication → URL Configuration → Redirect URLs**.
8. Test signup, email confirmation, login, dashboard protection, password reset, and logout on the deployed URL.

This remains a Flask application. Vercel runs it through the Python WSGI adapter in `api/index.py`; it does not use a frontend-only implementation. Because Vercel functions are stateless, Flask uses its signed session cookie instead of filesystem-backed sessions. Never put credentials other than the public anon key in templates or frontend JavaScript.

`Procfile` is retained for alternative Gunicorn hosts, but Vercel uses `vercel.json` and `api/index.py`.

## Configuration reference

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Long random value used to sign Flask data and sessions |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Public Supabase anon key; safe for server configuration, never use the service-role key |
| `SESSION_COOKIE_SECURE` | Production | Set `true` when HTTPS is enabled; use `false` for local HTTP |
| `PORT` | Local/other hosts | Optional local server port; Vercel supplies routing automatically |
| `LOG_LEVEL` | No | Python logging level, defaults to `INFO` |

`SUPABASE_KEY` is accepted as a backwards-compatible alias, but new deployments should use `SUPABASE_ANON_KEY`.

## Security notes

- Flask's signed session cookie uses `SECRET_KEY`; Supabase access and refresh tokens inside it are encrypted with a key derived from `SECRET_KEY`. Cookies are HTTP-only and SameSite Lax. Enable `SESSION_COOKIE_SECURE=true` in HTTPS production.
- Every state-changing form includes a session-bound CSRF token.
- Passwords are sent to Supabase Auth and are never stored by this Flask app.
- The public anon key is used only through the server-side Supabase client. Never put a service-role key in `.env.example`, templates, JavaScript, or GitHub.
- Authentication errors intentionally use generic wording to avoid account enumeration.
- Vercel functions are stateless, so do not depend on local filesystem files for persistent application data. Supabase remains the persistence layer.
