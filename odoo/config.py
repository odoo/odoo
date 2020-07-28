# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import collections
import configparser
import contextlib
import dataclasses
import distutils.util
import itertools
import functools
import operator
import os
import pathlib
import tempfile
import textwrap
import warnings
import sys
from collections.abc import Iterable
from getpass import getuser
from typing import Any, Callable, Optional, List

from odoo import appdirs
from odoo import release
from odoo.loglevels import PSEUDOCONFIG_MAPPER as loglevelmap


optionmap = {}      # option name to option object map
groupmap = {}       # group title to group object map
commandmap = {}     # subcommand name to command object map

sourcemap = {       # all configuration sources
    'cli': {},      # argparse
    'environ': {},  # os.getenv
    'file': {},     # configparser [common] section
    'default': {},  # source-hardcoded
    'readonly': {}, # non-configurable options
}

DELETED = object()  # placed in the user-config when an option is
                    # removed, used to raise a KeyError uppon access.


def die(message):
    raise SystemExit(f'Error: {message}\nCould not load configuration. Aborting.')


class DeprecatedAlias:
    def __init__(self, aliased_option):
        self.aliased_option = aliased_option
    def __repr__(self):
        return self.aliased_option


########################################################################
#                                                                      #
#                        TYPE-LIKE FUNCTIONS                           #
#           all sanity checks and type conversions goes here           #
#                                                                      #
########################################################################


class CommaSeparated(collections.UserList):
    def __init__(self, iterable=None):
        self.data = list(iterable) if iterable else []
        self.comma = ','.join(map(str, self.data))

    def __getattr__(self, key):
        """ Backward compatibility layer for old string format"""
        attr = getattr(self.comma, key, None)
        if attr is not None:
            warnings.warn(
                "The option should now be used as a list.",
                DeprecationWarning, stacklevel=2)
            return attr
        raise AttributeError(f"type object {super(self).__name__} has no attribute '{key}'")

    def __repr__(self):
        return type(self).__name__ + repr(self.data)

    @classmethod
    def merge(cls, oldcommas):
        new = cls()
        for oc in oldcommas:
            new.extend(oc)
        return new

    @classmethod
    def parser(cls, cast: callable):
        """
        Backward compatibility layer with old single argument comma-separated
        list of values. Returns a list of `cast` converted values.
        """
        return lambda rawopt: cls(map(cast, rawopt.split(',')))

    @staticmethod
    def formatter(rcast: callable):
        return lambda comma_separated: ",".join(map(rcast, comma_separated))


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


def choices(selection: list, cast: callable=str):
    def assert_in(rawopt):
        opt = cast(rawopt)
        if opt not in choices:
            die(f"{opt}, not a valid option, pick from %s" % ", ".join(choices))
        return opt
    return assert_in


def flatten(it):
    """ Chain all iterables into a single one """
    for e in it:
        if isinstance(e, CommaSeparated):
            yield e
        elif type(e) != str and isinstance(e, collections.abc.Iterable):
            yield from flatten(e)
        else:
            yield e


def fullpath(path: str):
    return pathlib.Path(path).expanduser().resolve().absolute()


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
        die(f'{path}, file requires {missing} permissions')
    if mode == os.W_OK and not os.access(path.parent, os.W_OK):
        die(f'{path.parent}, file requires write permission')
    if not path.is_file():
        die(f'{path}, no such file')
    return path


