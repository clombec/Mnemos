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
    response.raise_for_status()
    return response.json()["message"]["content"]


def embed(text: str) -> list[float]:
    response = httpx.post(
        f"{settings.OLLAMA_BASE_URL}/api/embed",
        json={"model": settings.OLLAMA_EMBED_MODEL, "input": text},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"][0]


def classify(message: str) -> str:
    """Returns 'question', 'info', or 'unclear'."""
    system_prompt = (
        "You are a message classifier. "
        "Respond with exactly one word: 'question' if the user is asking something, "
        "'info' if the user is providing information or a procedure to store, "
        "'unclear' if the intent is not clear or not understandable."
        "An information or procedure must contain at least one actionable instruction to be classified as 'info'. "
        "No punctuation, no explanation."
    )
    result = ask_ollama(system_prompt, message, model=settings.OLLAMA_MODEL).strip().lower()
    return result if result in ("question", "info", "unclear") else "unclear"
