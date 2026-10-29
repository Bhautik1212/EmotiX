@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
  echo Creating Python virtual environment...
  py -m venv .venv
  if errorlevel 1 python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if not defined EMOTIX_SECRET_KEY set EMOTIX_SECRET_KEY=change-this-local-secret-before-deployment
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
