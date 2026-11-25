"""
Checks on pythonanywhere_wsgi.py, the template for our WSGI file on
PythonAnywhere. It is read as text, not run: running it would point the
tests at the cloud database.
"""
import ast
from pathlib import Path

import pytest

import data.db_connect as dbc

WSGI_FILE = Path(__file__).resolve().parents[2] / 'pythonanywhere_wsgi.py'

CLOUD_FLAG = 'CLOUD_MONGO'
SECRET_ENVS = (dbc.MONGO_USER_ENV, dbc.MONGO_HOST_ENV, dbc.MONGO_PASSWD_ENV)


def env_settings() -> dict:
    """
    Return {name: value} for each os.environ['NAME'] = 'value' line.
    """
    settings = {}
    for node in ast.walk(ast.parse(WSGI_FILE.read_text())):
        if (isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Subscript)
                and ast.unparse(node.targets[0].value) == 'os.environ'):
            settings[node.targets[0].slice.value] = node.value.value
    return settings


def test_sets_exactly_the_cloud_settings():
    """
    The template sets the names db_connect reads, so renaming one in
    db_connect without updating the template fails here.
    """
    assert set(env_settings()) == {CLOUD_FLAG, *SECRET_ENVS}


def test_uses_cloud_mongo():
    assert env_settings()[CLOUD_FLAG] == dbc.CLOUD


@pytest.mark.parametrize('name', SECRET_ENVS)
def test_secrets_are_placeholders(name):
    """
    Real user names, hosts and passwords must never be committed.
    """
    value = env_settings()[name]
    assert value.startswith('<') and value.endswith('>')


def test_exports_app_as_application():
    """
    PythonAnywhere serves the object named `application`.
    """
    imports = [node for node in ast.walk(ast.parse(WSGI_FILE.read_text()))
               if isinstance(node, ast.ImportFrom)
               and node.module == 'server.endpoints']
    assert [(alias.name, alias.asname) for alias in imports[0].names] == \
        [('app', 'application')]
