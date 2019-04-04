# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" OpenERP core library."""


#----------------------------------------------------------
# odoo must be a namespace package for odoo.addons to become one too
# https://packaging.python.org/guides/packaging-namespace-packages/
#----------------------------------------------------------
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

# As of version 12.0, python 2 is no longer supported, ensure py version is >= 3.5
import sys
assert sys.version_info > (3, 5), "Python 2 detected, Odoo requires Python >= 3.5 to run."

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

# ----------------------------------------------------------
# module babel hack
# make sure unicode [world] territory is "001"
# whereas "unitag" notation is "AA"
# http://www.unicode.org/reports/tr35/#unicode_region_subtag
# http://www.unicode.org/reports/tr35/#unicode_region_subtag_validity
# BCP47: https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
# ----------------------------------------------------------
import babel
_babelCoreParseLocale = babel.core.parse_locale
def _babelCoreParseLocale_unitag(identifier, sep='_'):
    lang, territory, script, variant = _babelCoreParseLocale(identifier, sep)
    territory = '001' if territory == 'AA' else territory
    return lang, territory, script, variant

babel.core.parse_locale = _babelCoreParseLocale_unitag

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
