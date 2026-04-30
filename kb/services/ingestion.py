import re
from kb.models import Chunk
from kb.services.ollama import embed


def chunk_text(text: str, max_words: int = 150) -> list[str]:
    """Split text into chunks by paragraph, merging short ones."""
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    chunks = []
    current = []
    current_words = 0

    for para in paragraphs:
        words = len(para.split())
        if current_words + words > max_words and current:
            chunks.append(" ".join(current))
            current = [para]
            current_words = words
        else:
            current.append(para)
            current_words += words

    if current:
        chunks.append(" ".join(current))

    return chunks


def ingest(text: str, procedure=None) -> int:
    """Chunk, embed and store text. Returns the number of chunks created."""
    chunks = chunk_text(text)
    existing_count = Chunk.objects.filter(procedure=procedure).count()

    for i, content in enumerate(chunks):
        vector = embed(content)
        Chunk.objects.create(
            procedure=procedure,
            content=content,
            embedding=vector,
            chunk_index=existing_count + i,
        )

    return len(chunks)
