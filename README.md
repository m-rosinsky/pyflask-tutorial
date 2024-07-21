# 1-data-tier

## Goal

The goal of this branch is to separate the data operations of the application into its own layer.

Currently, all the application uses a local sqlite instance for data operations.

## Solution

I want to incorporate a remote postgres server instead of the local sqlite instance.

### The Postgres Server

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

### The DB Schema

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

### Switching from sqlite to psycopg2

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
# export DATABASE_URL=postgresql://flaskadmin:flaskpassword@postgres-container:32/flaskdb
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

### Auth Changes

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

### Blog Changes

We need to do the same type of updating when using for the blog backend as well:

`flaskr/blog.py`:
```python

```