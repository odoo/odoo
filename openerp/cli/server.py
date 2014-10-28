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

(c) 2003-TODAY, Fabien Pinckaers - OpenERP SA
"""

import logging
import os
import signal
import sys
import threading
import traceback
import time

import openerp

from . import Command

__author__ = openerp.release.author
__version__ = openerp.release.version

# Also use the `openerp` logger for the main script.
_logger = logging.getLogger('openerp')

def check_root_user():
    """ Exit if the process's user is 'root' (on POSIX system)."""
    if os.name == 'posix':
        import pwd
        if pwd.getpwuid(os.getuid())[0] == 'root' :
            sys.stderr.write("Running as user 'root' is a security risk, aborting.\n")
            sys.exit(1)

def check_postgres_user():
    """ Exit if the configured database user is 'postgres'.

    This function assumes the configuration has been initialized.
    """
    config = openerp.tools.config
    if config['db_user'] == 'postgres':
        sys.stderr.write("Using the database user 'postgres' is a security risk, aborting.")
        sys.exit(1)

def report_configuration():
    """ Log the server version and some configuration values.

    This function assumes the configuration has been initialized.
    """
    config = openerp.tools.config
    _logger.info("OpenERP version %s", __version__)
    for name, value in [('addons paths', config['addons_path']),
                        ('database hostname', config['db_host'] or 'localhost'),
                        ('database port', config['db_port'] or '5432'),
                        ('database user', config['db_user'])]:
        _logger.info("%s: %s", name, value)

def setup_pid_file():
    """ Create a file with the process id written in it.

    This function assumes the configuration has been initialized.
    """
    config = openerp.tools.config
    if config['pidfile']:
        fd = open(config['pidfile'], 'w')
        pidtext = "%d" % (os.getpid())
        fd.write(pidtext)
        fd.close()

def preload_registry(dbname):
    """ Preload a registry, and start the cron."""
    try:
        update_module = True if openerp.tools.config['init'] or openerp.tools.config['update'] else False
        db, registry = openerp.pooler.get_db_and_pool(dbname,update_module=update_module)
    except Exception:
        _logger.exception('Failed to initialize database `%s`.', dbname)
        return False
    return registry._assertion_report.failures == 0

def run_test_file(dbname, test_file):
    """ Preload a registry, possibly run a test file, and start the cron."""
    try:
        config = openerp.tools.config
        db, registry = openerp.pooler.get_db_and_pool(dbname, update_module=config['init'] or config['update'])
        cr = db.cursor()
        _logger.info('loading test file %s', test_file)
        openerp.tools.convert_yaml_import(cr, 'base', file(test_file), 'test', {}, 'init')

        if config['test_commit']:
            _logger.info('test %s has been commited', test_file)
            cr.commit()
        else:
            _logger.info('test %s has been rollbacked', test_file)
            cr.rollback()

        cr.close()
    except Exception:
        _logger.exception('Failed to initialize database `%s` and run test file `%s`.', dbname, test_file)

def export_translation():
    config = openerp.tools.config
    dbname = config['db_name']

    if config["language"]:
        msg = "language %s" % (config["language"],)
    else:
        msg = "new language"
    _logger.info('writing translation file for %s to %s', msg,
        config["translate_out"])

    fileformat = os.path.splitext(config["translate_out"])[-1][1:].lower()
    buf = file(config["translate_out"], "w")
    cr = openerp.pooler.get_db(dbname).cursor()
    openerp.tools.trans_export(config["language"],
        config["translate_modules"] or ["all"], buf, fileformat, cr)
    cr.close()
    buf.close()

    _logger.info('translation file written successfully')

def import_translation():
    config = openerp.tools.config
    context = {'overwrite': config["overwrite_existing_translations"]}
    dbname = config['db_name']

    cr = openerp.pooler.get_db(dbname).cursor()
    openerp.tools.trans_load( cr, config["translate_in"], config["language"],
        context=context)
    cr.commit()
    cr.close()

# Variable keeping track of the number of calls to the signal handler defined
# below. This variable is monitored by ``quit_on_signals()``.
quit_signals_received = 0

def signal_handler(sig, frame):
    """ Signal handler: exit ungracefully on the second handled signal.

    :param sig: the signal number
    :param frame: the interrupted stack frame or None
    """
    global quit_signals_received
    quit_signals_received += 1
    if quit_signals_received > 1:
        # logging.shutdown was already called at this point.
        sys.stderr.write("Forced shutdown.\n")
        os._exit(0)

def dumpstacks(sig, frame):
    """ Signal handler: dump a stack trace for each existing thread."""
    # code from http://stackoverflow.com/questions/132058/getting-stack-trace-from-a-running-python-application#answer-2569696
    # modified for python 2.5 compatibility
    threads_info = dict([(th.ident, {'name': th.name,
                                    'uid': getattr(th,'uid','n/a')})
                                for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        thread_info = threads_info.get(threadId)
        code.append("\n# Thread: %s (id:%s) (uid:%s)" % \
                    (thread_info and thread_info['name'] or 'n/a',
                     threadId,
                     thread_info and thread_info['uid'] or 'n/a'))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    _logger.info("\n".join(code))

def setup_signal_handlers():
    """ Register the signal handler defined above. """
    SIGNALS = map(lambda x: getattr(signal, "SIG%s" % x), "INT TERM".split())
    if os.name == 'posix':
        map(lambda sig: signal.signal(sig, signal_handler), SIGNALS)
        signal.signal(signal.SIGQUIT, dumpstacks)
    elif os.name == 'nt':
        import win32api
        win32api.SetConsoleCtrlHandler(lambda sig: signal_handler(sig, None), 1)

def quit_on_signals():
    """ Wait for one or two signals then shutdown the server.

    The first SIGINT or SIGTERM signal will initiate a graceful shutdown while
    a second one if any will force an immediate exit.

    """
    # Wait for a first signal to be handled. (time.sleep will be interrupted
    # by the signal handler.) The try/except is for the win32 case.
    try:
        while quit_signals_received == 0:
            time.sleep(60)
    except KeyboardInterrupt:
        pass

    config = openerp.tools.config
    openerp.service.stop_services()

    if getattr(openerp, 'phoenix', False):
        # like the phoenix, reborn from ashes...
        openerp.service._reexec()
        return

    if config['pidfile']:
        os.unlink(config['pidfile'])
    sys.exit(0)

def main(args):
    check_root_user()
    openerp.tools.config.parse_config(args)

    check_postgres_user()
    openerp.netsvc.init_logger()
    report_configuration()

    config = openerp.tools.config

    setup_signal_handlers()

    if config["test_file"]:
        run_test_file(config['db_name'], config['test_file'])
        sys.exit(0)

    if config["translate_out"]:
        export_translation()
        sys.exit(0)

    if config["translate_in"]:
        import_translation()
        sys.exit(0)

    if not config["stop_after_init"]:
        setup_pid_file()
        # Some module register themselves when they are loaded so we need the
        # services to be running before loading any registry.
        if config['workers']:
            openerp.service.start_services_workers()
        else:
            openerp.service.start_services()

    rc = 0
    if config['db_name']:
        for dbname in config['db_name'].split(','):
            if not preload_registry(dbname):
                rc += 1

    if config["stop_after_init"]:
        sys.exit(rc)

    _logger.info('OpenERP server is running, waiting for connections...')
    quit_on_signals()

class Server(Command):
    def run(self, args):
        main(args)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
