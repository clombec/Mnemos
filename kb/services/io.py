import base64
from datetime import datetime, timezone
from django.core.files.base import ContentFile
from kb.models import Procedure, Image


def _has_images(chunk_model) -> bool:
    return hasattr(chunk_model, 'images')


def _serialize_chunk(chunk, with_images: bool) -> dict:
    embedding = chunk.embedding
    if hasattr(embedding, 'tolist'):
        embedding = embedding.tolist()
    data = {
        "content": chunk.content,
        "source_text": getattr(chunk, 'source_text', chunk.content),
        "embedding": embedding,
        "chunk_index": chunk.chunk_index,
        "images": [],
    }
    if with_images:
        for img in chunk.images.all():
            with img.file.open('rb') as f:
                data["images"].append({
                    "name": img.file.name.split('/')[-1],
                    "caption": img.caption,
                    "data": base64.b64encode(f.read()).decode(),
                })
    return data


def export_kb(chunk_model, mode_key: str) -> dict:
    result = {
        "version": 1,
        "mode": mode_key,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "procedures": [],
        "orphan_chunks": [],
    }
    with_images = _has_images(chunk_model)

    for proc in Procedure.objects.all():
        qs = chunk_model.objects.filter(procedure=proc)
        if with_images:
            qs = qs.prefetch_related('images')
        result["procedures"].append({
            "title": proc.title,
            "created_at": proc.created_at.isoformat(),
            "chunks": [_serialize_chunk(c, with_images) for c in qs],
        })

    orphans = chunk_model.objects.filter(procedure__isnull=True)
    if with_images:
        orphans = orphans.prefetch_related('images')
    for chunk in orphans:
        result["orphan_chunks"].append(_serialize_chunk(chunk, with_images))

    return result


def import_kb(data: dict, user, chunk_model) -> dict:
    counts = {"procedures": 0, "chunks": 0, "images": 0}

    def _create_images(chunk, images_data):
        for img_data in images_data:
            content = base64.b64decode(img_data["data"])
            img = Image(chunk=chunk, caption=img_data.get("caption", ""))
            img.file.save(img_data.get("name", "image.png"), ContentFile(content), save=True)
            counts["images"] += 1

    def _create_chunk(procedure, chunk_data):
        fields = dict(
            procedure=procedure,
            content=chunk_data["content"],
            source_text=chunk_data.get("source_text", chunk_data["content"]),
            embedding=chunk_data["embedding"],
            chunk_index=chunk_data["chunk_index"],
        )
        # source_text only exists on ChunkSynthesis / ChunkRewrite, not legacy Chunk
        if not hasattr(chunk_model, 'source_text'):
            fields.pop('source_text')
        return chunk_model.objects.create(**fields)

    for proc_data in data.get("procedures", []):
        proc = Procedure.objects.create(title=proc_data["title"], created_by=user)
        counts["procedures"] += 1
        for chunk_data in proc_data.get("chunks", []):
            chunk = _create_chunk(proc, chunk_data)
            counts["chunks"] += 1
            _create_images(chunk, chunk_data.get("images", []))

    for chunk_data in data.get("orphan_chunks", []):
        chunk = _create_chunk(None, chunk_data)
        counts["chunks"] += 1
        _create_images(chunk, chunk_data.get("images", []))

    return counts
