# 1-data-tier

## Goal

The goal of this branch is to separate the data operations of the application into its own layer.

Currently, all the application uses a local sqlite instance for data operations.

## Solution

I want to incorporate a remote postgres server instead of the local sqlite instance. In this way, the web tier and data tier can be monitored and scaled independetly:

| ![Data Tier Design](./imgs/data-tier-design.png) |
| :--: |
| _Separating the Data Tier_ |

## The Postgres Server

There are many solutions to standing up a postgres server.

Ultimately, I decided to host my own in a separate Docker container connected by a bridge network.

The command to set this up is:

```
docker run -d \
  --name postgres_container \
  --network mynetwork \
  -e POSTGRES_USER=myuser \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=mydatabase \
  -p 5432:5432 \
  postgres:latest
```

We then have two containers, one running the application (which I'm also doing my development on), and the postgres server:

| ![Containers](./imgs/containers.png) |
| :--: |
| _A separate container for postgres_ |

## The DB Schema

Making the switch from sqlite to postgres requires switching a bit of syntactic sugar in the schema:

`flaskr/schema.sql`:

```postgres
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS posts;

CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE posts (
  id SERIAL PRIMARY KEY,
  author_id INTEGER NOT NULL,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  FOREIGN KEY (author_id) REFERENCES users (id)
);
```

## Switching from sqlite to psycopg2

To interact with our new postgres server, we'll use the `psycopg2` python module instead of the `sqlite` one that we were using before.

This requires changing a few files.

Firstly, `flaskr/db.py`, which is responsible for initializing the database, among other things:

```python
import os
import psycopg2
import click

from flask import current_app, g, Flask
from psycopg2.extras import DictCursor


def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            current_app.config['DATABASE'],
            cursor_factory=DictCursor
        )

    return g.db

# Unchanged functions omitted.
# ...

def init_db():
    db = get_db()
    cursor = db.cursor()

    with current_app.open_resource('schema.sql') as f:
        cursor.execute(f.read().decode('utf-8'))
        db.commit()

    cursor.close()
```

We use the `psychopg2.connect` function instead of the `sqlite.connect` function from before, and set up a `cursor_factory` to interact with the db later.

We also need to change the `flaskr/__init__.py`'s `create_app` function to get the connection info for the database.

Before, it needed to locate the local instance of the `sqlite` database file, but now it needs the address of the remote postgres server.

This can be stored in environment variables for secret keeping:

```
# export DATABASE_URL=postgresql://flaskadmin:flaskpassword@postgres-container:5432/flaskdb
```

These are the parameters we set when running the docker container for the postgres server.

We can then make this change in the app config:

```python
def create_app(test_config=None):
    # Create and configure the app.
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        DATABASE=os.getenv('DATABASE_URL')
    )

    # Unchanged code omitted.
    # ...
```

Now we should be able to initialize the database with the `click` command we registered in the base app:

```
# python3 -m flask --app flaskr init-db
Initialized the database.
```

## Auth Changes

We'll have to switch some of the syntax we use over to the postgres syntax:

`flaskr/auth.py`:
```python
try:
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, generate_password_hash(password)),
        )
        db.commit()
except psycopg2.IntegrityError:
    db.rollback()
    error = f"User '{username}' is already registered"
```

We now use the `db.cursor()` object to interact with the DB, instead of calling `db.execute()` directly when using the `sqlite` library.

We need to do the same type of updating when using for the blog backend as well.

## Updating the Testing Framework

We have to update how we test the application now that it interacts with a remote postgres server.

The first step in this is to update the GH Actions workflow to stand up a local postgres server:

```yml
jobs:
  build:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:latest
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: username
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    env:
      DATABASE_URL: postgresql://username:password@localhost/test_db

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.10
    # Same code omitted.
    # ...
```

Since the database connection URL is kept in environment variables for security reasons, we can set the environment variable for the local test server within the workflow manifest.

Then, we can change the test programs in the `./tests` directory to reflect the new `psycopg2` syntax instead of the `sqlite3` syntax from before.

Now we can test it locally against our remote server, and via GH actions:

```
# pytest
=============================== test session starts ===============================
platform linux -- Python 3.12.3, pytest-8.3.1, pluggy-1.5.0
rootdir: /code/pyflask-tutorial
configfile: pyproject.toml
testpaths: tests
collected 23 items                                                                                                                                                                                                                                           

tests/test_auth.py ........                [ 34%]
tests/test_blog.py ............            [ 86%]
tests/test_db.py ..                        [ 95%]
tests/test_factory.py .                    [100%]

=============================== 23 passed in 5.04s ===============================
```

## Dealing with Database Connection Issues

Since the DB is remote now, it's more likely that we can encounter an issue with connecting to the database than when we were using a local sqlite instance.

We need to add some kind of graceful error handling if we are unable to reach our database, so that the app doesn't crash.

For example, if we stop the postgres container and run the app, we are treated to this screen when trying to log in:

![DB Connection Failure](./imgs/db-connect-fail.png)

The desired behavior is that the webpage should render as much as it can, and report the user that the connection failed, rather than bringing down the web application.

`./flaskr/db.py`:
```python
def get_db():
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(
                current_app.config['DATABASE'],
                cursor_factory=DictCursor
            )
        except OperationalError as e:
            current_app.logger.error(f"Failed to connect to the database: {e}")
            return None

    return g.db
```

We add some error handling when connecting to the database. We log the error, then return `None` if the connection failed.

In this way, when an operation tries to retrieve the DB, we can check if that retrieve failed, and handle accordingly:

`./flaskr/blog.py`:
```python
@bp.route('/')
def index():
    db = get_db()
    if db is None:
        return render_template('blog/index.html', posts='error')
    
    with db.cursor() as cursor:
        cursor.execute(
            'SELECT p.id, title, body, created, author_id, username'
            ' FROM posts p JOIN users u ON p.author_id = u.id'
            ' ORDER BY created DESC'
        )
    
        posts = cursor.fetchall()
    return render_template('blog/index.html', posts=posts)
```

Now when we render the `index.html` page, we can check if `posts` is `None`, indicating the error:

```html
{% block content %}
  {% if posts == 'error' %}
    <p>🚨Failed to load posts🚨</p>
  {% else %}
    <!-- Render as normal -->
  {% endif %}
{% endblock %}
```

Now we gracefully handle the bad connection, instead of the server crashing:

| ![Error Page](./imgs/db-connect-fail-page.png) |
| :--: |
| _Graceful Error Handling_ |

We employ the same strategy with the `auth` module, opting to flash the error message when the user tries to login or register:

| ![Error Login](./imgs/db-connect-fail-login.png) |
| :--: |
| _Graceful Error Handling for Login_ |

## Testing with Connection Issues

Now we need to add tests to account for handling database outages.