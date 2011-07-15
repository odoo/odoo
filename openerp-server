#!/usr/bin/env python
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

"""
OpenERP - Server
OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - OpenERP s.a.
"""

#----------------------------------------------------------
# python imports
#----------------------------------------------------------
import logging
import os
import signal
import sys
import threading
import traceback
import time

import openerp
__author__ = openerp.release.author
__version__ = openerp.release.version

if os.name == 'posix':
    import pwd
    # We DON't log this using the standard logger, because we might mess
    # with the logfile's permissions. Just do a quick exit here.
    if pwd.getpwuid(os.getuid())[0] == 'root' :
        sys.stderr.write("Attempted to run OpenERP server as root. This is not good, aborting.\n")
        sys.exit(1)

#-----------------------------------------------------------------------
# parse the command line
#-----------------------------------------------------------------------
openerp.tools.config.parse_config(sys.argv[1:])
config = openerp.tools.config

#----------------------------------------------------------
# get logger
#----------------------------------------------------------
openerp.netsvc.init_logger()
logger = logging.getLogger('server')

logger.info("OpenERP version - %s", __version__)
for name, value in [('addons_path', config['addons_path']),
                    ('database hostname', config['db_host'] or 'localhost'),
                    ('database port', config['db_port'] or '5432'),
                    ('database user', config['db_user'])]:
    logger.info("%s - %s", name, value)

# Don't allow if the connection to PostgreSQL done by postgres user
if config['db_user'] == 'postgres':
    logger.error("Connecting to the database as 'postgres' user is forbidden, as it present major security issues. Shutting down.")
    sys.exit(1)

#----------------------------------------------------------
# init net service
#----------------------------------------------------------
logger.info('initialising distributed objects services')

#----------------------------------------------------------
# Load and update databases if requested
#----------------------------------------------------------

if not ( config["stop_after_init"] or \
    config["translate_in"] or \
    config["translate_out"] ):
    openerp.osv.osv.start_object_proxy()
    openerp.service.web_services.start_web_services()
    http_server = openerp.service.http_server
    netrpc_server = openerp.service.netrpc_server
    http_server.init_servers()
    http_server.init_xmlrpc()
    http_server.init_static_http()
    netrpc_server.init_servers()

if config['db_name']:
    for dbname in config['db_name'].split(','):
        db, pool = openerp.pooler.get_db_and_pool(dbname, update_module=config['init'] or config['update'], pooljobs=False)
        cr = db.cursor()

        if config["test_file"]:
            logger.info('loading test file %s', config["test_file"])
            openerp.tools.convert_yaml_import(cr, 'base', file(config["test_file"]), {}, 'test', True)
            cr.rollback()

        pool.get('ir.cron').restart(db.dbname)

        cr.close()

#----------------------------------------------------------
# translation stuff
#----------------------------------------------------------
if config["translate_out"]:
    if config["language"]:
        msg = "language %s" % (config["language"],)
    else:
        msg = "new language"
    logger.info('writing translation file for %s to %s', msg, config["translate_out"])

    fileformat = os.path.splitext(config["translate_out"])[-1][1:].lower()
    buf = file(config["translate_out"], "w")
    dbname = config['db_name']
    cr = openerp.pooler.get_db(dbname).cursor()
    openerp.tools.trans_export(config["language"], config["translate_modules"] or ["all"], buf, fileformat, cr)
    cr.close()
    buf.close()

    logger.info('translation file written successfully')
    sys.exit(0)

if config["translate_in"]:
    context = {'overwrite': config["overwrite_existing_translations"]}
    dbname = config['db_name']
    cr = openerp.pooler.get_db(dbname).cursor()
    openerp.tools.trans_load(cr,
                     config["translate_in"], 
                     config["language"],
                     context=context)
    openerp.tools.trans_update_res_ids(cr)
    cr.commit()
    cr.close()
    sys.exit(0)

#----------------------------------------------------------------------------------
# if we don't want the server to continue to run after initialization, we quit here
#----------------------------------------------------------------------------------
if config["stop_after_init"]:
    sys.exit(0)

openerp.netsvc.start_agent()

#----------------------------------------------------------
# Launch Servers
#----------------------------------------------------------

LST_SIGNALS = ['SIGINT', 'SIGTERM']

SIGNALS = dict(
    [(getattr(signal, sign), sign) for sign in LST_SIGNALS]
)

quit_signals_received = 0

def handler(signum, frame):
    """
    :param signum: the signal number
    :param frame: the interrupted stack frame or None
    """
    global quit_signals_received
    quit_signals_received += 1
    if quit_signals_received > 1:
        sys.stderr.write("Forced shutdown.\n")
        os._exit(0)

def dumpstacks(signum, frame):
    # code from http://stackoverflow.com/questions/132058/getting-stack-trace-from-a-running-python-application#answer-2569696
    # modified for python 2.5 compatibility
    thread_map = dict(threading._active, **threading._limbo)
    id2name = dict([(threadId, thread.getName()) for threadId, thread in thread_map.items()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name[threadId], threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    logging.getLogger('dumpstacks').info("\n".join(code))

for signum in SIGNALS:
    signal.signal(signum, handler)

if os.name == 'posix':
    signal.signal(signal.SIGQUIT, dumpstacks)

def quit():
    openerp.netsvc.Agent.quit()
    openerp.netsvc.Server.quitAll()
    if config['pidfile']:
        os.unlink(config['pidfile'])
    logger = logging.getLogger('shutdown')
    logger.info("Initiating OpenERP Server shutdown")
    logger.info("Hit CTRL-C again or send a second signal to immediately terminate the server...")
    logging.shutdown()

    # manually join() all threads before calling sys.exit() to allow a second signal
    # to trigger _force_quit() in case some non-daemon threads won't exit cleanly.
    # threading.Thread.join() should not mask signals (at least in python 2.5)
    for thread in threading.enumerate():
        if thread != threading.currentThread() and not thread.isDaemon():
            while thread.isAlive():
                # need a busyloop here as thread.join() masks signals
                # and would present the forced shutdown
                thread.join(0.05)
                time.sleep(0.05)
    sys.exit(0)

if config['pidfile']:
    fd = open(config['pidfile'], 'w')
    pidtext = "%d" % (os.getpid())
    fd.write(pidtext)
    fd.close()

openerp.netsvc.Server.startAll()

logger.info('OpenERP server is running, waiting for connections...')

while quit_signals_received == 0:
    time.sleep(60)

quit()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
