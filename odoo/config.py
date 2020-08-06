# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import argparse
import configparser
import contextlib
import dataclasses
import datetime
import distutils.util
import os
import tempfile
import warnings
import shlex
import sys
import traceback
from collections import ChainMap
from collections.abc import Iterable, Set, MutableMapping, Sequence, Collection
from pathlib import Path
from textwrap import dedent, wrap
from typing import Any, Callable, Optional, List

from odoo import appdirs
from odoo import release
from odoo.loglevels import PSEUDOCONFIG_MAPPER as loglevelmap


optionmap = {}      # option name to option object map
groupmap = {}       # group title to group object map
commandmap = {}     # subcommand name to command object map
sourcemap = {       # all configuration sources
    'cli': {},      # argparse
    'file': {},     # configparser [common] section
    'environ': {},  # os.getenv
    'default': {},  # source-hardcoded
}
DELETED = object()  # inserted in the top-most chained map to mark the
                    # option as removed


def logformat(level, message, exc_info=False):
    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S,%f')
    now = now[:-4]  # %f is nanosecond resolutions, we want centiseconds
    msg = "{now} {pid} {level} ? odoo.config: {message}".format(
        now=now,
        pid=os.getpid(),
        level=level,
        message=message
    )
    if exc_info:
        msg += "\n" + traceback.format_exc()
    return msg

def warn(*args, file=sys.stderr, **kwargs):
    message = kwargs.get('sep', ' ').join(map(str, args))
    print(logformat('WARNING', message), file=file, **kwargs)

def die(option, value, source, exc):
    raise SystemExit(logformat("CRITICAL", f"Could not parse {value!r} for option '{option}' from {source}\n{exc}"))


########################################################################
#                                                                      #
#                        TYPE-LIKE FUNCTIONS                           #
#           all sanity checks and type conversions goes here           #
#                                                                      #
########################################################################

class Alias:
    """
    Use this as default value to trigger automatic fallback to the given
    aliases option. This object exists solely to ensure backward
    compatiblity and should not be used for any new option. Please
    instead take advantage of configuration file sections and the
    ``Config.expose_file_section`` method.
    """

    aliased_option: str

    def __init__(self, aliased_option):
        self.aliased_option = aliased_option

    def __repr__(self):
        return "-> %s" % self.aliased_option


class Dynamic:
    """
    Use this as default value to trigger automatic function execution
    upon access. The function receives the current config object. This
    object exists solely to ensure backward compatibility and should not
    be used for any new option. Please add a property on ``Config`` instead.
    """

    function: Callable[["Config"], Any]

    def __init__(self, function):
        self.function = function

    def __repr__(self):
        return "%s()" % self.function.__name__


class CommaOption(Collection):
    @classmethod
    def parser(cls, cast: callable):
        return lambda rawopt: cls(map(cast, rawopt.split(',')))

    @classmethod
    def _merge(cls, co_list):
        new = cls()
        for co in co_list:
            new = new + co
        return new

    def split(self, char):
        warnings.warn(
            "The option has been parsed to the best suited collection "
            "already, there is no need to split it",
            DeprecationWarning, stacklevel=2)
        if char == ',':
            return self
        return str(self).split(char)

    def __contains__(self, key):
        return key in self.data

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __str__(self):
        return ','.join(map(str, self))

    def __radd__(self, other):
        return self + other


class CommaList(CommaOption, Sequence):
    def __init__(self, data=None):
        self.data = list(data) if data is not None else list()

    def __getitem__(self, key):
        return self.data[key]

    def __repr__(self):
        return "['%s']" % "', '".join(map(str, self))

    def __add__(self, other):
        new = type(self)()
        new.data.extend(self)
        new.data.extend(other)
        return new


class CommaSet(CommaOption, Set):
    def __init__(self, data=None):
        self.data = set(data) if data is not None else set()

    def __repr__(self):
        return "{'%s'}" % "', '".join(map(str, self))

    def __add__(self, other):
        new = type(self)()
        new.data.update(self)
        new.data.update(other)
        return new


def strtobool(rawopt: str):
    """
    Convert a bool or a case-insensitive string representation of truth
    to its corresponding bool.
    
    True values are True, 'y', 'yes', 't', 'true', 'on', and '1'.
    False values are False, 'n', 'no', 'f', 'false', 'off', and '0'.

    Raises ValueError if 'rawopt' is anything else.
    """
    if isinstance(rawopt, bool):
        return rawopt
    return distutils.util.strtobool(rawopt)


def choices(selection: list, cast: callable=str):
    def assert_in(rawopt):
        opt = cast(rawopt)
        if opt not in selection:
            raise ValueError(f"{opt}, not a valid option, pick from %s" % ", ".join(selection))
        return opt
    return assert_in


def fullpath(path: str):
    return Path(path).expanduser().resolve().absolute()


def _check_file_access(rawopt: str, mode: int) -> Path:
    """
    Ensure `rawopt` is a `mode` accessible file, the fullpath is returned.

    `mode` is an operating-system mode bitfield. Can be os.F_OK to test
    existence, or the inclusive-OR of os.R_OK, os.W_OK, and os.X_OK.
    """
    path = fullpath(rawopt)
    if path.is_file():
        if os.access(path, mode):
            return path
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = ", ".join(perm for bit, perm in pairs if bit & mode)
        raise ValueError(f"file requires {missing} permission(s)")
    elif not path.exists() and mode & os.W_OK:
        if os.access(path.parent, os.W_OK):
            return path
        raise ValueError("parent directory requires write permission")
    else:
        raise ValueError("no such file")
    return path


