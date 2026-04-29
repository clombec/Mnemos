# Test suite

## Overview

Tests are written with **pytest** + **pytest-django**. They cover the authentication layer (home access, login, logout) and run against a temporary PostgreSQL test database created and destroyed automatically by pytest-django.

Run all tests:
```bash
pytest kb/tests.py -v
```

---

## Structure

```
kb/tests.py
├── fixture: user          ← creates a standard test user in the DB
│
├── Home view
│   ├── test_home_redirects_when_not_logged_in
│   └── test_home_accessible_when_logged_in
│
├── Login view
│   ├── test_login_page_loads
│   ├── test_login_redirects_to_home_on_success
│   ├── test_login_stays_on_page_with_wrong_password
│   ├── test_login_redirects_already_authenticated_user
│   └── test_login_respects_next_param
│
└── Logout view
    ├── test_logout_requires_post
    ├── test_logout_redirects_to_home
    └── test_logout_ends_session
```

---

## Fixture

### `user`
Creates a standard Django user (`testuser` / `testpass123`) in the test database. Used by all tests that require an authenticated state.

---

## Home view tests

### `test_home_redirects_when_not_logged_in`
Verifies that an unauthenticated GET request to `/` returns a 302 redirect and that the redirect URL contains `/login/`. Ensures `@login_required` is active on the home view.

### `test_home_accessible_when_logged_in`
Verifies that an authenticated GET request to `/` returns HTTP 200. Confirms the home page renders normally for a logged-in user.

---

## Login view tests

### `test_login_page_loads`
Verifies that an unauthenticated GET request to `/login/` returns HTTP 200. Confirms the login page is publicly accessible.

### `test_login_redirects_to_home_on_success`
Verifies that a POST to `/login/` with correct credentials returns a 302 redirect to `/`. Confirms the happy-path login flow works end to end.

### `test_login_stays_on_page_with_wrong_password`
Verifies that a POST to `/login/` with a wrong password returns HTTP 200 (form re-displayed with errors). Ensures bad credentials do not grant access.

### `test_login_redirects_already_authenticated_user`
Verifies that a GET to `/login/` by an already authenticated user returns a 302 redirect to `/`. Prevents logged-in users from seeing the login page again.

### `test_login_respects_next_param`
Verifies that after a successful login, the user is redirected to the URL provided in the `?next=` query parameter (here `/admin/`) rather than the default home. Confirms the post-login redirect logic works correctly.

---

## Logout view tests

### `test_logout_requires_post`
Verifies that a GET request to `/logout/` returns HTTP 405 (Method Not Allowed). Ensures logout cannot be triggered by a simple link click, protecting against CSRF-based logout attacks.

### `test_logout_redirects_to_home`
Verifies that a POST to `/logout/` returns a 302 redirect to `/`. Confirms the logout flow completes correctly.

### `test_logout_ends_session`
Verifies that after a POST to `/logout/`, a subsequent GET to `/` returns a 302 redirect (user is no longer authenticated). Confirms the session is actually invalidated, not just redirected.
