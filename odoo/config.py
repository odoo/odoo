# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import collections
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


opttypemap = {}     # map every option to a type-like function, is
                    # automatically updated for every option

envoptmap = {}      # map environment variable to option, is 
                    # automatically updated for every envvar= options

ctxopt_stack = []   # stack of temporary user-defined sources controlled
                    # by a context manager, are injected as 1st sources.

srcoptmap = {       # all configuration sources
    "custom": {},   # user-defined
    "cli": {},      # argparse
    "environ": {},  # os.getenv
    "file": {},     # configparser [common] section
    "default": {},  # source-hardcoded
}

chainmap = collections.ChainMap(  # exposition order, top first
    # temporary sources are placed here, see __enter__ and __exit__
    srcoptmap["custom"],
    srcoptmap["cli"],
    # additionnal config file sections are placed here, see expose_file_section
    srcoptmap["file"],
    srcoptmap["environ"],
    srcoptmap["default"],
)

DELETED = object()  # placed in the custom-config when an option is
                    # removed, used to raise a KeyError uppon access.


class Alias:
    def __init__(self, alias):
        self.aliased_option = alias
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


def add(*args, dest, action='store', default=None, envvar=None, **kwargs):
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

    return add.wrapped(*args, dest=dest, action=action, default=None, **kwargs)


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
    elif os.access(ad, os.R_OK | os.W_OK | os.X_OK):
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


def osv_memory_age_limit(rawopt):
    msg = ("The osv-memory-age-limit is a deprecated alias to "
           "the transient-age-limit option, please use the latter")
    warnings.warn(msg, DeprecationWarning)
    return float(rawopt)


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
#                                                                      #
########################################################################

main_parser = argparse.ArgumentParser(description=textwrap.dedent("""\
    Odoo Command-Line Interface

    See online documentation at: 
    https://www.odoo.com/documentation/master/reference/ocli.html
    """))
subparsers = main_parser.add_subparsers()

