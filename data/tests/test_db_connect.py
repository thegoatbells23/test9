import importlib
import os
from unittest.mock import MagicMock, patch

import pytest

import data.db_connect as dbc


def test_drop():
    client = MagicMock()
    with patch.object(dbc, 'client', client):
        dbc.drop('some_collection', db='some_db')
    client['some_db']['some_collection'].drop.assert_called_once_with()


def test_delete_many():
    client = MagicMock()
    coll = client['some_db']['some_collection']
    coll.delete_many.return_value.deleted_count = 3
    with patch.object(dbc, 'client', client):
        assert dbc.delete_many('some_collection', {'a': 1}, db='some_db') == 3
    coll.delete_many.assert_called_once_with({'a': 1})


def test_needs_connection_connects_first():
    @dbc.needs_connection
    def fn(x, y=0):
        return x + y
    with patch.object(dbc, 'connect_db') as mock_connect:
        assert fn(1, y=2) == 3
    mock_connect.assert_called_once_with()


def test_needs_connection_keeps_name():
    assert dbc.create.__name__ == 'create'
    assert 'Insert a single doc' in dbc.create.__doc__


def test_db_call_connects_when_not_connected():
    with patch.object(dbc, 'client', None), \
            patch.object(dbc, 'connect_db') as mock_connect:
        mock_connect.side_effect = lambda: setattr(dbc, 'client',
                                                   MagicMock())
        dbc.drop('some_collection', db='some_db')
    mock_connect.assert_called_once_with()


def mock_client_with_docs(docs):
    """
    A fake client whose find() on some_db.some_collection returns docs.
    """
    client = MagicMock()
    client['some_db']['some_collection'].find.return_value = docs
    return client


def test_read_one_converts_mongo_id():
    client = mock_client_with_docs([{dbc.MONGO_ID: 123, 'a': 1}])
    with patch.object(dbc, 'client', client):
        doc = dbc.read_one('some_collection', {'a': 1}, db='some_db')
    assert doc == {dbc.MONGO_ID: '123', 'a': 1}
    client['some_db']['some_collection'].find.assert_called_once_with(
        {'a': 1})


def test_read_one_not_found():
    client = mock_client_with_docs([])
    with patch.object(dbc, 'client', client):
        assert dbc.read_one('some_collection', {'a': 1},
                            db='some_db') is None


def test_read_drops_mongo_id():
    client = mock_client_with_docs([{dbc.MONGO_ID: 1, 'a': 1},
                                    {dbc.MONGO_ID: 2, 'a': 2}])
    with patch.object(dbc, 'client', client):
        assert dbc.read('some_collection', db='some_db') == [{'a': 1},
                                                             {'a': 2}]


def test_read_keeps_mongo_id_as_str():
    client = mock_client_with_docs([{dbc.MONGO_ID: 1, 'a': 1}])
    with patch.object(dbc, 'client', client):
        docs = dbc.read('some_collection', db='some_db', no_id=False)
    assert docs == [{dbc.MONGO_ID: '1', 'a': 1}]


def test_read_no_filter_finds_all():
    client = mock_client_with_docs([])
    with patch.object(dbc, 'client', client):
        dbc.read('some_collection', db='some_db')
    client['some_db']['some_collection'].find.assert_called_once_with({})


def test_read_with_filter():
    client = mock_client_with_docs([{dbc.MONGO_ID: 1, 'code': 'AL'}])
    with patch.object(dbc, 'client', client):
        docs = dbc.read('some_collection', db='some_db',
                        filt={'code': 'AL'})
    assert docs == [{'code': 'AL'}]
    client['some_db']['some_collection'].find.assert_called_once_with(
        {'code': 'AL'})


def test_read_dict_keys_by_field():
    client = mock_client_with_docs([{dbc.MONGO_ID: 1, 'code': 'AL'},
                                    {dbc.MONGO_ID: 2, 'code': 'AK'}])
    with patch.object(dbc, 'client', client):
        recs = dbc.read_dict('some_collection', 'code', db='some_db')
    assert recs == {'AL': {'code': 'AL'}, 'AK': {'code': 'AK'}}


def reload_with_env(monkeypatch, value):
    if value is None:
        monkeypatch.delenv(dbc.DB_ENV, raising=False)
    else:
        monkeypatch.setenv(dbc.DB_ENV, value)
    importlib.reload(dbc)
    return dbc.SE_DB


