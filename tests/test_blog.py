import pytest
from flaskr.db import get_db


def test_index(client, auth):
    # Test GET for index page (no login).
    response = client.get('/')
    assert response.status_code == 200
    assert b'Log In' in response.data
    assert b'Register' in response.data

    # Login in to test user.
    auth.login()

    # Test GET for index page (with login).
    response = client.get('/')
    assert response.status_code == 200
    assert b'Log Out' in response.data
    assert b'test title' in response.data  # the name of the sample post.
    assert b'by test on 2018-01-01' in response.data  # date of sample post.
    assert b'test\nbody' in response.data  # username and body.
    assert b'href="/1/update"' in response.data  # link to edit post.


def test_noconnect_index(badclient):
    # Test GET for index page.
    response = badclient.get('/')
    assert response.status_code == 200
    assert b'Log In' in response.data
    assert b'Register' in response.data

    # Error message should be present.
    assert b'Failed to load posts' in response.data


@pytest.mark.parametrize('path', (
    '/create',
    '/1/update',
    '/1/delete',
))
def test_login_required(client, path):
    # All above paths require log in, so this should redirect to login page.
    response = client.post(path)
    assert response.headers["Location"] == "/auth/login"


def test_author_required(app, client, auth):
    # Change the post author to another user.
    with app.app_context():
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE posts SET author_id = 2 WHERE id = 1"
            )
            db.commit()

    # Login to test user.
    auth.login()

    # Current user can't modify other's posts.
    assert client.post('/1/update').status_code == 403
    assert client.post('/1/delete').status_code == 403

    # Current user shouldn't see edit link.
    assert b'href="/1/update"' not in client.get('/').data


@pytest.mark.parametrize('path', (
    '/2/update',
    '/2/delete',
))
def test_exists_required(client, auth, path):
    # Login to existing user.
    auth.login()

    # Try to POST an update or delete to an id that does not exist.
    assert client.post(path).status_code == 404


def test_create(client, auth, app):
    # Login to test user.
    auth.login()

    # User should be able to GET the create page.
    assert client.get('/create').status_code == 200

    # Create a blog post.
    client.post('/create', data={'title': 'created', 'body': ''})

    # Check that the blog post was added to the db.
    with app.app_context():
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(id) FROM posts"
            )
            count = cursor.fetchone()[0]

        # There should be 2 posts now.
        assert count == 2


def test_update(client, auth, app):
    # Login to test user.
    auth.login()

    # User should be able to GET the update page for first post.
    assert client.get('/1/update').status_code == 200

    # Post an update.
    client.post('/1/update', data={'title': 'updated', 'body': ''})

    # Check the db for update.
    with app.app_context():
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id = 1")
            post = cursor.fetchone()
        assert post['title'] == 'updated'


@pytest.mark.parametrize('path', (
    '/create',
    '/1/update',
))
def test_create_update_validate(client, auth, path):
    # Login to test user.
    auth.login()

    # Attempt to modify a post with an empty title.
    response = client.post(path, data={'title': '', 'body': ''})
    assert b'Title is required.' in response.data


def test_delete(client, auth, app):
    # Login to test user.
    auth.login()

    # Delete the test post, which should redirect to index page.
    response = client.post('/1/delete')
    assert response.headers["Location"] == '/'

    # Ensure post was deleted from db.
    with app.app_context():
        db = get_db()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM posts WHERE id = 1")
            post = cursor.fetchone()
        assert post is None