#
# Common, bootstraping required options
#
common_parser = argparse.ArgumentParser()
add.wrapped = main_parser.add_argument
main_parser.add_argument('-V', '--version', action='version', version=f"{release.description} {release.version}")
add('--addons-path', dest='addons_path', default=[pathlib.Path(__file__).parent.joinpath('addons').resolve()], type=comma(addons_path), action="append", metavar='DIRPATH', help="specify additional addons paths")
add('--upgrade-path', dest='upgrade_path', default=pathlib.Path(__file__).parent.joinpath('addons', 'base', 'maintenance', 'migrations').resolve(), type=upgrade_path, metavar='DIRPATH', help="specify an additional upgrade path.")
add('-D', '--data-dir', dest='data_dir', type=data_dir, default=get_default_datadir(), help="Directory where to store Odoo data")
add('--log-level', dest='log_level', type=str, default='info', metavar="LEVEL", choices=loglevelmap.keys(), help="specify the level of the logging")
add('--logfile', dest='logfile', type=checkfile('w'), default=None, metavar="FILEPATH", help="file where the server log will be stored")
add('--syslog', dest='syslog', action='store_true', help="Send the log to the syslog server")
add('--log-handler', dest='log_handler', action='append', type=str, default=[':INFO'], metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')


########################################################################
#                                                                      #
#                          SERVER SUBCOMMAND                           #
#                                                                      #
########################################################################
server_parser = subparsers.add_parser('server')

#
# Common
#
add.wrapped = server_parser.add_argument_group("Common").add_argument
add('-c', '--config', dest='config', type=checkfile('r'), metavar="FILEPATH", default=get_odoorc(), help="specify alternate config file name")
add('-s', '--save', dest='save', type=checkfile('w'), nargs='?', metavar="FILEPATH", default=None, const=get_odoorc(), help="save parsed config in PATH")
add('-i', '--init', dest='init', type=comma(str), action='append', default=[], help='install one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d')
add('-u', '--update', dest='update', type=comma(str), action='append', default=[], help='update one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d.')
add('--without-demo', dest='without_demo', action='store_true', help='disable loading demo data for modules to be installed (comma-separated or repeated option, use "all" for all modules), requires -d and -i.')
#'-P', '--import-partial'
add('--load', dest='server_wide_modules', type=comma(str), action='append', default=['base', 'web'], metavar='MODULE', help="framework modules to load once for all databases (comma-separated or repeated option)")
add('--pidfile', dest='pidfile', type=checkfile('w'), default=None, metavar='FILEPATH', help="file where the server pid will be stored")

#
# HTTP
#
add.wrapped = server_parser.add_argument_group("HTTP Service Configuration").add_argument
add('--http-interface', dest='http_interface', type=str, default='', metavar='INTERFACE', help="Listen interface address for HTTP services. Keep empty to listen on all interfaces (0.0.0.0)")
add('-p', '--http-port', dest='http_port', type=int, default=8069, metavar='PORT', help="Listen port for the main HTTP service")
add('--longpolling-port', dest='longpolling_port', type=int, default=8072, metavar='PORT', help="Listen port for the longpolling HTTP service")
add('--no-http', dest='http_enable', action='store_false', help="Disable the HTTP and Longpolling services entirely")
add('--proxy-mode', dest='proxy_mode', action='store_true', help="Activate reverse proxy WSGI wrappers (headers rewriting) Only enable this when running behind a trusted web proxy!")

#
# CRON
#
add.wrapped = server_parser.add_argument_group("CRON Service Configuration").add_argument
add('--max-cron-threads', dest='max_cron_threads', type=int, default=2, metavar='#THREAD', help="Maximum number of threads processing concurrently cron jobs.")
add('--limit-time-real-cron', dest='limit_time_real_cron', type=int, default=Alias('limit_time_real'), metavar="#SECONDS", help="Maximum allowed Real time per cron job. (default: --limit-time-real). Set to 0 for no limit.")


#
# Web
#
add.wrapped = server_parser.add_argument_group("Web interface Configuration").add_argument
add('--db-filter', dest='dbfilter', type=str, default='', metavar='REGEXP', help="Regular expressions for filtering available databases for Web UI. The expression can use %d (domain) and %h (host) placeholders.")


#
# Testing
#
add.wrapped = server_parser.add_argument_group("Testing Configuration").add_argument
add('--test-file', dest='test_file', type=checkfile('r'), default=None, metavar='FILEPATH', help="Launch a python test file.")
add('--test-enable', dest='test_enable', action='store_true', help="Enable unit tests while installing or upgrading a module.")
add('--test-tags', dest='test_tags', type=comma(str), action='append', default=[], help=textwrap.dedent("""\
    Comma-separated or repeated option list of spec to filter which tests to execute. Enable unit tests if set.
    A filter spec has the format: [-][tag][/module][:class][.method]
    The '-' specifies if we want to include or exclude tests matching this spec.
    The tag will match tags added on a class with a @tagged decorator. By default tag value is 'standard' when not
    given on include mode. '*' will match all tags. Tag will also match module name (deprecated, use /module)
    The module, class, and method will respectively match the module name, test class name and test method name.
    examples: :TestClass.test_func,/test_module,external"""))
add('--screencasts', dest='screencasts', type=checkdir('w'), default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), metavar='DIRPATH', help="Screencasts will go in DIR/<db_name>/screencasts.")
add('--screenshots', dest='screenshots', type=checkdir('w'), default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), metavar='DIRPATH', help="Screenshots will go in DIR/<db_name>/screenshots.")

#
# Advanced logging options
#
add.wrapped = server_parser.add_argument_group("Logging Configuration").add_argument
add('--log-request', dest='log_handler', action='append_const', const='odoo.http.rpc.request:DEBUG')
add('--log-response', dest='log_handler', action='append_const', const='odoo.http.rpc.response:DEBUG')
add('--log-web', dest='log_handler', action='append_const', const='odoo.http:DEBUG')
add('--log-sql', dest='log_handler', action='append_const', const='odoo.sql_db:DEBUG')
add('--log-db', dest='log_db', action='store_true', help="Enable database logs record")
add('--log-db-level', dest='log_db_level', metavar="LEVEL", default='warning', choices=loglevelmap.keys(), help="specify the level of the database logging")

