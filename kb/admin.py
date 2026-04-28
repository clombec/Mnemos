from django.contrib import admin
from .models import Procedure, Chunk, Image


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'created_at', 'updated_at')
    search_fields = ('title',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Chunk)
class ChunkAdmin(admin.ModelAdmin):
    list_display = ('chunk_index', 'procedure', 'created_at')
    list_filter = ('procedure', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'chunk', 'created_at')
    list_filter = ('chunk', 'created_at')
    readonly_fields = ('created_at',)
