import httpx
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import url_has_allowed_host_and_scheme
from kb.services.ollama import ask_ollama, classify
from kb.services.ingestion import ingest


@login_required
@require_http_methods(["GET"])
def home(request):
    """Page d'accueil"""
    return render(request, 'kb/home.html')


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Connexion utilisateur"""
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


@login_required
@require_http_methods(["GET", "POST"])
def chat(request):
    """Conversational interface"""
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        if not message:
            return HttpResponse(status=204)
        return render(request, "kb/chat_message.html", {"user_message": message})
    return render(request, "kb/chat.html")


@login_required
@require_http_methods(["GET"])
def chat_answer(request):
    """Phase 1 — classifies the message, returns a 'Thinking...' indicator or nothing."""
    message = request.GET.get("msg", "").strip()
    if not message:
        return HttpResponse("")
    try:
        intent = classify(message)
        if intent == "info":
            ingest(message)
            return HttpResponse("")
        return render(request, "kb/chat_indicator.html", {
            "label": "Thinking...",
            "next_url": request.build_absolute_uri(
                f"/chat/think/?msg={message}"
            ),
        })
    except httpx.ConnectError:
        return render(request, "kb/chat_answer.html", {
            "answer": "Ollama n'est pas accessible (port 11434).",
        })


@login_required
@require_http_methods(["GET"])
def chat_think(request):
    """Phase 2 — calls Ollama and returns the answer."""
    message = request.GET.get("msg", "").strip()
    if not message:
        return HttpResponse("")
    try:
        answer = ask_ollama(
            "You are a helpful assistant for internal company procedures. "
            "Answer concisely based on your knowledge. "
            "If you don't know, say so.",
            message,
        )
        return render(request, "kb/chat_answer.html", {"answer": answer})
    except httpx.ConnectError:
        return render(request, "kb/chat_answer.html", {
            "answer": "Ollama n'est pas accessible (port 11434).",
        })


@require_http_methods(["POST"])
def logout_view(request):
    """Déconnexion utilisateur"""
    logout(request)
    return redirect('kb:home')

