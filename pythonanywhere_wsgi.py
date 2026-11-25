"""
WSGI file for running our API server on PythonAnywhere.

Copy this into the WSGI configuration file on PythonAnywhere's Web tab
(the one named like /var/www/<account>_pythonanywhere_com_wsgi.py),
then replace every <...> placeholder with the real value there.
Never commit the real values to this file.
"""
import os
import sys

# MongoDB in the cloud (Atlas); data/db_connect.py reads these:
os.environ['CLOUD_MONGO'] = '1'
os.environ['MONGO_USER_NM'] = '<Atlas database user name>'
os.environ['MONGO_HOST'] = '<Atlas host only, like cluster0.abcde.mongodb.net>'
os.environ['MONGO_PASSWD'] = '<that user\'s password>'

# Where the repo is cloned on PythonAnywhere:
path = '/home/<PythonAnywhere account name>/HKH'
if path not in sys.path:
    sys.path.append(path)

from server.endpoints import app as application  # noqa: E402, F401
