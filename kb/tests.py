import pytest
from django.urls import reverse


@pytest.fixture
def user(db):
    from django.contrib.auth.models import User
    return User.objects.create_user(username="testuser", password="testpass123")


# --- Home view ---

def test_home_redirects_when_not_logged_in(client):
    response = client.get(reverse("kb:home"))
    assert response.status_code == 302
    assert "/login/" in response["Location"]

def test_home_accessible_when_logged_in(client, user):
    client.login(username="testuser", password="testpass123")
    response = client.get(reverse("kb:home"))
    assert response.status_code == 200


# --- Login view ---

def test_login_page_loads(client):
    response = client.get(reverse("kb:login"))
    assert response.status_code == 200

def test_login_redirects_to_home_on_success(client, user):
    response = client.post(reverse("kb:login"), {
        "username": "testuser",
        "password": "testpass123",
    })
    assert response.status_code == 302
    assert response["Location"] == reverse("kb:home")

def test_login_stays_on_page_with_wrong_password(client, user):
    response = client.post(reverse("kb:login"), {
        "username": "testuser",
        "password": "wrongpassword",
    })
    assert response.status_code == 200

def test_login_redirects_already_authenticated_user(client, user):
    client.login(username="testuser", password="testpass123")
    response = client.get(reverse("kb:login"))
    assert response.status_code == 302
    assert response["Location"] == reverse("kb:home")

def test_login_respects_next_param(client, user):
    response = client.post(
        reverse("kb:login") + "?next=/admin/",
        {"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 302
    assert response["Location"] == "/admin/"


# --- Logout view ---

def test_logout_requires_post(client, user):
    client.login(username="testuser", password="testpass123")
    response = client.get(reverse("kb:logout"))
    assert response.status_code == 405

def test_logout_redirects_to_home(client, user):
    client.login(username="testuser", password="testpass123")
    response = client.post(reverse("kb:logout"))
    assert response.status_code == 302
    assert response["Location"] == reverse("kb:home")

def test_logout_ends_session(client, user):
    client.login(username="testuser", password="testpass123")
    client.post(reverse("kb:logout"))
    response = client.get(reverse("kb:home"))
    assert response.status_code == 302  # redirected back to login
