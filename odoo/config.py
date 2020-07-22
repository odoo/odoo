# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import collections
import configparser
import contextlib
import distutils.util
import itertools
import functools
import operator
import os
import pathlib
import tempfile
import textwrap
import warnings
from collections.abc import Iterable
from getpass import getuser


try:
    from odoo import appdirs
    from odoo import release
    from odoo.loglevels import PSEUDOCONFIG_MAPPER as loglevelmap
except ImportError:
    # TODO @juc Don't merge me with that crap
    import appdirs
    import release
    from loglevels import PSEUDOCONFIG_MAPPER as loglevelmap


subcommand = None   # subcommand extracted from cli

opttypemap = {}     # map every option to a type-like function, is
                    # automatically updated for every option

envoptmap = {}      # map environment variable to option, is 
                    # automatically updated for every envvar= options

srcoptmap = {       # all configuration sources
    "cli": {},      # argparse
    "environ": {},  # os.getenv
    "file": {},     # configparser [common] section
    "default": {},  # source-hardcoded
}

DELETED = object()  # placed in the custom-config when an option is
                    # removed, used to raise a KeyError uppon access.


class DeprecatedAlias:
    def __init__(self, aliased_option):
        self.aliased_option = aliased_option
    def __repr__(self):
        return self.aliased_option


def strtobool(rawopt: str):
    """
    Convert a bool or a case-insensitive string representation of truth
    to its corresponding bool.
    
    True values are True, 'y', 'yes', 't', 'true', 'on', and '1'.
    False values are False, 'n', 'no', 'f', 'false', 'off', and '0'.

    Raises ValueError if 'rawopt' is anything else.
    """
    if type(rawopt) is bool:
        return rawopt
    return distutils.util.strtobool(rawopt)


def assert_in(rawopt, choices):
    if opt not in choices:
        raise SystemExit(f"{opt}: not a valid option, pick from %s" % ", ".join(choices))
    return opt


def flatten(it):
    """ Chain all iterables into a single one """
    for e in it:
        if type(e) != str and isinstance(e, collections.abc.Iterable):
            yield from flatten(e)
        else:
            yield e


def add(group, *args, dest, action='store', default=None, envvar=None, **kwargs):
    """
    Wrapper around add_argument, carefully map every option to a type,
    save the default value in the default source dictionnary and provide
    a new `envvar` optional kwarg-only to feed the environ source
    dictionnary.
    """
    # feed the {option: type} map
    choices = kwargs.get('choices')
    if choices:
        opttypemap[dest] = functools.partial(assert_in, choices=choices)
    else:
        switch_case = {
            'store_true': lambda: strtobool,
            'store_false': lambda: strtobool,
            'store_const': lambda: type(kwargs['const']),
            'append_const': lambda: type(kwargs['const']),
        }.get(action, lambda: kwargs['type'])
        opttypemap[dest] = switch_case()

    # feed default source 
    if action in ('store_true', 'store_false'):
        srcoptmap['default'][dest] = action == 'store_true'
    else:
        srcoptmap['default'][dest] = default

    # feed the {envvar: option} map
    if envvar:
        envoptmap[envvar] = dest

    return group.add_argument(*args, dest=dest, action=action, default=None, **kwargs)


########################################################################
#                                                                      #
#                        TYPE-LIKE FUNCTIONS                           #
#           all sanity checks and type conversions goes here           #
#                                                                      #
########################################################################


def comma(cast: callable):
    """
    Backward compatibility layer with old single argument comma-separated
    list of values. Returns a list of `cast` converted values.
    """
    return lambda rawopt: list(map(cast, rawopt.split(',')))


def fullpath(path: str):
    return pathlib.Path(path).expanduser().resolve()


