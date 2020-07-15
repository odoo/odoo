# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import collections
import contextlib
import operator
import os
import pathlib
import warnings
from distutils.util import strtobool
from getpass import getuser
from textwrap import dedent

try:
    from odoo import release
    from odoo.loglevels import PSEUDOCONFIG_MAPPER as loglevelmap
except ImportError:
    release = __import__("collections").namedtuple("release", ["description", "version"])("desc of odoo", "master")
    loglevelmap = {
        'debug_rpc_answer': 0, 'debug_rpc': 0, 'debug': 0, 'debug_sql': 0,
        'info': 0, 'runbot': 0, 'warn': 0, 'warning': 0, 'error': 0, 'critical': 0,
    }

# def assert_(test, value):
#     if test:
#         return value
#     raise 
# {metaoption.dest: partial(test, partial(operator.contains, metaoption.choices)) for ... in ... if hasattr(metaoption, 'choices')}


store_true = {'type': strtobool, 'action': 'store_const', 'const': 'True', 'default': 'False'}
store_false = {'type': strtobool, 'action': 'store_const', 'const': 'False', 'default': 'True'}
DELETED = object()

def fullpath(path):
    return pathlib.Path(path).expanduser().resolve()


def _check_file_access(rawopt, mode):
    path = fullpath(rawopt)
    if path.is_file() and not os.access(path, mode):
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = ", ".join(perm for bit, perm in pairs if bit & mode)
        raise SystemExit(f'{path}: requires {missing} permissions')
    if mode == os.W_OK and not os.access(path.parent, os.W_OK):
        raise SystemExit(f'{path.parent}: requires write permission')
    return path


def coma(cast):
    return lambda rawopt: list(map(cast, rawopt.split(',')))


def check_dir_access(rawopt, mode):
    path = fullpath(rawopt)
    if not path.is_dir():
        raise SystemExit(f"{path}: no such directory")
    if not os.access(path, mode):
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = ", ".join(perm for bit, perm in pairs if bit & mode)
        raise SystemExit(f"{path}: requires {missing} permissions")
    return path


