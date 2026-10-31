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
from contextlib import closing

import psycopg2
from psycopg2.errors import InsufficientPrivilege

from odoo.release import author as __author__  # noqa: F401
from odoo.release import version as __version__  # noqa: F401
from odoo.service import server
from odoo.sql_db import db_connect
from odoo.tools import config

from . import Command

# Also use the `odoo` logger for the main script.
_logger = logging.getLogger('odoo')


def check_root_user():
    """Warn if the process's user is 'root' (on POSIX system)."""
    if os.name == 'posix' and os.getuid() == 0:
        sys.stderr.write("Running as user 'root' is a security risk.\n")


def check_postgres_user():
    """ Exit if the connected PostgreSQL role has superuser-like privileges.

        A role that is SUPERUSER / REPLICATION / BYPASSRLS (directly, or
        reachable via SET ROLE) can read and tamper with every database in the
        cluster, which defeats Odoo's isolation between databases.
        This function assumes the configuration has been initialized.
    """
    if (config['db_user'] or os.environ.get('PGUSER')) == 'postgres':
        sys.exit("Using the database user 'postgres' is a security risk, aborting.")

    sys_cr = None
    for dbname in [config['db_system'], 'postgres']:
        try:
            sys_cr = db_connect(dbname).cursor()
            break
        except psycopg2.errors.OperationalError:
            _logger.info("Could not connect to %r for the role privilege check", dbname)

    if sys_cr is None:
        _logger.warning("Could not verify the database role privileges: no system database is reachable")
        return

    try:
        with closing(sys_cr) as cr:
            cr.execute("""
                SELECT r.rolname,
                       r.rolsuper,
                       r.rolreplication,
                       r.rolbypassrls,
                       ARRAY(
                            SELECT r1.rolname
                              FROM pg_auth_members m
                              JOIN pg_roles r1 ON r1.oid = m.roleid
                             WHERE m.member = r.oid
                               AND m.set_option  -- (PG16+)
                               AND EXISTS (
                                        SELECT 1
                                        FROM pg_roles r2
                                        WHERE (r2.rolsuper OR r2.rolreplication OR r2.rolbypassrls)
                                        AND (r1.oid = r2.oid OR pg_has_role(r1.oid, r2.oid, 'SET'))
                                   )
                       )
                  FROM pg_roles r
                 WHERE r.rolname = CURRENT_USER
            """)
            rolname, rolsuper, rolreplication, rolbypassrls, escalation_roles = cr.fetchone()
    except psycopg2.Error as e:
        _logger.warning("Could not verify the database role privileges: %s", e)
        return

    privileges = [rol for rol, held in {
        'SUPERUSER': rolsuper,
        'REPLICATION': rolreplication,
        'BYPASSRLS': rolbypassrls,
    }.items() if held]

    if not privileges and not escalation_roles:
        return

    error_msg = (
        f"Odoo cannot run with role {rolname!r}: it can read and tamper with every "
        "database in the cluster, which defeats the isolation between Odoo databases.\n"
        "Fix it as a database administrator (e.g. sudo -u postgres psql), then restart Odoo.\n"
        "Fixes:\n"
    )
    act_as_super = 'sudo -u postgres psql -d postgres -c'
    if privileges:
        error_msg += f'\t{act_as_super} \'ALTER ROLE "{rolname}" WITH NOSUPERUSER NOREPLICATION NOBYPASSRLS CREATEDB;\'\n'
    for role in escalation_roles:
        # disable SET ROLE escalation but keep inherited privileges (unlike REVOKE)
        error_msg += f'\t{act_as_super} \'GRANT "{role}" TO "{rolname}" WITH SET FALSE;\'\n'
    sys.exit(error_msg)


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
    if config.has_db_replica:
        _logger.info('replica database: %s@%s:%s', user, config['db_replica_host'] or 'default', config['db_replica_port'] or 'default')
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
        from odoo.modules import db  # noqa: PLC0415
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
