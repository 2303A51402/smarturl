# ⚡ SmartURL — AI-Powered URL Shortener with Analytics

> A production-grade URL shortener with real-time click analytics, AI-based categorisation, and a clean dashboard UI.

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite%2FSQLAlchemy-blue)](https://www.sqlalchemy.org)
[![Deployed on Render](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render)](https://render.com)
[![Frontend on Netlify](https://img.shields.io/badge/Frontend-Netlify-00C7B7?logo=netlify)](https://netlify.com)

---

## 🚀 Live Demo

- **Frontend:** `https://smarturl-kalyan.netlify.app`
- **API Docs (Swagger):** `https://smarturl-api.onrender.com/docs`

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔗 URL Shortening | Hash-based + optional custom alias |
| 🤖 AI Categorisation | Auto-tags links as GitHub / YouTube / News / Cloud / etc. |
| 📊 Click Analytics | Per-URL daily & hourly click charts |
| 📋 Dashboard | Total URLs, total clicks, top links, category breakdown |
| 🗑️ Delete URLs | Full CRUD via REST API |
| 📄 Swagger UI | Auto-generated API docs at `/docs` |
| 💾 Persistent DB | SQLite via SQLAlchemy ORM |
| 🌐 CORS-enabled | Ready for frontend/backend separation |

---

## 🏗️ Tech Stack

```
Backend   FastAPI · SQLAlchemy · SQLite · Uvicorn · Pydantic v2
Frontend  Vanilla HTML/CSS/JS · Chart.js
Deploy    Render (backend) · Netlify (frontend)
```

---

## 📂 Project Structure

```
url-shortener/
├── backend/
│   ├── main.py            # All API routes + DB models
│   └── requirements.txt   # Python dependencies
├── frontend/
│   └── index.html         # Single-page dashboard UI
├── serve.py               # Combined server (optional)
├── render.yaml            # Render deployment config
├── netlify.toml           # Netlify redirect config
├── Procfile               # Railway / Heroku deploy
└── README.md
```

---

## 🛠️ Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/smarturl.git
cd smarturl

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Start the backend
uvicorn backend.main:app --reload --port 8000

# 4. Open the frontend
# Just open frontend/index.html in your browser
# OR visit http://localhost:8000/docs for the API
```

---

## 🌐 Deploy to Production (Free)

### Step 1 — Deploy Backend to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Deploy — Render gives you a live URL like `https://smarturl-api.onrender.com`

### Step 2 — Update Frontend API URL

In `frontend/index.html`, find line:
```js
const API = '';  // same origin
```
Change it to:
```js
const API = 'https://smarturl-api.onrender.com';
```

### Step 3 — Deploy Frontend to Netlify

1. Go to [netlify.com](https://netlify.com) → New site from Git
2. Connect your GitHub repo
3. Set **Publish directory** to `frontend`
4. Deploy — Netlify gives you a live URL like `https://smarturl-kalyan.netlify.app`

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/shorten` | Shorten a URL, returns AI title + category |
| `GET` | `/api/urls` | List all URLs (`?limit=20&skip=0`) |
| `GET` | `/api/stats/{code}` | Click analytics for a URL |
| `GET` | `/api/dashboard` | Overview stats + category breakdown |
| `DELETE` | `/api/urls/{code}` | Delete a shortened URL |
| `GET` | `/{code}` | Redirect + log click |
| `GET` | `/docs` | Swagger interactive API docs |

### Example Request

```bash
curl -X POST https://smarturl-api.onrender.com/api/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/2303A51402", "custom_alias": "my-github"}'
```

### Example Response

```json
{
  "short_code": "my-github",
  "short_url": "https://smarturl-api.onrender.com/my-github",
  "original_url": "https://github.com/2303A51402",
  "ai_title": "Github 2303a51402",
  "ai_category": "GitHub",
  "created_at": "2025-01-15T10:30:00",
  "click_count": 0
}
```

---

## 🧠 System Design Highlights

- **Hash-based short codes** using MD5 with collision fallback to random codes
- **Click logging** stored in a separate `clicks` table for analytics
- **Rule-based AI categorisation** — extensible to real ML models
- **SQLAlchemy ORM** with clean separation of models, schemas, and routes
- **CORS middleware** for frontend/backend decoupled architecture
- **Pydantic v2** for request validation and response serialisation

---

## 👤 Author

**Vanga Kalyan Prasad**  
[LinkedIn](https://www.linkedin.com/in/kalyan-p-0135a53b6) · [GitHub](https://github.com/2303A51402) · [Email](mailto:vangakalyan18@gmail.com)