def _check_dir_access(rawopt, mode):
    """
    Verify `rawopt` is a `mode` accessible file, the fullpath is returned.

    `mode` is an operating-system mode bitfield. Can be os.F_OK to test
    existence, or the inclusive-OR of os.R_OK, os.W_OK, and os.X_OK.
    """
    path = fullpath(rawopt)
    if not path.is_dir():
        die(f"{path}, no such directory")
    if not os.access(path, mode):
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = "".join(perm for bit, perm in pairs if bit & mode)
        die(f"{path}, directory requires {missing} permission(s)")
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
            die(f'{rawopt}, not a valid addons path')
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
            die(f"{rawopt}, is not a valid upgrade path, looks like you forgot the migrations folder")
        die(f"{rawopt}, is not a valid upgrade path")
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
        die(f"{ad}, requires rwx access")
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
        die(f"{sd}, requires rwx access")

    fd = datadir.joinpath('filestore')
    if not fd.exists():
        fd.mkdir(mode=0o700)
    elif not os.access(fd, os.R_OK | os.W_OK | os.X_OK):
        die(f"{fd}, requires rwx access")


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
        die(f"{rawopt}, is not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return path


def i18n_output_file(rawopt):
    """ Ensure `rawopt` is a valid translation file, the fullpath is returned """
    path = _check_file_access(rawopt, 'w')
    formats = {'.csv', '.po', '.tgz'}
    if not path.suffixes or path.suffixes[-1].lower() not in formats:
        die(f"{rawopt}, is not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return path



########################################################################
#                                                                      #
#                               OPTIONS                                #
#                                                                      #
########################################################################

@dataclasses.dataclass(frozen=True)
class Option:
    name: str                            # python-side option name
    type : Callable[[str], Any]          # source -> python converting function
    rtype : Callable[[Any], str] = str   # python -> config file converting function

    default: Any = None                  # default, last-resort, option value
    file: bool = True                    # should the option be read from/save to the config file
    cli: bool = True                     # should the option be read from the cli
    envvar: Optional[str] = None         # environment variable to load the option from

    shortopt: Optional[str] = None       # argparse's -o
    longopt: Optional[str] = None        # argparse's --option
    action: str = "store"                # argparse's action
    metavar: Optional[str] = None        # argparse's metavar
    const: Any = None                    # argparse's const
    nargs: Optional[int] = None          # argparse's nargs
    help: Optional[str] = None           # argparse's help

    def __post_init__(self):
        optionmap.setdefault(self.name, self)

Option('addons_path', longopt="--addons-path", type=CommaSeparated.parser(addons_path), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated([pathlib.Path(__file__).parent.joinpath('addons').resolve()]), envvar=None, metavar="DIRPATH", help="specify additional addons paths")
Option('upgrade_path', longopt="--upgrade-path", type=CommaSeparated.parser(upgrade_path), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, metavar="DIRPATH", help="specify an additional upgrade path.")
Option('data_dir', shortopt="-D", longopt="--data-dir", type=data_dir, rtype=str, action='store', default=get_default_datadir(), envvar=None, metavar=None, help="Directory where to store Odoo data")
Option('log_level', longopt="--log-level", type=choices(loglevelmap.keys()), rtype=str, action='store', default='info', envvar=None, metavar="LEVEL", help="specify the level of the logging")
Option('logfile', longopt="--logfile", type=checkfile('w'), rtype=str, action='store', default=None, envvar=None, metavar="FILEPATH", help="file where the server log will be stored")
Option('syslog', longopt="--syslog", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, metavar=None, help="Send the log to the syslog server")
Option('log_handler', longopt="--log-handler", type=str, rtype=str, action='append', default=[':INFO'], envvar=None, metavar=None, help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')
Option('config', shortopt="-c", longopt="--config", type=checkfile('r'), rtype=str, action='store', default=get_odoorc(), envvar=None, metavar="FILEPATH", file=False, help="specify alternate config file name")
Option('save', shortopt="-s", longopt="--save", type=checkfile('w'), rtype=str, action='store', nargs='?', default=None, const=get_odoorc(), envvar=None, file=False, metavar="FILEPATH", help="save parsed config in PATH")

Option('init', shortopt="-i", longopt="--init", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, file=False, metavar=None, help='install one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d')
Option('update', shortopt="-u", longopt="--update", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, file=False, metavar=None, help='update one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d.')
Option('without_demo', longopt="--without-demo", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, metavar=None, help='disable loading demo data for modules to be installed (comma-separated or repeated option, use "all" for all modules), requires -d and -i.')
Option('server_wide_modules', longopt="--load", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(['base','web']), envvar=None, metavar="MODULE", help="framework modules to load once for all databases (comma-separated or repeated option)")
Option('pidfile', longopt="--pidfile", type=checkfile('w'), rtype=str, action='store', default=None, envvar=None, metavar="FILEPATH", help="file where the server pid will be stored")

Option('http_interface', longopt="--http-interface", type=str, rtype=str, action='store', default='', envvar=None, metavar="INTERFACE", help="Listen interface address for HTTP services. Keep empty to listen on all interfaces (0.0.0.0)")
Option('http_port', shortopt="-p", longopt="--http-port", type=int, rtype=str, action='store', default=8069, envvar=None, metavar="PORT", help="Listen port for the main HTTP service")
Option('longpolling_port', longopt="--longpolling-port", type=int, rtype=str, action='store', default=8072, envvar=None, metavar="PORT", help="Listen port for the longpolling HTTP service")
Option('http_enable', longopt="--no-http", type=str, rtype=str, action='store_false', default=None, envvar=None, metavar=None, help="Disable the HTTP and Longpolling services entirely")
Option('proxy_mode', longopt="--proxy-mode", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, metavar=None, help="Activate reverse proxy WSGI wrappers (headers rewriting) Only enable this when running behind a trusted web proxy!")

Option('max_cron_threads', longopt="--max-cron-threads", type=int, rtype=str, action='store', default=2, envvar=None, metavar=None, help="Maximum number of threads processing concurrently cron jobs.")
Option('limit_time_real_cron', longopt="--limit-time-real-cron", type=int, rtype=str, action='store', default=DeprecatedAlias('limit_time_real'), envvar=None, metavar=None, help="Maximum allowed Real time per cron job. (default: --limit-time-real). Set to 0 for no limit.")

Option('dbfilter', longopt="--db-filter", type=str, rtype=str, action='store', default='', envvar=None, metavar="REGEXP", help="Regular expressions for filtering available databases for Web UI. The expression can use %%d (domain) and %%h (host) placeholders.")

Option('test_file', longopt="--test-file", type=checkfile('r'), rtype=str, action='store', default=None, envvar=None, metavar="FILEPATH", help="Launch a python test file.")
Option('test_enable', longopt="--test-enable", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, metavar=None, help="Enable unit tests while installing or upgrading a module.")
Option('test_tags', longopt="--test-tags", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, metavar=None, help=textwrap.dedent("""\
    Comma-separated or repeated option list of spec to filter which tests to execute. Enable unit tests if set.
    A filter spec has the format: [-][tag][/module][:class][.method]
    The '-' specifies if we want to include or exclude tests matching this spec.
    The tag will match tags added on a class with a @tagged decorator. By default tag value is 'standard' when not
    given on include mode. '*' will match all tags. Tag will also match module name (deprecated, use /module)
    The module, class, and method will respectively match the module name, test class name and test method name.
    examples: :TestClass.test_func,/test_module,external"""))
Option('screencasts', longopt="--screencasts", type=checkdir('w'), rtype=str, action='store', default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), envvar=None, metavar="DIRPATH", help="Screencasts will go in DIR/<db_name>/screencasts.")
Option('screenshots', longopt="--screenshots", type=checkdir('w'), rtype=str, action='store', default=fullpath(tempfile.gettempdir()).joinpath('odoo_tests'), envvar=None, metavar="DIRPATH", help="Screenshots will go in DIR/<db_name>/screenshots.")

_loghandlers = [
    Option('log_handler', longopt="--log-request", type=str, rtype=str, action='append_const', const='odoo.http.rpc.request:DEBUG', default=None, envvar=None, metavar=None, help="shortcut for --log-handler=odoo.http.rpc.request:DEBUG"),
    Option('log_handler', longopt="--log-response", type=str, rtype=str, action='append_const', const='odoo.http.rpc.response:DEBUG', default=None, envvar=None, metavar=None, help="shortcut for --log-handler=odoo.http.rpc.response:DEBUG"),
    Option('log_handler', longopt="--log-web", type=str, rtype=str, action='append_const', const='odoo.http:DEBUG', default=None, envvar=None, metavar=None, help="shortcut for --log-handler=odoo.http:DEBUG"),
    Option('log_handler', longopt="--log-sql", type=str, rtype=str, action='append_const', const='odoo.sql_db:DEBUG', default=None, envvar=None, metavar=None, help="shortcut for --log-handler=odoo.sql_db:DEBUG"),
]
Option('log_db', longopt="--log-db", type=str, rtype=strtobool, action='store_true', default=None, envvar=None, metavar=None, help="Enable database logs record")
Option('log_db_level', longopt="--log-db-level", type=choices(loglevelmap.keys()), rtype=str, action='store', default='warning', envvar=None, metavar="LEVEL", help="specify the level of the database logging")

Option('email_from', longopt="--email-from", type=str, rtype=str, action='store', default=None, envvar=None, metavar="EMAIL", help="specify the SMTP email address for sending email")
Option('smtp_server', longopt="--smtp", type=str, rtype=str, action='store', default='localhost', envvar=None, metavar="HOST", help="specify the SMTP server for sending email")
Option('smtp_port', longopt="--smtp-port", type=int, rtype=str, action='store', default=25, envvar=None, metavar="PORT", help="specify the SMTP port")
Option('smtp_ssl', longopt="--smtp-ssl", type=str, rtype=strtobool, action='store_true', default=None, envvar=None, metavar=None, help="if passed, SMTP connections will be encrypted with SSL (STARTTLS)")
Option('smtp_user', longopt="--smtp-user", type=str, rtype=str, action='store', default=None, envvar=None, metavar=None, help="specify the SMTP username for sending email")
Option('smtp_password', longopt="--smtp-password", type=str, rtype=str, action='store', default=None, envvar=None, metavar=None, help="specify the SMTP password for sending email")

Option('db_name', shortopt="-d", longopt="--database", type=str, rtype=str, action='store', default=None, envvar='PGDATABASE', metavar="DBNAME", help="database name to connect to")
Option('db_user', shortopt="-r", longopt="--db_user", type=str, rtype=str, action='store', default=None, envvar='PGUSER', metavar="USERNAME", help="database user to connect as")
Option('db_password', shortopt="-w", longopt="--db_password", type=str, rtype=str, action='store', default=None, envvar='PGPASSWORD', metavar="PWD", help='password to be used if the database demands password authentication. Using this argument is a security risk, see the "The Password File" section in the PostgreSQL documentation for alternatives.')
Option('db_host', longopt="--db_host", type=str, rtype=str, action='store', default=None, envvar='PGHOST', metavar="HOSTNAME", help="database server host or socket directory")
Option('db_port', longopt="--db_port", type=str, rtype=str, action='store', default=None, envvar='PGPORT', metavar="PORT", help="database server port")
Option('db_sslmode', longopt="--db_sslmode", type=str, rtype=str, action='store', default='prefer', envvar=None, metavar="METHOD", help="determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server")
Option('pg_path', longopt="--pg_path", type=pg_utils_path, rtype=str, action='store', default=None, envvar=None, metavar="DIRPATH", help="postgres utilities directory")
Option('db_template', longopt="--db-template", type=str, rtype=str, action='store', default='template0', envvar=None, metavar="DBNAME", help="custom database template to create a new database")
Option('db_maxconn', longopt="--db_maxconn", type=int, rtype=str, action='store', default=64, envvar=None, metavar=None, help="specify the maximum number of physical connections to PostgreSQL")
Option('unaccent', longopt="--unaccent", type=str, rtype=strtobool, action='store_true', default=None, envvar=None, metavar=None, help="Try to enable the unaccent extension when creating new databases")

Option('transient_age_limit', longopt="--transient-age-limit", type=float, rtype=str, action='store', default=1.0, envvar=None, metavar="HOURS", help="Time in hours records created with a TransientModel (mosly wizard) are kept in the database.")
Option('osv_memory_age_limit', longopt="--osv-memory-age-limit", type=float, rtype=str, action='store', default=DeprecatedAlias('transient_age_limit'), envvar=None, metavar=None, help=argparse.SUPPRESS)

Option('load_language', longopt="--load-language", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='store', default=CommaSeparated(), envvar=None, file=False, metavar="LANGCODE", help="specifies the languages for the translations you want to be loaded")
Option('language', shortopt="-l", longopt="--language", type=str, rtype=str, action='store', default=None, envvar=None, metavar="LANGCODE", help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
Option('translate_out', longopt="--i18n-export", type=i18n_output_file, rtype=str, action='store', default=None, envvar=None, metavar="FILEPATH", help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit. The '-l' option is required")
Option('translate_in', longopt="--i18n-import", type=i18n_input_file, rtype=str, action='store', default=None, envvar=None, metavar="FILEPATH", help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
Option('overwrite_existing_translations', longopt="--i18n-overwrite", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, metavar=None, help="overwrites existing translation terms on updating a module or importing a CSV or a PO file. Use with -u/--update or --i18n-import.")
Option('translate_modules', longopt="--modules", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='store', default=CommaSeparated(), envvar=None, metavar=None, help="specify modules to export. Use in combination with --i18n-export")

Option('list_db', longopt="--no-database-list", type=str, rtype=str, action='store_false', default=None, envvar=None, metavar=None, help="Disable the ability to obtain or view the list of databases. Also disable access to the database manager and selector, so be sure to set a proper --database parameter first.")

Option('dev_mode', longopt="--dev", type=CommaSeparated.parser(choices(['all', 'pudb', 'wdb', 'ipdb', 'pdb', 'reload', 'qweb', 'werkzeug', 'xml'])), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, file=False, metavar=None, help="Enable developer mode")
Option('shell_interface', longopt="--shell-interface", type=str, rtype=str, action='store', default='python', envvar=None, file=False, metavar=None, help="Specify a preferred REPL to use in shell mode")
Option('stop_after_init', longopt="--stop-after-init", type=strtobool, rtype=str, action='store_true', default=None, envvar=None, file=False, metavar=None, help="stop the server after its initialization")
Option('geoip_database', longopt="--geoip-db", type=checkfile('r'), rtype=str, action='store', default=pathlib.Path('/usr/share/GeoIP/GeoLite2-City.mmdb'), envvar=None, metavar=None, help="Absolute path to the GeoIP database file.")

Option('workers', longopt="--workers", type=int, rtype=str, action='store', default=0, envvar=None, metavar=None, help="Specify the number of workers, 0 disable prefork mode.")
Option('limit_memory_soft', longopt="--limit-memory-soft", type=int, rtype=str, action='store', default=2048*1024*1024, envvar=None, metavar="BYTES", help="Maximum allowed virtual memory per worker, when reached the worker be reset after the current request (default 2048MiB).")
Option('limit_memory_hard', longopt="--limit-memory-hard", type=int, rtype=str, action='store', default=2560*1024*1024, envvar=None, metavar="BYTES", help="Maximum allowed virtual memory per worker (in bytes), when reached, any memory allocation will fail (default 2560MiB).")
Option('limit_time_cpu', longopt="--limit-time-cpu", type=int, rtype=str, action='store', default=60, envvar=None, metavar="SECONDS", help="Maximum allowed CPU time per request (default 60).")
Option('limit_time_real', longopt="--limit-time-real", type=int, rtype=str, action='store', default=120, envvar=None, metavar="SECONDS", help="Maximum allowed Real time per request (default 120).")
Option('limit_request', longopt="--limit-request", type=int, rtype=str, action='store', default=8192, envvar=None, metavar=None, help="Maximum number of request to be processed per worker (default 8192).")

Option('admin_passwd', cli=False, type=str, default='admin')
Option('csv_internal_sep', cli=False, type=str, default=',')
Option('publisher_warranty_url', cli=False, file=False, type=str, default='http://services.openerp.com/publisher-warranty/')
Option('reportgz', cli=False, type=strtobool, default=False)
Option('root_path', cli=False, file=False, type=checkdir(os.R_OK), default=fullpath(pathlib.Path(__file__)).parent)

Option('population_size', longopt="--size", type=str, rtype=str, action='store', default='small', envvar=None, metavar=None, help="Populate database with auto-generated data")
Option('populate_models', longopt="--models", type=CommaSeparated.parser(str), rtype=CommaSeparated.formatter(str), action='append', default=CommaSeparated(), envvar=None, metavar="MODEL OR PATTERN", help="List of model (comma separated or repeated option) or pattern")


########################################################################
#                                                                      #
#                                GROUPS                                #
#                                                                      #
########################################################################

@dataclasses.dataclass(frozen=True)
class Group:
    title: str
    options: List[Option]

    def __post_init__(self):
        groupmap[self.title] = self


Group('Common options', [
    optionmap['init'],
    optionmap['update'],
    optionmap['without_demo'],
    optionmap['server_wide_modules'],
    optionmap['pidfile'],
])

Group('HTTP Service Configuration', [
    optionmap['http_interface'],
    optionmap['http_port'],
    optionmap['longpolling_port'],
    optionmap['http_enable'],
    optionmap['proxy_mode'],
])

Group('CRON Service Configuration', [
    optionmap['max_cron_threads'],
    optionmap['limit_time_real_cron'],
])

Group('Web interface Configuration', [
    optionmap['dbfilter'],
])

Group('Testing Configuration', [
    optionmap['test_file'],
    optionmap['test_enable'],
    optionmap['test_tags'],
    optionmap['screencasts'],
    optionmap['screenshots'],
])

Group('Logging Configuration', [
    *_loghandlers,
    optionmap['log_db'],
    optionmap['log_db_level'],
])

Group('SMTP Configuration', [
    optionmap['email_from'],
    optionmap['smtp_server'],
    optionmap['smtp_port'],
    optionmap['smtp_ssl'],
    optionmap['smtp_user'],
    optionmap['smtp_password'],
])

Group('Database related options', [
    optionmap['db_name'],
    optionmap['db_user'],
    optionmap['db_password'],
    optionmap['db_host'],
    optionmap['db_port'],
    optionmap['db_sslmode'],
    optionmap['pg_path'],
    optionmap['db_template'],
    optionmap['db_maxconn'],
    optionmap['unaccent'],
])

Group('ORM Configuration', [
    optionmap['transient_age_limit'],
    optionmap['osv_memory_age_limit'],
])

Group('Internationalisation options', [
    optionmap['load_language'],
    optionmap['language'],
    optionmap['translate_out'],
    optionmap['translate_in'],
    optionmap['overwrite_existing_translations'],
    optionmap['translate_modules'],
])

Group('Security-related options', [
    optionmap['list_db'],
])

Group('Misc options', [
    optionmap['dev_mode'],
    optionmap['shell_interface'],
    optionmap['stop_after_init'],
    optionmap['geoip_database'],
])

Group('Multiprocessing options', [
    optionmap['workers'],
    optionmap['limit_memory_soft'],
    optionmap['limit_memory_hard'],
    optionmap['limit_time_cpu'],
    optionmap['limit_time_real'],
    optionmap['limit_request'],
])

Group('Populate options', [
    optionmap['population_size'],
    optionmap['populate_models'],
])


########################################################################
#                                                                      #
#                              COMMANDS                                #
#                                                                      #
########################################################################


@dataclasses.dataclass(frozen=True)
class Command:
    name: str
    section: str
    options: List[Option] = dataclasses.field(default_factory=list)
    groups : List[Group] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        commandmap[self.name] = self

Command(
    name='',
    section='options',
    options=[
        optionmap['addons_path'],
        optionmap['upgrade_path'],
        optionmap['data_dir'],
        optionmap['log_level'],
        optionmap['logfile'],
        optionmap['syslog'],
        optionmap['log_handler'],
        optionmap['config'],
        optionmap['save'],
     ])

Command(
    name='server',
    section='options',
    options=[
        optionmap['admin_passwd'],
        optionmap['csv_internal_sep'],
        optionmap['publisher_warranty_url'],
        optionmap['reportgz'],
        optionmap['root_path'],
    ],
    groups=[
        groupmap['Common options'],
        groupmap['HTTP Service Configuration'],
        groupmap['CRON Service Configuration'],
        groupmap['Web interface Configuration'],
        groupmap['Testing Configuration'],
        groupmap['Logging Configuration'],
        groupmap['SMTP Configuration'],
        groupmap['Database related options'],
        groupmap['ORM Configuration'],
        groupmap['Internationalisation options'],
        groupmap['Security-related options'],
        groupmap['Misc options'],
        groupmap['Multiprocessing options'],
    ])

Command(
    name='populate',
    section='populate',
    groups=[
        groupmap['Common options'],
        groupmap['HTTP Service Configuration'],
        groupmap['CRON Service Configuration'],
        groupmap['Web interface Configuration'],
        groupmap['Testing Configuration'],
        groupmap['Logging Configuration'],
        groupmap['SMTP Configuration'],
        groupmap['Database related options'],
        groupmap['ORM Configuration'],
        groupmap['Internationalisation options'],
        groupmap['Security-related options'],
        groupmap['Misc options'],
        groupmap['Multiprocessing options'],
        groupmap['Populate options'],
    ])


########################################################################
########################################################################
########################################################################


def load_default():
    sourcemap['default'].clear()
    sourcemap['default'].update({
        option.name: option.default for option in optionmap.values()
    })


def load_environ():
    options = sourcemap['environ']
    options.clear()

    for option in optionmap.values():
        if option.envvar:
            val = os.getenv(option.envvar)
            if val:
                options[opt] = opttypemap[opt](val)


def load_cli(argv):
    def add_options(parser, options):
        for option in options:
            if not option.cli:
                continue
            args = [opt for opt in (option.shortopt, option.longopt) if opt]
            kwargs = {
                'dest': option.name,
                'action': option.action,
                'help': option.help,
                **{'nargs': o.nargs for o in (option,) if o.nargs},
                **{'metavar': o.metavar for o in (option,) if o.metavar},
                **{'const': o.const for o in (option,) if o.const},
            }
            try:
                parser.add_argument(*args, **kwargs)
            except Exception as exc:
                raise Exception(f"{args} {kwargs}") from exc
        

    # Build the CLI
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers(dest='subcommand')
    for command in commandmap.values():
        parser = subparsers.add_parser(command.name) if command.name else main_parser
        add_options(parser, command.options)

        for group in command.groups:
            groupcli = parser.add_argument_group(group.title)
            add_options(parser, group.options)

    # Process parsed args
    options = sourcemap['cli']
    options.clear()
    cli_options = vars(main_parser.parse_args(argv))

    Config.subcommand = cli_options.pop('subcommand', 'server')
    for opt, val in cli_options.items():
        if val is None:
            pass
        elif type(val) != str and isinstance(val, Iterable):
            val = list(flatten(map(optionmap[opt].type, val)))
            if all(isinstance(e, CommaSeparated) for e in val):
                val = CommaSeparated.merge(val)
            options[opt] = val
        else:
            options[opt] = optionmap[opt].type(val)


def load_file():
    configpath = config['config']
    try:
        if configpath.stat().st_mode & 0o777 != 0o600:
            warnings.warn("Running as user 'root' is a security risk.")
            warnings.warn(f"{configpath}, Wrong permissions, should be user-only read/write (0600)")
        p = configparser.RawConfigParser()
        p.read([configpath])
    except (FileNotFoundError, IOError):
        warnings.warn(f"{configpath}, Could not read configuration file")
        return

    for sec in p.sections():
        options = sourcemap['file' if sec == 'options' else 'file_' + sec]
        options.clear()
        for opt, val in p.items(sec):
            if opt not in optionmap:
                warnings.warn(f'{opt}, unknown option')
            elif not optionmap[opt].file:
                warnings.warn(f"{opt}, cannot be read from config file")
            else:
                options[opt] = optionmap[opt].type(val)



class Config(collections.abc.MutableMapping):
    subcommand = None

    def __init__(self, userchain=None, sectopts=None):
        self._userchain = userchain or collections.ChainMap({})
        self._sectopts = sectopts or {}
        self._chainmap = collections.ChainMap(
            self._userchain,
            sourcemap["cli"],
            self._sectopts,
            sourcemap["file"],
            sourcemap["environ"],
            sourcemap["default"],
            sourcemap["readonly"],
        )

    def copy(self):
        return type(self)(
            collections.ChainMap([
                useropts.copy()
                for useropts
                in self._userchain.maps
            ]),
            self._sectopts.copy(),
        )

    def expose_file_section(self, section):
        """
        Load the `section` from the configfile and expose it priority to
        the default configfile section
        """
        if not section.startswith('file_'):
            section = 'file_' + section
        self._sectopts.clear()
        self._sectopts.update(sourcemap[section])

    def show(self):
        for option, value in self.items():
            print(repr(option), repr(value), sep=": ")

    def save(self, configpath=None):
        """
        Export the currently exposed configuration with additionnal
        sections to a file
        """
        p = configparser.RawConfigParser()

        # default section, export currently exposed configuration
        p.add_section('options')
        for opt, val in self.items():
            if not optionmap[opt].file:
                continue
            if type(val) != str and isinstance(val, collections.abc.Iterable):
                p.set('options', opt, ",".join(val))
            else:
                p.set('options', opt, str(val))

        # other sections, rewrite them as-is
        for source, options in sourcemap.items():
            if not source.startswith('file_'):
                continue
            section = source[5:]
            p.add_section(section)
            for opt, val in options.items():
                if not optionmap[opt].file:
                    continue
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

    def __contains__(self, option):
        """ True if option exists and wasn't removed, False otherwise """
        try:
            self[option]
        except KeyError:
            return False
        return True

    def __getitem__(self, option):
        """
        Return the corresponding option value automatically following
        option aliases. A KeyError exception is raised for missing or
        removed options.
        """
        val = self._chainmap[option]
        if val is DELETED:
            raise KeyError(f"{option} has been removed")
        elif isinstance(val, DeprecatedAlias):
            warnings.warn(
                f"The {option} is a deprecated alias to {val.aliased_option}, "
                "please use the latter. The option may be overridable via a "
                "dedication section in the configuration file.",
                DeprecationWarning)
            return self[val.aliased_option]
        return val

    def __setitem__(self, option, value):
        """
        Set the corresponding option value in the top-most chained user
        dictionnary.
        """
        if type(value) is str:
            value = opttypemap[option](value)
        setattr(super(), option, value)

    def __delitem__(self, option):
        """
        Mark the corresponding option as removed to prevent subsequent use
        """
        setattr(super(), option, DELETED)

    def __iter__(self):
        return iter(self._chainmap)

    def __len__(self):
        return len(self._chainmap)

    @contextlib.contextmanager
    def __call__(self, tempopts=None):
        """
        Temporary override the current configuration with provided
        options or a clean dictionnary. The previous configuration is
        restored upon leaving the context.
        """
        if tempopts is None:
            tempopts = {}
        self._userchain.maps.insert(0, tempopts)
        try:
            yield self
        finally:
            self._userchain.maps.remove[tempopts]

    @property
    def rcfile(self):
        return get_odoorc()

    @property
    def evented(self):
        return type(self).subcommand == 'gevent'

    @property
    def addons_data_dir(self):
        return self['data_dir'].joinpath('addons')

    @property
    def session_dir(self):
        return self['data_dir'].joinpath('sessions')

    def filestore(self, dbname):
        return self['data_dir'].joinpath('filestore', dbname)


config = Config()
