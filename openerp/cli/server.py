# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
OpenERP - Server
OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - OpenERP SA
"""

import atexit
import csv
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
    """Warn if the process's user is 'root' (on POSIX system)."""
    if os.name == 'posix':
        import pwd
        if pwd.getpwuid(os.getuid())[0] == 'root':
            sys.stderr.write("Running as user 'root' is a security risk.\n")

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
    _logger.info('addons paths: %s', openerp.modules.module.ad_paths)
    host = config['db_host'] or os.environ.get('PGHOST', 'default')
    port = config['db_port'] or os.environ.get('PGPORT', 'default')
    user = config['db_user'] or os.environ.get('PGUSER', 'default')
    _logger.info('database: %s@%s:%s', user, host, port)

def rm_pid_file(main_pid):
    config = openerp.tools.config
    if config['pidfile'] and main_pid == os.getpid():
        try:
            os.unlink(config['pidfile'])
        except OSError:
            pass

def setup_pid_file():
    """ Create a file with the process id written in it.

    This function assumes the configuration has been initialized.
    """
    config = openerp.tools.config
    if not openerp.evented and config['pidfile']:
        pid = os.getpid()
        with open(config['pidfile'], 'w') as fd:
            fd.write(str(pid))
        atexit.register(rm_pid_file, pid)

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

    with open(config["translate_out"], "w") as buf:
        registry = openerp.modules.registry.RegistryManager.new(dbname)
        with openerp.api.Environment.manage():
            with registry.cursor() as cr:
                openerp.tools.trans_export(config["language"],
                    config["translate_modules"] or ["all"], buf, fileformat, cr)

    _logger.info('translation file written successfully')

def import_translation():
    config = openerp.tools.config
    context = {'overwrite': config["overwrite_existing_translations"]}
    dbname = config['db_name']

    registry = openerp.modules.registry.RegistryManager.new(dbname)
    with openerp.api.Environment.manage():
        with registry.cursor() as cr:
            openerp.tools.trans_load(
                cr, config["translate_in"], config["language"], context=context,
            )

def main(args):
    check_root_user()
    openerp.tools.config.parse_config(args)
    check_postgres_user()
    report_configuration()

    config = openerp.tools.config

    # the default limit for CSV fields in the module is 128KiB, which is not
    # quite sufficient to import images to store in attachment. 500MiB is a
    # bit overkill, but better safe than sorry I guess
    csv.field_size_limit(500 * 1024 * 1024)

    if config["db_name"]:
        for db_name in config['db_name'].split(','):
            try:
                openerp.service.db._create_empty_database(db_name)
            except openerp.service.db.DatabaseExists:
                pass

    if config["test_file"]:
        config["test_enable"] = True

    if config["translate_out"]:
        export_translation()
        sys.exit(0)

    if config["translate_in"]:
        import_translation()
        sys.exit(0)

    # This needs to be done now to ensure the use of the multiprocessing
    # signaling mecanism for registries loaded with -d
    if config['workers']:
        openerp.multi_process = True

    preload = []
    if config['db_name']:
        preload = config['db_name'].split(',')

    stop = config["stop_after_init"]

    setup_pid_file()
    rc = openerp.service.server.start(preload=preload, stop=stop)
    sys.exit(rc)

class Server(Command):
    """Start the odoo server (default command)"""
    def run(self, args):
        main(args)
