# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet : Mnemos — Base de Connaissance IA Locale

Application web **100% locale** permettant à une entreprise d'enregistrer des procédures et de les restituer via une interface conversationnelle IA. Aucune donnée ne transite par internet.

---

## Commandes de développement

```bash
# Installer les dépendances
pip install django djangorestframework psycopg2-binary pgvector httpx Pillow

# Initialiser le projet (à faire une seule fois)
django-admin startproject mnemos .
python manage.py startapp kb

# Migrations et démarrage
python manage.py makemigrations
python manage.py migrate
python manage.py runserver

# Créer un superuser
python manage.py createsuperuser

# Lancer les tests
python manage.py test
python manage.py test kb.tests.TestClassName.test_method  # test unique

# Extensions PostgreSQL requises (à activer une fois)
# psql -d <dbname> -c "CREATE EXTENSION IF NOT EXISTS vector;"
# psql -d <dbname> -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

# Vérifier qu'Ollama tourne
curl http://localhost:11434/api/tags
```

---

## Architecture

### Stack

- **Backend** : Python / Django + Django REST Framework
- **BDD** : PostgreSQL + pgvector (vectoriel) + pg_trgm (full-text BM25)
- **LLM** : Ollama local (`http://localhost:11434`)
- **Frontend** : HTMX + Alpine.js (pas de SPA), templates Django

### Structure d'application Django

Le projet Django s'appelle `mnemos`, l'app principale s'appelle `kb` (knowledge base).

```
mnemos/          ← projet Django (settings, urls racine)
kb/              ← app principale
  models.py      ← Procedure, Chunk, Image
  views.py       ← chat, ingestion
  services/      ← logique métier : ollama.py, rag.py, ingestion.py
  templates/kb/  ← HTML HTMX
```

### Modèles de données

```
Procedure  →  title, created_at, updated_at, created_by (FK User)
Chunk      →  procedure (FK nullable), content, embedding (VectorField), chunk_index, created_at
Image      →  chunk (FK), file (ImageField), caption, created_at
```

Auth : système natif Django (User + Session). Toute vue nécessite `@login_required`.

### Pipeline RAG

Deux flux selon la classification du message entrant :

**Question** → recherche hybride (vectorielle pgvector + BM25 pg_trgm) → 20 candidats → re-ranking → top 5 → prompt Ollama → réponse avec images

**Apport d'info** → chunking sémantique → embedding → stockage PostgreSQL → ack silencieux (aucune réponse affichée)

Re-ranking : top 5 sur 20 candidats. Latence cible : ~4 s.

### Configuration LLM

Dans `settings.py`, une seule variable à changer selon l'environnement :

```python
OLLAMA_MODEL = "qwen2.5:7b-instruct-q8_0"      # proto MacBook Air M4
# OLLAMA_MODEL = "qwen2.5:14b-instruct-q4_K_M"  # prod RTX 3060
OLLAMA_BASE_URL = "http://localhost:11434"
```

### Appel Ollama

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

## Contraintes critiques

- **Aucune API cloud** sans validation explicite — données sensibles (procédures internes)
- **Authentification obligatoire** sur toutes les vues
- **Export/import JSON** : procédures + embeddings + images base64 doivent être portables hors réseau

---

## Phase 1 MVP — état d'avancement

- [ ] Auth Django (login/logout)
- [ ] Interface conversationnelle (HTMX)
- [ ] Classifieur question/info (prompt Ollama)
- [ ] Ingestion : chunking + embedding + stockage pgvector
- [ ] Recherche hybride vectorielle + full-text
- [ ] Re-ranking des chunks candidats
- [ ] Réponse avec images associées
- [ ] Export / Import JSON
