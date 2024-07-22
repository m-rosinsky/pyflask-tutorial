import os
import psycopg2
import click

from flask import current_app, g, Flask
from psycopg2.extras import DictCursor
from psycopg2 import OperationalError


def get_db():
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(
                current_app.config['DATABASE'],
                cursor_factory=DictCursor
            )
        except OperationalError as e:
            current_app.logger.error(f"Failed to connect to the database: {e}")
            raise RuntimeError("Failed to connect to the database. Please check the database connection settings.")

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    try:
        db = get_db()
        cursor = db.cursor()

        with current_app.open_resource('schema.sql') as f:
            cursor.execute(f.read().decode('utf-8'))
            db.commit()

        cursor.close()
    except Exception as e:
        current_app.logger.error(f"Failed to initialize the database: {e}")
        raise RuntimeError("Failed to initialize the database. Please check the schema and the database connection.")


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    try:
        init_db()
        click.echo('Initialized the database.')
    except RuntimeError as e:
        click.echo(f"Error: {e}")


def init_app(app: Flask):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
