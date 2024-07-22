import os
import pytest
import psycopg2

from flask import Flask
from flaskr import create_app
from flaskr.db import get_db, init_db

with open(os.path.join(os.path.dirname(__file__), 'data.sql'), 'rb') as f:
    _data_sql = f.read().decode('utf-8')


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'DATABASE': os.getenv('DATABASE_URL'),
    })

    with app.app_context():
        init_db()
        db = get_db()

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_data_sql)
            conn.commit()

    yield app

    with app.app_context():
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DROP TABLE IF EXISTS posts')
                cur.execute('DROP TABLE IF EXISTS users')
            conn.commit()


@pytest.fixture
def client(app: Flask):
    return app.test_client()


@pytest.fixture
def runner(app: Flask):
    return app.test_cli_runner()


class AuthActions(object):
    def __init__(self, client):
        self._client = client

    def login(self, username='test', password='test'):
        return self._client.post(
            '/auth/login',
            data={'username': username, 'password': password}
        )

    def logout(self):
        return self._client.get('/auth/logout')


@pytest.fixture
def auth(client):
    return AuthActions(client)
