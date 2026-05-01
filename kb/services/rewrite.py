from kb.models import ChunkRewrite
from kb.services.ingestion import chunk_text
from kb.services.ollama import embed, ask_ollama


def _rewrite(text: str) -> str:
    system = (
        "You are a knowledge base manager. "
        "Reformulate the following information in a clear, concise, factual way. "
        "Extract the key facts. Remove noise and redundancy. "
        "Return only the reformulated knowledge — no explanation, no preamble."
    )
    return ask_ollama(system, text)


def ingest_rewrite(text: str, procedure=None) -> int:
    """Mode 3: chunk → LLM reformulates → embed → store (source_text keeps verbatim original)."""
    chunks = chunk_text(text)
    existing_count = ChunkRewrite.objects.filter(procedure=procedure).count()

    for i, content in enumerate(chunks):
        rewritten = _rewrite(content)
        vector = embed(rewritten)
        ChunkRewrite.objects.create(
            procedure=procedure,
            content=rewritten,
            source_text=content,
            embedding=vector,
            chunk_index=existing_count + i,
        )

    return len(chunks)