def checkfile(mode):
    mode = {'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    return partial(_check_file_access, mode=mode)


def addons_path(rawopt):
    path = check_dir_access(rawopt, os.R_OK | os.X_OK)
    if not next(path.glob('*/__manifest__.py'), None):
        olds = path.glob('*/__openerp__.py')
        if not olds:
            raise SystemExit(f'{rawopt}: not a valid addons path')
        warnings.warn(
            'Using "__openerp__.py" as module manifest is deprecated, '
            'please renome them as "__manifest__.py". Affected '
            'modules: %s' % ", ".join((old.parent.name for old in olds)),
            DeprecationWarning)
    return path


def upgrade_path(rawopt):
    path = check_dir_access(rawopt, os.R_OK | os.X_OK)
    if not any(path.glob(f'*/*/{x}-*.py') for x in ["pre", "post", "end"]):
        if path.joinpath('migrations').is_dir():  # for colleagues
            raise SystemExit(f"{rawopt}: is not a valid upgrade path, looks like you forgot the migrations folder")
        raise SystemExit(f"{rawopt}: is not a valid upgrade path")
    return path


def data_dir(rawopt):
    datadir = check_dir_access(rawopt, os.R_OK | os.W_OK | os.X_OK)

    ad = datadir.joinpath('addons')
    if not ad.exists():
        ad.mkdir(mode=0o700)
    elif os.access(ad, os.R_OK | os.W_OK | os.X_OK):
        raise
    adr = ad.joinpath(release.series)
    if not adr.exists():
        # try to make +rx placeholder dir, will need manual +w to activate it
        try:
            adr.mkdir(mode=0o500)
        except OSError:
            warnings.warn("Failed to create addons data dir %s", adr)

    sd = datadir.joinpath('sessions')
    if not sd.exists():
        sd.mkdir(mode=0o700)
    elif not os.access(sd, os.R_OK | os.W_OK | os.X_OK):
        raise

    fd = datadir.joinpath('filestore')
    if not fd.exists():
        fd.mkdir(mode=0o700)
    elif not os.access(fd, os.R_OK | os.W_OK | os.X_OK):
        raise

    return datadir


def pg_utils_path(rawopt):
    path = check_dir_access(rawopt, os.X_OK)
    pg_utils = {'psql', 'pg_dump', 'pg_restore'}
    if not any(file.stem in pg_utils for file in path.iterdir()):
        raise
    return path


def osv_memory_age_limit(rawopt):
    msg = ("The osv-memory-age-limit is a deprecated alias to "
           "the transient-age-limit option, please use the latter")
    warnings.warn(msg, DeprecationWarning)
    return float(rawopt)


main_parser = argparse.ArgumentParser(description=dedent("""\
    Odoo Command-Line Interface

    See online documentation at: 
    https://www.odoo.com/documentation/master/reference/ocli.html
    """))
subparsers = main_parser.add_subparsers()


#
# Common, bootstraping required options
#
add = main_parser.add_argument
add('-V', '--version', action='version', version=f"{release.description} {release.version}")
add('--addons-path', dest='addons_path', type=coma(addons_path), action="append", nargs='*', metavar='DIRPATH', help="specify additional addons paths")
add('--upgrade-path', dest='upgrade_path', type=upgrade_path, nargs=1, metavar='DIRPATH', help="specify an additional upgrade path.")
add('-D', '--data-dir', dest='data_dir', type=data_dir, nargs=1, help="")
add('--log-level', dest='log_level', type=str, nargs=1, metavar="LEVEL", choices=loglevelmap.keys(), "specify the level of the logging")
add('--logfile', dest='logfile', type=str, nargs=1, metavar="FILEPATH", help="file where the server log will be stored")
add('--syslog', dest='syslog', **store_true, help="Send the log to the syslog server")
add('--log-handler', dest='log_handler', action='append', default=[':INFO'], metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')


#
# Advanced logging options
#
logging_parser = argparse.ArgumentParser()
add = logging_parser.add_argument
add('--log-request', dest='log_handler', action='append_const', const='odoo.http.rpc.request:DEBUG', help=argparse.SUPPRESS)
add('--log-response', dest='log_handler', action='append_const', const='odoo.http.rpc.response:DEBUG', help=argparse.SUPPRESS)
add('--log-web', dest='log_handler', action='append_const', const='odoo.http:DEBUG', help=argparse.SUPPRESS)
add('--log-sql', dest='log_handler', action='append_const', const='odoo.sql_db:DEBUG', help=argparse.SUPPRESS)
add('--log-db', dest='log_db', **store_true, help="Enable database logs record")
add('--log-db-level', dest='log_level', type=str, nargs=1, metavar="LEVEL", default='warning', choices=loglevelmap.keys(), "specify the level of the database logging")

#
# Configuration file options
#
config_parser = argparse.ArgumentParser()
add = logging_parser.add_argument
if os.name == 'nt':
    odoorc = pathlib.Path(sys.argv[0]).resolve().parent().joinpath('odoo.conf')
else:
    odoorc = pathlib.Path.home().joinpath('.odoorc')
add('-c', '--config', dest='config', type=argparse.FileType('r'), nargs=1, metavar="FILEPATH", default=odoorc, help="specify alternate config file name")
add('-s', '--save', dest='save', type=checkfile('w'), nargs='?', metavar="FILEPATH", default=None, const=odoorc, help="save parsed config in PATH")

#
# Database options
#
database_parser = argparse.ArgumentParser()
add = database_parser.add_argument
add('-d', '--database', dest='db_name', type=str, nargs=1, metavar="DBNAME", help='database name to connect to (default: "%s")' % os.getenv('PGDATABASE', getuser()))
add('-r', '--db_user', dest='db_user', type=str, nargs=1, metavar="USERNAME", help='database user to connect as (default: "%s")' % getuser())
add('-w', '--db_password', dest='db_password', type=str, nargs=1, metavar="PWD", help='password to be used if the database demands password authentication. Using this argument is a security risk, see the "The Password File" section in the PostgreSQL documentation for alternatives.')
add('--db_host', dest='db_host', type=str, nargs=1, metavar="HOSTNAME", help='database server host or socket directory (default: "%s")' % os.geten('PGHOST', 'local socket'))
add('--db_port', dest='db_port', type=str, nargs=1, metavar="PORT", help='database server port (default: %d)' % os.getenv('PGPORT', 5432))
add('--db_sslmode', dest='db_sslmode', type=str, nargs=1, metavar="METHOD", default='prefer', choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'], help="determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server")
add('--pg_path', dest='pg_path', type=pg_utils_path, nargs=1, metavar="DIRPATH", default=None, help="postgres utilities directory")
add('--db-template', dest='db_template', type=str, nargs=1, metavar="DBNAME", default='template0', help="custom database template to create a new database")
add('--unaccent', dest="unaccent", **store_true, help="Try to enable the unaccent extension when creating new databases")

#
# ORM
#
orm_parser = argparse.ArgumentParser()
add = orm_parser.add_argument
add('--transient-age-limit', dest='transient_age_limit', type=float, nargs=1, metavar="HOUR", default=1.0, help="Time in hours records created with a TransientModel (mosly wizard) are kept in the database.")
add('--osv-memory-age-limit', dest='transient_age_limit', type=osv_memory_age_limit, nargs=1, help=argparse.SUPPRESS)

#
# I18N
#
i18n_parser = argparse.ArgumentParser()
add = i18n_parser.add_argument
add('--load-language', dest='load_language', type=coma(str), nargs='*', metavar='LANGCODE', default=None, help="specifies the languages for the translations you want to be loaded")
'-l', '--language'
'--i18n-export'
'--i18n-import'
'--i18n-overwrite'
'--modules'

#
# Security
#
'--no-database-list'

#
# Developers
#
'--dev'
'--shell-interface'

#
# Misc
#
'--stop-after-init'
'--geoip-db'

#
# Server stuff
#
'--pidfile'

#
# Database loading stuff
#
'-i', '--init'
'-u', '--update'
'--without-demo'
#'-P', '--import-partial'
'--load'

#
# HTTP options
#
'--http-interface'
'-p', '--http-port'
'--no-http'
'--proxy-mode'

#
# xmlrpc options
#
'--xmlrpc-interface'
'--xmlrpc-port'
'--no-xmlrpc'

#
# web options
#
'--db-filter'

#
# testing options
#
'--test-file'
'--test-enable'
'--test-tags'
'--screencasts'
'--screenshots'

#
# smtp options
#
'--email-from'
'--smtp'
'--smtp-port'
'--smtp-ssl'
'--smtp-user'
'--smtp-password'

#
# CRON
#
'--max-cron-threads'
'--limit-time-real-cron'

#
# Longpolling options
#
'--longpolling-port'

#
# Workers
#
'--workers'


#
# Limits
#
'--db_maxconn'
'--limit-memory-soft'
'--limit-memory-hard'
'--limit-time-cpu'
'--limit-time-real'
'--limit-request'

#
# Server subcommand
#
server_parser = subparsers.add_parser('server', parents=[main_parser, logging_parser, config_parser])


ctxopt_stack = []
srcoptmap = {
    "custom": {},
    "cli": {},
    "http": {},
    "cron": {},
    "environ": {},
    "file": {},
    "default": {},
}
chainmap = collections.ChainMap(
    srcoptmap["custom"],
    srcoptmap["cli"],
    srcoptmap["file"],
    srcoptmap["default"],
)

class configmanager(collections.abc.MutableMapping):
    def parse_load(self, configpath=None):
        # clear all previously loaded options except
        # the defaults as there is no way they change
        for src, opt in srcoptmap.items():
            if src == 'default':
                continue
            opt.clear()

        # reload all sources
        srcoptmap["cli"].update({} if islib else cli.parse_args())
        srcoptmap["file"].update(parse_file(configpath or chainmap["config"]))

    def prioritize(self, source):
        options = srcoptmap[source]
        with contextlib.suppress(IndexError):
            chainmap.maps.pop(chainmap.maps.index(options))
        chainmap.maps.insert(1, options)

    def save(self, configpath=None):
        if configpath is None:
            configpath = chainmap["config"]
        pass

    def pop(self, option):
        val = self[options]
        del self[options]
        return val

    def __getitem__(self, option):
        val = chainmap[option]
        if val is DELETED:
            raise KeyError(f"{option} has been removed")
        return val

    def __setitem__(self, option, value):
        chainmap[option] = value

    def __delitem__(self, option):
        chainmap[option] = DELETED

    def __iter__(self):
        return iter(chainmap)

    def __len__(self):
        return len(chainmap)

    def __enter__(self, ctxopts=None):
        if ctxopts is None:
            ctxopts = {}
        ctxopts_stack.append(ctxopts)
        chainmap.insert(0, ctxopts)
        return ctxopts

    def __exit__ (self, type, value, tb):
        ctxopts = ctxopts_stack.pop()
        chainmap.maps.remove(ctxopts)

config = configmanager()  # singleton



# TODO: destination variables, grouping of options, etc.
def main():
    # ------------- #
    #  Main parser  #
    # ------------- #
    main_parser = argparse.ArgumentParser(
        prog='ocli', description='Odoo Command-Line Interface'
    )
    main_parser.add_argument(
        '-v', '--version', action='store_true',
        help="show version information about Odoo and the Odoo CLI"
    )
    # ----------------- #
    #  Logging options  #
    # ----------------- #
    logging_parser = argparse.ArgumentParser(add_help=False)
    logging_parser.add_argument(
        '--logfile', nargs=1, metavar='PATH', type=str,
        help="path to where the log file should be saved"
    )
    logging_parser.add_argument(
        '--syslog', action='store_true',
        help="save odoo logs as system logs"
    )
    logging_parser.add_argument(
        '--log-level', nargs=1, metavar='EXPR', type=str,
        help="which type of logs to display to stdin"
    )
    # ---------------- #
    #  Common options  #
    # ---------------- #
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        '--addons-path', nargs='+', metavar='PATH',
        type=str,
        help="space-separated list of paths to check for addons"
    )
    common_parser.add_argument(
        '--data-dir', nargs=1, metavar='PATH', type=str,
        help="path to a directory where odoo-generated files should be stored"
    )
    # ------------ #
    #  Subparsers  #
    # ------------ #
    top_level_subparsers = main_parser.add_subparsers(help='sub-command help')
    dbname_parser = argparse.ArgumentParser(add_help=False)
    dbname_parser.add_argument(
        'dbname', nargs=1, type=str, metavar='DATABASE',
        help="name of the database"
    )
    # ------------- #
    #  DB creation  #
    # ------------- #
    create_parser = top_level_subparsers.add_parser(
        'create',
        help="create odoo databases",
        parents=[dbname_parser, logging_parser, common_parser]
    )
    create_parser.add_argument(
        '-d', '--demo', action='store_true',
        help="if specified demo data will be installed in the database"
    )
    create_parser.add_argument(
        '-l', '--launch', action='store_true',
        help="if specified, the db will be launched after it is created"
    )
    # ---------------- #
    #  DB duplication  #
    # ---------------- #
    dupe_parser = top_level_subparsers.add_parser(
        'duplicate',
        help="duplicate odoo databases",
    )
    dupe_parser.add_argument(
        'source', nargs=1, type=str, metavar='SOURCE',
        help="name of the source database"
    )
    dupe_parser.add_argument(
        'destination', nargs=1, type=str, metavar='DESTINATION',
        help="name of the destination database"
    )
    # --------- #
    #  DB dump  #
    # --------- #
    dump_parser = top_level_subparsers.add_parser(
        'dump',
        help="dump odoo databases",
        parents=[dbname_parser, logging_parser]
    )
    dump_parser.add_argument(
        'path', nargs='?', type=str, metavar='PATH',
        help="path where the dump should be stored"
    )
    dump_parser.add_argument(
        '-f', '--format', choices=['gzip', 'raw', 'sql'],
        help="one of three available formats for the dump file"
    )
    # Defaults
    dump_parser.set_defaults(path='.', format='gzip')
    # ------------ #
    #  DB restore  #
    # ------------ #
    restore_parser = top_level_subparsers.add_parser(
        'restore',
        help="restore odoo databases",
        parents=[dbname_parser, logging_parser]
    )
    restore_parser.add_argument(
        'path', nargs='?', type=str, metavar='PATH',
        help="path of the dump to restore"
    )
    restore_parser.add_argument(
        '--dbuuid', type=str, help="dbuuid of the db to restore"
    )
    restore_parser.set_defaults(path='.')
    # -------------- #
    #  Cron Process  #
    # -------------- #
    cron_parser = top_level_subparsers.add_parser(
        'cron',
        help="launch a cron server for running all of the databases' cron jobs"
    )
    cron_parser.add_argument(
        '-w', '--workers', nargs=1,
        help="amount of workers to assign to this cron server (default: 2)"
    )
    cron_parser.add_argument(
        '--pid-file', nargs=1, type=str, metavar='PATH',
        help="file where the pid of the cron server will be stored"
    )
    # TODO: not one, but different --limit-* commands, maybe make a parser
    # and inherit in subparsers
    # ------------ #
    #  Migrations  #
    # ------------ #
    migration_parser = top_level_subparsers.add_parser(
        'migrate',
        help="migrate the specified odoo database",
        parents=[dbname_parser, logging_parser]
    )
    migration_parser.add_argument(
        'path', nargs=1, type=str, metavar='PATH',
        help="path to the migration scripts for the specified database"
    )
    # --------- #
    #  Imports  #
    # --------- #
    import_parser = top_level_subparsers.add_parser(
        'import',
        help="import csv data into odoo",
        parents=[dbname_parser, logging_parser, common_parser]
    )
    import_parser.add_argument(
        'path', nargs=1, type=str, metavar='PATH',
        help="path to the csv file to import into the odoo database"
    )
    import_parser.add_argument(
        # In master, this argument takes a file where intermediate states are
        # stored, IMO it'd be best to save this to /tmp since the user is
        # likely to retry the import immediately after crashing, no need
        # to litter the user's file system
        '-p', '--import-partial', action='store_true',
        help="import in incremental steps, primarily used to import big "
        "amounts of data"
    )
    # --------------------- #
    #  Module installation  #
    # --------------------- #
    install_parser = top_level_subparsers.add_parser(
        'install',
        help="install odoo modules",
        parents=[dbname_parser, logging_parser, common_parser]
    )
    install_parser.add_argument(
        'modules', nargs='+', metavar='MODULE', type=str,
        help="space-separated list of modules to be installed"
    )
    # ---------------- #
    #  Module updates  #
    # ---------------- #
    update_parser = top_level_subparsers.add_parser(
        'update',
        help="update odoo modules",
        parents=[dbname_parser, logging_parser, common_parser]
    )
    update_parser.add_argument(
        'modules', nargs='+', metavar='MODULE', type=str,
        help="space-separated list of modules to be updated"
    )
    # --------------------------- #
    #  Standalone test execution  #
    # --------------------------- #
    test_parser = top_level_subparsers.add_parser(
        'test', help="execute specific unit tests",
        parents=[logging_parser, common_parser]
    )
    test_parser.add_argument(
        # Equivalent of +tag
        'tag', nargs='*', type=str, metavar='TAG',
        help="only run tests with the specified tags"
    )
    test_parser.add_argument(
        # Print the test results in a more user-friendly format, current format
        # is hard to read (but is still okay for the runbot I guess...)
        '--pretty-print', action='store_true',
        help="print the test results in a human-readable format"
    )
    test_parser.add_argument(
        # Equivalent of -tag
        '-e', '--exclude', nargs='+', type=str, metavar='TAG',
        help="exclude tests with these tags when running the tests suite"
    )
    test_parser.add_argument(
        # Stop execution of the tests at the first failure, this could be
        # extremely useful at reducing runbot time and also makes sense,
        # if I'm debugging my code I don't need to see 50 failures, I can just
        # see one and fix as I go
        '-ff', '--fail-fast', action='store_true',
        help="terminate the test execution upon first failure"
    )
    test_parser.add_argument(
        '-s', '--save', metavar='PATH', type=str,
        help="save the test results to the specified file"
    )
    # -------------- #
    #  Translations  #
    # -------------- #
    translation_parser = top_level_subparsers.add_parser(
        'translate', help="tools for handling translations in odoo",
        parents=[dbname_parser, logging_parser, common_parser]
    )
    translation_subparsers = translation_parser.add_subparsers(
        help='translation toolset help'
    )
    # Load subcommand
    t_load_parser = translation_subparsers.add_parser(
        'load', help="load a translation into the specified database"
    )
    t_load_parser.add_argument(
        'language', nargs=1, type=str, metavar='LANG',
        help="language to be loaded"
    )
    # Import subcommand
    t_import_parser = translation_subparsers.add_parser(
        'import', help="import translations"
    )
    t_import_parser.add_argument(
        'language', nargs=1, type=str, metavar='LANG',
        help="language for which translations will be imported"
    )
    t_import_parser.add_argument(
        'infile', nargs=1, type=str, metavar='PATH',
        help="path to the PO/CSV file containing the translations"
    )
    t_import_parser.add_argument(
        '-o', '--overwrite', action='store_true',
        help="if specified, translations in the database will be overwritten "
        "for those found in the input file"
    )
    # Export subcommand
    t_export_parser = translation_subparsers.add_parser(
        'export', help="export translations"
    )
    t_export_parser.add_argument(
        'language', nargs=1, type=str, metavar='LANG',
        help="language for which translations will be exported"
    )
    t_export_parser.add_argument(
        'outfile', nargs=1, type=str, metavar='PATH',
        help="path to where the exported records will be stored"
    )
    t_export_parser.add_argument(
        '-t', '--template', action='store_true', help="???"
    )
    # ------- #
    #  Serve  #
    # ------- #
    serve_parser = top_level_subparsers.add_parser(
        'serve',
        parents=[common_parser, logging_parser],
        help="launch an odoo server"
    )
    serve_parser.add_argument(
        '-i', '--init', nargs='+', type=str, metavar='MODULE',
        help="space-separated list of modules to install during server launch"
    )
    serve_parser.add_argument(
        '-u', '--update', nargs='+', type=str, metavar='MODULE',
        help="space-separated list of modules to update during server launch"
    )
    serve_parser.add_argument(
        '-l', '--load', nargs='+', type=str, metavar='MODULE',
        help="space-separated list of server-wide modules"
    )
    serve_parser.add_argument(
        '--interface-address', nargs=1, type=str, metavar='ADDRESS',
        help="IPv4 address for the HTTP/XMLRPC interface"
    )
    serve_parser.add_argument(
        '-m', '--proxy-mode', action='store_true',
        help="something something reverse proxy"
    )
    serve_parser.add_argument(
        '-p', '--port', nargs=1, type=int, metavar='PORT',
        help="HTTP port for the server"
    )
    serve_parser.add_argument(
        '--longpolling-port', nargs=1, type=int, metavar='PORT',
        help="longpolling port for the server"
    )
    serve_parser.add_argument(
        '-d', '--database', nargs=1, type=str, metavar='DATABASE',
        help="database to select or create if it doesn't exist"
    )
    serve_parser.add_argument(
        '--db-filter', nargs=1, type=str, metavar='REGEX',
        help="databases to make available"
    )
    serve_parser.add_argument(
        '-n', '--no-database-list', action='store_true',
        help="don't show list of databases through Web UI"
    )
    serve_parser.add_argument(
        '--dev', nargs='+',
        choices=[
            # TODO: Re-parse this later on and remove duplicates
            'pudb', 'wdb', 'ipdb', 'pdb', 'all', 'reload', 'qweb',
            'werkzeug', 'xml'
        ],
        help="enable developer mode"
    )
    serve_parser.add_argument(
        '--without-demo', nargs='+', type=str, metavar='MODULE',
        help="disable loading demo data for modules to be installed"
    )
    serve_parser.add_argument(
        '--pid-file', nargs=1, metavar='PATH', type=str,
        help="file where the server pid will be stored"
    )
    # Advanced options
    serve_parser.add_argument(
        '--limit-virt-count', nargs=1, type=int, metavar='RECORDS',
        help="Force a limit on the maximum number of records kept in the "
        "virtual osv_memory tables. The default is False, which means no "
        "count-based limit."
    )
    serve_parser.add_argument(
        '--limit-virt-age', nargs=1, type=float, metavar='HOURS',
        help="Force a limit on the maximum age of records kept in the "
        "virtual osv_memory tables. This is a decimal value expressed in "
        "hours, the default is 1 hours."
    )
    serve_parser.add_argument(
        '--max-cron-threads', nargs=1, type=int, metavar='THREADS',
        help="Maximum number of threads processing concurrently cron jobs "
        "(default 2)."
    )
    # Multi-processing, POSIX only
    if os.name == 'posix':
        serve_parser.add_argument(
            '--workers', nargs=1, type=int, metavar='WORKERS',
            help="Specify the number of workers, 0 to disable prefork mode."
        )
        # Different limits
        serve_parser.add_argument(
            '--limit-memory-soft', nargs=1, type=str, metavar='BYTES',
            help="Maximum allowed virtual memory per worker, when reached the "
            "worker will be reset after the current request (default 2GiB)"
        )
        serve_parser.add_argument(
            '--limit-memory-hard', nargs=1, type=str, metavar='BYTES',
            help="Maximum allowed virtual memory per worker, when reached, "
            "memory allocation will fail (default 2.5GiB)"
        )
        serve_parser.add_argument(
            '--limit-time-cpu', nargs=1, type=int, metavar='SECONDS',
            help="Maximum allowed CPU time per request in seconds (default 60)"
        )
        serve_parser.add_argument(
            '--limit-time-real', nargs=1, type=int, metavar='SECONDS',
            help="Maximum allowed real time per request in seconds "
            "(default 120)"
        )
        serve_parser.add_argument(
            '--limit-time-real-cron', nargs=1, type=int, metavar='SECONDS',
            help="Maximum allowed real time per cron job in seconds "
            "(default --limit-time-real), set to 0 for no limit"
        )
        serve_parser.add_argument(
            '--limit-request', nargs=1, type=int, metavar='REQUESTS',
            help="Maximum number of request to be processed per worker "
            "(default 8192)"
        )
    # --------------- #
    #  Configuration  #
    # --------------- #
    config_parser = top_level_subparsers.add_parser(
        'config',
        help="set up your Odoo configuration"
    )
    config_parser.add_argument(
        'setting', nargs=1, type=str, metavar='SETTING',
        help="setting to modify"
    )
    # Just to avoid any shenanigans
    ex_group = config_parser.add_mutually_exclusive_group()
    ex_group.add_argument(
        'new_val', nargs='?', type=str, metavar='VALUE', default=None,
        help="new value for the specified setting"
    )
    ex_group.add_argument(
        '-e', '--edit', action='store_true',
        help="open the settings file with the preferred text editor"
    )
    # ------------ #
    #  Deployment  #
    # ------------ #
    deploy_parser = top_level_subparsers.add_parser(
        'deploy',
        help="deploy a module on an Odoo instance"
    )
    deploy_parser.add_argument(
        'path', nargs=1, type=str, metavar='PATH',
        help="path of the module to be deployed"
    )
    deploy_parser.add_argument(
        'url', nargs='?', metavar='URL',
        help="url of the server",
        default="http://localhost:8069"
    )
    # ---------- #
    #  Scaffold  #
    # ---------- #
    scaffold_parser = top_level_subparsers.add_parser(
        'scaffold',
        help="create an empty module following a template"
    )
    scaffold_parser.add_argument(
        'name', nargs=1, type=str, metavar='NAME',
        help="name of the module to create"
    )
    scaffold_parser.add_argument(
        'dest', nargs='?', type=str, metavar='PATH', default='.',
        help="directory where the newly-created module will be stored "
        "(default is current working directory)"
    )
    scaffold_parser.add_argument(
        '-t', '--template', nargs=1, type=str, metavar='PATH',
        help="provide a template for the module to be generated"
    )
    # ----------------- #
    #  Shell Interface  #
    # ----------------- #
    shell_parser = top_level_subparsers.add_parser(
        'shell',
        help="activate the shell interface for the specified database",
        parents=[common_parser, logging_parser]
    )
    shell_parser.add_argument(
        '-d', '--database', type=str, metavar='DATABASE',
        help="a database to run the shell on, creates a new one by default"
    )
    shell_parser.add_argument(
        '-r', '--repl', choices=['python', 'ipython', 'ptpython'],
        metavar='REPL', help="the repl to be used for the shell session"
    )

    # Parse them args
    parsed = main_parser.parse_args()
    print(parsed)