def _check_dir_access(rawopt: str, mode: int) -> Path:
    """
    Ensure `rawopt` is a `mode` accessible dir, the fullpath is returned.

    Missing `os.W_OK` directories are automatically created.

    `mode` is an operating-system mode bitfield. Can be os.F_OK to test
    existence, or the inclusive-OR of os.R_OK, os.W_OK, and os.X_OK.
    """
    path = fullpath(rawopt)
    if path.is_dir():
        if os.access(path, mode):
            return path
        pairs = [(os.R_OK, 'read'), (os.W_OK, 'write'), (os.X_OK, 'exec')]
        missing = "".join(perm for bit, perm in pairs if bit & mode)
        raise ValueError(f"directory requires {missing} permission(s)")
    elif not path.exists() and mode & os.W_OK:
        try:
            path.mkdir(parents=True)
            return path
        except OSError:
            raise ValueError("parent directory requires write permission")
    else:
        raise ValueError("no such directory")
    return path


def checkfile(mode: int) -> Callable[[str], str]:
    """
    Ensure the given file will be `mode` accessible.

    `mode` is an operating-system mode bitfield or single-char alias. Can
    be os.F_OK to test existence, or the inclusive-OR of os.R_OK, os.W_OK,
    and os.X_OK. Aliases are 'e': F_OK, 'r': R_OK, 'w': W_OK, 'x': X_OK.
    """
    mode = {'e': os.F_OK, 'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    return lambda rawopt: str(_check_file_access(rawopt, mode))


def checkdir(mode: int) -> Callable[[str], str]:
    """
    Ensure the given directory will be `mode` accessible.

    `mode` is an operating-system mode bitfield or single-char alias. Can
    be os.F_OK to test existence, or the inclusive-OR of os.R_OK, os.W_OK,
    and os.X_OK. Aliases are 'e': F_OK, 'r': R_OK, 'w': W_OK, 'x': X_OK.
    """
    mode = {'e': os.F_OK, 'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    return lambda rawopt: str(_check_dir_access(rawopt, mode))


def checkpath(mode: int) -> Callable[[str], str]:
    """
    Ensure the given path is either a file or a directory and  will be
    `mode` accessible.

    `mode` is an operating-system mode bitfield or single-char alias. Can
    be os.F_OK to test existence, or the inclusive-OR of os.R_OK, os.W_OK,
    and os.X_OK. Aliases are 'e': F_OK, 'r': R_OK, 'w': W_OK, 'x': X_OK.
    """
    mode = {'e': os.F_OK, 'r': os.R_OK, 'w': os.W_OK, 'x': os.X_OK}.get(mode, mode)
    def exists(rawopt):
        try:
            return _check_file_access(rawopt, mode)
        except ValueError as exc:
            if exc.args[0] != 'no such file':
                raise
        try:
            return _check_dir_access(rawopt, mode)
        except ValueError as exc:
            if exc.args[0] != 'no such directory':
                raise
        raise ValueError('no such file or directory')
    return exists




def addons_path(rawopt: str) -> str:
    """ Ensure `rawopt` is a valid addons path, the fullpath is returned """
    path = _check_dir_access(rawopt, os.R_OK | os.X_OK)
    if not next(path.glob('*/__manifest__.py'), None):
        olds = path.glob('*/__openerp__.py')
        if not olds:
            raise ValueError("not a valid addons path, doesn't contain modules")
        warnings.warn(
            'Using "__openerp__.py" as module manifest is deprecated, '
            'please renome them as "__manifest__.py". Affected '
            'modules: %s' % ", ".join((old.parent.name for old in olds)),
            DeprecationWarning)
    return str(path)


def upgrade_path(rawopt: str) -> str:
    """ Ensure `rawopt` is a valid upgrade path, the fullpath is returned """
    path = _check_dir_access(rawopt, os.R_OK | os.X_OK)
    if not any(path.glob(f'*/*/{x}-*.py') for x in ["pre", "post", "end"]):
        if path.joinpath('migrations').is_dir():  # for colleagues
            raise ValueError("not a valid upgrade path, looks like you forgot the migrations folder")
        raise ValueError("not a valid upgrade path, migration scripts not found")
    return str(path)


def get_default_datadir() -> str:
    if Path('~').expanduser().is_dir():
        func = appdirs.user_data_dir
    elif sys.platform in ['win32', 'darwin']:
        func = appdirs.site_data_dir
    else:
        func = lambda **kwarg: "/var/lib/%s" % kwarg['appname'].lower()
    # No "version" kwarg as session and filestore paths are shared against series
    return str(fullpath(func(appname=release.product_name, appauthor=release.author)))


def get_default_addons_path():
    root = fullpath(__file__).parent
    return CommaList([
        str(root.joinpath('addons').resolve().absolute()),
        str(root.parent.joinpath('addons').resolve().absolute()),
    ])


def get_odoorc() -> str:
    if os.name == 'nt':
        return str(fullpath(sys.argv[0]).parent().joinpath('odoo.conf'))
    return str(Path.home().joinpath('.odoorc'))


def data_dir(rawopt: str) -> str:
    return str(_check_dir_access(rawopt, os.R_OK | os.W_OK | os.X_OK))


def ensure_data_dir(datadir: str):
    """
    Ensure the `datadir` is a valid data dir, the addons, sessions, and
    filestore are automatically created if missing.
    """
    datadir = Path(datadir)
    ad = datadir.joinpath('addons')
    if not ad.exists():
        ad.mkdir(mode=0o700)
    elif not os.access(ad, os.R_OK | os.W_OK | os.X_OK):
        raise ValueError(f"{ad} requires rwx access")
    adr = ad.joinpath(release.series)
    if not adr.exists():
        # try to make +rx placeholder dir, will need manual +w to activate it
        try:
            adr.mkdir(mode=0o500)
        except OSError:
            warn(f"Failed to create addons data dir at {adr}")

    sd = datadir.joinpath('sessions')
    if not sd.exists():
        sd.mkdir(mode=0o700)
    elif not os.access(sd, os.R_OK | os.W_OK | os.X_OK):
        raise ValueError(f"{sd} requires rwx access")

    fd = datadir.joinpath('filestore')
    if not fd.exists():
        fd.mkdir(mode=0o700)
    elif not os.access(fd, os.R_OK | os.W_OK | os.X_OK):
        raise ValueError(f"{fd} requires rwx access")


def pg_utils_path(rawopt: str) -> str:
    """
    Ensure `rawopt` is path which contains PostgreSQL system utilities,
    the fullpath is returned.
    """
    path = _check_dir_access(rawopt, os.X_OK)
    pg_utils = {'psql', 'pg_dump', 'pg_restore'}
    if not any(file.stem in pg_utils for file in path.iterdir()):
        raise
    return str(path)


def i18n_input_file(rawopt: str) -> str:
    """ Ensure `rawopt` is a valid translation file, the fullpath is returned """
    path = _check_file_access(rawopt, 'r')
    formats = {'.csv', '.po'}
    if not path.suffixes or path.suffixes[-1].lower() not in formats:
        raise ValueError("not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return str(path)


def i18n_output_file(rawopt: str) -> str:
    """ Ensure `rawopt` is a valid translation file, the fullpath is returned """
    path = _check_file_access(rawopt, 'w')
    formats = {'.csv', '.po', '.tgz'}
    if not path.suffixes or path.suffixes[-1].lower() not in formats:
        raise ValueError("not a valid translation file, allowed formats are %s" % ", ".join(formats))
    return str(path)


def dyndemo(config) -> List[str]:
    return config['init'] if not config['without_demo'] else {}



########################################################################
#                                                                      #
#                               OPTIONS                                #
#                                                                      #
########################################################################

@dataclasses.dataclass(frozen=True)
class Option:
    name: str                            # python-side option name
    parse: Callable[[str], Any]          # source -> python converting function

    format: Callable[[str], Any] = str   # python -> config file converting function
    required: bool = False               # should the default value be skipped
    default: Any = None                  # default, last-resort, option value
    file: bool = True                    # should the option be read from/save to the config file
    envvar: Optional[str] = None         # environment variable to load the option from

    args: List[str] = (                  # argparse's argument and flags
        dataclasses.field(default_factory=list))
    action: str = "store"                # argparse's action
    metavar: Optional[str] = None        # argparse's metavar
    const: Any = None                    # argparse's const
    nargs: Optional[int] = None          # argparse's nargs
    help: Optional[str] = None           # argparse's help

    def __post_init__(self):
        optionmap.setdefault(self.name, self)

Option('addons_path', args=["--addons-path"], parse=CommaList.parser(addons_path), action='append', default=get_default_addons_path(), metavar="DIRPATH", help="specify additional addons paths")
Option('upgrade_path', args=["--upgrade-path"], parse=CommaList.parser(upgrade_path), action='append', default=CommaList(), metavar="DIRPATH", help="specify an additional upgrade path.")
Option('data_dir', args=["-D", "--data-dir"], parse=data_dir, action='store', default=get_default_datadir(), help="Directory where to store Odoo data")
Option('log_level', args=["--log-level"], parse=choices(loglevelmap.keys()), action='store', default='info', metavar="LEVEL", help="specify the level of the logging")
Option('logfile', args=["--logfile"], parse=checkfile('w'), action='store', metavar="FILEPATH", help="file where the server log will be stored")
Option('syslog', args=["--syslog"], parse=strtobool, action='store_true', help="Send the log to the syslog server")
Option('log_handler', args=["--log-handler"], parse=CommaList.parser(str), action='append', default=CommaList([':INFO']), help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')
Option('config', args=["-c", "--config"], parse=checkfile('r'), action='store', default=get_odoorc(), metavar="FILEPATH", file=False, help="specify alternate config file name")
Option('save', args=["-s", "--save"], parse=checkfile('w'), action='store', nargs='?', const=get_odoorc(), file=False, metavar="FILEPATH", help="save parsed config in PATH")

Option('init', args=["-i", "--init"], parse=CommaSet.parser(str), action='append', default=CommaSet(), file=False, help='install one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d')
Option('update', args=["-u", "--update"], parse=CommaSet.parser(str), action='append', default=CommaSet(), file=False, help='update one or more modules (comma-separated list or repeated option, use "all" for all modules), requires -d.')
Option('demo', default=Dynamic(dyndemo), parse=dict, file=False)
Option('without_demo', args=["--without-demo"], parse=strtobool, action='store_true', help='disable loading demo data for modules to be installed (comma-separated or repeated option, use "all" for all modules), requires -d and -i.')
Option('server_wide_modules', args=["--load"], parse=CommaSet.parser(str), action='append', default=CommaSet({'base','web'}), metavar="MODULE", help="framework modules to load once for all databases (comma-separated or repeated option)")
Option('pidfile', args=["--pidfile"], parse=checkfile('w'), action='store', metavar="FILEPATH", help="file where the server pid will be stored")

Option('http_interface', args=["--http-interface"], parse=str, action='store', default='', metavar="INTERFACE", help="Listen interface address for HTTP services. Keep empty to listen on all interfaces (0.0.0.0)")
Option('http_port', args=["-p", "--http-port"], parse=int, action='store', default=8069, metavar="PORT", help="Listen port for the main HTTP service")
Option('longpolling_port', args=["--longpolling-port"], parse=int, action='store', default=8072, metavar="PORT", help="Listen port for the longpolling HTTP service")
Option('http_enable', args=["--no-http"], parse=strtobool, action='store_false', help="Disable the HTTP and Longpolling services entirely")
Option('proxy_mode', args=["--proxy-mode"], parse=strtobool, action='store_true', help="Activate reverse proxy WSGI wrappers (headers rewriting) Only enable this when running behind a trusted web proxy!")

Option('max_cron_threads', args=["--max-cron-threads"], parse=int, action='store', default=2, help="Maximum number of threads processing concurrently cron jobs.")
Option('limit_time_real_cron', args=["--limit-time-real-cron"], parse=int, action='store', default=Alias('limit_time_real'), help="Maximum allowed Real time per cron job. (default: --limit-time-real). Set to 0 for no limit.")

Option('dbfilter', args=["--db-filter"], parse=str, action='store', default='', metavar="REGEXP", help="Regular expressions for filtering available databases for Web UI. The expression can use %%d (domain) and %%h (host) placeholders.")

Option('test_file', args=["--test-file"], parse=checkfile('r'), action='store', metavar="FILEPATH", help="Launch a python test file.")
Option('test_enable', args=["--test-enable"], parse=strtobool, action='store_true', help="Enable unit tests while installing or upgrading a module.")
Option('test_tags', args=["--test-tags"], parse=CommaList.parser(str), action='append', default=CommaList(), help=dedent("""\
    Comma-separated or repeated option list of spec to filter which tests to execute. Enable unit tests if set.
    A filter spec has the format: [-][tag][/module][:class][.method]
    The '-' specifies if we want to include or exclude tests matching this spec.
    The tag will match tags added on a class with a @tagged decorator. By default tag value is 'standard' when not
    given on include mode. '*' will match all tags. Tag will also match module name (deprecated, use /module)
    The module, class, and method will respectively match the module name, test class name and test method name.
    examples: :TestClass.test_func,/test_module,external"""))
Option('screencasts', args=["--screencasts"], parse=checkdir('w'), action='store', default=str(fullpath(tempfile.gettempdir()).joinpath('odoo_tests')), metavar="DIRPATH", help="Screencasts will go in DIR/<db_name>/screencasts.")
Option('screenshots', args=["--screenshots"], parse=checkdir('w'), action='store', default=str(fullpath(tempfile.gettempdir()).joinpath('odoo_tests')), metavar="DIRPATH", help="Screenshots will go in DIR/<db_name>/screenshots.")

_loghandlers = [
    Option('log_handler', args=["--log-request"], parse=str, action='append_const', const='odoo.http.rpc.request:DEBUG', help="shortcut for --log-handler=odoo.http.rpc.request:DEBUG"),
    Option('log_handler', args=["--log-response"], parse=str, action='append_const', const='odoo.http.rpc.response:DEBUG', help="shortcut for --log-handler=odoo.http.rpc.response:DEBUG"),
    Option('log_handler', args=["--log-web"], parse=str, action='append_const', const='odoo.http:DEBUG', help="shortcut for --log-handler=odoo.http:DEBUG"),
    Option('log_handler', args=["--log-sql"], parse=str, action='append_const', const='odoo.sql_db:DEBUG', help="shortcut for --log-handler=odoo.sql_db:DEBUG"),
]
Option('log_db', args=["--log-db"], parse=strtobool, action='store_true', help="Enable database logs record")
Option('log_db_level', args=["--log-db-level"], parse=choices(loglevelmap.keys()), action='store', default='warning', metavar="LEVEL", help="specify the level of the database logging")

Option('email_from', args=["--email-from"], parse=str, action='store', metavar="EMAIL", help="specify the SMTP email address for sending email")
Option('smtp_server', args=["--smtp"], parse=str, action='store', default='localhost', metavar="HOST", help="specify the SMTP server for sending email")
Option('smtp_port', args=["--smtp-port"], parse=int, action='store', default=25, metavar="PORT", help="specify the SMTP port")
Option('smtp_ssl', args=["--smtp-ssl"], parse=strtobool, action='store_true', help="if passed, SMTP connections will be encrypted with SSL (STARTTLS)")
Option('smtp_user', args=["--smtp-user"], parse=str, action='store', help="specify the SMTP username for sending email")
Option('smtp_password', args=["--smtp-password"], parse=str, action='store', help="specify the SMTP password for sending email")

Option('db_name', args=["-d", "--database"], parse=str, action='store', envvar='PGDATABASE', metavar="DBNAME", help="database name to connect to")
Option('db_user', args=["-r", "--db_user"], parse=str, action='store', envvar='PGUSER', metavar="USERNAME", help="database user to connect as")
Option('db_password', args=["-w", "--db_password"], parse=str, action='store', envvar='PGPASSWORD', metavar="PWD", help='password to be used if the database demands password authentication. Using this argument is a security risk, see the "The Password File" section in the PostgreSQL documentation for alternatives.')
Option('db_host', args=["--db_host"], parse=str, action='store', envvar='PGHOST', metavar="HOSTNAME", help="database server host or socket directory")
Option('db_port', args=["--db_port"], parse=str, action='store', envvar='PGPORT', metavar="PORT", help="database server port")
Option('db_sslmode', args=["--db_sslmode"], parse=str, action='store', default='prefer', metavar="METHOD", help="determines whether or with what priority a secure SSL TCP/IP connection will be negotiated with the server")
Option('pg_path', args=["--pg_path"], parse=pg_utils_path, action='store', metavar="DIRPATH", help="postgres utilities directory")
Option('db_template', args=["--db-template"], parse=str, action='store', default='template0', metavar="DBNAME", help="custom database template to create a new database")
Option('db_maxconn', args=["--db_maxconn"], parse=int, action='store', default=64, help="specify the maximum number of physical connections to PostgreSQL")
Option('unaccent', args=["--unaccent"], parse=strtobool, action='store_true', help="Try to enable the unaccent extension when creating new databases")

Option('transient_age_limit', args=["--transient-age-limit"], parse=float, action='store', default=1.0, metavar="HOURS", help="Time in hours records created with a TransientModel (mosly wizard) are kept in the database.")
Option('osv_memory_age_limit', args=["--osv-memory-age-limit"], parse=float, action='store', default=Alias('transient_age_limit'), help=argparse.SUPPRESS)

Option('load_language', args=["--load-language"], parse=CommaList.parser(str), action='store', default=CommaList(), file=False, metavar="LANGCODE", help="specifies the languages for the translations you want to be loaded")
Option('language', shortopt="-l", args=["--language"], parse=str, action='store', metavar="LANGCODE", help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
Option('translate_out', longopt="--i18n-export", parse=i18n_output_file, action='store', metavar="FILEPATH", help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit. The '-l' option is required")
Option('translate_in', longopt="--i18n-import", parse=i18n_input_file, action='store', metavar="FILEPATH", help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
Option('overwrite_existing_translations', longopt="--i18n-overwrite", parse=strtobool, action='store_true', help="overwrites existing translation terms on updating a module or importing a CSV or a PO file. Use with -u/--update or --i18n-import.")
Option('translate_modules', args=["--modules"], parse=CommaList.parser(str), action='store', default=CommaList(), help="specify modules to export. Use in combination with --i18n-export")

Option('list_db', args=["--no-database-list"], parse=strtobool, action='store_false', help="Disable the ability to obtain or view the list of databases. Also disable access to the database manager and selector, so be sure to set a proper --database parameter first.")

Option('dev_mode', args=["--dev"], parse=CommaList.parser(choices(['all', 'pudb', 'wdb', 'ipdb', 'pdb', 'reload', 'qweb', 'werkzeug', 'xml'])), action='append', default=CommaList(), file=False, help="Enable developer mode")
Option('shell_interface', args=["--shell-interface"], parse=str, action='store', default='python', file=False, help="Specify a preferred REPL to use in shell mode")
Option('stop_after_init', args=["--stop-after-init"], parse=strtobool, action='store_true', file=False, help="stop the server after its initialization")
Option('geoip_database', args=["--geoip-db"], parse=str, action='store', default='/usr/share/GeoIP/GeoLite2-City.mmdb', help="Absolute path to the GeoIP database file.")

Option('workers', args=["--workers"], parse=int, action='store', default=0, help="Specify the number of workers, 0 disable prefork mode.")
Option('limit_memory_soft', args=["--limit-memory-soft"], parse=int, action='store', default=2048*1024*1024, metavar="BYTES", help="Maximum allowed virtual memory per worker, when reached the worker be reset after the current request (default 2048MiB).")
Option('limit_memory_hard', args=["--limit-memory-hard"], parse=int, action='store', default=2560*1024*1024, metavar="BYTES", help="Maximum allowed virtual memory per worker (in bytes), when reached, any memory allocation will fail (default 2560MiB).")
Option('limit_time_cpu', args=["--limit-time-cpu"], parse=int, action='store', default=60, metavar="SECONDS", help="Maximum allowed CPU time per request (default 60).")
Option('limit_time_real', args=["--limit-time-real"], parse=int, action='store', default=120, metavar="SECONDS", help="Maximum allowed Real time per request (default 120).")
Option('limit_request', args=["--limit-request"], parse=int, action='store', default=8192, help="Maximum number of request to be processed per worker (default 8192).")

Option('admin_passwd', parse=str, default='admin')
Option('csv_internal_sep', parse=str, default=',')
Option('publisher_warranty_url', file=False, parse=str, default='http://services.openerp.com/publisher-warranty/')
Option('reportgz', parse=strtobool, default=False)
Option('root_path', file=False, parse=checkdir(os.R_OK), default=str(fullpath(Path(__file__)).parent))

Option('population_size', args=["--size"], parse=str, action='store', default='small', help="Populate database with auto-generated data")
Option('populate_models', args=["--models"], parse=CommaList.parser(str), action='append', default=CommaList(), metavar="MODEL OR PATTERN", help="List of model (comma separated or repeated option) or pattern")

Option('verbose', shortopt='-v', longopt='--verbose', action='count', parse=int, default=0, help="Increase verbosity")
Option('clocpaths', shortopt='-p', longopt='--path', action='append', parse=CommaList.parser(checkpath('r')), default=CommaList(), metavar="PATH", help="File or directory")

Option('deploy_module_path', parse=checkdir('r'), file=False, metavar="DIR", help="Url of the server (default=http://localhost:8069)")
Option('deploy_url', parse=str, default='http://localhost:8069', nargs='?', metavar="URL" help="Url of the server")
Option('deploy_db', args=["--db"], parse=str, help='Database to use if server does not use db-filter.')
Option('deploy_login', args=["--login"], parse=str, default='admin', help="Login (default=admin)")
Option('deploy_pwd', args=["--password"], parse=str, default='admin', help="Password (default=admin). Setting the password via the cli is a security risk, you may instead use the configuration file.")
Option('deploy_verify_ssl', args=["--verify-ssl"], parse=strtobool, action='store_true', default=False, help="Verify SSL certificate")
Option('deploy_force', args=["--force"], parse=strtobool, action='store_true', default=False, help="Force init even if module is already installed. (will update `noupdate="1"` records)")


########################################################################
#                                                                      #
#                                GROUPS                                #
#                                                                      #
########################################################################

@dataclasses.dataclass(frozen=True)
class Group:
    title: str
    desc: str
    options: List[Option]

    def __post_init__(self):
        groupmap[self.title] = self


Group('Bootstraping options', "Options used during library bootstrap.", [
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

Group('Common options', "Options used during server bootup.", [
    optionmap['init'],
    optionmap['update'],
    optionmap['demo'],
    optionmap['without_demo'],
    optionmap['server_wide_modules'],
    optionmap['pidfile'],
])

Group('HTTP Service Configuration', dedent("""\
    Options used to configure the HTTP service. Mind you can use the
    [http] additional section of the configuration file to special
    limits dedicated to this service.
    """), [
    optionmap['http_interface'],
    optionmap['http_port'],
    optionmap['longpolling_port'],
    optionmap['http_enable'],
    optionmap['proxy_mode'],
])

Group('CRON Service Configuration', dedent("""\
    Options used to configure the CRON service. Mind you can use the
    [cron] additional section of the configuration file to special
    limits dedicated to this service.
    """), [
    optionmap['max_cron_threads'],
    optionmap['limit_time_real_cron'],
])

Group('Web interface Configuration', "", [
    optionmap['dbfilter'],
])

Group('Testing Configuration', dedent("""\
    Options used to enable and refine testing. Mind Odoo only tests
    modules on installation or updating, -i/-u is advised. Mind the
    server keeps running when tests are done, you might considere the
    --stop-after-init option.
    """), [
    optionmap['test_enable'],
    optionmap['test_file'],
    optionmap['test_tags'],
    optionmap['screencasts'],
    optionmap['screenshots'],
])

Group('Logging Configuration', dedent("""\
    Additionnal logging configuration, enable pre-configured log
    handlers or enable database logging to the database.
    """), [
    *_loghandlers,
    optionmap['log_db'],
    optionmap['log_db_level'],
])

Group('SMTP Configuration', dedent("""\
    Options used to connect to the SMTP server. Mind you can configure
    them via the Outgoing Mail Server settings in the technical settings.
    """), [
    optionmap['email_from'],
    optionmap['smtp_server'],
    optionmap['smtp_port'],
    optionmap['smtp_ssl'],
    optionmap['smtp_user'],
    optionmap['smtp_password'],
])

Group('Database related options', dedent("""\
    Options used to connect to the PostgreSQL server. Most of those
    options are also configurable via PG_* environment variables.
    """), [
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

Group('ORM Configuration', "", [
    optionmap['transient_age_limit'],
    optionmap['osv_memory_age_limit'],
])

Group('Internationalisation options', dedent("""\
    Use these options to translate Odoo to another language.
    See i18n section of the user manual. Option '-d' is mandatory.
    Option '-l' is mandatory in case of importation.
    """), [
    optionmap['load_language'],
    optionmap['language'],
    optionmap['translate_out'],
    optionmap['translate_in'],
    optionmap['overwrite_existing_translations'],
    optionmap['translate_modules'],
])

Group('Security-related options', "", [
    optionmap['list_db'],
])

Group('Misc options', "", [
    optionmap['dev_mode'],
    optionmap['shell_interface'],
    optionmap['stop_after_init'],
    optionmap['geoip_database'],
])

Group('Multiprocessing options', dedent("""\
    Options used to start Odoo in multi-processing mode instead of
    multi-threading. Limits set via the command line are global for all
    services and override limits set via the configuration file. If you
    desire to set per-service limits, you can set them via the optionnal
    [http], [cron] and [longpolling] sections in the configuration file.
    """), [
    optionmap['workers'],
    optionmap['limit_memory_soft'],
    optionmap['limit_memory_hard'],
    optionmap['limit_time_cpu'],
    optionmap['limit_time_real'],
    optionmap['limit_request'],
])


########################################################################
#                                                                      #
#                              COMMANDS                                #
#                                                                      #
########################################################################


@dataclasses.dataclass(frozen=True)
class Command:
    name: str
    desc: str
    section: str
    options: List[Option] = dataclasses.field(default_factory=list)
    groups : List[Group] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        commandmap[self.name] = self

Command(
    # Common options are grouped in this special fake command for ease of use
    name='',
    desc=dedent("""\
        Odoo command line interface
    """),
    section='',
    options=groupmap['Bootstraping options'].options,
)

Command(
    name='server',
    desc=dedent("""\
        Multi-purpose primary command. Main purpose is to bootstrap the
        Odoo library and to run the various services to handle incomming
        requests. This commands is also used to run unittests and to
        import/export translation files.
    """),
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
    desc="Populate a model with dummy data",
    section='options',
    options=[
        optionmap['population_size'],
        optionmap['populate_models'],
        *commandmap['server'].options,
    ],
    groups=commandmap['server'].groups,
    )

Command(
    name='cloc',
    desc=dedent("""\
    Odoo cloc is a tool to count the number of relevant lines written in
    Python, Javascript or XML. This can be used as rough metric for
    pricing maintenance of customizations.

    It has two modes of operation, either by providing a path:

        odoo-bin cloc -p module_path

    Or by providing the name of a database:

        odoo-bin --addons-path=dirs cloc -d database

    In the latter mode, only the custom code is accounted for.
    """),
    options=[
        optionmap['verbose'],
        optionmap['inputpaths'],
    ],
    groups=[
        groupmap['Database related options'],
    ])

Command(
    name='deploy',
    desc="Deploy a module on an Odoo instance",
    section='deploy',
    options=[
        optionmap['deploy_module_path'],
        optionmap['deploy_url'],
        optionmap['deploy_db'],
        optionmap['deploy_login'],
        optionmap['deploy_pwd'],
        optionmap['deploy_verify_ssl'],
        optionmap['deploy_force'],
    ],
    groups=[],
    )

########################################################################
#                                                                      #
#                               PARSERS                                #
#                                                                      #
########################################################################

def backward_compatible_parse_args(main_parser, argv):
    """ Old v13- and new v14+ dual command-line arguments parser """
    try:
        cli_options = vars(main_parser.parse_args(argv))
    except SystemExit as exc:  # TODO juc, use exit_on_error=False in py3.9
        if '-h' in argv or '--help' in argv:
            raise
        # retry after converting argv from old odoobin cli
        new_argv = from_odoobin(argv.copy())
        try:
            cli_options = vars(main_parser.parse_args(new_argv))
        except SystemExit:
            # not odoobin compatible
            raise exc
        else:
            warnings.warn("\n\n  {}\n\n  {}\n".format("\n  ".join(wrap(dedent("""\
                The old odoo-bin format CLI is deprecated. Your command
                line was automatically converted this time. Run Odoo
                with the '--help' flag to see what changed.
                Using command:
                """))),
                "{exec} {argv0} {argv}".format(
                    exec=sys.executable,
                    argv0='-m odoo' if sys.argv[0].endswith('__main__.py') else sys.argv[0],
                    argv=" ".join(map(shlex.quote, new_argv)),
                )
                
            ), DeprecationWarning)

    return cli_options

def from_odoobin(argv):
    """ Convert v13 odoo-bin CLI arguments to v14 """

    # In v14+ parser, the subcommand is mandatory and bootstraping 
    # options are to be put before the subcommand. This function moves
    # those options before the given subcommand.

    # find the subcommand and its position
    for cmd in commandmap.values():
        with contextlib.suppress(ValueError):
            cmd_index = argv.index(cmd.name)
            break
    else:
        # subcommand not found, force the 'server' subcommand
        cmd = commandmap['server']
        cmd_index = 0
        argv.insert(0, cmd.name)

    # move all bootstraping options before the subcommand
    for opt in groupmap['Bootstraping options'].options:
        try:
            opt_index = argv.index(opt.shortopt)
        except ValueError:
            try:
                opt_index = argv.index(opt.longopt)
            except ValueError:
                continue  # option not present, skip

        if opt_index < cmd_index:
            continue  # option before the command already, skip

        # rewrite argv so the option is moved at the beginning
        argcnt = {'save': 1, 'syslog': 1}.get(opt.name, 2)
        argv = (
            argv[opt_index:opt_index+argcnt]  # [option, value]
          + argv[:opt_index]                  # + all preceding options
          + argv[opt_index+argcnt:]           # + all following options
        )
        cmd_index += argcnt

    return argv


def load_default():
    sourcemap['default'].clear()
    sourcemap['default'].update({
        option.name: option.default
        for option
        in optionmap.values()
        if not option.required
    })


def load_environ():
    options = sourcemap['environ']
    options.clear()

    for option in optionmap.values():
        if option.envvar:
            val = os.getenv(option.envvar)
            if val:
                try:
                    options[opt] = option.parse(val)
                except ValueError as exc:
                    die(opt, val, f"{option.envvar} environment variable", exc)


def load_cli(argv):
    options = sourcemap['cli']
    options.clear()

    # Build the CLI
    def add_options(parser, options):
        for option in options:
            if not option.args:
                continue
            kwargs = {
                'dest': option.name,
                'action': option.action,
                'help': option.help,
                **{'nargs': o.nargs for o in (option,) if o.nargs},
                **{'metavar': o.metavar for o in (option,) if o.metavar},
                **{'const': o.const for o in (option,) if o.const},
            }
            try:
                parser.add_argument(*options.args, **kwargs)
            except Exception as exc:
                raise Exception(option) from exc

    main_parser = argparse.ArgumentParser(description=commandmap[''].desc)
    subparsers = main_parser.add_subparsers(dest='subcommand', required=True)
    for command in commandmap.values():
        parser = main_parser
        if command.name != '':
            parser = subparsers.add_parser(command.name, description=command.desc)
        add_options(parser, command.options)

        for group in command.groups:
            groupcli = parser.add_argument_group(group.title, group.desc)
            add_options(groupcli, group.options)

    # Parse args and process them
    cli_options = parse_args(main_parser, argv)
    Config.subcommand = cli_options.pop('subcommand')

    def parser(option):
        def parse(value):
            try:
                return option.parse(value)
            except ValueError as exc:
                die(option.name, value, "command line", exc)
        return parse

    def flatten(it):
        for e in it:
            if isinstance(e, CommaOption):
                yield e
            elif type(e) != str and isinstance(e, Iterable):
                yield from flatten(e)
            else:
                yield e

    for opt, val in cli_options.items():
        # Missing argument, skip
        if val is None:
            pass

        # Composite argument, parse each item and save the resulting list
        elif type(val) != str and isinstance(val, Iterable):
            val = list(flatten(map(parser(optionmap[opt]), val)))
            # parsing comma separated arguments like "-i base -i web,website"
            # gives a list of CommaOption like [("base",), ("web","website")],
            # we merge such lists into a single CommaOption
            if all(isinstance(e, CommaOption) for e in val):
                val = CommaOption._merge(val)
            options[opt] = val

        # Normal option, parse and save it
        else:
            options[opt] = parser(optionmap[opt])(val)


def load_file():
    configpath = config['config']
    try:
        if os.stat(configpath).st_mode & 0o777 != 0o600:
            warn(f"Wrong configuration file permissions at {configpath}, should be user-only read/write (0600).")
        p = configparser.RawConfigParser()
        p.read([configpath])
    except (FileNotFoundError, IOError):
        warn(f"Could not read configuration file at {configpath}, skipped.")
        return

    command_section = commandmap[Config.subcommand].section if Config.subcommand else None
    for sec in p.sections():
        options = sourcemap.setdefault('file' if sec == command_section else 'file_' + sec, {})
        options.clear()
        for opt, val in p.items(sec):
            # Skip unknown, non-file authorized and False/None invalid placeholders
            if opt not in optionmap:
                warn(f'unknown option {opt} in config file {configpath} in [{sec}], skipped.')
                continue
            if not optionmap[opt].file:
                warn(f"option {opt} cannot be read from config file, skipped.")
                continue
            if val in ('False', 'None') and optionmap[opt].parse != strtobool:
                warn(f"invalid value {val!r} for option {opt} in config file {configpath} in [{sec}], please remove it, skipped.")
                continue

            # Parse the option string
            try:
                options[opt] = optionmap[opt].parse(val)
            except ValueError as exc:
                die(opt, val, f"config file {configpath} in [{sec}]", exc)


########################################################################
#                                                                      #
#                     CHAINED CONFIGURATION OBJECT                     #
#                                                                      #
########################################################################


class Config(MutableMapping):
    subcommand = None

    def __init__(self, userchain=None, sectopts=None):
        self._userchain = userchain or ChainMap({})
        self._sectopts = sectopts or {}
        self._chainmap = ChainMap(
            self._userchain,
            sourcemap["cli"],
            self._sectopts,
            sourcemap["file"],
            sourcemap["environ"],
            sourcemap["default"],
        )

    def copy(self):
        return type(self)(
            ChainMap([
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
        class NotSet:
            def __repr__(self):
                return ''
        notset = NotSet()

        allsources = {'temp%i' % i: temp for i, temp in enumerate(self._userchain.maps[:-1])}
        allsources['user'] = self._userchain.maps[-1]
        allsources['cli'] = sourcemap['cli']
        allsources['[section]'] = self._sectopts
        allsources.update(sourcemap)

        sys.stdout.flush()
        sys.stderr.flush()
        print("{:<20}".format('option'), *["{:<20}".format(src) for src in allsources], sep=" | ")
        for no, option in enumerate(self):
            if no % 4 == 0:
                print("-|-".join("-" * 20 for i in range(len(allsources) + 1)))
            print("{:<20}".format(option)[:20], *["{:<20}".format(repr(src.get(option, notset)))[:20] for src in allsources.values()], sep=" | ")
        sys.stdout.flush()

    def save(self):
        """
        Export the currently exposed configuration with additionnal
        sections to a file
        """
        p = configparser.RawConfigParser()

        # command dedicated section, overwrite using current config skipping
        # deleted and not-set options.
        if self.subcommand:
            command = commandmap[self.subcommand]
            p.add_section(command.section)
            for opt in [command.options, *[grp.options for grp in command.groups]]:
                val = self._chainmap[opt.name]
                if any([val in [DELETED, None, sourcemap['default'][opt]],
                        not opt.file,
                        isinstance(val, Alias, Dynamic)]):
                    continue
                p.set(command.section, opt.name, opt.format(val))

        # other sections, rewrite them as-is
        for source, options in sourcemap.items():
            if not source.startswith('file_'):
                continue
            section = source[5:]
            p.add_section(section)
            for optname, val in options.items():
                p.set(section, optname, optionmap[optname].format(val))

        # ensure file exists and write on disk
        configpath = self["save"]
        if not configpath.exists():
            with contextlib.suppress(FileExistsError):
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
        option aliases or executing dynamic option function. A KeyError
        exception is raised for missing or removed options.
        """
        val = self._chainmap[option]
        if val is DELETED:
            raise KeyError(f'{option} has been removed')
        if isinstance(val, Alias):
            return self[val.aliased_option]
        if isinstance(val, Dynamic):
            return val.function(self)
        return val

    def __setitem__(self, option, value):
        """
        Set the corresponding option value in the top-most chained user
        dictionnary.
        """
        self._userchain[option] = value

    def __delitem__(self, option):
        """
        Mark the corresponding option as removed to prevent subsequent use
        """
        self._userchain[option] = DELETED

    def __iter__(self):
        return iter(self._chainmap)

    def __len__(self):
        return len(self._chainmap)

    @contextlib.contextmanager
    def override(self, tempopts=None):
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
            self._userchain.maps.remove(tempopts)

    @property
    def rcfile(self):
        return get_odoorc()

    @property
    def evented(self):
        return type(self).subcommand == 'gevent'

    @property
    def multi_process(self):
        return bool(self.get('workers'))

    @property
    def addons_data_dir(self):
        return os.path.join(self['data_dir'], 'addons')

    @property
    def session_dir(self):
        return os.path.join(self['data_dir'], 'sessions')

    def filestore(self, dbname):
        return os.path.join(self['data_dir'], 'filestore', dbname)


config = Config()
