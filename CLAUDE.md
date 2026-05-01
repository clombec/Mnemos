# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Mnemos — Local AI Knowledge Base

A **100% local** web application allowing a company to store internal procedures and retrieve them via a conversational AI interface. No data leaves the machine.

---

## Setup on a new machine

### Prerequisites
- Python 3.12+, Docker Desktop, Ollama

### Installation

```bash
# 1. Clone the repo and create the virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install django djangorestframework psycopg2-binary pgvector httpx Pillow

# 3. Create the .env file (not committed — see structure below)

# 4. Start PostgreSQL
docker compose up -d

# 5. Create PostgreSQL extensions (once per volume)
docker exec mnemos-postgres psql -U postgres -d mnemos_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec mnemos-postgres psql -U postgres -d mnemos_dev -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# 6. Run migrations and create a Django superuser
python manage.py migrate
python manage.py createsuperuser

# 7. Start the dev server
python manage.py runserver
```

### `.env` file structure (create manually, never commit)

```
SECRET_KEY=<generate with: python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))">
DB_NAME=mnemos_dev
DB_USER=postgres
DB_PASSWORD=<postgres superuser password>
DB_HOST=localhost
DB_PORT=5432
POSTGRES_SUPERUSER=postgres
POSTGRES_SUPERUSER_PASSWORD=<same password>
```

`settings.py` loads `.env` at startup with no external dependency (pure stdlib).

### Common commands

```bash
# Run tests
python manage.py test
python manage.py test kb.tests.TestClassName.test_method

# Check Ollama is running
curl http://localhost:11434/api/tags
```

---

## Architecture

### Stack

| Layer | Technology |
|---|---|
| Backend | Python / Django 5.1 + Django REST Framework |
| Database | PostgreSQL 15 + pgvector (vector search) + pg_trgm (full-text BM25) |
| LLM | Ollama local (`http://localhost:11434`) |
| Frontend | HTMX + Alpine.js — server-rendered templates, no SPA |
| Infrastructure | Docker (PostgreSQL only) |

### Project structure

The Django project is named `mnemos`, the main app is `kb` (knowledge base).

```
mnemos/                   ← Django project
  settings.py             ← all configuration, loads .env at startup
  urls.py                 ← root router: '' → kb.urls, 'admin/' → admin

kb/                       ← main application
  models.py               ← Procedure, Chunk, Image
  views.py                ← home, login_view, logout_view (+ future: chat, ingestion)
  urls.py                 ← app_name='kb', routes below
  services/               ← business logic (to implement)
    ollama.py             ← LLM calls
    rag.py                ← hybrid search + reranking
    ingestion.py          ← chunking + embedding
  templates/kb/
    home.html             ← main page (requires login), topbar with username + logout
    login.html            ← standalone login form, no base template yet
    chat.html             ← full chat page (HTMX, messages list + input form)
    chat_message.html     ← fragment: user bubble + classifying indicator (auto-triggers chat_answer)
    chat_indicator.html   ← fragment: animated thinking dots (auto-triggers next_url)
    chat_answer.html      ← fragment: assistant answer bubble
```

### URL routing

| URL | View | Auth required |
|---|---|---|
| `/` | `kb:home` | Yes |
| `/login/` | `kb:login` | No |
| `/logout/` | `kb:logout` (POST only) | No |
| `/chat/` | `kb:chat` (GET: page, POST: user message fragment) | Yes |
| `/chat/answer/` | `kb:chat_answer` (GET: classify → ingest or thinking indicator) | Yes |
| `/chat/think/` | `kb:chat_think` (GET: Ollama answer fragment) | Yes |
| `/admin/` | Django admin | Yes (superuser) |

### Data models

```
Procedure  →  title, created_at, updated_at, created_by (FK User)
Chunk      →  procedure (FK nullable), content, embedding (VectorField 768d), chunk_index, created_at
Image      →  chunk (FK), file (ImageField), caption, created_at
```

### Authentication

- Django native auth (User + Session)
- Every view requires `@login_required`
- `LOGIN_URL = 'kb:login'` in settings
- Login redirects to `?next=` param if present, validated with `url_has_allowed_host_and_scheme`
- Logout is POST-only (CSRF protection)

### RAG pipeline

Two flows based on message classification:

**Question** → hybrid search (pgvector + BM25 pg_trgm) → 20 candidates → reranking → top 5 → Ollama prompt → response with associated images

**Information input** → semantic chunking → embedding → store in PostgreSQL → silent acknowledgment (no response displayed)

Reranking: top 5 from 20 candidates. Target latency: ~4s.

### LLM configuration

One variable to change per environment in `settings.py`:

```python
OLLAMA_MODEL = "qwen2.5:7b-instruct-q4_K_M"    # current — RTX 4060 8 Go
OLLAMA_EMBED_MODEL = "nomic-embed-text"          # 768-dim embeddings
OLLAMA_BASE_URL = "http://localhost:11434"
```

### Ollama call pattern

```python
import httpx
from django.conf import settings

def ask_ollama(system_prompt: str, user_message: str, model: str = None) -> str:
    model = model or settings.OLLAMA_MODEL
    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        },
        timeout=60.0,
    )
    return response.json()["message"]["content"]
```

---

## Critical constraints

- **No cloud API** without explicit validation — data is sensitive (internal procedures)
- **Authentication required** on every view
- **JSON export/import**: procedures + embeddings + base64 images must be portable offline

---

## Phase 1 MVP — progress

- [x] Django auth (login/logout) — `@login_required` on all views, `LOGIN_URL = 'kb:login'`, secure `?next=` redirect
- [x] Conversational interface (HTMX) — two-phase response: user bubble immediately, then Ollama async
- [x] Question/info classifier (Ollama prompt) — `classify()` in `kb/services/ollama.py`, fast model
- [x] Ingestion: chunking + embedding + pgvector storage — `kb/services/ingestion.py`
- [x] Hybrid vector + full-text search — `kb/services/rag.py`, pgvector cosine + pg_trgm word_similarity
- [x] Candidate chunk reranking — score = 0.7 × vec_sim + 0.3 × trgm_sim, top 5 from 20
- [ ] Response with associated images
- [x] JSON export / import — `kb/services/io.py`, vues `export_view` + `import_view`, boutons dans `home.html`

---

## Technical notes

- **Sessions**: `SESSION_ENGINE = 'django.contrib.sessions.backends.cache'` — avoids a DB hit on every request
- **DB connection**: `CONN_MAX_AGE = 60` — reuses PostgreSQL connections to avoid WSL2/Docker TCP overhead on Windows (~2s per new connection)
- **Credentials**: all in `.env` (not committed). `docker-compose.yml` reads via `${VAR}`. `settings.py` parses `.env` at startup without external libraries.
- **PostgreSQL port**: bound to `127.0.0.1:5432` only — not exposed on the local network
