import json
from functools import wraps
import httpx
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import url_has_allowed_host_and_scheme
from kb.models import ChunkSynthesis, ChunkRewrite
from kb.services.ollama import ask_ollama, classify
from kb.services.synthesis import ingest_synthesis
from kb.services.rewrite import ingest_rewrite
from kb.services.rag import build_rag_prompt
from kb.services.io import export_kb, import_kb

# ── Mode registry ─────────────────────────────────────────────────────────────
# Each mode maps a display label to its ingestion function and chunk model.
# Adding a new mode only requires a new entry here.
KB_MODES = {
    'synthesis': {
        'label': 'Synthèse',
        'description': 'Fusionne les infos similaires via le LLM',
        'ingest': ingest_synthesis,
        'chunk_model': ChunkSynthesis,
    },
    'rewrite': {
        'label': 'Réécriture',
        'description': 'Le LLM reformule chaque info avant stockage',
        'ingest': ingest_rewrite,
        'chunk_model': ChunkRewrite,
    },
}
DEFAULT_MODE = 'synthesis'


def _get_mode(request):
    key = request.session.get('kb_mode', DEFAULT_MODE)
    return KB_MODES.get(key, KB_MODES[DEFAULT_MODE])


def htmx_login_required(view_func):
    """Like @login_required but returns 401 for HTMX requests instead of redirecting."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if request.headers.get('HX-Request'):
                return HttpResponse("Session expirée.", status=401)
            return redirect('kb:login')
        return view_func(request, *args, **kwargs)
    return wrapped


# ── Pages ─────────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def home(request):
    return render(request, 'kb/home.html')


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('kb:home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('kb:home')
    else:
        form = AuthenticationForm()
    return render(request, 'kb/login.html', {'form': form})


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return redirect('kb:home')


# ── Chat ──────────────────────────────────────────────────────────────────────

@htmx_login_required
@require_http_methods(["GET", "POST"])
def chat(request):
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if not message:
            return HttpResponse(status=204)
        return render(request, "kb/chat_message.html", {"user_message": message})
    mode_key = request.session.get('kb_mode', DEFAULT_MODE)
    return render(request, "kb/chat.html", {
        'kb_modes': KB_MODES,
        'current_mode': mode_key,
    })


@htmx_login_required
@require_http_methods(["POST"])
def set_mode(request):
    """Stores the selected KB mode in the session."""
    mode = request.POST.get('mode')
    if mode in KB_MODES:
        request.session['kb_mode'] = mode
    return HttpResponse(status=204)


@htmx_login_required
@require_http_methods(["GET"])
def chat_answer(request):
    """Phase 1 — classifies the message, ingests if info or returns thinking indicator."""
    message = request.GET.get("msg", "").strip()
    if not message:
        return HttpResponse("")
    try:
        intent = classify(message)
        if intent == "info":
            mode = _get_mode(request)
            mode['ingest'](message)
            return HttpResponse("")
        return render(request, "kb/chat_indicator.html", {
            "label": "Thinking...",
            "next_url": request.build_absolute_uri(f"/chat/think/?msg={message}"),
        })
    except httpx.ConnectError:
        return render(request, "kb/chat_answer.html", {
            "answer": "Ollama n'est pas accessible (port 11434).",
        })


@htmx_login_required
@require_http_methods(["GET"])
def chat_think(request):
    print("MODE:", request.session.get('kb_mode'))
    """Phase 2 — searches relevant chunks and calls Ollama with context."""
    message = request.GET.get("msg", "").strip()
    if not message:
        return HttpResponse("")
    try:
        chunk_model = _get_mode(request)['chunk_model']
        answer = ask_ollama(build_rag_prompt(message, chunk_model), message)
        return render(request, "kb/chat_answer.html", {"answer": answer})
    except httpx.ConnectError:
        return render(request, "kb/chat_answer.html", {
            "answer": "Ollama n'est pas accessible (port 11434).",
        })


# ── Export / Import ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def export_view(request):
    mode_key = request.session.get('kb_mode', DEFAULT_MODE)
    mode = KB_MODES.get(mode_key, KB_MODES[DEFAULT_MODE])
    data = export_kb(mode['chunk_model'], mode_key)
    response = HttpResponse(
        json.dumps(data, ensure_ascii=False, indent=2),
        content_type='application/json',
    )
    response['Content-Disposition'] = f'attachment; filename="mnemos_export_{mode_key}.json"'
    return response


@login_required
@require_http_methods(["POST"])
def import_view(request):
    file = request.FILES.get('file')
    if not file:
        return HttpResponse("Aucun fichier fourni.", status=400)
    try:
        data = json.load(file)
        mode_key = data.get('mode', request.session.get('kb_mode', DEFAULT_MODE))
        mode = KB_MODES.get(mode_key, KB_MODES[DEFAULT_MODE])
        import_kb(data, request.user, mode['chunk_model'])
        return redirect('kb:home')
    except Exception as e:
        return HttpResponse(f"Erreur d'import : {e}", status=400)
