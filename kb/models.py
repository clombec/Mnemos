from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField


class Procedure(models.Model):
    """Procédure enregistrée dans la base de connaissance"""
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Chunk(models.Model):
    """Fragment d'une procédure avec embedding vectoriel"""
    procedure = models.ForeignKey(
        Procedure,
        on_delete=models.CASCADE,
        related_name='chunks',
        null=True,
        blank=True
    )
    content = models.TextField()
    embedding = VectorField(dimensions=768, null=True, blank=True)
    chunk_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk {self.chunk_index}: {self.content[:50]}..."

    class Meta:
        ordering = ['procedure', 'chunk_index']


class Image(models.Model):
    """Image associée à un chunk"""
    chunk = models.ForeignKey(
        Chunk,
        on_delete=models.CASCADE,
        related_name='images'
    )
    file = models.ImageField(upload_to='kb_images/')
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image: {self.caption or self.file.name}"

    class Meta:
        ordering = ['-created_at']
