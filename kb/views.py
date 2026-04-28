from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.utils.http import url_has_allowed_host_and_scheme


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


@require_http_methods(["POST"])
def logout_view(request):
    """Déconnexion utilisateur"""
    logout(request)
    return redirect('kb:home')

