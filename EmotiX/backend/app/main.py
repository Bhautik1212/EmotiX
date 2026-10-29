from __future__ import annotations
import base64, hashlib, hmac, json, os, re, secrets, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import create_engine, String, Integer, Float, DateTime, Text, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "index.html"
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'emotix.db').as_posix()}")
(ROOT / "data").mkdir(exist_ok=True)
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="EmotiX user")
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    module: Mapped[str] = mapped_column(String(30), index=True)
    score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(20))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    crisis_flag: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
Base.metadata.create_all(engine)

def db_session():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(key).decode()
def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_s, key_s = stored.split("$", 1)
        salt, expected = base64.b64decode(salt_s), base64.b64decode(key_s)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except Exception: return False

def _b64(data: bytes) -> str: return base64.urlsafe_b64encode(data).decode().rstrip("=")
def _token(user_id: int) -> str:
    secret = os.getenv("EMOTIX_SECRET_KEY", "dev-only-change-this-secret-before-deployment").encode()
    payload = _b64(json.dumps({"sub": user_id, "exp": int(time.time()) + 60*60*12}).encode())
    sig = _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return payload + "." + sig
def _decode_token(token: str) -> int:
    try:
        payload, sig = token.split(".", 1)
        secret = os.getenv("EMOTIX_SECRET_KEY", "dev-only-change-this-secret-before-deployment").encode()
        expected = _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected): raise ValueError()
        raw = payload + "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(raw))
        if data["exp"] < time.time(): raise ValueError()
        return int(data["sub"])
    except Exception: raise HTTPException(401, "Session expired or invalid. Please sign in again.")

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(db_session)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in to save private assessments.")
    uid = _decode_token(authorization.split(None, 1)[1])
    user = db.get(User, uid)
    if not user: raise HTTPException(401, "Account no longer exists.")
    return user

class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=128)
class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
class AssessmentIn(BaseModel):
    module: str = Field(pattern="^(behaviour|chat|face|voice|fused)$")
    score: float = Field(ge=0, le=10)
    payload: dict[str, Any] = Field(default_factory=dict)
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
class ChatBatchIn(BaseModel):
    messages: list[ChatIn] = Field(max_length=200)

app = FastAPI(title="EmotiX API", version="1.0.0", description="Local prototype API for EmotiX wellbeing assessment.")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"], allow_credentials=True, allow_methods=["GET","POST","DELETE"], allow_headers=["Authorization","Content-Type"])

@app.get("/bridge.js")
def bridge_js():
    path = ROOT / "frontend" / "bridge.js"
    return FileResponse(path, media_type="application/javascript")

@app.get("/", response_class=HTMLResponse)
def home():
    if not FRONTEND.exists(): return HTMLResponse("EmotiX frontend missing. See README.", status_code=500)
    return FRONTEND.read_text(encoding="utf-8")
@app.get("/api/health")
def health(): return {"status":"ok", "app":"EmotiX", "mode":"local-prototype", "llm_configured":bool(os.getenv("OPENAI_API_KEY")), "face_model":"browser-side demo/model-dependent", "voice_model":"browser-side heuristic prototype"}
@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(db_session)):
    email = body.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "An account with this email already exists.")
    user = User(email=email, display_name=body.name.strip(), password_hash=_hash_password(body.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token":_token(user.id), "token_type":"bearer", "user":{"id":user.id,"email":user.email,"name":user.display_name}}
@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))
    if not user or not _verify_password(body.password, user.password_hash): raise HTTPException(401, "Email or password is incorrect.")
    return {"access_token":_token(user.id), "token_type":"bearer", "user":{"id":user.id,"email":user.email,"name":user.display_name}}
@app.get("/api/auth/me")
def me(user: User = Depends(current_user)): return {"id":user.id,"email":user.email,"name":user.display_name}

def band(score: float) -> str:
    return "Low" if score < 3.5 else "Moderate" if score < 6 else "High" if score < 8.5 else "Critical"
