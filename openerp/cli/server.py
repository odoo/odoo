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
    for name, value in [('addons paths', openerp.modules.module.ad_paths),
                        ('database hostname', config['db_host'] or 'localhost'),
                        ('database port', config['db_port'] or '5432'),
                        ('database user', config['db_user'])]:
        _logger.info("%s: %s", name, value)

def rm_pid_file():
    config = openerp.tools.config
    if not openerp.evented and config['pidfile']:
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
        with open(config['pidfile'], 'w') as fd:
            pidtext = "%d" % (os.getpid())
            fd.write(pidtext)
        atexit.register(rm_pid_file)


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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
