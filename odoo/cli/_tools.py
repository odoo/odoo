# ruff: noqa: PLC0415

import atexit
import contextlib
import logging
import os
import sys

from pathlib import Path

import odoo

__author__ = odoo.release.author
__version__ = odoo.release.version
_logger = logging.getLogger('odoo')


def check_root_user():
    """ Warn if the process's user is 'root' (on POSIX system)."""
    if os.name == 'posix':
        import getpass
        if getpass.getuser() == 'root':
            sys.stderr.write("Running as user 'root' is a security risk.\n")


def check_postgres_user():
    """ Exit if the configured database user is 'postgres'.
        This function assumes the configuration has been initialized.
    """
    if (odoo.tools.config['db_user'] or os.environ.get('PGUSER')) == 'postgres':
        sys.exit("Using the database user 'postgres' is a security risk, aborting.")


def rm_pid_file(main_pid):
    config = odoo.tools.config
    if config['pidfile'] and main_pid == os.getpid():
        with contextlib.suppress(OSError):
            os.unlink(config['pidfile'])


def touch_pid_file():
    """ Create a file with the process id written in it.
        We assume that the configuration has been initialized.
    """
    config = odoo.tools.config
    if not odoo.evented and config['pidfile']:
        pid = os.getpid()
        Path(config['pidfile']).write_text(str(pid), encoding="utf-8")
        atexit.register(rm_pid_file, pid)


def report_configuration():
    """ Log the server version and some configuration values.

    This function assumes the configuration has been initialized.
    """
    config = odoo.tools.config
    _logger.info("Odoo version %s", __version__)

    if os.path.isfile(config.rcfile):
        _logger.info("Using configuration file at %s", config.rcfile)
    _logger.info('addons paths: %s', odoo.addons.__path__)

    if config.get('upgrade_path'):
        _logger.info('upgrade path: %s', config['upgrade_path'])

    host = config['db_host'] or os.environ.get('PGHOST', 'default')
    port = config['db_port'] or os.environ.get('PGPORT', 'default')
    user = config['db_user'] or os.environ.get('PGUSER', 'default')
    _logger.info('database: %s@%s:%s', user, host, port)

    replica_host = config['db_replica_host']
    replica_port = config['db_replica_port']

    if replica_host is not False or replica_port:
        _logger.info('replica database: %s@%s:%s', user, replica_host or 'default', replica_port or 'default')

    if sys.version_info[:2] > odoo.MAX_PY_VERSION:
        _logger.warning("Python %s is not officially supported, please use Python %s instead",
            '.'.join(map(str, sys.version_info[:2])),
            '.'.join(map(str, odoo.MAX_PY_VERSION))
        )