def test_db_name_from_env(monkeypatch):
    orig = os.environ.get(dbc.DB_ENV)
    try:
        assert reload_with_env(monkeypatch, 'test_other') == 'test_other'
        assert dbc.create.__wrapped__.__defaults__ == ('test_other',)
    finally:
        reload_with_env(monkeypatch, orig)


def test_db_name_default(monkeypatch):
    orig = os.environ.get(dbc.DB_ENV)
    try:
        assert reload_with_env(monkeypatch, None) == dbc.DEFAULT_DB
    finally:
        reload_with_env(monkeypatch, orig)


def test_is_db_up_when_ping_succeeds():
    client = MagicMock()
    with patch.object(dbc, 'client', client):
        assert dbc.is_db_up() is True
    client.admin.command.assert_called_once_with('ping')


def test_is_db_up_when_ping_fails():
    client = MagicMock()
    timeout_err = dbc.pm.errors.ServerSelectionTimeoutError('no server')
    client.admin.command.side_effect = timeout_err
    with patch.object(dbc, 'client', client):
        assert dbc.is_db_up() is False


def test_connect_db_local_default_uri(monkeypatch):
    monkeypatch.delenv('CLOUD_MONGO', raising=False)
    monkeypatch.delenv(dbc.MONGO_URI_ENV, raising=False)
    with patch.object(dbc, 'client', None), \
            patch.object(dbc.pm, 'MongoClient') as mock_client:
        dbc.connect_db()
    mock_client.assert_called_once_with(
        dbc.DEFAULT_LOCAL_URI, serverSelectionTimeoutMS=dbc.DB_TIMEOUT_MS)


def test_connect_db_local_uri_from_env(monkeypatch):
    monkeypatch.delenv('CLOUD_MONGO', raising=False)
    monkeypatch.setenv(dbc.MONGO_URI_ENV, 'mongodb://mongo:27017')
    with patch.object(dbc, 'client', None), \
            patch.object(dbc.pm, 'MongoClient') as mock_client:
        dbc.connect_db()
    mock_client.assert_called_once_with(
        'mongodb://mongo:27017', serverSelectionTimeoutMS=dbc.DB_TIMEOUT_MS)


def test_connect_db_reuses_client():
    client = MagicMock()
    with patch.object(dbc, 'client', client), \
            patch.object(dbc.pm, 'MongoClient') as mock_client:
        assert dbc.connect_db() is client
    mock_client.assert_not_called()


def test_count_all():
    client = MagicMock()
    coll = client['some_db']['some_collection']
    coll.count_documents.return_value = 52
    with patch.object(dbc, 'client', client):
        assert dbc.count('some_collection', db='some_db') == 52
    coll.count_documents.assert_called_once_with({})


def test_count_with_filter():
    client = MagicMock()
    coll = client['some_db']['some_collection']
    coll.count_documents.return_value = 1
    with patch.object(dbc, 'client', client):
        assert dbc.count('some_collection', {'code': 'NY'},
                         db='some_db') == 1
    coll.count_documents.assert_called_once_with({'code': 'NY'})


def test_db_info_local(monkeypatch):
    monkeypatch.delenv('CLOUD_MONGO', raising=False)
    monkeypatch.delenv(dbc.MONGO_URI_ENV, raising=False)
    with patch.object(dbc, 'is_db_up', return_value=True):
        info = dbc.db_info()
    assert info == {'location': 'local', 'uri': dbc.DEFAULT_LOCAL_URI,
                    'db': dbc.SE_DB, 'up': True}


def test_db_info_reports_down(monkeypatch):
    monkeypatch.delenv('CLOUD_MONGO', raising=False)
    with patch.object(dbc, 'is_db_up', return_value=False):
        assert dbc.db_info()['up'] is False


def test_db_info_cloud_hides_uri(monkeypatch):
    monkeypatch.setenv('CLOUD_MONGO', dbc.CLOUD)
    monkeypatch.setenv('MONGO_PASSWD', 'secret')
    monkeypatch.delenv('MONGO_HOST', raising=False)
    with patch.object(dbc, 'is_db_up', return_value=True):
        info = dbc.db_info()
    assert info['location'] == 'cloud'
    assert info['uri'] is None
    assert 'secret' not in str(info)


