from pgvector.django import CosineDistance
from kb.models import ChunkSynthesis
from kb.services.ingestion import chunk_text
from kb.services.ollama import embed, ask_ollama

SYNTHESIS_THRESHOLD = 0.92  # cosine similarity above which we synthesize instead of adding


def _find_similar(vector) -> ChunkSynthesis | None:
    result = (
        ChunkSynthesis.objects
        .filter(embedding__isnull=False)
        .annotate(dist=CosineDistance('embedding', vector))
        .order_by('dist')
        .first()
    )
    if result is None:
        return None
    similarity = 1 - result.dist / 2
    return result if similarity >= SYNTHESIS_THRESHOLD else None


def _synthesize(existing: str, new_info: str) -> str:
    system = (
        "You are a knowledge base manager. "
        "Merge EXISTING and NEW into one clear, complete piece of knowledge. "
        "If they are duplicates, return the most complete version. "
        "If they complement each other, combine them. "
        "If they contradict, prefer the NEW information. "
        "Return only the merged knowledge — no explanation, no preamble."
    )
    return ask_ollama(system, f"EXISTING:\n{existing}\n\nNEW:\n{new_info}")


def ingest_synthesis(text: str, procedure=None) -> int:
    """Mode 2: chunk → embed → synthesize with similar existing chunk or store new."""
    chunks = chunk_text(text)
    existing_count = ChunkSynthesis.objects.filter(procedure=procedure).count()
    stored = 0

    for i, content in enumerate(chunks):
        vector = embed(content)
        similar = _find_similar(vector)

        if similar:
            synthesized = _synthesize(similar.content, content)
            similar.content = synthesized
            similar.embedding = embed(synthesized)
            similar.save(update_fields=['content', 'embedding'])
        else:
            ChunkSynthesis.objects.create(
                procedure=procedure,
                content=content,
                source_text=content,
                embedding=vector,
                chunk_index=existing_count + stored,
            )
            stored += 1

    return len(chunks)
