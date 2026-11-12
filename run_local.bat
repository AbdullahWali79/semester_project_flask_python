@echo off
set USE_LOCAL_DB=true
set SECRET_KEY=local-demo-secret-change-me
set SESSION_COOKIE_SECURE=false
set PORT=5000
python app.py