def _check_file_access(rawopt: str, mode: int):
    """
    Verify `rawopt` is a `mode` accessible file, the fullpath is returned.

    `mode` is an operating-system mode bitfield. Can be os.F_OK to test
    existence, or the inclusive-OR of os.R_OK, os.W_OK, and os.X_OK.
    """
    path = fullpath(rawopt)
    if path.is_file() and not os.access(path, mode):
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = ", ".join(perm for bit, perm in pairs if bit & mode)
        raise SystemExit(f'{path}: requires {missing} permissions')
    if mode == os.W_OK and not os.access(path.parent, os.W_OK):
        raise SystemExit(f'{path.parent}: requires write permission')
    if not path.is_file():
        raise SystemExit(f'{path}: not found')
    return path


def _check_dir_access(rawopt, mode):
    """
    Verify `rawopt` is a `mode` accessible file, the fullpath is returned.

    `mode` is an operating-system mode bitfield. Can be os.F_OK to test
    existence, or the inclusive-OR of os.R_OK, os.W_OK, and os.X_OK.
    """
    mode = modes.get(mode, mode)
    path = fullpath(rawopt)
    if not path.is_dir():
        raise SystemExit(f"{path}: no such directory")
    if not os.access(path, mode):
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = "".join(perm for bit, perm in pairs if bit & mode)
        raise SystemExit(f"{path}: requires {missing} permission(s)")
    return path