def set_cloud_env(monkeypatch, user='me', password='secret',
                  host='cluster0.abcde.mongodb.net'):
    monkeypatch.setenv('CLOUD_MONGO', dbc.CLOUD)
    for name, value in ((dbc.MONGO_USER_ENV, user),
                        (dbc.MONGO_PASSWD_ENV, password),
                        (dbc.MONGO_HOST_ENV, host)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def test_cloud_uri():
    assert dbc.cloud_uri('me', 'secret', 'cluster0.abcde.mongodb.net',
                         db='some_db') == (
        'mongodb+srv://me:secret@cluster0.abcde.mongodb.net/some_db'
        + '?retryWrites=true&w=majority')


def test_cloud_settings(monkeypatch):
    set_cloud_env(monkeypatch)
    assert dbc.cloud_settings() == ('me', 'secret',
                                    'cluster0.abcde.mongodb.net')


@pytest.mark.parametrize('missing', ['user', 'password', 'host'])
def test_cloud_settings_missing(monkeypatch, missing):
    set_cloud_env(monkeypatch, **{missing: None})
    with pytest.raises(ValueError) as err:
        dbc.cloud_settings()
    assert 'secret' not in str(err.value)


def test_connect_db_cloud(monkeypatch):
    set_cloud_env(monkeypatch)
    with patch.object(dbc, 'client', None), \
            patch.object(dbc.pm, 'MongoClient') as mock_client:
        dbc.connect_db()
    mock_client.assert_called_once_with(
        dbc.cloud_uri('me', 'secret', 'cluster0.abcde.mongodb.net'),
        **dbc.cloud_client_options())


def test_connect_db_cloud_needs_settings(monkeypatch):
    set_cloud_env(monkeypatch, password=None)
    with patch.object(dbc, 'client', None), \
            patch.object(dbc.pm, 'MongoClient') as mock_client:
        with pytest.raises(ValueError):
            dbc.connect_db()
    mock_client.assert_not_called()


def test_cloud_uri_encodes_user_and_password():
    uri = dbc.cloud_uri('me@nyu', 'p@ss:w/rd', 'cluster0.abcde.mongodb.net',
                        db='some_db')
    assert uri.startswith('mongodb+srv://me%40nyu:p%40ss%3Aw%2Frd@'
                          + 'cluster0.abcde.mongodb.net/some_db?')


def test_cloud_settings_strips_spaces(monkeypatch):
    set_cloud_env(monkeypatch, user=' me ', password='secret\n',
                  host=' cluster0.abcde.mongodb.net')
    assert dbc.cloud_settings() == ('me', 'secret',
                                    'cluster0.abcde.mongodb.net')


def test_cloud_settings_only_spaces_is_missing(monkeypatch):
    set_cloud_env(monkeypatch, host='   ')
    with pytest.raises(ValueError, match=dbc.MONGO_HOST_ENV):
        dbc.cloud_settings()


def test_db_info_cloud_shows_host_only(monkeypatch):
    set_cloud_env(monkeypatch)
    with patch.object(dbc, 'is_db_up', return_value=True):
        info = dbc.db_info()
    assert info['uri'] == 'mongodb+srv://cluster0.abcde.mongodb.net'
    assert '@' not in info['uri']
    assert 'secret' not in str(info)


def test_convert_mongo_id():
    doc = {dbc.MONGO_ID: 123, 'a': 1}
    dbc.convert_mongo_id(doc)
    assert doc == {dbc.MONGO_ID: '123', 'a': 1}


def test_convert_mongo_id_no_id():
    doc = {'a': 1}
    dbc.convert_mongo_id(doc)
    assert doc == {'a': 1}


def test_cloud_client_options():
    opts = dbc.cloud_client_options()
    assert opts['tlsCAFile'] == dbc.certifi.where()
    assert opts['serverSelectionTimeoutMS'] == dbc.CLOUD_TIMEOUT_MS
    # PythonAnywhere's recommended settings:
    assert opts['connectTimeoutMS'] == 30000
    assert opts['socketTimeoutMS'] is None
    assert opts['connect'] is False
    assert opts['maxPoolSize'] == 1


def test_check_cloud_host_ok():
    host = 'cluster0.abcde.mongodb.net'
    assert dbc.check_cloud_host(host) == host


@pytest.mark.parametrize('host', [
    'mongodb+srv://me:pw@cluster0.abcde.mongodb.net/',
    'me:pw@cluster0.abcde.mongodb.net',
    'cluster0.abcde.mongodb.net/',
    'cluster0',
])
def test_check_cloud_host_bad(host):
    with pytest.raises(ValueError) as err:
        dbc.check_cloud_host(host)
    assert 'pw' not in str(err.value)


def test_cloud_settings_rejects_connection_string(monkeypatch):
    set_cloud_env(monkeypatch,
                  host='mongodb+srv://me:pw@cluster0.abcde.mongodb.net/')
    with pytest.raises(ValueError, match=dbc.MONGO_HOST_ENV):
        dbc.cloud_settings()
