"""
All interaction with MongoDB should be through this file!
We may be required to use a new database at any point.
"""
import os
from functools import wraps
from urllib.parse import quote_plus

import certifi

import pymongo as pm

LOCAL = "0"
CLOUD = "1"

# Tests set GEODATA_DB to a test database (see common.mk):
DB_ENV = 'GEODATA_DB'
DEFAULT_DB = 'geodata2026'
SE_DB = os.environ.get(DB_ENV, DEFAULT_DB)

# Local MongoDB (e.g. the Docker container started with
# `docker run -d --name mongodb -p 27017:27017 mongo`).
# Set MONGO_URI to point somewhere else, e.g. mongodb://mongo:27017
# when the server itself runs in Docker Compose.
MONGO_URI_ENV = 'MONGO_URI'
DEFAULT_LOCAL_URI = 'mongodb://localhost:27017'

# Give up quickly if MongoDB is not running, instead of pymongo's
# default 30 seconds:
DB_TIMEOUT_MS = 2000

# MongoDB in the cloud (Atlas). Each developer sets these in their own
# environment; they must never be committed:
MONGO_USER_ENV = 'MONGO_USER_NM'    # Atlas database user name
MONGO_HOST_ENV = 'MONGO_HOST'       # e.g. cluster0.abcde.mongodb.net
MONGO_PASSWD_ENV = 'MONGO_PASSWD'   # that user's password
CLOUD_MDB = 'mongodb+srv'
CLOUD_PARAMS = 'retryWrites=true&w=majority'
# Cloud connections can be slower than local ones:
CLOUD_TIMEOUT_MS = 10000
# PythonAnywhere's recommended settings for MongoDB Atlas (pymongo 4),
# see https://help.pythonanywhere.com/pages/MongoDB
CLOUD_CONN_TIMEOUT_MS = 30000

client = None

MONGO_ID = '_id'


def check_cloud_host(host: str) -> str:
    """
    Make sure host is just an Atlas host name, like
    cluster0.abcde.mongodb.net, and not a whole connection string.
    Returns host; raises ValueError (without repeating the value, which
    might contain a password) if it is not.
    """
    bad_parts = ('://', '@', '/', ' ')
    if '.' not in host or any(part in host for part in bad_parts):
        raise ValueError(f'{MONGO_HOST_ENV} should be just the host, '
                         + 'like cluster0.abcde.mongodb.net.')
    return host


def cloud_settings() -> tuple:
    """
    Return (user, password, host) for MongoDB in the cloud, read from
    the environment. Raises ValueError naming any that are missing
    (never their values). Spaces copied in by accident are removed.
    """
    names = (MONGO_USER_ENV, MONGO_PASSWD_ENV, MONGO_HOST_ENV)
    values = tuple(os.environ.get(name, '').strip() for name in names)
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise ValueError('To use Mongo in the cloud, set '
                         + ', '.join(missing) + ' in your environment.')
    check_cloud_host(values[2])
    return values


def cloud_uri(user: str, password: str, host: str, db=SE_DB) -> str:
    """
    Build the connection string for a MongoDB Atlas cluster.
    The user name and password are URL-encoded, so characters such as
    @ : / in a password cannot break the connection string.
    """
    return (f'{CLOUD_MDB}://{quote_plus(user)}:{quote_plus(password)}'
            + f'@{host}/{db}?{CLOUD_PARAMS}')


def cloud_client_options() -> dict:
    """
    Extra MongoClient settings for the cloud: a trusted certificate list,
    plus the settings PythonAnywhere recommends for MongoDB Atlas.
    """
    return {
        'tlsCAFile': certifi.where(),
        'serverSelectionTimeoutMS': CLOUD_TIMEOUT_MS,
        'connectTimeoutMS': CLOUD_CONN_TIMEOUT_MS,
        'socketTimeoutMS': None,
        'connect': False,
        'maxPoolSize': 1,
    }


