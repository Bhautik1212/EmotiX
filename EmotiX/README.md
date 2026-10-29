# EmotiX — local full-stack prototype

EmotiX preserves the supplied dark clinical-tech HTML interface and adds a FastAPI backend, SQLite database, account registration/login, private assessment history, chat safety fallback, and PDF report export.

## Quick start (Windows)
1. Install **Python 3.11 or newer** from https://www.python.org/downloads/ and enable **Add Python to PATH**.
2. Extract the ZIP to a folder you can write to.
3. Double-click `run_windows.bat` (or run it from Command Prompt). The script creates a virtual environment, installs packages, and starts the server.
4. Open **http://127.0.0.1:8000** in your browser.
5. API documentation is at **http://127.0.0.1:8000/docs**.

The first install needs internet access to download Python packages. If package downloads are blocked, allow `pypi.org` and `files.pythonhosted.org`, then run the script again.

## What works in this prototype
- Existing EmotiX landing page, behaviour form, chat UI, dashboard, and browser-side camera/microphone UI are retained.
- FastAPI backend and SQLite persistence.
- Account creation and login with salted PBKDF2 password hashes and signed bearer tokens.
- Authenticated assessment history; behaviour/fused prototype scores can be saved for a signed-in user.
- Chat history persistence for signed-in users and server-side crisis keyword fallback.
- Downloadable PDF report of saved assessment entries.
- Health endpoint at `/api/health` and interactive API docs at `/docs`.
- Unit tests for risk bands, password hashing, and crisis fallback.

## Honest capability notes
- **This is a student/research prototype, not a clinical tool.** Its scores are not clinically validated and must not be used to diagnose or make treatment decisions.
- The existing frontend contains browser-side heuristic scoring and model-dependent facial analysis. A webcam or microphone being available does not mean a validated model is running. No trained face/voice weights are bundled here, so do not represent these outputs as validated predictions.
- The counselling backend uses a safety-oriented local fallback, not a configured LLM. To add a real LLM, implement and evaluate a provider adapter before enabling it for users. Never put provider API keys in frontend JavaScript.
- Crisis keyword detection can miss context and is not a substitute for emergency services. In India, call 112 for immediate danger; Tele-MANAS is 14416.
- The supplied page includes project-reported model evaluation numbers. They are preserved as supplied project information and have not been independently verified here.
- This local prototype has not undergone a security audit or production deployment review.

## Run tests
Open a terminal in the extracted folder and run:

```bat
.venv\Scripts\activate
python -m pytest backend\tests -q
```

## Environment and deployment
- `DATABASE_URL` may be set to a PostgreSQL SQLAlchemy URL for a compatible production database.
- Set a strong random `EMOTIX_SECRET_KEY` environment variable before any shared deployment. The default is for local development only.
- Use HTTPS, secure deployment secrets, database migrations, rate limiting, email verification, retention/deletion policy, and a privacy review before exposing this to the public. The included app is intended for local evaluation.
- SQLite data is stored at `data/emotix.db`. Keep the file private and back it up only if needed.

## Privacy
Assessment and chat data is persisted on the server only when signed in, and the API restricts records to the authenticated account. Pre-login chat text is held only in page memory until sign-in or the page is closed. The frontend stores the access token in browser local storage for convenience in this prototype; for a production system, consider secure, HttpOnly cookies and a more complete session/CSRF design. Avoid entering unnecessary personal or highly sensitive details.


# RUN Command
- .\run_windows.bat
# Frontend: http://127.0.0.1:8000 
# Backend: http://127.0.0.1:8000/docs
