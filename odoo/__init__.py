# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core library."""

#----------------------------------------------------------
# Running mode flags (gevent, prefork)
#----------------------------------------------------------
# Is the server running with gevent.
import sys
evented = False
if len(sys.argv) > 1 and sys.argv[1] == 'gevent':
    sys.argv.remove('gevent')
    import gevent.monkey
    gevent.monkey.patch_all()
    import psycogreen.gevent
    psycogreen.gevent.patch_psycopg()
    evented = True

# Is the server running in prefork mode (e.g. behind Gunicorn).
# If this is True, the processes have to communicate some events,
# e.g. database update or cache invalidation. Each process has also
# its own copy of the data structure and we don't need to care about
# locks between threads.
multi_process = False

#----------------------------------------------------------
# libc UTC hack
#----------------------------------------------------------
# Make sure the OpenERP server runs in UTC.
import os
os.environ['TZ'] = 'UTC' # Set the timezone
import time
if hasattr(time, 'tzset'):
    time.tzset()

#----------------------------------------------------------
# Shortcuts
#----------------------------------------------------------
# The hard-coded super-user id (a.k.a. administrator, or root user).
SUPERUSER_ID = 1

def registry(database_name=None):
    """
    Return the model registry for the given database, or the database mentioned
    on the current thread. If the registry does not exist yet, it is created on
    the fly.
    """
    if database_name is None:
        import threading
        database_name = threading.currentThread().dbname
    return modules.registry.Registry(database_name)

#----------------------------------------------------------
# Imports
#----------------------------------------------------------
from . import addons
from . import conf
from . import loglevels
from . import modules
from . import netsvc
from . import osv
from . import release
from . import report
from . import service
from . import sql_db
from . import tools

#----------------------------------------------------------
# Model classes, fields, api decorators, and translations
#----------------------------------------------------------
from . import models
from . import fields
from . import api
from odoo.tools.translate import _

#----------------------------------------------------------
# Other imports, which may require stuff from above
#----------------------------------------------------------
from . import cli
from . import http