def connect_db():
    """
    This provides a uniform way to connect to the DB across all uses.
    Returns a mongo client object... maybe we shouldn't?
    Also set global client variable.
    We should probably either return a client OR set a
    client global.
    """
    global client
    if client is None:  # not connected yet!
        print('Setting client because it is None.')
        if os.environ.get('CLOUD_MONGO', LOCAL) == CLOUD:
            user, password, host = cloud_settings()
            print(f'Connecting to Mongo in the cloud at {host}.')
            client = pm.MongoClient(cloud_uri(user, password, host),
                                    **cloud_client_options())
        else:
            uri = os.environ.get(MONGO_URI_ENV, DEFAULT_LOCAL_URI)
            print(f"Connecting to Mongo locally at {uri}.")
            client = pm.MongoClient(uri,
                                    serverSelectionTimeoutMS=DB_TIMEOUT_MS)
    return client


def needs_connection(fn):
    """
    Decorate every function that uses the client: make sure we are
    connected to the DB first, then call the function.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        connect_db()
        return fn(*args, **kwargs)
    return wrapper


def is_db_up():
    """
    Returns True if the DB is up and running: we can connect and it
    answers a ping. Returns False (instead of raising) if it does not.
    """
    try:
        connect_db()
        client.admin.command('ping')
        return True
    except pm.errors.PyMongoError as err:
        print(f'Error connecting to MongoDB: {err}')
        return False


@needs_connection
def count(collection, filt=None, db=SE_DB) -> int:
    """
    Return how many docs in collection match the filter (all docs if
    no filter), without reading the docs themselves.
    """
    return client[db][collection].count_documents(filt or {})


def db_info() -> dict:
    """
    Describe which MongoDB we are set up to use and whether it is up.
    Never include the cloud user name or password: for the cloud, only
    the host is shown.
    """
    cloud = os.environ.get('CLOUD_MONGO', LOCAL) == CLOUD
    if cloud:
        host = os.environ.get(MONGO_HOST_ENV, '').strip()
        uri = f'{CLOUD_MDB}://{host}' if host else None
    else:
        uri = os.environ.get(MONGO_URI_ENV, DEFAULT_LOCAL_URI)
    return {
        'location': 'cloud' if cloud else 'local',
        'uri': uri,
        'db': SE_DB,
        'up': is_db_up(),
    }


def convert_mongo_id(doc: dict):
    if MONGO_ID in doc:
        # Convert mongo ID to a string so it works as JSON
        doc[MONGO_ID] = str(doc[MONGO_ID])


@needs_connection
def create(collection, doc, db=SE_DB):
    """
    Insert a single doc into collection.
    """
    print(f'{db=}')
    return client[db][collection].insert_one(doc)


@needs_connection
def drop(collection, db=SE_DB):
    """
    Drop the whole collection, if it exists.
    """
    client[db][collection].drop()


@needs_connection
def read_one(collection, filt, db=SE_DB):
    """
    Find with a filter and return on the first doc found.
    Return None if not found.
    """
    for doc in client[db][collection].find(filt):
        convert_mongo_id(doc)
        return doc


@needs_connection
def delete(collection: str, filt: dict, db=SE_DB):
    """
    Find with a filter and return on the first doc found.
    """
    print(f'{filt=}')
    del_result = client[db][collection].delete_one(filt)
    return del_result.deleted_count


@needs_connection
def delete_many(collection: str, filt: dict, db=SE_DB):
    """
    Delete every doc matching the filter; return how many were deleted.
    """
    return client[db][collection].delete_many(filt).deleted_count


@needs_connection
def update(collection, filters, update_dict, db=SE_DB):
    return client[db][collection].update_one(filters, {'$set': update_dict})


@needs_connection
def read(collection, db=SE_DB, no_id=True, filt=None) -> list:
    """
    Returns a list from the db: every doc in the collection, or only
    those matching the filter if one is given.
    """
    ret = []
    for doc in client[db][collection].find(filt or {}):
        if no_id:
            del doc[MONGO_ID]
        else:
            convert_mongo_id(doc)
        ret.append(doc)
    return ret


def read_dict(collection, key, db=SE_DB, no_id=True) -> dict:
    recs = read(collection, db=db, no_id=no_id)
    recs_as_dict = {}
    for rec in recs:
        recs_as_dict[rec[key]] = rec
    return recs_as_dict


@needs_connection
def fetch_all_as_dict(key, collection, db=SE_DB):
    ret = {}
    for doc in client[db][collection].find():
        del doc[MONGO_ID]
        ret[doc[key]] = doc
    return ret
