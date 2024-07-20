import pytest
from flask import g, session
from flaskr.db import get_db


def test_register(client, app):
    # Test successful GET of registration page.
    assert client.get('/auth/register').status_code == 200

    # Test POST of a new user successfully redirects to login page.
    response = client.post(
        '/auth/register',
        data={
            'username': 'a',
            'password': 'a',
        }
    )
    assert response.headers["Location"] == "/auth/login"

    # Test that the entry was successfully entered into db.
    with app.app_context():
        assert get_db().execute(
            "SELECT * FROM user WHERE username = 'a'",
        ).fetchone() is not None


@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('', '', b'Username is required'),
    ('a', '', b'Password is required'),
    ('test', 'test', b'already registered'),
))
def test_register_validate_input(client, username, password, message):
    response = client.post(
        '/auth/register',
        data={'username': username, 'password': password},
    )
    assert message in response.data


def test_login(client, auth):
    # Test successful GET of login page.
    assert client.get('/auth/login').status_code == 200

    # Test POST of an existing user that redirects to blog index page.
    response = auth.login()
    assert response.headers["Location"] == "/"

    # Test that the user login info is stored in the session.
    with client:
        client.get('/')
        assert session['user_id'] == 1
        assert g.user['username'] == 'test'


@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('a', 'test', b'Incorrect username.'),
    ('test', 'a', b'Incorrect password.'),
))
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert 'user_id' not in session
