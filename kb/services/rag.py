from pgvector.django import CosineDistance
from django.db.models import FloatField
from django.db.models.expressions import RawSQL
from kb.services.ollama import embed


def hybrid_search(question: str, chunk_model, top_k: int = 5, candidates: int = 20) -> list[str]:
    """Vector + trigram search on chunk_model → rerank → top_k chunk contents."""
    if not chunk_model.objects.filter(embedding__isnull=False).exists():
        return []

    query_vector = embed(question)

    results = list(
        chunk_model.objects
        .filter(embedding__isnull=False)
        .annotate(vec_dist=CosineDistance('embedding', query_vector))
        .annotate(trgm_sim=RawSQL(
            "word_similarity(%s, content)",
            [question],
            output_field=FloatField(),
        ))
        .order_by('vec_dist')[:candidates]
    )

    scored = [
        (0.7 * (1 - c.vec_dist / 2) + 0.3 * c.trgm_sim, c.content)
        for c in results
    ]
    scored.sort(key=lambda x: x[0], reverse=True)

    return [content for _, content in scored[:top_k]]


def build_rag_prompt(question: str, chunk_model) -> str:
    """Returns a system prompt with relevant chunks from chunk_model injected as context."""
    chunks = hybrid_search(question, chunk_model)

    if not chunks:
        return (
            "You are a helpful assistant for internal company procedures. "
            "No relevant procedures are stored yet. "
            "Answer based on your general knowledge or say you don't know."
        )

    context = "\n\n---\n\n".join(chunks)
    return (
        "You are a helpful assistant for internal company procedures. "
        "Answer the question using ONLY the context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"CONTEXT:\n{context}"
    )
