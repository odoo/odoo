# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" OpenERP core library."""

#----------------------------------------------------------
# Running mode flags (gevent, prefork)
#----------------------------------------------------------
# Is the server running with gevent.
import sys
evented = False
if sys.modules.get("gevent") is not None:
    evented = True

# Is the server running in pefork mode (e.g. behind Gunicorn).
# If this is True, the processes have to communicate some events,
# e.g. database update or cache invalidation. Each process has also
# its own copy of the data structure and we don't need to care about
# locks between threads.
multi_process = False

#----------------------------------------------------------
# libc UTC hack
#----------------------------------------------------------
# Make sure the OpenERP server runs in UTC. This is especially necessary
# under Windows as under Linux it seems the real import of time is
# sufficiently deferred so that setting the TZ environment variable
# in openerp.cli.server was working.
import os
os.environ['TZ'] = 'UTC' # Set the timezone...
import time              # ... *then* import time.
del os
del time

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
    return modules.registry.RegistryManager.get(database_name)

#----------------------------------------------------------
# Imports
#----------------------------------------------------------
import addons
import conf
import loglevels
import modules
import netsvc
import osv
import pooler
import release
import report
import service
import sql_db
import tools
import workflow

#----------------------------------------------------------
# Model classes, fields, api decorators, and translations
#----------------------------------------------------------
from . import models
from . import fields
from . import api
from openerp.tools.translate import _

#----------------------------------------------------------
# Other imports, which may require stuff from above
#----------------------------------------------------------
import cli
import http

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