def checkfile(mode: int):
    """
    Ensure the given file will be `mode` accessible.

    `mode` is an operating-system mode bitfield or single-char alias. Can
    be os.F_OK to test existence, or the inclusive-OR of os.R_OK, os.W_OK,
    and os.X_OK. Aliases are 'e': F_OK, 'r': R_OK, 'w': W_OK, 'x': X_OK.
    """
    mode = {'e': os.F_OK, 'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    return functools.partial(_check_file_access, mode=mode)


def checkdir(mode: int):
    """
    Ensure the given directory will be `mode` accessible.

    `mode` is an operating-system mode bitfield or single-char alias. Can
    be os.F_OK to test existence, or the inclusive-OR of os.R_OK, os.W_OK,
    and os.X_OK. Aliases are 'e': F_OK, 'r': R_OK, 'w': W_OK, 'x': X_OK.
    """
    mode = {'e': os.F_OK, 'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    return functools.partial(_check_dir_access, mode=mode)


def addons_path(rawopt):
    """ Ensure `rawopt` is a valid addons path, the fullpath is returned """
    path = _check_dir_access(rawopt, os.R_OK | os.X_OK)
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
    """ Ensure `rawopt` is a valid upgrade path, the fullpath is returned """
    path = _check_dir_access(rawopt, os.R_OK | os.X_OK)
    if not any(path.glob(f'*/*/{x}-*.py') for x in ["pre", "post", "end"]):
        if path.joinpath('migrations').is_dir():  # for colleagues
            raise SystemExit(f"{rawopt}: is not a valid upgrade path, looks like you forgot the migrations folder")
        raise SystemExit(f"{rawopt}: is not a valid upgrade path")
    return path


def get_default_datadir():
    if pathlib.Path('~').expanduser().is_dir():
        func = appdirs.user_data_dir
    elif sys.platform in ['win32', 'darwin']:
        func = appdirs.site_data_dir
    else:
        func = lambda **kwarg: "/var/lib/%s" % kwarg['appname'].lower()
    # No "version" kwarg as session and filestore paths are shared against series
    return fullpath(func(appname=release.product_name, appauthor=release.author))


def get_odoorc():
    if os.name == 'nt':
        return fullpath(sys.argv[0]).parent().joinpath('odoo.conf')
    return pathlib.Path.home().joinpath('.odoorc')


def data_dir(rawopt):
    datadir = _check_dir_access(rawopt, os.R_OK | os.W_OK | os.X_OK)


def ensure_data_dir(datadir):
    """
    Ensure the `datadir` is a valid data dir, the addons, sessions, and
    filestore are automatically created if missing.
    """
    ad = datadir.joinpath('addons')
    if not ad.exists():
        ad.mkdir(mode=0o700)
    elif not os.access(ad, os.R_OK | os.W_OK | os.X_OK):
        raise SystemExit(f"{ad}: requires rwx access")
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
        raise SystemExit(f"{sd}: requires rwx access")

    fd = datadir.joinpath('filestore')
    if not fd.exists():
        fd.mkdir(mode=0o700)
    elif not os.access(fd, os.R_OK | os.W_OK | os.X_OK):
        raise SystemExit(f"{fd}: requires rwx access")


def pg_utils_path(rawopt):
    """
    Ensure `rawopt` is path which contains PostgreSQL system utilities,
    the fullpath is returned.
    """
    path = _check_dir_access(rawopt, os.X_OK)
    pg_utils = {'psql', 'pg_dump', 'pg_restore'}
    if not any(file.stem in pg_utils for file in path.iterdir()):
        raise
    return path


def i18n_input_file(rawopt):
    """ Ensure `rawopt` is a valid translation file, the fullpath is returned """
    path = _check_file_access(rawopt, 'r')
    formats = {'.csv', '.po'}
    if not path.suffixes or path.suffixes[-1].lower() not in formats:
        raise SystemExit(f"{rawopt}: is not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return path


def i18n_output_file(rawopt):
    """ Ensure `rawopt` is a valid translation file, the fullpath is returned """
    path = _check_file_access(rawopt, 'w')
    formats = {'.csv', '.po', '.tgz'}
    if not path.suffixes or path.suffixes[-1].lower() not in formats:
        raise SystemExit(f"{rawopt}: is not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return path



########################################################################
#                                                                      #
#                       COMMAND LINE INTERFACE                         #
#        all option specs are extracted from the argparse parser       #
#                                                                      #
########################################################################

main_parser = argparse.ArgumentParser(description="See online documentation at: https://www.odoo.com/documentation/master/reference/ocli.html")
main_parser.add_argument('-V', '--version', action='version', version=f"{release.description} {release.version}")
subparsers = main_parser.add_subparsers(dest='subcommand')

#
# Bootstraping required options
#
add(main_parser, '--addons-path', dest='addons_path', default=[pathlib.Path(__file__).parent.joinpath('addons').resolve()], type=comma(addons_path), action="append", metavar='DIRPATH', help="specify additional addons paths")
add(main_parser, '--upgrade-path', dest='upgrade_path', default=pathlib.Path(__file__).parent.joinpath('addons', 'base', 'maintenance', 'migrations').resolve(), type=upgrade_path, metavar='DIRPATH', help="specify an additional upgrade path.")
add(main_parser, '-D', '--data-dir', dest='data_dir', type=data_dir, default=get_default_datadir(), help="Directory where to store Odoo data")
add(main_parser, '--log-level', dest='log_level', type=str, default='info', metavar="LEVEL", choices=loglevelmap.keys(), help="specify the level of the logging")
add(main_parser, '--logfile', dest='logfile', type=checkfile('w'), default=None, metavar="FILEPATH", help="file where the server log will be stored")
add(main_parser, '--syslog', dest='syslog', action='store_true', help="Send the log to the syslog server")
add(main_parser, '--log-handler', dest='log_handler', action='append', type=str, default=[':INFO'], metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')


########################################################################
#                                                                      #
#                          SERVER SUBCOMMAND                           #
#                                                                      #
########################################################################
server_parser = argparse.ArgumentParser(add_help=False)

#
# Common
#
server_common = server_parser.add_argument_group("Common")
add(server_common, '-c', '--config', dest='config', type=checkfile('r'), metavar="FILEPATH", default=get_odoorc(), help="specify alternate config file name")
add(server_common, '-s', '--save', dest='save', type=checkfile('w'), nargs='?', metavar="FILEPATH", default=None, const=get_odoorc(), help="save parsed config in PATH")
add(server_common, '-i', '--init', dest='init', type=comma(str), action='append', default=[], help='install one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d')
add(server_common, '-u', '--update', dest='update', type=comma(str), action='append', default=[], help='update one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d.')
add(server_common, '--without-demo', dest='without_demo', action='store_true', help='disable loading demo data for modules to be installed (comma-separated or repeated option, use "all" for all modules), requires -d and -i.')
#'-P', '--import-, partial'
add(server_common, '--load', dest='server_wide_modules', type=comma(str), action='append', default=['base', 'web'], metavar='MODULE', help="framework modules to load once for all databases (comma-separated or repeated option)")
add(server_common, '--pidfile', dest='pidfile', type=checkfile('w'), default=None, metavar='FILEPATH', help="file where the server pid will be stored")

#
# HTTP
#
server_http = server_parser.add_argument_group("HTTP Service Configuration")
add(server_http, '--http-interface', dest='http_interface', type=str, default='', metavar='INTERFACE', help="Listen interface address for HTTP services. Keep empty to listen on all interfaces (0.0.0.0)")
add(server_http, '-p', '--http-port', dest='http_port', type=int, default=8069, metavar='PORT', help="Listen port for the main HTTP service")
add(server_http, '--longpolling-port', dest='longpolling_port', type=int, default=8072, metavar='PORT', help="Listen port for the longpolling HTTP service")
add(server_http, '--no-http', dest='http_enable', action='store_false', help="Disable the HTTP and Longpolling services entirely")
add(server_http, '--proxy-mode', dest='proxy_mode', action='store_true', help="Activate reverse proxy WSGI wrappers (headers rewriting) Only enable this when running behind a trusted web proxy!")

#
# CRON
#
server_cron = server_parser.add_argument_group("CRON Service Configuration")
add(server_cron, '--max-cron-threads', dest='max_cron_threads', type=int, default=2, metavar='#THREAD', help="Maximum number of threads processing concurrently cron jobs.")
add(server_cron, '--limit-time-real-cron', dest='limit_time_real_cron', type=int, default=DeprecatedAlias('limit_time_real'), metavar="#SECONDS", help="Maximum allowed Real time per cron job. (default: --limit-time-real). Set to 0 for no limit.")


#
# Web
#
server_web = server_parser.add_argument_group("Web interface Configuration")
add(server_web, '--db-filter', dest='dbfilter', type=str, default='', metavar='REGEXP', help="Regular expressions for filtering available databases for Web UI. The expression can use %%d (domain) and %%h (host) placeholders.")


#
# Testing
#
server_test = server_parser.add_argument_group("Testing Configuration")
add(server_test, '--test-file', dest='test_file', type=checkfile('r'), default=None, metavar='FILEPATH', help="Launch a python test file.")
add(server_test, '--test-enable', dest='test_enable', action='store_true', help="Enable unit tests while installing or upgrading a module.")
add(server_test, '--test-tags', dest='test_tags', type=comma(str), action='append', default=[], help=textwrap.dedent("""\
    Comma-separated or repeated option list of spec to filter which tests to execute. Enable unit tests if set.
    A filter spec has the format: [-][tag][/module][:class][.method]
    The '-' specifies if we want to include or exclude tests matching this spec.
    The tag will match tags added on a class with a @tagged decorator. By default tag value is 'standard' when not
    given on include mode. '*' will match all tags. Tag will also match module name (deprecated, use /module)
    The module, class, and method will respectively match the module name, test class name and test method name.
    examples: :TestClass.test_func,/test_module,external"""))
add(server_test, '--screencasts', dest='screencasts', type=checkdir('w'), default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), metavar='DIRPATH', help="Screencasts will go in DIR/<db_name>/screencasts.")
add(server_test, '--screenshots', dest='screenshots', type=checkdir('w'), default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), metavar='DIRPATH', help="Screenshots will go in DIR/<db_name>/screenshots.")

#
# Advanced logging options
#
server_logging = server_parser.add_argument_group("Logging Configuration")
add(server_logging, '--log-request', dest='log_handler', action='append_const', const='odoo.http.rpc.request:DEBUG')
add(server_logging, '--log-response', dest='log_handler', action='append_const', const='odoo.http.rpc.response:DEBUG')
add(server_logging, '--log-web', dest='log_handler', action='append_const', const='odoo.http:DEBUG')
add(server_logging, '--log-sql', dest='log_handler', action='append_const', const='odoo.sql_db:DEBUG')
add(server_logging, '--log-db', dest='log_db', action='store_true', help="Enable database logs record")
add(server_logging, '--log-db-level', dest='log_db_level', metavar="LEVEL", default='warning', choices=loglevelmap.keys(), help="specify the level of the database logging")

#
# SMTP options
#
server_smtp = server_parser.add_argument_group("SMTP Configuration")
add(server_smtp, '--email-from', dest='email_from', type=str, default=None, metavar="EMAIL", help="specify the SMTP email address for sending email")
add(server_smtp, '--smtp', dest='smtp_server', type=str, default='localhost', metavar="HOST", help="specify the SMTP server for sending email")
add(server_smtp, '--smtp-port', dest='smtp_port', type=int, default=25, metavar="PORT", help="specify the SMTP port")
add(server_smtp, '--smtp-ssl', dest='smtp_ssl', action='store_true', help="if passed, SMTP connections will be encrypted with SSL (STARTTLS)")
add(server_smtp, '--smtp-user', dest='smtp_user', type=str, default=None, help="specify the SMTP username for sending email")
add(server_smtp, '--smtp-password', dest='smtp_password', type=str, default=None, help="specify the SMTP password for sending email")

#
# Database options
#
server_db = server_parser.add_argument_group("Database related options")
add(server_db, '-d', '--database', dest='db_name', type=str, default=None, envvar="PGDATABASE", metavar="DBNAME", help="database name to connect to")
add(server_db, '-r', '--db_user', dest='db_user', type=str, default=None, envvar="PGUSER", metavar="USERNAME", help="database user to connect as")
add(server_db, '-w', '--db_password', dest='db_password', type=str, default=None, envvar="PGPASSWORD", metavar="PWD", help='password to be used if the database demands password authentication. Using this argument is a security risk, see the "The Password File" section in the PostgreSQL documentation for alternatives.')
add(server_db, '--db_host', dest='db_host', type=str, default=None, envvar="PGHOST", metavar="HOSTNAME", help="database server host or socket directory")
add(server_db, '--db_port', dest='db_port', type=str, default=None, envvar="PGPORT", metavar="PORT", help="database server port")
add(server_db, '--db_sslmode', dest='db_sslmode', metavar="METHOD", default='prefer', choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'], help="determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server")
add(server_db, '--pg_path', dest='pg_path', type=pg_utils_path, metavar="DIRPATH", default=None, help="postgres utilities directory")
add(server_db, '--db-template', dest='db_template', type=str, metavar="DBNAME", default='template0', help="custom database template to create a new database")
add(server_db, '--db_maxconn', dest='db_maxconn', type=int, metavar="#CONN", default=64, help="specify the maximum number of physical connections to PostgreSQL")
add(server_db, '--unaccent', dest="unaccent", action='store_true', help="Try to enable the unaccent extension when creating new databases")

#
# ORM
#
server_orm = server_parser.add_argument_group("ORM")
add(server_orm, '--transient-age-limit', dest='transient_age_limit', type=float, metavar="HOUR", default=1.0, help="Time in hours records created with a TransientModel (mosly wizard) are kept in the database.")
add(server_orm, '--osv-memory-age-limit', dest='osv_memory_age_limit', type=float, default=DeprecatedAlias('transient_age_limit'), help=argparse.SUPPRESS)

#
# I18N
#
server_i18n = server_parser.add_argument_group("Internationalization")
add(server_i18n, '--load-language', dest='load_language', type=comma(str), metavar='LANGCODE', default=None, help="specifies the languages for the translations you want to be loaded")
add(server_i18n, '-l', '--language', dest='language', type=str, metavar='LANGCODE', default=None, help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
add(server_i18n, '--i18n-export', dest='translate_out', type=i18n_output_file, metavar='FILEPATH', default=None, help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit. The '-l' option is required")
add(server_i18n, '--i18n-import', dest='tranlate_in', type=i18n_input_file, metavar='FILEPATH', default=None, help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
add(server_i18n, '--i18n-overwrite', dest='overwrite_existing_translations', action='store_true', help="overwrites existing translation terms on updating a module or importing a CSV or a PO file. Use with -u/--update or --i18n-import.")
add(server_i18n, '--modules', dest="translate_modules", type=comma(str), default=None, help="specify modules to export. Use in combination with --i18n-export")

#
# Security
#
server_security = server_parser.add_argument_group("Security-related options")
add(server_security, '--no-database-list', dest='list_db', action='store_false', help="Disable the ability to obtain or view the list of databases. Also disable access to the database manager and selector, so be sure to set a proper --database parameter first.")

#
# Developers
#
server_dev = server_parser.add_argument_group("Developers")
add(server_dev, '--dev', dest='dev_mode', action='append', type=comma(str), default=[], choices=['all', 'pudb', 'wdb', 'ipdb', 'pdb', 'reload', 'qweb', 'werkzeug', 'xml'], help="Enable developer mode")
add(server_dev, '--shell-interface', dest='shell_interface', default='python', choices=['ipython', 'ptpython', 'bpython', 'python'], help="Specify a preferred REPL to use in shell mode")

#
# Misc
#
server_misc = server_parser.add_argument_group("Misc")
add(server_misc, '--stop-after-init', dest='stop_after_init', action='store_true', help="stop the server after its initialization")
add(server_misc, '--geoip-db', dest='geoip_database', type=checkfile('r'), default=pathlib.Path('/usr/share/GeoIP/GeoLite2-City.mmdb'), help="Absolute path to the GeoIP database file.")


if os.name == 'posix':
    #
    # Workers & Limits
    #
    server_multi = server_parser.add_argument_group("Multiprocessing options")
    add(server_multi, '--workers', dest='workers', type=int, metavar='#WORKER', default=0, help="Specify the number of workers, 0 disable prefork mode.")
    add(server_multi, '--limit-memory-soft', dest='limit_memory_soft', default=2048 * 1024 * 1024, metavar="BYTES", type=int, help="Maximum allowed virtual memory per worker, when reached the worker be reset after the current request (default 2048MiB).")
    add(server_multi, '--limit-memory-hard', dest='limit_memory_hard', default=2560 * 1024 * 1024, metavar="BYTES", type=int, help="Maximum allowed virtual memory per worker (in bytes), when reached, any memory allocation will fail (default 2560MiB).")
    add(server_multi, '--limit-time-cpu', dest='limit_time_cpu', default=60, metavar="SECONDS", type=int, help="Maximum allowed CPU time per request (default 60).")
    add(server_multi, '--limit-time-real', dest='limit_time_real', default=120, metavar="SECONDS", type=int, help="Maximum allowed Real time per request (default 120).")
    add(server_multi, '--limit-request', dest='limit_request', default=8192, metavar="#REQUEST", type=int, help="Maximum number of request to be processed per worker (default 8192).")


subparsers.add_parser('server', parents=[server_parser])


########################################################################
#                                                                      #
#                         POPULATE SUBCOMMAND                          #
#                                                                      #
########################################################################

populate_parser = argparse.ArgumentParser(add_help=False)
populate_conf = populate_parser.add_argument_group('Populate Configuration')
add(populate_conf, '--size', dest='population_size', type=str, default='small', choices=['small', 'medium', 'large'], help="Populate database with auto-generated data")
add(populate_conf, '--models', action='append', dest='populate_models', type=comma(str), metavar='MODEL OR PATTERN', help="List of model (comma separated or repeated option) or pattern")
subparsers.add_parser('populate', parents=[server_parser, populate_parser])



########################################################################
########################################################################
########################################################################


def load_environ(self):
    options = srcoptmap['environ']
    options.clear()
    for envvar, opt in envoptmap.items():
        val = os.getenv(envvar)
        if val:
            options[opt] = opttypemap[opt](val)


def load_cli(self):
    global subcommand
    options = srcoptmap['cli']
    options.clear()
    cli_options = vars(main_parser.parse_args())
    subcommand = cli_options.pop("subcommand", "server")
    for opt, val in cli_options.items():
        if val is None:
            continue
        # flatten lists, this is caused by action='append', type=comma(...)
        if type(val) != str and isinstance(val, Iterable):
            val = list(flatten(val))

        options[opt] = val  # already casted by argparse
        

def load_file(self):
    configpath = config['config']
    try:
        if configpath.stat().st_mode & 0o777 != 0o600:
            warnings.warn(f"{configpath}: Wrong permissions, should be user-only read/write (0600)")
        p.read([configpath])
    except (FileNotFoundError, IOError):
        warnings.warn(f"{configpath}: Could not read configuration file")
        return

    for sec in p.sections():
        options = srcoptmap['file' if sec == 'options' else 'file_' + sec]
        options.clear()
        for opt, val in p.items(sec):
                options[opt] = opttypemap[opt](val)


class Config(collections.abc.MutableMapping):
    def __init__(self, tempopts_chain=None, useropts=None, sectopts=None):
        self._tempopts_chain = ChainMap(*(tempopts_chain or []))
        self._useropts = useropts or {}
        self._sectopts = sectopts or {}
        self._chainmap = Chainmap(
            self._tempopts_chain,
            self._useropts,
            srcoptmap["cli"],
            self._sectopts,
            srcoptmap["file"],
            srcoptmap["environ"],
            srcoptmap["default"],
        )
        self.subcommand = subcommand

    def copy(self):
        return type(self)(
            [tempopts.copy() for tempopts_chain in self._tempopts_chain.maps],
            self._useropts.copy(),
            self._sectopts.copy(),
        )

    def expose_file_section(self, section):
        """
        Exposes the [`section`] of the configuration file just before
        the file [options] section.
        """
        if not section.startswith('file_'):
            section = 'file_' + section
        self._sectopts.clear()
        self._sectopts.update(srcoptmap[section])

    def save(self, configpath=None):
        """
        Export the currently exposed configuration with additionnal
        sections
        """
        p = configparser.RawConfigParser()

        # default section, export currently exposed configuration
        p.add_section('options')
        for opt, val in self.items():
            if type(val) != str and isinstance(val, collections.abc.Iterable):
                p.set('options', opt, ",".join(val))
            else:
                p.set('options', opt, str(val))

        # other sections, rewrite them as-is
        for source, options in srcoptmap.items():
            if not source.startswith('file_'):
                continue
            section = source[5:]
            p.add_section(section)
            for opt, val in options.items():
                if type(val) != str and isinstance(val, collections.abc.Iterable):
                    p.set(section, opt, ",".join(val))
                else:
                    p.set(section, opt, str(val))

        # ensure file exists and write on disk
        if configpath is None:
            configpath = chainmap["config"]
        if not configpath.exists():
            configpath.parent.mkdir(mode=0o755, parents=True)
            configpath.touch(mode=0o600)
        with configpath.open('w') as fd:
            p.write(fd)

    def pop(self, option, *default):
        val = self.get(option, default[0]) if default else self[option]
        del self[option]
        return val

    def __contains__(self, option):
        try:
            self[option]
        except KeyError:
            return False
        return True

    def __getitem__(self, option):
        val = self._chainmap[option]
        if val is DELETED:
            raise KeyError(f"{option} has been removed")
        elif type(val) is DeprecatedAlias:
            warnings.warn(
                f"The {option} is a deprecated alias to {val.aliased_option}, "
                "please use the latter. The option may be overridable via a "
                "dedication section in the configuration file.",
                DeprecationWarning)
            return self[val.aliased_option]
        return val

    def __setitem__(self, option, value):
        if type(value) is str:
            value = opttypemap[option](value)
        self._useropts[option] = value

    def __delitem__(self, option):
        self._useropts[option] = DELETED

    def __iter__(self):
        return iter(self._chainmap)

    def __len__(self):
        return len(self._chainmap)

    def __enter__(self, tempopts=None):
        if tempopts is None:
            tempopts = {}

        self._tempopts_chain.maps.insert(0, tempopts)
        return tempopts

    def __exit__ (self, type, value, tb):
        del self._tempopts_chain.maps[0]


config = Config()
