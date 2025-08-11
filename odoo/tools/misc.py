# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""
Miscellaneous tools used by Odoo.
"""
from __future__ import annotations

import base64
import collections
import csv
import datetime
import enum
import hashlib
import hmac as hmac_lib
import itertools
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import traceback
import typing
import unicodedata
import warnings
import zlib
from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, MutableMapping, MutableSet, Reversible
from contextlib import ContextDecorator, contextmanager
from difflib import HtmlDiff
from functools import reduce, wraps
from itertools import islice, groupby as itergroupby
from operator import itemgetter

import babel
import babel.dates
import markupsafe
import pytz
from lxml import etree, objectify

# get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are moved to loglevels until we refactor tools.
from odoo.loglevels import exception_to_unicode, get_encodings, ustr  # noqa: F401

from .config import config
from .float_utils import float_round
from .which import which

K = typing.TypeVar('K')
T = typing.TypeVar('T')
if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence
    from odoo.api import Environment
    from odoo.addons.base.models.res_lang import LangData

    P = typing.TypeVar('P')

__all__ = [
    'DEFAULT_SERVER_DATETIME_FORMAT',
    'DEFAULT_SERVER_DATE_FORMAT',
    'DEFAULT_SERVER_TIME_FORMAT',
    'NON_BREAKING_SPACE',
    'SKIPPED_ELEMENT_TYPES',
    'DotDict',
    'LastOrderedSet',
    'OrderedSet',
    'Reverse',
    'babel_locale_parse',
    'clean_context',
    'consteq',
    'discardattr',
    'exception_to_unicode',
    'file_open',
    'file_open_temporary_directory',
    'file_path',
    'find_in_path',
    'formatLang',
    'format_amount',
    'format_date',
    'format_datetime',
    'format_duration',
    'format_time',
    'frozendict',
    'get_encodings',
    'get_iso_codes',
    'get_lang',
    'groupby',
    'hmac',
    'hash_sign',
    'verify_hash_signed',
    'html_escape',
    'human_size',
    'is_list_of',
    'merge_sequences',
    'mod10r',
    'mute_logger',
    'parse_date',
    'partition',
    'posix_to_ldml',
    'remove_accents',
    'replace_exceptions',
    'reverse_enumerate',
    'split_every',
    'str2bool',
    'street_split',
    'topological_sort',
    'unique',
    'ustr',
    'real_time',
]

_logger = logging.getLogger(__name__)

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (etree._Comment, etree._ProcessingInstruction, etree.CommentBase, etree.PIBase, etree._Entity)

# Configure default global parser
etree.set_default_parser(etree.XMLParser(resolve_entities=False))
default_parser = etree.XMLParser(resolve_entities=False, remove_blank_text=True)
default_parser.set_element_class_lookup(objectify.ObjectifyElementClassLookup())
objectify.set_default_parser(default_parser)

NON_BREAKING_SPACE = u'\N{NO-BREAK SPACE}'

# ensure we have a non patched time for query times when using freezegun
real_time = time.time.__call__  # type: ignore


class Sentinel(enum.Enum):
    """Class for typing parameters with a sentinel as a default"""
    SENTINEL = -1


SENTINEL = Sentinel.SENTINEL

#----------------------------------------------------------
# Subprocesses
#----------------------------------------------------------

def find_in_path(name):
    path = os.environ.get('PATH', os.defpath).split(os.pathsep)
    if config.get('bin_path') and config['bin_path'] != 'None':
        path.append(config['bin_path'])
    return which(name, path=os.pathsep.join(path))

# ----------------------------------------------------------
# Postgres subprocesses
# ----------------------------------------------------------


def find_pg_tool(name):
    path = None
    if config['pg_path'] and config['pg_path'] != 'None':
        path = config['pg_path']
    try:
        return which(name, path=path)
    except OSError:
        raise Exception('Command `%s` not found.' % name)


def exec_pg_environ():
    """
    Force the database PostgreSQL environment variables to the database
    configuration of Odoo.

    Note: On systems where pg_restore/pg_dump require an explicit password
    (i.e.  on Windows where TCP sockets are used), it is necessary to pass the
    postgres user password in the PGPASSWORD environment variable or in a
    special .pgpass file.

    See also https://www.postgresql.org/docs/current/libpq-envars.html
    """
    env = os.environ.copy()
    if config['db_host']:
        env['PGHOST'] = config['db_host']
    if config['db_port']:
        env['PGPORT'] = str(config['db_port'])
    if config['db_user']:
        env['PGUSER'] = config['db_user']
    if config['db_password']:
        env['PGPASSWORD'] = config['db_password']
    if config['db_app_name']:
        env['PGAPPNAME'] = config['db_app_name'].replace('{pid}', f'env{os.getpid()}')[:63]
    if config['db_sslmode']:
        env['PGSSLMODE'] = config['db_sslmode']
    return env


# ----------------------------------------------------------
# File paths
# ----------------------------------------------------------


def file_path(file_path: str, filter_ext: tuple[str, ...] = ('',), env: Environment | None = None, *, check_exists: bool = True) -> str:
    """Verify that a file exists under a known `addons_path` directory and return its full path.

    Examples::

    >>> file_path('hr')
    >>> file_path('hr/static/description/icon.png')
    >>> file_path('hr/static/description/icon.png', filter_ext=('.png', '.jpg'))

    :param str file_path: absolute file path, or relative path within any `addons_path` directory
    :param list[str] filter_ext: optional list of supported extensions (lowercase, with leading dot)
    :param env: optional environment, required for a file path within a temporary directory
        created using `file_open_temporary_directory()`
    :param check_exists: check that the file exists (default: True)
    :return: the absolute path to the file
    :raise FileNotFoundError: if the file is not found under the known `addons_path` directories
    :raise ValueError: if the file doesn't have one of the supported extensions (`filter_ext`)
    """
    import odoo.addons  # noqa: PLC0415
    is_abs = os.path.isabs(file_path)
    normalized_path = os.path.normpath(os.path.normcase(file_path))

    if filter_ext and not normalized_path.lower().endswith(filter_ext):
        raise ValueError("Unsupported file: " + file_path)

    # ignore leading 'addons/' if present, it's the final component of root_path, but
    # may sometimes be included in relative paths
    normalized_path = normalized_path.removeprefix('addons' + os.sep)

    # if path is relative and represents a loaded module, accept only the
    # __path__ for that module; otherwise, search in all accepted paths
    file_path_split = normalized_path.split(os.path.sep)
    if not is_abs and (module := sys.modules.get(f'odoo.addons.{file_path_split[0]}')):
        addons_paths = list(map(os.path.dirname, module.__path__))
    else:
        root_path = os.path.abspath(config.root_path)
        temporary_paths = env.transaction._Transaction__file_open_tmp_paths if env else ()
        addons_paths = [*odoo.addons.__path__, root_path, *temporary_paths]

    for addons_dir in addons_paths:
        # final path sep required to avoid partial match
        parent_path = os.path.normpath(os.path.normcase(addons_dir)) + os.sep
        if is_abs:
            fpath = normalized_path
        else:
            fpath = os.path.normpath(os.path.join(parent_path, normalized_path))
        if fpath.startswith(parent_path) and (
            # we check existence when asked or we have multiple paths to check
            # (there is one possibility for absolute paths)
            (not check_exists and (is_abs or len(addons_paths) == 1))
            or os.path.exists(fpath)
        ):
            return fpath

    raise FileNotFoundError("File not found: " + file_path)


def file_open(name: str, mode: str = "r", filter_ext: tuple[str, ...] = (), env: Environment | None = None):
    """Open a file from within the addons_path directories, as an absolute or relative path.

    Examples::

        >>> file_open('hr/static/description/icon.png')
        >>> file_open('hr/static/description/icon.png', filter_ext=('.png', '.jpg'))
        >>> with file_open('/opt/odoo/addons/hr/static/description/icon.png', 'rb') as f:
        ...     contents = f.read()

    :param name: absolute or relative path to a file located inside an addon
    :param mode: file open mode, as for `open()`
    :param list[str] filter_ext: optional list of supported extensions (lowercase, with leading dot)
    :param env: optional environment, required to open a file within a temporary directory
        created using `file_open_temporary_directory()`
    :return: file object, as returned by `open()`
    :raise FileNotFoundError: if the file is not found under the known `addons_path` directories
    :raise ValueError: if the file doesn't have one of the supported extensions (`filter_ext`)
    """
    path = file_path(name, filter_ext=filter_ext, env=env, check_exists=False)
    encoding = None
    if 'b' not in mode:
        # Force encoding for text mode, as system locale could affect default encoding,
        # even with the latest Python 3 versions.
        # Note: This is not covered by a unit test, due to the platform dependency.
        #       For testing purposes you should be able to force a non-UTF8 encoding with:
        #         `sudo locale-gen fr_FR; LC_ALL=fr_FR.iso8859-1 python3 ...'
        # See also PEP-540, although we can't rely on that at the moment.
        encoding = "utf-8"
    if any(m in mode for m in ('w', 'x', 'a')) and not os.path.isfile(path):
        # Don't let create new files
        raise FileNotFoundError(f"Not a file: {path}")
    return open(path, mode, encoding=encoding)


@contextmanager
def file_open_temporary_directory(env: Environment):
    """Create and return a temporary directory added to the directories `file_open` is allowed to read from.

    `file_open` will be allowed to open files within the temporary directory
    only for environments of the same transaction than `env`.
    Meaning, other transactions/requests from other users or even other databases
    won't be allowed to open files from this directory.

    Examples::

        >>> with odoo.tools.file_open_temporary_directory(self.env) as module_dir:
        ...    with zipfile.ZipFile('foo.zip', 'r') as z:
        ...        z.extract('foo/__manifest__.py', module_dir)
        ...    with odoo.tools.file_open('foo/__manifest__.py', env=self.env) as f:
        ...        manifest = f.read()

    :param env: environment for which the temporary directory is created.
    :return: the absolute path to the created temporary directory
    """
    assert not env.transaction._Transaction__file_open_tmp_paths, 'Reentrancy is not implemented for this method'
    with tempfile.TemporaryDirectory() as module_dir:
        try:
            env.transaction._Transaction__file_open_tmp_paths = (module_dir,)
            yield module_dir
        finally:
            env.transaction._Transaction__file_open_tmp_paths = ()


#----------------------------------------------------------
# iterables
#----------------------------------------------------------
def flatten(list):
    """Flatten a list of elements into a unique list
    Author: Christophe Simonis (christophe@tinyerp.com)

    Examples::
    >>> flatten(['a'])
    ['a']
    >>> flatten('b')
    ['b']
    >>> flatten( [] )
    []
    >>> flatten( [[], [[]]] )
    []
    >>> flatten( [[['a','b'], 'c'], 'd', ['e', [], 'f']] )
    ['a', 'b', 'c', 'd', 'e', 'f']
    >>> t = (1,2,(3,), [4, 5, [6, [7], (8, 9), ([10, 11, (12, 13)]), [14, [], (15,)], []]])
    >>> flatten(t)
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    """
    warnings.warn(
        "deprecated since 18.0",
        category=DeprecationWarning,
        stacklevel=2,
    )
    r = []
    for e in list:
        if isinstance(e, (bytes, str)) or not isinstance(e, collections.abc.Iterable):
            r.append(e)
        else:
            r.extend(flatten(e))
    return r


def reverse_enumerate(lst: Sequence[T]) -> Iterator[tuple[int, T]]:
    """Like enumerate but in the other direction

    Usage::

        >>> a = ['a', 'b', 'c']
        >>> it = reverse_enumerate(a)
        >>> it.next()
        (2, 'c')
        >>> it.next()
        (1, 'b')
        >>> it.next()
        (0, 'a')
        >>> it.next()
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        StopIteration
    """
    return zip(range(len(lst) - 1, -1, -1), reversed(lst))


def partition(pred: Callable[[T], bool], elems: Iterable[T]) -> tuple[list[T], list[T]]:
    """ Return a pair equivalent to:
    ``filter(pred, elems), filter(lambda x: not pred(x), elems)`` """
    yes: list[T] = []
    nos: list[T] = []
    for elem in elems:
        (yes if pred(elem) else nos).append(elem)
    return yes, nos


def topological_sort(elems: Mapping[T, Collection[T]]) -> list[T]:
    """ Return a list of elements sorted so that their dependencies are listed
    before them in the result.

    :param elems: specifies the elements to sort with their dependencies; it is
        a dictionary like `{element: dependencies}` where `dependencies` is a
        collection of elements that must appear before `element`. The elements
        of `dependencies` are not required to appear in `elems`; they will
        simply not appear in the result.

    :returns: a list with the keys of `elems` sorted according to their
        specification.
    """
    # the algorithm is inspired by [Tarjan 1976],
    # http://en.wikipedia.org/wiki/Topological_sorting#Algorithms
    result = []
    visited = set()

    def visit(n):
        if n not in visited:
            visited.add(n)
            if n in elems:
                # first visit all dependencies of n, then append n to result
                for it in elems[n]:
                    visit(it)
                result.append(n)

    for el in elems:
        visit(el)

    return result


def merge_sequences(*iterables: Iterable[T]) -> list[T]:
    """ Merge several iterables into a list. The result is the union of the
        iterables, ordered following the partial order given by the iterables,
        with a bias towards the end for the last iterable::

            seq = merge_sequences(['A', 'B', 'C'])
            assert seq == ['A', 'B', 'C']

            seq = merge_sequences(
                ['A', 'B', 'C'],
                ['Z'],                  # 'Z' can be anywhere
                ['Y', 'C'],             # 'Y' must precede 'C';
                ['A', 'X', 'Y'],        # 'X' must follow 'A' and precede 'Y'
            )
            assert seq == ['A', 'B', 'X', 'Y', 'C', 'Z']
    """
    # dict is ordered
    deps: defaultdict[T, list[T]] = defaultdict(list)  # {item: elems_before_item}
    for iterable in iterables:
        prev: T | Sentinel = SENTINEL
        for item in iterable:
            if prev is SENTINEL:
                deps[item]  # just set the default
            else:
                deps[item].append(prev)
            prev = item
    return topological_sort(deps)


def get_iso_codes(lang: str) -> str:
    if lang.find('_') != -1:
        lang_items = lang.split('_')
        if lang_items[0] == lang_items[1].lower():
            lang = lang_items[0]
    return lang


def scan_languages() -> list[tuple[str, str]]:
    """ Returns all languages supported by OpenERP for translation

    :returns: a list of (lang_code, lang_name) pairs
    :rtype: [(str, unicode)]
    """
    try:
        # read (code, name) from languages in base/data/res.lang.csv
        with file_open('base/data/res.lang.csv') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            fields = next(reader)
            code_index = fields.index("code")
            name_index = fields.index("name")
            result = [
                (row[code_index], row[name_index])
                for row in reader
            ]
    except Exception:
        _logger.error("Could not read res.lang.csv")
        result = []

    return sorted(result or [('en_US', u'English')], key=itemgetter(1))


def mod10r(number: str) -> str:
    """
    Input number : account or invoice number
    Output return: the same number completed with the recursive mod10
    key
    """
    codec=[0,9,4,6,8,2,7,1,3,5]
    report = 0
    result=""
    for digit in number:
        result += digit
        if digit.isdigit():
            report = codec[ (int(digit) + report) % 10 ]
    return result + str((10 - report) % 10)


def str2bool(s: str, default: bool | None = None) -> bool:
    # allow this (for now?) because it's used for get_param
    if type(s) is bool:
        return s  # type: ignore

    if not isinstance(s, str):
        warnings.warn(
            f"Passed a non-str to `str2bool`: {s}",
            DeprecationWarning,
            stacklevel=2,
        )

        if default is None:
            raise ValueError('Use 0/1/yes/no/true/false/on/off')
        return bool(default)

    s = s.lower()
    if s in ('y', 'yes', '1', 'true', 't', 'on'):
        return True
    if s in ('n', 'no', '0', 'false', 'f', 'off'):
        return False
    if default is None:
        raise ValueError('Use 0/1/yes/no/true/false/on/off')
    return bool(default)


def human_size(sz: float | str) -> str | typing.Literal[False]:
    """
    Return the size in a human readable format
    """
    if not sz:
        return False
    units = ('bytes', 'Kb', 'Mb', 'Gb', 'Tb')
    if isinstance(sz, str):
        sz=len(sz)
    s, i = float(sz), 0
    while s >= 1024 and i < len(units)-1:
        s /= 1024
        i += 1
    return "%0.2f %s" % (s, units[i])


DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_TIME_FORMAT)

DATE_LENGTH = len(datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))

# Python's strftime supports only the format directives
# that are available on the platform's libc, so in order to
# be cross-platform we map to the directives required by
# the C standard (1989 version), always available on platforms
# with a C standard implementation.
DATETIME_FORMATS_MAP = {
        '%C': '', # century
        '%D': '%m/%d/%Y', # modified %y->%Y
        '%e': '%d',
        '%E': '', # special modifier
        '%F': '%Y-%m-%d',
        '%g': '%Y', # modified %y->%Y
        '%G': '%Y',
        '%h': '%b',
        '%k': '%H',
        '%l': '%I',
        '%n': '\n',
        '%O': '', # special modifier
        '%P': '%p',
        '%R': '%H:%M',
        '%r': '%I:%M:%S %p',
        '%s': '', #num of seconds since epoch
        '%T': '%H:%M:%S',
        '%t': ' ', # tab
        '%u': ' %w',
        '%V': '%W',
        '%y': '%Y', # Even if %y works, it's ambiguous, so we should use %Y
        '%+': '%Y-%m-%d %H:%M:%S',

        # %Z is a special case that causes 2 problems at least:
        #  - the timezone names we use (in res_user.context_tz) come
        #    from pytz, but not all these names are recognized by
        #    strptime(), so we cannot convert in both directions
        #    when such a timezone is selected and %Z is in the format
        #  - %Z is replaced by an empty string in strftime() when
        #    there is not tzinfo in a datetime value (e.g when the user
        #    did not pick a context_tz). The resulting string does not
        #    parse back if the format requires %Z.
        # As a consequence, we strip it completely from format strings.
        # The user can always have a look at the context_tz in
        # preferences to check the timezone.
        '%z': '',
        '%Z': '',
}

POSIX_TO_LDML = {
    'a': 'E',
    'A': 'EEEE',
    'b': 'MMM',
    'B': 'MMMM',
    #'c': '',
    'd': 'dd',
    '-d': 'd',
    'H': 'HH',
    'I': 'hh',
    'j': 'DDD',
    'm': 'MM',
    '-m': 'M',
    'M': 'mm',
    'p': 'a',
    'S': 'ss',
    'U': 'w',
    'w': 'e',
    'W': 'w',
    'y': 'yy',
    'Y': 'yyyy',
    # see comments above, and babel's format_datetime assumes an UTC timezone
    # for naive datetime objects
    #'z': 'Z',
    #'Z': 'z',
}


def posix_to_ldml(fmt: str, locale: babel.Locale) -> str:
    """ Converts a posix/strftime pattern into an LDML date format pattern.

    :param fmt: non-extended C89/C90 strftime pattern
    :param locale: babel locale used for locale-specific conversions (e.g. %x and %X)
    :return: unicode
    """
    buf = []
    pc = False
    minus = False
    quoted = []

    for c in fmt:
        # LDML date format patterns uses letters, so letters must be quoted
        if not pc and c.isalpha():
            quoted.append(c if c != "'" else "''")
            continue
        if quoted:
            buf.append("'")
            buf.append(''.join(quoted))
            buf.append("'")
            quoted = []

        if pc:
            if c == '%': # escaped percent
                buf.append('%')
            elif c == 'x': # date format, short seems to match
                buf.append(locale.date_formats['short'].pattern)
            elif c == 'X': # time format, seems to include seconds. short does not
                buf.append(locale.time_formats['medium'].pattern)
            elif c == '-':
                minus = True
                continue
            else: # look up format char in static mapping
                if minus:
                    c = '-' + c
                    minus = False
                buf.append(POSIX_TO_LDML[c])
            pc = False
        elif c == '%':
            pc = True
        else:
            buf.append(c)

    # flush anything remaining in quoted buffer
    if quoted:
        buf.append("'")
        buf.append(''.join(quoted))
        buf.append("'")

    return ''.join(buf)


@typing.overload
def split_every(n: int, iterable: Iterable[T]) -> Iterator[tuple[T, ...]]:
    ...


@typing.overload
def split_every(n: int, iterable: Iterable[T], piece_maker: type[Collection[T]]) -> Iterator[Collection[T]]:
    ...


@typing.overload
def split_every(n: int, iterable: Iterable[T], piece_maker: Callable[[Iterable[T]], P]) -> Iterator[P]:
    ...


def split_every(n: int, iterable: Iterable[T], piece_maker=tuple):
    """Splits an iterable into length-n pieces. The last piece will be shorter
       if ``n`` does not evenly divide the iterable length.

       :param int n: maximum size of each generated chunk
       :param Iterable iterable: iterable to chunk into pieces
       :param piece_maker: callable taking an iterable and collecting each
                           chunk from its slice, *must consume the entire slice*.
    """
    iterator = iter(iterable)
    piece = piece_maker(islice(iterator, n))
    while piece:
        yield piece
        piece = piece_maker(islice(iterator, n))


def discardattr(obj: object, key: str) -> None:
    """ Perform a ``delattr(obj, key)`` but without crashing if ``key`` is not present. """
    try:
        delattr(obj, key)
    except AttributeError:
        pass

# ---------------------------------------------
# String management
# ---------------------------------------------


# Inspired by http://stackoverflow.com/questions/517923
def remove_accents(input_str: str) -> str:
    """Suboptimal-but-better-than-nothing way to replace accented
    latin letters by an ASCII equivalent. Will obviously change the
    meaning of input_str and work only for some cases"""
    if not input_str:
        return input_str
    nkfd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join(c for c in nkfd_form if not unicodedata.combining(c))


class unquote(str):
    """A subclass of str that implements repr() without enclosing quotation marks
       or escaping, keeping the original string untouched. The name come from Lisp's unquote.
       One of the uses for this is to preserve or insert bare variable names within dicts during eval()
       of a dict's repr(). Use with care.

       Some examples (notice that there are never quotes surrounding
       the ``active_id`` name:

       >>> unquote('active_id')
       active_id
       >>> d = {'test': unquote('active_id')}
       >>> d
       {'test': active_id}
       >>> print d
       {'test': active_id}
    """
    __slots__ = ()

    def __repr__(self):
        return self


class mute_logger(logging.Handler):
    """Temporary suppress the logging.

    Can be used as context manager or decorator::

        @mute_logger('odoo.plic.ploc')
        def do_stuff():
            blahblah()

        with mute_logger('odoo.foo.bar'):
            do_suff()
    """
    def __init__(self, *loggers):
        super().__init__()
        self.loggers = loggers
        self.old_params = {}

    def __enter__(self):
        for logger_name in self.loggers:
            logger = logging.getLogger(logger_name)
            self.old_params[logger_name] = (logger.handlers, logger.propagate)
            logger.propagate = False
            logger.handlers = [self]

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        for logger_name in self.loggers:
            logger = logging.getLogger(logger_name)
            logger.handlers, logger.propagate = self.old_params[logger_name]

    def __call__(self, func):
        @wraps(func)
        def deco(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return deco

    def emit(self, record):
        pass


class lower_logging(logging.Handler):
    """Temporary lower the max logging level.
    """
    def __init__(self, max_level, to_level=None):
        super().__init__()
        self.old_handlers = None
        self.old_propagate = None
        self.had_error_log = False
        self.max_level = max_level
        self.to_level = to_level or max_level

    def __enter__(self):
        logger = logging.getLogger()
        self.old_handlers = logger.handlers[:]
        self.old_propagate = logger.propagate
        logger.propagate = False
        logger.handlers = [self]
        self.had_error_log = False
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        logger = logging.getLogger()
        logger.handlers = self.old_handlers
        logger.propagate = self.old_propagate

    def emit(self, record):
        if record.levelno > self.max_level:
            record.levelname = f'_{record.levelname}'
            record.levelno = self.to_level
            self.had_error_log = True
            record.args = tuple(arg.replace('Traceback (most recent call last):', '_Traceback_ (most recent call last):') if isinstance(arg, str) else arg for arg in record.args)

        if logging.getLogger(record.name).isEnabledFor(record.levelno):
            for handler in self.old_handlers:
                if handler.level <= record.levelno:
                    handler.emit(record)


def stripped_sys_argv(*strip_args):
    """Return sys.argv with some arguments stripped, suitable for reexecution or subprocesses"""
    strip_args = sorted(set(strip_args) | set(['-s', '--save', '-u', '--update', '-i', '--init', '--i18n-overwrite']))
    assert all(config.parser.has_option(s) for s in strip_args)
    takes_value = dict((s, config.parser.get_option(s).takes_value()) for s in strip_args)

    longs, shorts = list(tuple(y) for _, y in itergroupby(strip_args, lambda x: x.startswith('--')))
    longs_eq = tuple(l + '=' for l in longs if takes_value[l])

    args = sys.argv[:]

    def strip(args, i):
        return args[i].startswith(shorts) \
            or args[i].startswith(longs_eq) or (args[i] in longs) \
            or (i >= 1 and (args[i - 1] in strip_args) and takes_value[args[i - 1]])

    return [x for i, x in enumerate(args) if not strip(args, i)]


class ConstantMapping(Mapping[typing.Any, T], typing.Generic[T]):
    """
    An immutable mapping returning the provided value for every single key.

    Useful for default value to methods
    """
    __slots__ = ['_value']

    def __init__(self, val: T):
        self._value = val

    def __len__(self):
        """
        defaultdict updates its length for each individually requested key, is
        that really useful?
        """
        return 0

    def __iter__(self):
        """
        same as len, defaultdict updates its iterable keyset with each key
        requested, is there a point for this?
        """
        return iter([])

    def __getitem__(self, item) -> T:
        return self._value


def dumpstacks(sig=None, frame=None, thread_idents=None, log_level=logging.INFO):
    """ Signal handler: dump a stack trace for each existing thread or given
    thread(s) specified through the ``thread_idents`` sequence.
    """
    code = []

    def extract_stack(stack):
        for filename, lineno, name, line in traceback.extract_stack(stack):
            yield 'File: "%s", line %d, in %s' % (filename, lineno, name)
            if line:
                yield "  %s" % (line.strip(),)

    # code from http://stackoverflow.com/questions/132058/getting-stack-trace-from-a-running-python-application#answer-2569696
    # modified for python 2.5 compatibility
    threads_info = {th.ident: {'repr': repr(th),
                               'uid': getattr(th, 'uid', 'n/a'),
                               'dbname': getattr(th, 'dbname', 'n/a'),
                               'url': getattr(th, 'url', 'n/a'),
                               'query_count': getattr(th, 'query_count', 'n/a'),
                               'query_time': getattr(th, 'query_time', None),
                               'perf_t0': getattr(th, 'perf_t0', None)}
                    for th in threading.enumerate()}
    for threadId, stack in sys._current_frames().items():
        if not thread_idents or threadId in thread_idents:
            thread_info = threads_info.get(threadId, {})
            query_time = thread_info.get('query_time')
            perf_t0 = thread_info.get('perf_t0')
            remaining_time = None
            if query_time is not None and perf_t0:
                remaining_time = '%.3f' % (real_time() - perf_t0 - query_time)
                query_time = '%.3f' % query_time
            # qc:query_count qt:query_time pt:python_time (aka remaining time)
            code.append("\n# Thread: %s (db:%s) (uid:%s) (url:%s) (qc:%s qt:%s pt:%s)" %
                        (thread_info.get('repr', threadId),
                         thread_info.get('dbname', 'n/a'),
                         thread_info.get('uid', 'n/a'),
                         thread_info.get('url', 'n/a'),
                         thread_info.get('query_count', 'n/a'),
                         query_time or 'n/a',
                         remaining_time or 'n/a'))
            for line in extract_stack(stack):
                code.append(line)

    import odoo  # eventd
    if odoo.evented:
        # code from http://stackoverflow.com/questions/12510648/in-gevent-how-can-i-dump-stack-traces-of-all-running-greenlets
        import gc
        from greenlet import greenlet
        for ob in gc.get_objects():
            if not isinstance(ob, greenlet) or not ob:
                continue
            code.append("\n# Greenlet: %r" % (ob,))
            for line in extract_stack(ob.gr_frame):
                code.append(line)

    _logger.log(log_level, "\n".join(code))


def freehash(arg: typing.Any) -> int:
    try:
        return hash(arg)
    except Exception:
        if isinstance(arg, Mapping):
            return hash(frozendict(arg))
        elif isinstance(arg, Iterable):
            return hash(frozenset(freehash(item) for item in arg))
        else:
            return id(arg)


def clean_context(context: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """ This function take a dictionary and remove each entry with its key
    starting with ``default_``
    """
    return {k: v for k, v in context.items() if not k.startswith('default_')}


class frozendict(dict[K, T], typing.Generic[K, T]):
    """ An implementation of an immutable dictionary. """
    __slots__ = ()

    def __delitem__(self, key):
        raise NotImplementedError("'__delitem__' not supported on frozendict")

    def __setitem__(self, key, val):
        raise NotImplementedError("'__setitem__' not supported on frozendict")

    def clear(self):
        raise NotImplementedError("'clear' not supported on frozendict")

    def pop(self, key, default=None):
        raise NotImplementedError("'pop' not supported on frozendict")

    def popitem(self):
        raise NotImplementedError("'popitem' not supported on frozendict")

    def setdefault(self, key, default=None):
        raise NotImplementedError("'setdefault' not supported on frozendict")

    def update(self, *args, **kwargs):
        raise NotImplementedError("'update' not supported on frozendict")

    def __hash__(self) -> int:  # type: ignore
        return hash(frozenset((key, freehash(val)) for key, val in self.items()))


class Collector(dict[K, tuple[T, ...]], typing.Generic[K, T]):
    """ A mapping from keys to tuples.  This implements a relation, and can be
        seen as a space optimization for ``defaultdict(tuple)``.
    """
    __slots__ = ()

    def __getitem__(self, key: K) -> tuple[T, ...]:
        return self.get(key, ())

    def __setitem__(self, key: K, val: Iterable[T]):
        val = tuple(val)
        if val:
            super().__setitem__(key, val)
        else:
            super().pop(key, None)

    def add(self, key: K, val: T):
        vals = self[key]
        if val not in vals:
            self[key] = vals + (val,)

    def discard_keys_and_values(self, excludes: Collection[K | T]) -> None:
        for key in excludes:
            self.pop(key, None)  # type: ignore
        for key, vals in list(self.items()):
            self[key] = tuple(val for val in vals if val not in excludes)  # type: ignore


class StackMap(MutableMapping[K, T], typing.Generic[K, T]):
    """ A stack of mappings behaving as a single mapping, and used to implement
        nested scopes. The lookups search the stack from top to bottom, and
        returns the first value found. Mutable operations modify the topmost
        mapping only.
    """
    __slots__ = ['_maps']

    def __init__(self, m: MutableMapping[K, T] | None = None):
        self._maps = [] if m is None else [m]

    def __getitem__(self, key: K) -> T:
        for mapping in reversed(self._maps):
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key: K, val: T):
        self._maps[-1][key] = val

    def __delitem__(self, key: K):
        del self._maps[-1][key]

    def __iter__(self) -> Iterator[K]:
        return iter({key for mapping in self._maps for key in mapping})

    def __len__(self) -> int:
        return sum(1 for key in self)

    def __str__(self) -> str:
        return f"<StackMap {self._maps}>"

    def pushmap(self, m: MutableMapping[K, T] | None = None):
        self._maps.append({} if m is None else m)

    def popmap(self) -> MutableMapping[K, T]:
        return self._maps.pop()


class OrderedSet(MutableSet[T], typing.Generic[T]):
    """ A set collection that remembers the elements first insertion order. """
    __slots__ = ['_map']

    def __init__(self, elems: Iterable[T] = ()):
        self._map: dict[T, None] = dict.fromkeys(elems)

    def __contains__(self, elem):
        return elem in self._map

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def add(self, elem):
        self._map[elem] = None

    def discard(self, elem):
        self._map.pop(elem, None)

    def update(self, elems):
        self._map.update(zip(elems, itertools.repeat(None)))

    def difference_update(self, elems):
        for elem in elems:
            self.discard(elem)

    def __repr__(self):
        return f'{type(self).__name__}({list(self)!r})'

    def intersection(self, *others):
        return reduce(OrderedSet.__and__, others, self)


class LastOrderedSet(OrderedSet[T], typing.Generic[T]):
    """ A set collection that remembers the elements last insertion order. """
    def add(self, elem):
        self.discard(elem)
        super().add(elem)


class Callbacks:
    """ A simple queue of callback functions.  Upon run, every function is
    called (in addition order), and the queue is emptied.

    ::

        callbacks = Callbacks()

        # add foo
        def foo():
            print("foo")

        callbacks.add(foo)

        # add bar
        callbacks.add
        def bar():
            print("bar")

        # add foo again
        callbacks.add(foo)

        # call foo(), bar(), foo(), then clear the callback queue
        callbacks.run()

    The queue also provides a ``data`` dictionary, that may be freely used to
    store anything, but is mostly aimed at aggregating data for callbacks.  The
    dictionary is automatically cleared by ``run()`` once all callback functions
    have been called.

    ::

        # register foo to process aggregated data
        @callbacks.add
        def foo():
            print(sum(callbacks.data['foo']))

        callbacks.data.setdefault('foo', []).append(1)
        ...
        callbacks.data.setdefault('foo', []).append(2)
        ...
        callbacks.data.setdefault('foo', []).append(3)

        # call foo(), which prints 6
        callbacks.run()

    Given the global nature of ``data``, the keys should identify in a unique
    way the data being stored.  It is recommended to use strings with a
    structure like ``"{module}.{feature}"``.
    """
    __slots__ = ['_funcs', 'data']

    def __init__(self):
        self._funcs: collections.deque[Callable] = collections.deque()
        self.data = {}

    def add(self, func: Callable) -> None:
        """ Add the given function. """
        self._funcs.append(func)

    def run(self) -> None:
        """ Call all the functions (in addition order), then clear associated data.
        """
        while self._funcs:
            func = self._funcs.popleft()
            func()
        self.clear()

    def clear(self) -> None:
        """ Remove all callbacks and data from self. """
        self._funcs.clear()
        self.data.clear()


class ReversedIterable(Reversible[T], typing.Generic[T]):
    """ An iterable implementing the reversal of another iterable. """
    __slots__ = ['iterable']

    def __init__(self, iterable: Reversible[T]):
        self.iterable = iterable

    def __iter__(self):
        return reversed(self.iterable)

    def __reversed__(self):
        return iter(self.iterable)


def groupby(iterable: Iterable[T], key: Callable[[T], K] = lambda arg: arg) -> Iterable[tuple[K, list[T]]]:
    """ Return a collection of pairs ``(key, elements)`` from ``iterable``. The
        ``key`` is a function computing a key value for each element. This
        function is similar to ``itertools.groupby``, but aggregates all
        elements under the same key, not only consecutive elements.
    """
    groups = defaultdict(list)
    for elem in iterable:
        groups[key(elem)].append(elem)
    return groups.items()


def unique(it: Iterable[T]) -> Iterator[T]:
    """ "Uniquifier" for the provided iterable: will output each element of
    the iterable once.

    The iterable's elements must be hashahble.

    :param Iterable it:
    :rtype: Iterator
    """
    seen = set()
    for e in it:
        if e not in seen:
            seen.add(e)
            yield e


def submap(mapping: Mapping[K, T], keys: Iterable[K]) -> Mapping[K, T]:
    """
    Get a filtered copy of the mapping where only some keys are present.

    :param Mapping mapping: the original dict-like structure to filter
    :param Iterable keys: the list of keys to keep
    :return dict: a filtered dict copy of the original mapping
    """
    keys = frozenset(keys)
    return {key: mapping[key] for key in mapping if key in keys}


class Reverse(object):
    """ Wraps a value and reverses its ordering, useful in key functions when
    mixing ascending and descending sort on non-numeric data as the
    ``reverse`` parameter can not do piecemeal reordering.
    """
    __slots__ = ['val']

    def __init__(self, val):
        self.val = val

    def __eq__(self, other): return self.val == other.val
    def __ne__(self, other): return self.val != other.val

    def __ge__(self, other): return self.val <= other.val
    def __gt__(self, other): return self.val < other.val
    def __le__(self, other): return self.val >= other.val
    def __lt__(self, other): return self.val > other.val

class replace_exceptions(ContextDecorator):
    """
    Hide some exceptions behind another error. Can be used as a function
    decorator or as a context manager.

    .. code-block:

        @route('/super/secret/route', auth='public')
        @replace_exceptions(AccessError, by=NotFound())
        def super_secret_route(self):
            if not request.session.uid:
                raise AccessError("Route hidden to non logged-in users")
            ...

        def some_util():
            ...
            with replace_exceptions(ValueError, by=UserError("Invalid argument")):
                ...
            ...

    :param exceptions: the exception classes to catch and replace.
    :param by: the exception to raise instead.
    """
    def __init__(self, *exceptions, by):
        if not exceptions:
            raise ValueError("Missing exceptions")

        wrong_exc = next((exc for exc in exceptions if not issubclass(exc, Exception)), None)
        if wrong_exc:
            raise TypeError(f"{wrong_exc} is not an exception class.")

        self.exceptions = exceptions
        self.by = by

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None and issubclass(exc_type, self.exceptions):
            if isinstance(self.by, type) and exc_value.args:
                # copy the message
                raise self.by(exc_value.args[0]) from exc_value
            else:
                raise self.by from exc_value


html_escape = markupsafe.escape


def get_lang(env: Environment, lang_code: str | None = None) -> LangData:
    """
    Retrieve the first lang object installed, by checking the parameter lang_code,
    the context and then the company. If no lang is installed from those variables,
    fallback on english or on the first lang installed in the system.

    :param env:
    :param str lang_code: the locale (i.e. en_US)
    :return LangData: the first lang found that is installed on the system.
    """
    langs = [code for code, _ in env['res.lang'].get_installed()]
    lang = 'en_US' if 'en_US' in langs else langs[0]
    if lang_code and lang_code in langs:
        lang = lang_code
    elif (context_lang := env.context.get('lang')) in langs:
        lang = context_lang
    elif (company_lang := env.user.with_context(lang='en_US').company_id.partner_id.lang) in langs:
        lang = company_lang
    return env['res.lang']._get_data(code=lang)


def babel_locale_parse(lang_code: str | None) -> babel.Locale:
    if lang_code:
        try:
            return babel.Locale.parse(lang_code)
        except Exception:  # noqa: BLE001
            pass
    try:
        return babel.Locale.default()
    except Exception:  # noqa: BLE001
        return babel.Locale.parse("en_US")


def formatLang(
    env: Environment,
    value: float | typing.Literal[''],
    digits: int = 2,
    grouping: bool = True,
    dp: str | None = None,
    currency_obj: typing.Any | None = None,
    rounding_method: typing.Literal['HALF-UP', 'HALF-DOWN', 'HALF-EVEN', "UP", "DOWN"] = 'HALF-EVEN',
    rounding_unit: typing.Literal['decimals', 'units', 'thousands', 'lakhs', 'millions'] = 'decimals',
) -> str:
    """
    This function will format a number `value` to the appropriate format of the language used.

    :param env: The environment.
    :param value: The value to be formatted.
    :param digits: The number of decimals digits.
    :param grouping: Usage of language grouping or not.
    :param dp: Name of the decimals precision to be used. This will override ``digits``
                   and ``currency_obj`` precision.
    :param currency_obj: Currency to be used. This will override ``digits`` precision.
    :param rounding_method: The rounding method to be used:
        **'HALF-UP'** will round to the closest number with ties going away from zero,
        **'HALF-DOWN'** will round to the closest number with ties going towards zero,
        **'HALF_EVEN'** will round to the closest number with ties going to the closest
        even number,
        **'UP'** will always round away from 0,
        **'DOWN'** will always round towards 0.
    :param rounding_unit: The rounding unit to be used:
        **decimals** will round to decimals with ``digits`` or ``dp`` precision,
        **units** will round to units without any decimals,
        **thousands** will round to thousands without any decimals,
        **lakhs** will round to lakhs without any decimals,
        **millions** will round to millions without any decimals.

    :returns: The value formatted.
    """
    # We don't want to return 0
    if value == '':
        return ''

    if rounding_unit == 'decimals':
        if dp:
            digits = env['decimal.precision'].precision_get(dp)
        elif currency_obj:
            digits = currency_obj.decimal_places
    else:
        digits = 0

    rounding_unit_mapping = {
        'decimals': 1,
        'thousands': 10**3,
        'lakhs': 10**5,
        'millions': 10**6,
        'units': 1,
    }

    value /= rounding_unit_mapping[rounding_unit]

    rounded_value = float_round(value, precision_digits=digits, rounding_method=rounding_method)
    lang = env['res.lang'].browse(get_lang(env).id)
    formatted_value = lang.format(f'%.{digits}f', rounded_value, grouping=grouping)

    if currency_obj and currency_obj.symbol:
        arguments = (formatted_value, NON_BREAKING_SPACE, currency_obj.symbol)

        return '%s%s%s' % (arguments if currency_obj.position == 'after' else arguments[::-1])

    return formatted_value


def format_date(
    env: Environment,
    value: datetime.datetime | datetime.date | str,
    lang_code: str | None = None,
    date_format: str | typing.Literal[False] = False,
) -> str:
    """
        Formats the date in a given format.

        :param env: an environment.
        :param date, datetime or string value: the date to format.
        :param string lang_code: the lang code, if not specified it is extracted from the
            environment context.
        :param string date_format: the format or the date (LDML format), if not specified the
            default format of the lang.
        :return: date formatted in the specified format.
        :rtype: string
    """
    if not value:
        return ''
    from odoo.fields import Datetime  # noqa: PLC0415
    if isinstance(value, str):
        if len(value) < DATE_LENGTH:
            return ''
        if len(value) > DATE_LENGTH:
            # a datetime, convert to correct timezone
            value = Datetime.from_string(value)
            value = Datetime.context_timestamp(env['res.lang'], value)
        else:
            value = Datetime.from_string(value)
    elif isinstance(value, datetime.datetime) and not value.tzinfo:
        # a datetime, convert to correct timezone
        value = Datetime.context_timestamp(env['res.lang'], value)

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not date_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)

    assert isinstance(value, datetime.date)  # datetime is a subclass of date
    return babel.dates.format_date(value, format=date_format, locale=locale)


def parse_date(env: Environment, value: str, lang_code: str | None = None) -> datetime.date | str:
    """
        Parse the date from a given format. If it is not a valid format for the
        localization, return the original string.

        :param env: an environment.
        :param string value: the date to parse.
        :param string lang_code: the lang code, if not specified it is extracted from the
            environment context.
        :return: date object from the localized string
        :rtype: datetime.date
    """
    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    try:
        return babel.dates.parse_date(value, locale=locale)
    except Exception:  # noqa: BLE001
        return value


def format_datetime(
    env: Environment,
    value: datetime.datetime | str,
    tz: str | typing.Literal[False] = False,
    dt_format: str = 'medium',
    lang_code: str | None = None,
) -> str:
    """ Formats the datetime in a given format.

    :param env:
    :param str|datetime value: naive datetime to format either in string or in datetime
    :param str tz: name of the timezone  in which the given datetime should be localized
    :param str dt_format: one of “full”, “long”, “medium”, or “short”, or a custom date/time pattern compatible with `babel` lib
    :param str lang_code: ISO code of the language to use to render the given datetime
    :rtype: str
    """
    if not value:
        return ''
    if isinstance(value, str):
        from odoo.fields import Datetime  # noqa: PLC0415
        timestamp = Datetime.from_string(value)
    else:
        timestamp = value

    tz_name = tz or env.user.tz or 'UTC'
    utc_datetime = pytz.utc.localize(timestamp, is_dst=False)
    try:
        context_tz = pytz.timezone(tz_name)
        localized_datetime = utc_datetime.astimezone(context_tz)
    except Exception:
        localized_datetime = utc_datetime

    lang = get_lang(env, lang_code)

    locale = babel_locale_parse(lang.code or lang_code)  # lang can be inactive, so `lang`is empty
    if not dt_format or dt_format == 'medium':
        date_format = posix_to_ldml(lang.date_format, locale=locale)
        time_format = posix_to_ldml(lang.time_format, locale=locale)
        dt_format = '%s %s' % (date_format, time_format)

    # Babel allows to format datetime in a specific language without change locale
    # So month 1 = January in English, and janvier in French
    # Be aware that the default value for format is 'medium', instead of 'short'
    #     medium:  Jan 5, 2016, 10:20:31 PM |   5 janv. 2016 22:20:31
    #     short:   1/5/16, 10:20 PM         |   5/01/16 22:20
    # Formatting available here : http://babel.pocoo.org/en/latest/dates.html#date-fields
    return babel.dates.format_datetime(localized_datetime, dt_format, locale=locale)


def format_time(
    env: Environment,
    value: datetime.time | datetime.datetime | str,
    tz: str | typing.Literal[False] = False,
    time_format: str = 'medium',
    lang_code: str | None = None,
) -> str:
    """ Format the given time (hour, minute and second) with the current user preference (language, format, ...)

        :param env:
        :param value: the time to format
        :type value: `datetime.time` instance. Could be timezoned to display tzinfo according to format (e.i.: 'full' format)
        :param tz: name of the timezone  in which the given datetime should be localized
        :param time_format: one of “full”, “long”, “medium”, or “short”, or a custom time pattern
        :param lang_code: ISO

        :rtype str
    """
    if not value:
        return ''

    if isinstance(value, datetime.time):
        localized_time = value
    else:
        if isinstance(value, str):
            from odoo.fields import Datetime  # noqa: PLC0415
            value = Datetime.from_string(value)
        assert isinstance(value, datetime.datetime)
        tz_name = tz or env.user.tz or 'UTC'
        utc_datetime = pytz.utc.localize(value, is_dst=False)
        try:
            context_tz = pytz.timezone(tz_name)
            localized_time = utc_datetime.astimezone(context_tz).timetz()
        except Exception:
            localized_time = utc_datetime.timetz()

    lang = get_lang(env, lang_code)
    locale = babel_locale_parse(lang.code)
    if not time_format or time_format == 'medium':
        time_format = posix_to_ldml(lang.time_format, locale=locale)

    return babel.dates.format_time(localized_time, format=time_format, locale=locale)


def _format_time_ago(
    env: Environment,
    time_delta: datetime.timedelta,
    lang_code: str | None = None,
    add_direction: bool = True,
) -> str:
    if not lang_code:
        langs: list[str] = [code for code, _ in env['res.lang'].get_installed()]
        if (ctx_lang := env.context.get('lang')) in langs:
            lang_code = ctx_lang
        else:
            lang_code = env.user.company_id.partner_id.lang or langs[0]
        assert isinstance(lang_code, str)
    locale = babel_locale_parse(lang_code)
    return babel.dates.format_timedelta(-time_delta, add_direction=add_direction, locale=locale)


def format_decimalized_number(number: float, decimal: int = 1) -> str:
    """Format a number to display to nearest metrics unit next to it.

    Do not display digits if all visible digits are null.
    Do not display units higher then "Tera" because most people don't know what
    a "Yotta" is.

    ::

        >>> format_decimalized_number(123_456.789)
        123.5k
        >>> format_decimalized_number(123_000.789)
        123k
        >>> format_decimalized_number(-123_456.789)
        -123.5k
        >>> format_decimalized_number(0.789)
        0.8
    """
    for unit in ['', 'k', 'M', 'G']:
        if abs(number) < 1000.0:
            return "%g%s" % (round(number, decimal), unit)
        number /= 1000.0
    return "%g%s" % (round(number, decimal), 'T')


def format_decimalized_amount(amount: float, currency=None) -> str:
    """Format an amount to display the currency and also display the metric unit
    of the amount.

    ::

        >>> format_decimalized_amount(123_456.789, env.ref("base.USD"))
        $123.5k
    """
    formated_amount = format_decimalized_number(amount)

    if not currency:
        return formated_amount

    if currency.position == 'before':
        return "%s%s" % (currency.symbol or '', formated_amount)

    return "%s %s" % (formated_amount, currency.symbol or '')


def format_amount(env: Environment, amount: float, currency, lang_code: str | None = None, trailing_zeroes: bool = True) -> str:
    fmt = "%.{0}f".format(currency.decimal_places)
    lang = env['res.lang'].browse(get_lang(env, lang_code).id)

    formatted_amount = lang.format(fmt, currency.round(amount), grouping=True)\
        .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

    if not trailing_zeroes:
        formatted_amount = re.sub(fr'{re.escape(lang.decimal_point)}?0+$', '', formatted_amount)

    pre = post = u''
    if currency.position == 'before':
        pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
    else:
        post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')

    return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)


def format_duration(value: float) -> str:
    """ Format a float: used to display integral or fractional values as
        human-readable time spans (e.g. 1.5 as "01:30").
    """
    hours, minutes = divmod(abs(value) * 60, 60)
    minutes = round(minutes)
    if minutes == 60:
        minutes = 0
        hours += 1
    if value < 0:
        return '-%02d:%02d' % (hours, minutes)
    return '%02d:%02d' % (hours, minutes)


consteq = hmac_lib.compare_digest


class ReadonlyDict(Mapping[K, T], typing.Generic[K, T]):
    """Helper for an unmodifiable dictionary, not even updatable using `dict.update`.

    This is similar to a `frozendict`, with one drawback and one advantage:

    - `dict.update` works for a `frozendict` but not for a `ReadonlyDict`.
    - `json.dumps` works for a `frozendict` by default but not for a `ReadonlyDict`.

    This comes from the fact `frozendict` inherits from `dict`
    while `ReadonlyDict` inherits from `collections.abc.Mapping`.

    So, depending on your needs,
    whether you absolutely must prevent the dictionary from being updated (e.g., for security reasons)
    or you require it to be supported by `json.dumps`, you can choose either option.

        E.g.
          data = ReadonlyDict({'foo': 'bar'})
          data['baz'] = 'xyz' # raises exception
          data.update({'baz', 'xyz'}) # raises exception
          dict.update(data, {'baz': 'xyz'}) # raises exception
    """
    __slots__ = ('_data__',)

    def __init__(self, data):
        self._data__ = dict(data)

    def __contains__(self, key: K):
        return key in self._data__

    def __getitem__(self, key: K) -> T:
        return self._data__[key]

    def __len__(self):
        return len(self._data__)

    def __iter__(self):
        return iter(self._data__)


class DotDict(dict):
    """Helper for dot.notation access to dictionary attributes

        E.g.
          foo = DotDict({'bar': False})
          return foo.bar
    """
    def __getattr__(self, attrib):
        val = self.get(attrib)
        return DotDict(val) if isinstance(val, dict) else val


def get_diff(data_from, data_to, custom_style=False, dark_color_scheme=False):
    """
    Return, in an HTML table, the diff between two texts.

    :param tuple data_from: tuple(text, name), name will be used as table header
    :param tuple data_to: tuple(text, name), name will be used as table header
    :param tuple custom_style: string, style css including <style> tag.
    :param bool dark_color_scheme: true if dark color scheme is used
    :return: a string containing the diff in an HTML table format.
    """
    def handle_style(html_diff, custom_style, dark_color_scheme):
        """ The HtmlDiff lib will add some useful classes on the DOM to
        identify elements. Simply append to those classes some BS4 ones.
        For the table to fit the modal width, some custom style is needed.
        """
        to_append = {
            'diff_header': 'bg-600 text-light text-center align-top px-2',
            'diff_next': 'd-none',
        }
        for old, new in to_append.items():
            html_diff = html_diff.replace(old, "%s %s" % (old, new))
        html_diff = html_diff.replace('nowrap', '')
        colors = ('#7f2d2f', '#406a2d', '#51232f', '#3f483b') if dark_color_scheme else (
            '#ffc1c0', '#abf2bc', '#ffebe9', '#e6ffec')
        html_diff += custom_style or '''
            <style>
                .modal-dialog.modal-lg:has(table.diff) {
                    max-width: 1600px;
                    padding-left: 1.75rem;
                    padding-right: 1.75rem;
                }
                table.diff { width: 100%%; }
                table.diff th.diff_header { width: 50%%; }
                table.diff td.diff_header { white-space: nowrap; }
                table.diff td.diff_header + td { width: 50%%; }
                table.diff td { word-break: break-all; vertical-align: top; }
                table.diff .diff_chg, table.diff .diff_sub, table.diff .diff_add {
                    display: inline-block;
                    color: inherit;
                }
                table.diff .diff_sub, table.diff td:nth-child(3) > .diff_chg { background-color: %s }
                table.diff .diff_add, table.diff td:nth-child(6) > .diff_chg { background-color: %s }
                table.diff td:nth-child(3):has(>.diff_chg, .diff_sub) { background-color: %s }
                table.diff td:nth-child(6):has(>.diff_chg, .diff_add) { background-color: %s }
            </style>
        ''' % colors
        return html_diff

    diff = HtmlDiff(tabsize=2).make_table(
        data_from[0].splitlines(),
        data_to[0].splitlines(),
        data_from[1],
        data_to[1],
        context=True,  # Show only diff lines, not all the code
        numlines=3,
    )
    return handle_style(diff, custom_style, dark_color_scheme)


def hmac(env, scope, message, hash_function=hashlib.sha256):
    """Compute HMAC with `database.secret` config parameter as key.

    :param env: sudo environment to use for retrieving config parameter
    :param message: message to authenticate
    :param scope: scope of the authentication, to have different signature for the same
        message in different usage
    :param hash_function: hash function to use for HMAC (default: SHA-256)
    """
    if not scope:
        raise ValueError('Non-empty scope required')

    secret = env['ir.config_parameter'].get_param('database.secret')
    message = repr((scope, message))
    return hmac_lib.new(
        secret.encode(),
        message.encode(),
        hash_function,
    ).hexdigest()


def hash_sign(env, scope, message_values, expiration=None, expiration_hours=None):
    """ Generate an urlsafe payload signed with the HMAC signature for an iterable set of data.
    This feature is very similar to JWT, but in a more generic implementation that is inline with out previous hmac implementation.

    :param env: sudo environment to use for retrieving config parameter
    :param scope: scope of the authentication, to have different signature for the same
        message in different usage
    :param message_values: values to be encoded inside the payload
    :param expiration: optional, a datetime or timedelta
    :param expiration_hours: optional, a int representing a number of hours before expiration. Cannot be set at the same time as expiration
    :return: the payload that can be used as a token
    """
    assert not (expiration and expiration_hours)
    assert message_values is not None

    if expiration_hours:
        expiration = datetime.datetime.now() + datetime.timedelta(hours=expiration_hours)
    else:
        if isinstance(expiration, datetime.timedelta):
            expiration = datetime.datetime.now() + expiration
    expiration_timestamp = 0 if not expiration else int(expiration.timestamp())
    message_strings = json.dumps(message_values)
    hash_value = hmac(env, scope, f'1:{message_strings}:{expiration_timestamp}', hash_function=hashlib.sha256)
    token = b"\x01" + expiration_timestamp.to_bytes(8, 'little') + bytes.fromhex(hash_value) + message_strings.encode()
    return base64.urlsafe_b64encode(token).decode().rstrip('=')


def verify_hash_signed(env, scope, payload):
    """ Verify and extract data from a given urlsafe  payload generated with hash_sign()

    :param env: sudo environment to use for retrieving config parameter
    :param scope: scope of the authentication, to have different signature for the same
        message in different usage
    :param payload: the token to verify
    :return: The payload_values if the check was successful, None otherwise.
    """

    token = base64.urlsafe_b64decode(payload.encode()+b'===')
    version = token[:1]
    if version != b'\x01':
        raise ValueError('Unknown token version')

    expiration_value, hash_value, message = token[1:9], token[9:41].hex(), token[41:].decode()
    expiration_value = int.from_bytes(expiration_value, byteorder='little')
    hash_value_expected = hmac(env, scope, f'1:{message}:{expiration_value}', hash_function=hashlib.sha256)

    if consteq(hash_value, hash_value_expected) and (expiration_value == 0 or datetime.datetime.now().timestamp() < expiration_value):
        message_values = json.loads(message)
        return message_values
    return None


def limited_field_access_token(record, field_name, timestamp=None, *, scope):
    """Generate a token granting access to the given record and field_name in
    the given scope.

    The validitiy of the token is determined by the timestamp parameter.
    When it is not specified, a timestamp is automatically generated with a
    validity of at least 14 days. For a given record and field_name, the
    generated timestamp is deterministic within a 14-day period (even across
    different days/months/years) to allow browser caching, and expires after
    maximum 42 days to prevent infinite access. Different record/field
    combinations expire at different times to prevent thundering herd problems.

    :param record: the record to generate the token for
    :type record: class:`odoo.models.Model`
    :param field_name: the field name of record to generate the token for
    :type field_name: str
    :param scope: scope of the authentication, to have different signature for the same
        record/field in different usage
    :type scope: str
    :param timestamp: expiration timestamp of the token, or None to generate one
    :type timestamp: int, optional
    :return: the token, which includes the timestamp in hex format
    :rtype: string
    """
    record.ensure_one()
    if not timestamp:
        unique_str = repr((record._name, record.id, field_name))
        two_weeks = 1209600  # 2 * 7 * 24 * 60 * 60
        start_of_period = int(time.time()) // two_weeks * two_weeks
        adler32_max = 4294967295
        jitter = two_weeks * zlib.adler32(unique_str.encode()) // adler32_max
        timestamp = hex(start_of_period + 2 * two_weeks + jitter)
    token = hmac(record.env(su=True), scope, (record._name, record.id, field_name, timestamp))
    return f"{token}o{timestamp}"


def verify_limited_field_access_token(record, field_name, access_token, *, scope):
    """Verify the given access_token grants access to field_name of record.
    In particular, the token must have the right format, must be valid for the
    given record, and must not have expired.

    :param record: the record to verify the token for
    :type record: class:`odoo.models.Model`
    :param field_name: the field name of record to verify the token for
    :type field_name: str
    :param access_token: the access token to verify
    :type access_token: str
    :param scope: scope of the authentication, to have different signature for the same
        record/field in different usage
    :return: whether the token is valid for the record/field_name combination at
        the current date and time
    :rtype: bool
    """
    *_, timestamp = access_token.rsplit("o", 1)
    return consteq(
        access_token, limited_field_access_token(record, field_name, timestamp, scope=scope)
    ) and datetime.datetime.now() < datetime.datetime.fromtimestamp(int(timestamp, 16))


ADDRESS_REGEX = re.compile(r'^(.*?)(\s[0-9][0-9\S]*)?(?: - (.+))?$', flags=re.DOTALL)
def street_split(street):
    match = ADDRESS_REGEX.match(street or '')
    results = match.groups('') if match else ('', '', '')
    return {
        'street_name': results[0].strip(),
        'street_number': results[1].strip(),
        'street_number2': results[2],
    }


def is_list_of(values, type_: type) -> bool:
    """Return True if the given values is a list / tuple of the given type.

    :param values: The values to check
    :param type_: The type of the elements in the list / tuple
    """
    return isinstance(values, (list, tuple)) and all(isinstance(item, type_) for item in values)


def has_list_types(values, types: tuple[type, ...]) -> bool:
    """Return True if the given values have the same types as
    the one given in argument, in the same order.

    :param values: The values to check
    :param types: The types of the elements in the list / tuple
    """
    return (
        isinstance(values, (list, tuple)) and len(values) == len(types)
        and all(itertools.starmap(isinstance, zip(values, types)))
    )


def get_flag(country_code: str) -> str:
    """Get the emoji representing the flag linked to the country code.

    This emoji is composed of the two regional indicator emoji of the country code.
    """
    return "".join(chr(int(f"1f1{ord(c)+165:02x}", base=16)) for c in country_code)


def format_frame(frame) -> str:
    code = frame.f_code
    return f'{code.co_name} {code.co_filename}:{frame.f_lineno}'


def named_to_positional_printf(string: str, args: Mapping) -> tuple[str, tuple]:
    """ Convert a named printf-style format string with its arguments to an
    equivalent positional format string with its arguments.
    """
    pargs = _PrintfArgs(args)
    return string.replace('%%', '%%%%') % pargs, tuple(pargs.values)


class _PrintfArgs:
    """ Helper object to turn a named printf-style format string into a positional one. """
    __slots__ = ('mapping', 'values')

    def __init__(self, mapping):
        self.mapping: Mapping = mapping
        self.values: list = []

    def __getitem__(self, key):
        self.values.append(self.mapping[key])
        return "%s"
