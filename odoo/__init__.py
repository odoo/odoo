# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core library."""


#----------------------------------------------------------
# odoo must be a namespace package for odoo.addons to become one too
# https://packaging.python.org/guides/packaging-namespace-packages/
#----------------------------------------------------------
import pkgutil
import os.path
__path__ = [
    os.path.abspath(path)
    for path in pkgutil.extend_path(__path__, __name__)
]

import sys
assert sys.version_info > (3, 7), "Outdated python version detected, Odoo requires Python >= 3.7 to run."

#----------------------------------------------------------
# Running mode flags (gevent, prefork)
#----------------------------------------------------------
# Is the server running with gevent.
evented = False
if len(sys.argv) > 1 and sys.argv[1] == 'gevent':
    sys.argv.remove('gevent')
    import gevent.monkey
    import psycopg2
    from gevent.socket import wait_read, wait_write
    gevent.monkey.patch_all()

    def gevent_wait_callback(conn, timeout=None):
        """A wait callback useful to allow gevent to work with Psycopg."""
        # Copyright (C) 2010-2012 Daniele Varrazzo <daniele.varrazzo@gmail.com>
        # This function is borrowed from psycogreen module which is licensed
        # under the BSD license (see in odoo/debian/copyright)
        while 1:
            state = conn.poll()
            if state == psycopg2.extensions.POLL_OK:
                break
            elif state == psycopg2.extensions.POLL_READ:
                wait_read(conn.fileno(), timeout=timeout)
            elif state == psycopg2.extensions.POLL_WRITE:
                wait_write(conn.fileno(), timeout=timeout)
            else:
                raise psycopg2.OperationalError(
                    "Bad result from poll: %r" % state)
    psycopg2.extensions.set_wait_callback(gevent_wait_callback)
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
# PyPDF2 hack
# ensure that zlib does not throw error -5 when decompressing
# because some pdf won't fit into allocated memory
# https://docs.python.org/3/library/zlib.html#zlib.decompressobj
# ----------------------------------------------------------
import PyPDF2

try:
    import zlib

    def _decompress(data):
        zobj = zlib.decompressobj()
        return zobj.decompress(data)

    import PyPDF2.filters  # needed after PyPDF2 2.0.0 and before 2.11.0
    PyPDF2.filters.decompress = _decompress
except ImportError:
    pass # no fix required

# ---------------------------------------------------------
# some charset are known by Python under a different name
# ---------------------------------------------------------
import encodings.aliases  # noqa: E402

encodings.aliases.aliases['874'] = 'cp874'
encodings.aliases.aliases['windows_874'] = 'cp874'

#----------------------------------------------------------
# alias hebrew iso-8859-8-i and iso-8859-8-e on iso-8859-8
# https://bugs.python.org/issue18624
#----------------------------------------------------------
import codecs
import re

iso8859_8 = codecs.lookup('iso8859_8')
iso8859_8ie_re = re.compile(r'iso[-_]?8859[-_]8[-_]?[ei]', re.IGNORECASE)
codecs.register(lambda charset: iso8859_8 if iso8859_8ie_re.match(charset) else None)

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
        database_name = threading.current_thread().dbname
    return modules.registry.Registry(database_name)

#----------------------------------------------------------
# Imports
#----------------------------------------------------------
from . import upgrade  # this namespace must be imported first
from . import addons
from . import conf
from . import loglevels
from . import modules
from . import netsvc
from . import osv
from . import release
from . import service
from . import sql_db
from . import tools

#----------------------------------------------------------
# Model classes, fields, api decorators, and translations
#----------------------------------------------------------
from . import models
from . import fields
from . import api
from odoo.tools.translate import _, _lt
from odoo.fields import Command

#----------------------------------------------------------
# Other imports, which may require stuff from above
#----------------------------------------------------------
from . import cli
from . import http