#
# SMTP options
#
add.wrapped = server_parser.add_argument_group("SMTP Configuration").add_argument
add('--email-from', dest='email_from', type=str, default=None, metavar="EMAIL", help="specify the SMTP email address for sending email")
add('--smtp', dest='smtp_server', type=str, default='localhost', metavar="HOST", help="specify the SMTP server for sending email")
add('--smtp-port', dest='smtp_port', type=int, default=25, metavar="PORT", help="specify the SMTP port")
add('--smtp-ssl', dest='smtp_ssl', action='store_true', help="if passed, SMTP connections will be encrypted with SSL (STARTTLS)")
add('--smtp-user', dest='smtp_user', type=str, default=None, help="specify the SMTP username for sending email")
add('--smtp-password', dest='smtp_password', type=str, default=None, help="specify the SMTP password for sending email")

#
# Database options
#
add.wrapped = server_parser.add_argument_group("Database related options").add_argument
add('-d', '--database', dest='db_name', type=str, default=getuser(), envvar="PGDATABASE", metavar="DBNAME", help="database name to connect to")
add('-r', '--db_user', dest='db_user', type=str, default=getuser(), envvar="PGUSER", metavar="USERNAME", help="database user to connect as")
add('-w', '--db_password', dest='db_password', type=str, default=None, envvar="PGPASSWORD", metavar="PWD", help='password to be used if the database demands password authentication. Using this argument is a security risk, see the "The Password File" section in the PostgreSQL documentation for alternatives.')
add('--db_host', dest='db_host', type=str, default=None, envvar="PGHOST", metavar="HOSTNAME", help="database server host or socket directory")
add('--db_port', dest='db_port', type=str, default=None, envvar="PGPORT", metavar="PORT", help="database server port")
add('--db_sslmode', dest='db_sslmode', metavar="METHOD", default='prefer', choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'], help="determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server")
add('--pg_path', dest='pg_path', type=pg_utils_path, metavar="DIRPATH", default=None, help="postgres utilities directory")
add('--db-template', dest='db_template', type=str, metavar="DBNAME", default='template0', help="custom database template to create a new database")
add('--db_maxconn', dest='db_maxconn', type=int, metavar="#CONN", default=64, help="specify the maximum number of physical connections to PostgreSQL")
add('--unaccent', dest="unaccent", action='store_true', help="Try to enable the unaccent extension when creating new databases")

#
# ORM
#
add.wrapped = server_parser.add_argument_group("ORM").add_argument
add('--transient-age-limit', dest='transient_age_limit', type=float, metavar="HOUR", default=1.0, help="Time in hours records created with a TransientModel (mosly wizard) are kept in the database.")
add('--osv-memory-age-limit', dest='transient_age_limit', type=osv_memory_age_limit, help=argparse.SUPPRESS)

#
# I18N
#
add.wrapped = server_parser.add_argument_group("Internationalization").add_argument
add('--load-language', dest='load_language', type=comma(str), metavar='LANGCODE', default=None, help="specifies the languages for the translations you want to be loaded")
add('-l', '--language', dest='language', type=str, metavar='LANGCODE', default=None, help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
add('--i18n-export', dest='translate_out', type=i18n_output_file, metavar='FILEPATH', default=None, help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit. The '-l' option is required")
add('--i18n-import', dest='tranlate_in', type=i18n_input_file, metavar='FILEPATH', default=None, help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
add('--i18n-overwrite', dest='overwrite_existing_translations', action='store_true', help="overwrites existing translation terms on updating a module or importing a CSV or a PO file. Use with -u/--update or --i18n-import.")
add('--modules', dest="translate_modules", type=comma(str), default=None, help="specify modules to export. Use in combination with --i18n-export")

#
# Security
#
add.wrapped = server_parser.add_argument_group("Security-related options").add_argument
add('--no-database-list', dest='list_db', action='store_false', help="Disable the ability to obtain or view the list of databases. Also disable access to the database manager and selector, so be sure to set a proper --database parameter first.")

#
# Developers
#
add.wrapped = server_parser.add_argument_group("Developers").add_argument
add('--dev', dest='dev_mode', action='append', type=comma(str), default=[], choices=['all', 'pudb', 'wdb', 'ipdb', 'pdb', 'reload', 'qweb', 'werkzeug', 'xml'], help="Enable developer mode")
add('--shell-interface', dest='shell_interface', default='python', choices=['ipython', 'ptpython', 'bpython', 'python'], help="Specify a preferred REPL to use in shell mode")

#
# Misc
#
add.wrapped = server_parser.add_argument_group("Misc").add_argument
add('--stop-after-init', dest='stop_after_init', action='store_true', help="stop the server after its initialization")
add('--geoip-db', dest='geoip_database', type=checkfile('r'), default=pathlib.Path('/usr/share/GeoIP/GeoLite2-City.mmdb'), help="Absolute path to the GeoIP database file.")


if os.name == 'posix':
    #
    # Workers
    #
    add.wrapped = server_parser.add_argument_group("Multiprocessing options").add_argument
    add('--workers', dest='workers', type=int, metavar='#WORKER', default=0, help="Specify the number of workers, 0 disable prefork mode.")

    #
    # Limits
    #
    add('--limit-memory-soft', dest='limit_memory_soft', default=2048 * 1024 * 1024, metavar="BYTES", type=int, help="Maximum allowed virtual memory per worker, when reached the worker be reset after the current request (default 2048MiB).")
    add('--limit-memory-hard', dest='limit_memory_hard', default=2560 * 1024 * 1024, metavar="BYTES", type=int, help="Maximum allowed virtual memory per worker (in bytes), when reached, any memory allocation will fail (default 2560MiB).")
    add('--limit-time-cpu', dest='limit_time_cpu', default=60, metavar="SECONDS", type=int, help="Maximum allowed CPU time per request (default 60).")
    add('--limit-time-real', dest='limit_time_real', default=120, metavar="SECONDS", type=int, help="Maximum allowed Real time per request (default 120).")
    add('--limit-request', dest='limit_request', default=8192, metavar="#REQUEST", type=int, help="Maximum number of request to be processed per worker (default 8192).")


from pprint import pprint
options = main_parser.parse_args()
for opt, val in vars(options).items():
    if val is None:
        continue

    while (type(val) in (list, tuple)
           and any(type(elem) in (list, tuple) for elem in val)):
        val = list(itertools.chain.from_iterable(val))

    srcoptmap['cli'][opt] = val

pprint(chainmap)
exit()


class configmanager(collections.abc.MutableMapping):
    def parse_load(self, configpath=None):
        # clear all previously loaded options
        for source, options in srcoptmap.items():
            if source != 'default':
                options.clear()

        # reload environment
        for envvar, opt in envoptmap.items():
            val = os.getenv(envvar)
            if val:
                srcoptmap['environ'][opt] = val

        # reload command line
        options = main_parser.parse_args()
        for opt, val in vars(cli_options).items():
            if val is None:
                continue

            while (type(val) in (list, tuple)
                   and any(type(elem) in (list, tuple) for elem in val)):
                val = list(itertools.chain.from_iterable(val))

            srcoptmap['cli'][opt] = val

        # reload configuration file
        for section, options in parse_file(configpath or chainmap['config']):
            srcoptmap[section].update(options)

        # post processing
        ensure_data_dir(chainmap['data_dir'])

    def expose_file_section(self, section):
        """
        Exposes the [`section`] of the configuration file just before
        the [common] options.
        """
        if not section.startswith('file_'):
            section = 'file_' + section

        source = srcoptmap[section]
        if source not in chainmap.maps:
            file_index = chainmap.maps.index('file')
            chainmap.maps.insert(source, file_index)


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
        elif type(val) is Alias:
            return self[val.aliased_option]
        return val

    def __setitem__(self, option, value):
        srcoptmap["custom"][option] = opttypemap[option](value)

    def __delitem__(self, option):
        srcoptmap["custom"] = DELETED

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
        ctxopts_stack.pop()
        del chainmap.maps[0]

config = configmanager()  # singleton
