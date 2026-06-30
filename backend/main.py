from typing import Optional, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import hashlib, random, string, re, os
from collections import Counter
from passlib.context import CryptContext
from jose import JWTError, jwt

# ── Auth config ─────────────────────────────────────────────────────────────
# In production, set SECRET_KEY as an environment variable (e.g. on Render).
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)

# ── Database setup ────────────────────────────────────────────────────────────
DATABASE_URL = "sqlite:///./urls.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

class URLRecord(Base):
    __tablename__ = "urls"
    short_code   = Column(String(10), primary_key=True, index=True)
    original_url = Column(Text, nullable=False)
    custom_alias = Column(String(50), nullable=True)
    ai_title     = Column(String(200), nullable=True)
    ai_category  = Column(String(50), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    click_count  = Column(Integer, default=0)
    last_clicked = Column(DateTime, nullable=True)
    owner_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

class ClickLog(Base):
    __tablename__ = "clicks"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    short_code = Column(String(10), index=True)
    clicked_at = Column(DateTime, default=datetime.utcnow)
    user_agent = Column(Text, nullable=True)
    referer    = Column(Text, nullable=True)

Base.metadata.create_all(bind=engine)

# ── AI helpers (no API key needed — rule-based smart categorisation) ──────────
CATEGORY_RULES = {
    "GitHub":     ["github.com"],
    "YouTube":    ["youtube.com", "youtu.be"],
    "LinkedIn":   ["linkedin.com"],
    "News":       ["news", "bbc", "cnn", "hindu", "times", "reuters", "ndtv"],
    "E-commerce": ["amazon", "flipkart", "myntra", "meesho", "shopify"],
    "Docs":       ["docs", "confluence", "notion", "readme"],
    "Social":     ["twitter.com", "x.com", "instagram", "facebook", "reddit"],
    "Research":   ["arxiv", "scholar", "ieee", "springer", "researchgate"],
    "Cloud":      ["aws", "azure", "cloud", "gcp", "heroku", "vercel", "netlify", "render"],
    "Video":      ["vimeo", "dailymotion", "twitch"],
}

def ai_categorise(url: str) -> tuple[str, str]:
    """Smart rule-based AI-style categorisation + title extraction."""
    lower = url.lower()
    category = "General"
    for cat, keywords in CATEGORY_RULES.items():
        if any(k in lower for k in keywords):
            category = cat
            break

    # Extract a human-readable title from the URL path
    try:
        path = re.sub(r"https?://[^/]+", "", url).strip("/")
        parts = re.split(r"[/\-_?&=#]", path)
        words = [p for p in parts if len(p) > 2 and not p.isdigit()]
        title = " ".join(words[:5]).title() if words else url[:60]
    except Exception:
        title = url[:60]

    return title or url[:60], category

def generate_short_code(url: str, length: int = 6) -> str:
    h = hashlib.md5(url.encode()).hexdigest()[:length]
    return h

def random_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

# ── Auth helpers ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> "User":
    """Required auth — raises 401 if no valid token is provided."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception
        return user
    finally:
        db.close()

def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional["User"]:
    """Optional auth — returns None instead of raising, so anonymous shortening still works."""
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == int(user_id)).first()
    finally:
        db.close()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="SmartURL API",
    description="AI-Powered URL Shortener with Click Analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str

class ShortenRequest(BaseModel):
    url: str
    custom_alias: Optional[str] = None

class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    ai_title: str
    ai_category: str
    created_at: str
    click_count: int

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "SmartURL API is running 🚀", "docs": "/docs"}

# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.post("/api/signup", response_model=TokenResponse, tags=["Auth"])
def signup(body: SignupRequest):
    """Register a new user and return a JWT access token."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == body.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        if len(body.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

        user = User(email=body.email, hashed_password=hash_password(body.password))
        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token(user.id)
        return TokenResponse(access_token=token, email=user.email)
    finally:
        db.close()

@app.post("/api/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest):
    """Authenticate a user and return a JWT access token."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == body.email).first()
        if not user or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        token = create_access_token(user.id)
        return TokenResponse(access_token=token, email=user.email)
    finally:
        db.close()

@app.get("/api/me", tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {"id": current_user.id, "email": current_user.email, "created_at": current_user.created_at.isoformat()}

@app.post("/api/shorten", response_model=URLResponse, tags=["URLs"])
def shorten_url(body: ShortenRequest, request: Request, current_user: Optional[User] = Depends(get_optional_user)):
    """Shorten a URL with optional custom alias. AI auto-categorises the link.
    Works anonymously, but if logged in, the link is attached to your account."""
    db = SessionLocal()
    try:
        url = body.url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        alias = body.custom_alias.strip() if body.custom_alias else None

        if alias:
            existing = db.query(URLRecord).filter(URLRecord.short_code == alias).first()
            if existing:
                raise HTTPException(status_code=409, detail="Alias already taken")
            code = alias
        else:
            code = generate_short_code(url)
            if db.query(URLRecord).filter(URLRecord.short_code == code).first():
                code = random_code()

        ai_title, ai_category = ai_categorise(url)
        base = str(request.base_url).rstrip("/")

        record = URLRecord(
            short_code=code,
            original_url=url,
            custom_alias=alias,
            ai_title=ai_title,
            ai_category=ai_category,
            owner_id=current_user.id if current_user else None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return URLResponse(
            short_code=code,
            short_url=f"{base}/{code}",
            original_url=url,
            ai_title=ai_title,
            ai_category=ai_category,
            created_at=record.created_at.isoformat(),
            click_count=0,
        )
    finally:
        db.close()

@app.get("/api/my-urls", tags=["URLs"])
def list_my_urls(limit: int = 20, skip: int = 0, current_user: User = Depends(get_current_user)):
    """List only the URLs created by the currently authenticated user. Requires login."""
    db = SessionLocal()
    try:
        query = db.query(URLRecord).filter(URLRecord.owner_id == current_user.id)
        total = query.count()
        records = query.order_by(URLRecord.created_at.desc()).offset(skip).limit(limit).all()
        return {
            "total": total,
            "urls": [
                {
                    "short_code": r.short_code,
                    "original_url": r.original_url,
                    "ai_title": r.ai_title,
                    "ai_category": r.ai_category,
                    "created_at": r.created_at.isoformat(),
                    "click_count": r.click_count,
                    "last_clicked": r.last_clicked.isoformat() if r.last_clicked else None,
                }
                for r in records
            ],
        }
    finally:
        db.close()

@app.get("/api/urls", tags=["URLs"])
def list_urls(limit: int = 20, skip: int = 0):
    """List all shortened URLs with stats."""
    db = SessionLocal()
    try:
        records = db.query(URLRecord).order_by(URLRecord.created_at.desc()).offset(skip).limit(limit).all()
        total = db.query(URLRecord).count()
        return {
            "total": total,
            "urls": [
                {
                    "short_code": r.short_code,
                    "original_url": r.original_url,
                    "ai_title": r.ai_title,
                    "ai_category": r.ai_category,
                    "created_at": r.created_at.isoformat(),
                    "click_count": r.click_count,
                    "last_clicked": r.last_clicked.isoformat() if r.last_clicked else None,
                }
                for r in records
            ],
        }
    finally:
        db.close()

@app.get("/api/stats/{short_code}", tags=["Analytics"])
def get_stats(short_code: str):
    """Get detailed click analytics for a specific short URL."""
    db = SessionLocal()
    try:
        record = db.query(URLRecord).filter(URLRecord.short_code == short_code).first()
        if not record:
            raise HTTPException(status_code=404, detail="Short code not found")

        clicks = db.query(ClickLog).filter(ClickLog.short_code == short_code).all()

        # Clicks by day
        daily: Counter = Counter()
        for c in clicks:
            day = c.clicked_at.strftime("%Y-%m-%d")
            daily[day] += 1

        # Clicks by hour
        hourly: Counter = Counter()
        for c in clicks:
            hourly[c.clicked_at.hour] += 1

        return {
            "short_code": record.short_code,
            "original_url": record.original_url,
            "ai_title": record.ai_title,
            "ai_category": record.ai_category,
            "created_at": record.created_at.isoformat(),
            "total_clicks": record.click_count,
            "last_clicked": record.last_clicked.isoformat() if record.last_clicked else None,
            "daily_clicks": dict(sorted(daily.items())),
            "hourly_clicks": {str(h): hourly[h] for h in range(24)},
        }
    finally:
        db.close()

@app.get("/api/dashboard", tags=["Analytics"])
def dashboard():
    """Overall dashboard stats — total URLs, total clicks, category breakdown."""
    db = SessionLocal()
    try:
        records = db.query(URLRecord).all()
        total_urls = len(records)
        total_clicks = sum(r.click_count for r in records)

        category_counts: Counter = Counter(r.ai_category for r in records)
        top_urls = sorted(records, key=lambda r: r.click_count, reverse=True)[:5]

        return {
            "total_urls": total_urls,
            "total_clicks": total_clicks,
            "categories": dict(category_counts),
            "top_urls": [
                {
                    "short_code": r.short_code,
                    "ai_title": r.ai_title,
                    "click_count": r.click_count,
                }
                for r in top_urls
            ],
        }
    finally:
        db.close()

@app.delete("/api/urls/{short_code}", tags=["URLs"])
def delete_url(short_code: str, current_user: User = Depends(get_current_user)):
    """Delete a shortened URL. Requires login, and you can only delete links you own."""
    db = SessionLocal()
    try:
        record = db.query(URLRecord).filter(URLRecord.short_code == short_code).first()
        if not record:
            raise HTTPException(status_code=404, detail="Short code not found")
        if record.owner_id is not None and record.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this link")
        db.delete(record)
        db.commit()
        return {"message": f"Deleted {short_code}"}
    finally:
        db.close()

@app.get("/{short_code}", tags=["Redirect"])
def redirect_url(short_code: str, request: Request):
    """Redirect to the original URL and log the click."""
    db = SessionLocal()
    try:
        record = db.query(URLRecord).filter(URLRecord.short_code == short_code).first()
        if not record:
            raise HTTPException(status_code=404, detail="URL not found")

        record.click_count += 1
        record.last_clicked = datetime.utcnow()

        log = ClickLog(
            short_code=short_code,
            user_agent=request.headers.get("user-agent", ""),
            referer=request.headers.get("referer", ""),
        )
        db.add(log)
        db.commit()

        return RedirectResponse(url=record.original_url, status_code=302)
    finally:
        db.close()