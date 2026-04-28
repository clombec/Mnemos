# Mnemos

A **100% local** AI-powered knowledge base for internal procedures. Store documents, ask questions in natural language, and get answers — no data ever leaves your machine.

## How it works

Mnemos uses a RAG (Retrieval-Augmented Generation) pipeline:

1. **Ingest** — paste or upload a procedure; it is split into chunks, embedded, and stored in PostgreSQL
2. **Ask** — type a question in the chat interface; Mnemos retrieves the most relevant chunks via hybrid search (vector + full-text) and feeds them to the LLM
3. **Answer** — the local LLM (via Ollama) generates a response grounded in your documents, with associated images if any

Everything runs locally: PostgreSQL in Docker, LLM via Ollama.

## Stack

- **Backend** — Python / Django 5.1 + Django REST Framework
- **Database** — PostgreSQL 15 with pgvector and pg_trgm extensions
- **LLM** — Ollama (`qwen2.5:7b` for dev, `qwen2.5:14b` for prod)
- **Frontend** — HTMX + Alpine.js, server-rendered templates

## Requirements

- Python 3.12+
- Docker Desktop
- [Ollama](https://ollama.com) with `qwen2.5:7b-instruct-q8_0` pulled

## Getting started

### 1. Clone and set up the virtual environment

```bash
git clone <repo-url>
cd mnemos
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install django djangorestframework psycopg2-binary pgvector httpx Pillow
```

### 2. Create the `.env` file

Create a `.env` file at the project root (never committed):

```
SECRET_KEY=<generate: python -c "from django.utils.crypto import get_random_string; print(get_random_string(50))">
DB_NAME=mnemos_dev
DB_USER=postgres
DB_PASSWORD=<your password>
DB_HOST=localhost
DB_PORT=5432
POSTGRES_SUPERUSER=postgres
POSTGRES_SUPERUSER_PASSWORD=<same password>
```

### 3. Start PostgreSQL

```bash
docker compose up -d
```

### 4. Initialize the database

```bash
# Enable required extensions (once per volume)
docker exec mnemos-postgres psql -U postgres -d mnemos_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec mnemos-postgres psql -U postgres -d mnemos_dev -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Run migrations and create your user
python manage.py migrate
python manage.py createsuperuser
```

### 5. Pull the LLM model

```bash
ollama pull qwen2.5:7b-instruct-q8_0
```

### 6. Start the server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) and log in.

## Configuration

The LLM model is set in `mnemos/settings.py`:

```python
OLLAMA_MODEL = "qwen2.5:7b-instruct-q8_0"      # dev — MacBook Air M4
# OLLAMA_MODEL = "qwen2.5:14b-instruct-q4_K_M"  # prod — RTX 3060
```

## License

See [LICENSE](LICENSE).
