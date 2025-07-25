# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""
OpenERP - Server
OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - OpenERP SA
"""

import atexit
import logging
import os
import sys

from psycopg2.errors import InsufficientPrivilege

from odoo.release import author as __author__  # noqa: F401
from odoo.release import version as __version__  # noqa: F401
from odoo.service import server
from odoo.tools import config

from . import Command

# Also use the `odoo` logger for the main script.
_logger = logging.getLogger('odoo')


def check_root_user():
    """Warn if the process's user is 'root' (on POSIX system)."""
    if os.name == 'posix' and os.getuid() == 0:
        sys.stderr.write("Running as user 'root' is a security risk.\n")


def check_postgres_user():
    """ Exit if the configured database user is 'postgres'.

    This function assumes the configuration has been initialized.
    """
    if (config['db_user'] or os.environ.get('PGUSER')) == 'postgres':
        sys.stderr.write("Using the database user 'postgres' is a security risk, aborting.")
        sys.exit(1)

def report_configuration():
    """ Log the server version and some configuration values.

    This function assumes the configuration has been initialized.
    """
    import odoo.addons  # noqa: PLC0415
    import odoo.release  # noqa: PLC0415
    _logger.info("Odoo version %s", odoo.release.version)
    if os.path.isfile(config['config']):
        _logger.info("Using configuration file at %s", config['config'])
    _logger.info('addons paths: %s', odoo.addons.__path__)
    if config.get('upgrade_path'):
        _logger.info('upgrade path: %s', config['upgrade_path'])
    if config.get('pre_upgrade_scripts'):
        _logger.info('extra upgrade scripts: %s', config['pre_upgrade_scripts'])
    host = config['db_host'] or os.environ.get('PGHOST', 'default')
    port = config['db_port'] or os.environ.get('PGPORT', 'default')
    user = config['db_user'] or os.environ.get('PGUSER', 'default')
    _logger.info('database: %s@%s:%s', user, host, port)
    replica_host = config['db_replica_host']
    replica_port = config['db_replica_port']
    if replica_host or replica_port or 'replica' in config['dev_mode']:
        _logger.info('replica database: %s@%s:%s', user, replica_host or 'default', replica_port or 'default')
    if sys.version_info[:2] > odoo.release.MAX_PY_VERSION:
        _logger.warning("Python %s is not officially supported, please use Python %s instead",
            '.'.join(map(str, sys.version_info[:2])),
            '.'.join(map(str, odoo.release.MAX_PY_VERSION))
        )

def rm_pid_file(main_pid):
    if config['pidfile'] and main_pid == os.getpid():
        try:
            os.unlink(config['pidfile'])
        except OSError:
            pass

def setup_pid_file():
    """ Create a file with the process id written in it.

    This function assumes the configuration has been initialized.
    """
    import odoo  # for evented  # noqa: PLC0415
    if not odoo.evented and config['pidfile']:
        pid = os.getpid()
        with open(config['pidfile'], 'w') as fd:
            fd.write(str(pid))
        atexit.register(rm_pid_file, pid)


def main(args):
    check_root_user()
    config.parse_config(args, setup_logging=True)
    check_postgres_user()
    report_configuration()

    for db_name in config['db_name']:
        from odoo.service import db  # noqa: PLC0415
        try:
            db._create_empty_database(db_name)
            config['init']['base'] = True
        except InsufficientPrivilege as err:
            # We use an INFO loglevel on purpose in order to avoid
            # reporting unnecessary warnings on build environment
            # using restricted database access.
            _logger.info("Could not determine if database %s exists, "
                         "skipping auto-creation: %s", db_name, err)
        except db.DatabaseExists:
            pass

    stop = config["stop_after_init"]

    setup_pid_file()
    rc = server.start(preload=config['db_name'], stop=stop)
    sys.exit(rc)


class Server(Command):
    """Start the odoo server (default command)"""

    def run(self, args):
        config.parser.prog = self.prog
        main(args)