@app.post("/api/assessments", status_code=201)
def create_assessment(body: AssessmentIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    # This stores the prototype's supplied score. It does not assert clinical validity.
    row = Assessment(user_id=user.id, module=body.module, score=round(body.score, 2), risk_level=band(body.score), payload_json=json.dumps(body.payload, ensure_ascii=False)[:100_000])
    db.add(row); db.commit(); db.refresh(row)
    return {"id":row.id,"module":row.module,"score":row.score,"risk_level":row.risk_level,"created_at":row.created_at.isoformat()}
@app.get("/api/assessments")
def history(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.scalars(select(Assessment).where(Assessment.user_id == user.id).order_by(Assessment.created_at.desc()).limit(100)).all()
    return [{"id":r.id,"module":r.module,"score":r.score,"risk_level":r.risk_level,"created_at":r.created_at.isoformat()} for r in rows]
@app.delete("/api/assessments")
def delete_history(user: User = Depends(current_user), db: Session = Depends(db_session)):
    db.query(Assessment).filter(Assessment.user_id == user.id).delete(); db.commit(); return {"deleted":True}

CRISIS = re.compile(r"\b(kill myself|killing myself|end my life|want to die|wanna die|suicid\w*|self[- ]?harm|hurt myself|harm myself|no reason to live|better off dead|end it all|can'?t go on|cut myself|don'?t want to live|do not want to live|take my own life)\b", re.I)
def counsellor_reply(message: str, crisis: bool) -> str:
    if crisis:
        return ("I'm really glad you told me. Your safety matters. If you may act on these thoughts or are in immediate danger, call India's emergency number 112 now. You can also call Tele-MANAS at 14416 for free 24/7 mental-health support. If possible, move near someone you trust and tell them directly what is happening. I'm an AI tool and can't provide emergency care.")
    t = message.lower()
    if any(x in t for x in ("anxious","anxiety","panic","worry","worried")):
        return "That sounds unsettling, and I'm glad you shared it. Try taking a slow breath out for a little longer than you breathe in, a few times. What feels like the biggest source of worry right now?"
    if any(x in t for x in ("sad","depress","lonely","hopeless","cry","empty")):
        return "I'm sorry this has been weighing on you. You deserve support, and you don't have to solve everything at once. Would you like to tell me what has been hardest today, or think together about one small next step?"
    if any(x in t for x in ("stress","overwhelm","pressure","exam","workload")):
        return "It sounds like a lot is landing on you at once. It may help to name just one thing that needs attention first and one thing that can wait. What is the most pressing part right now?"
    return "Thank you for sharing that with me. I can listen and help you reflect, though I'm not a clinician. What has been affecting you most lately, and what kind of support would feel useful right now?"
@app.post("/api/chat")
def chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    crisis = bool(CRISIS.search(body.message))
    db.add(ChatMessage(user_id=user.id, role="user", content=body.message, crisis_flag=int(crisis)))
    reply = counsellor_reply(body.message, crisis)
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply, crisis_flag=int(crisis)))
    db.commit()
    return {"reply":reply,"crisis_detected":crisis,"support":{"emergency":"112","tele_manas":"14416"} if crisis else None,"mode":"safety-fallback"}
@app.post("/api/chat/history")
def save_chat_history(body: ChatBatchIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    saved = 0
    for item in body.messages:
        crisis = bool(CRISIS.search(item.message))
        db.add(ChatMessage(user_id=user.id, role="user", content=item.message, crisis_flag=int(crisis))); saved += 1
    db.commit(); return {"saved":saved}
@app.get("/api/chat/history")
def get_chat_history(user: User = Depends(current_user), db: Session = Depends(db_session)):
    rows = db.scalars(select(ChatMessage).where(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at.desc()).limit(100)).all()
    return [{"role":r.role,"content":r.content,"crisis_detected":bool(r.crisis_flag),"created_at":r.created_at.isoformat()} for r in reversed(rows)]
@app.get("/api/report.pdf")
def pdf_report(user: User = Depends(current_user), db: Session = Depends(db_session)):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    rows = db.scalars(select(Assessment).where(Assessment.user_id == user.id).order_by(Assessment.created_at.desc()).limit(50)).all()
    buf=BytesIO(); c=canvas.Canvas(buf,pagesize=letter); w,h=letter; y=h-54
    c.setTitle("EmotiX Wellbeing Report"); c.setFont("Helvetica-Bold",18); c.drawString(48,y,"EmotiX Wellbeing Report"); y-=28
    c.setFont("Helvetica",10); c.drawString(48,y,f"Account: {user.display_name} ({user.email})"); y-=18; c.drawString(48,y,"Experimental prototype — not a diagnosis or substitute for professional care."); y-=28
    if not rows: c.drawString(48,y,"No saved assessments yet."); y-=18
    for r in rows:
        line=f"{r.created_at.strftime('%Y-%m-%d %H:%M')} | {r.module.title()} | {r.score:.1f}/10 | {r.risk_level}"
        c.drawString(48,y,line[:100]); y-=17
        if y<65: c.showPage(); y=h-54; c.setFont("Helvetica",10)
    y-=12; c.drawString(48,y,"If you are in immediate danger in India, call 112. Tele-MANAS: 14416 (24/7).")
    c.save(); return Response(buf.getvalue(),media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=EmotiX-report.pdf"})
@app.get("/api/docs-info")
def docs_info(): return {"api_docs":"/docs","privacy":"Assessments and chat are stored locally in the SQLite database and tied to your account. Do not enter identifying details you do not need to share."}
