# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


"""
Miscellaneous tools used by OpenERP.
"""
from functools import wraps
import babel
from contextlib import contextmanager
import datetime
import subprocess
import io
import os

import collections
import passlib.utils
import pickle as pickle_
import re
import socket
import sys
import threading
import time
import types
import werkzeug.utils
import zipfile
from collections import defaultdict, Iterable, Mapping, MutableSet, OrderedDict
from itertools import islice, groupby, repeat
from lxml import etree

from .which import which
import traceback
from operator import itemgetter

try:
    # pylint: disable=bad-python3-import
    import cProfile
except ImportError:
    import profile as cProfile


from .config import config
from .cache import *
from .parse_version import parse_version 
from . import pycompat

import odoo
# get_encodings, ustr and exception_to_unicode were originally from tools.misc.
# There are moved to loglevels until we refactor tools.
from odoo.loglevels import get_encodings, ustr, exception_to_unicode     # noqa

_logger = logging.getLogger(__name__)

# List of etree._Element subclasses that we choose to ignore when parsing XML.
# We include the *Base ones just in case, currently they seem to be subclasses of the _* ones.
SKIPPED_ELEMENT_TYPES = (etree._Comment, etree._ProcessingInstruction, etree.CommentBase, etree.PIBase, etree._Entity)

# Configure default global parser
etree.set_default_parser(etree.XMLParser(resolve_entities=False))

#----------------------------------------------------------
# Subprocesses
#----------------------------------------------------------

def find_in_path(name):
    path = os.environ.get('PATH', os.defpath).split(os.pathsep)
    if config.get('bin_path') and config['bin_path'] != 'None':
        path.append(config['bin_path'])
    return which(name, path=os.pathsep.join(path))

def _exec_pipe(prog, args, env=None):
    cmd = (prog,) + args
    # on win32, passing close_fds=True is not compatible
    # with redirecting std[in/err/out]
    close_fds = os.name=="posix"
    pop = subprocess.Popen(cmd, bufsize=-1, stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=close_fds, env=env)
    return pop.stdin, pop.stdout

def exec_command_pipe(name, *args):
    prog = find_in_path(name)
    if not prog:
        raise Exception('Command `%s` not found.' % name)
    return _exec_pipe(prog, args)

#----------------------------------------------------------
# Postgres subprocesses
#----------------------------------------------------------

def find_pg_tool(name):
    path = None
    if config['pg_path'] and config['pg_path'] != 'None':
        path = config['pg_path']
    try:
        return which(name, path=path)
    except IOError:
        raise Exception('Command `%s` not found.' % name)

def exec_pg_environ():
    """
    Force the database PostgreSQL environment variables to the database
    configuration of Odoo.

    Note: On systems where pg_restore/pg_dump require an explicit password
    (i.e.  on Windows where TCP sockets are used), it is necessary to pass the
    postgres user password in the PGPASSWORD environment variable or in a
    special .pgpass file.

    See also http://www.postgresql.org/docs/8.4/static/libpq-envars.html
    """
    env = os.environ.copy()
    if odoo.tools.config['db_host']:
        env['PGHOST'] = odoo.tools.config['db_host']
    if odoo.tools.config['db_port']:
        env['PGPORT'] = str(odoo.tools.config['db_port'])
    if odoo.tools.config['db_user']:
        env['PGUSER'] = odoo.tools.config['db_user']
    if odoo.tools.config['db_password']:
        env['PGPASSWORD'] = odoo.tools.config['db_password']
    return env

def exec_pg_command(name, *args):
    prog = find_pg_tool(name)
    env = exec_pg_environ()
    with open(os.devnull) as dn:
        args2 = (prog,) + args
        rc = subprocess.call(args2, env=env, stdout=dn, stderr=subprocess.STDOUT)
        if rc:
            raise Exception('Postgres subprocess %s error %s' % (args2, rc))

def exec_pg_command_pipe(name, *args):
    prog = find_pg_tool(name)
    env = exec_pg_environ()
    return _exec_pipe(prog, args, env)

#----------------------------------------------------------
# File paths
#----------------------------------------------------------
#file_path_root = os.getcwd()
#file_path_addons = os.path.join(file_path_root, 'addons')

def file_open(name, mode="r", subdir='addons', pathinfo=False):
    """Open a file from the OpenERP root, using a subdir folder.

    Example::
    
    >>> file_open('hr/report/timesheer.xsl')
    >>> file_open('addons/hr/report/timesheet.xsl')

    @param name name of the file
    @param mode file open mode
    @param subdir subdirectory
    @param pathinfo if True returns tuple (fileobject, filepath)

    @return fileobject if pathinfo is False else (fileobject, filepath)
    """
    import odoo.modules as addons
    adps = addons.module.ad_paths
    rtp = os.path.normcase(os.path.abspath(config['root_path']))

    basename = name

    if os.path.isabs(name):
        # It is an absolute path
        # Is it below 'addons_path' or 'root_path'?
        name = os.path.normcase(os.path.normpath(name))
        for root in adps + [rtp]:
            root = os.path.normcase(os.path.normpath(root)) + os.sep
            if name.startswith(root):
                base = root.rstrip(os.sep)
                name = name[len(base) + 1:]
                break
        else:
            # It is outside the OpenERP root: skip zipfile lookup.
            base, name = os.path.split(name)
        return _fileopen(name, mode=mode, basedir=base, pathinfo=pathinfo, basename=basename)

    if name.replace(os.sep, '/').startswith('addons/'):
        subdir = 'addons'
        name2 = name[7:]
    elif subdir:
        name = os.path.join(subdir, name)
        if name.replace(os.sep, '/').startswith('addons/'):
            subdir = 'addons'
            name2 = name[7:]
        else:
            name2 = name

    # First, try to locate in addons_path
    if subdir:
        for adp in adps:
            try:
                return _fileopen(name2, mode=mode, basedir=adp,
                                 pathinfo=pathinfo, basename=basename)
            except IOError:
                pass

    # Second, try to locate in root_path
    return _fileopen(name, mode=mode, basedir=rtp, pathinfo=pathinfo, basename=basename)


def _fileopen(path, mode, basedir, pathinfo, basename=None):
    name = os.path.normpath(os.path.normcase(os.path.join(basedir, path)))

    import odoo.modules as addons
    paths = addons.module.ad_paths + [config['root_path']]
    for addons_path in paths:
        addons_path = os.path.normpath(os.path.normcase(addons_path)) + os.sep
        if name.startswith(addons_path):
            break
    else:
        raise ValueError("Unknown path: %s" % name)

    if basename is None:
        basename = name
    # Give higher priority to module directories, which is
    # a more common case than zipped modules.
    if os.path.isfile(name):
        if 'b' in mode:
            fo = open(name, mode)
        else:
            fo = io.open(name, mode, encoding='utf-8')
        if pathinfo:
            return fo, name
        return fo

    # Support for loading modules in zipped form.
    # This will not work for zipped modules that are sitting
    # outside of known addons paths.
    head = os.path.normpath(path)
    zipname = False
    while os.sep in head:
        head, tail = os.path.split(head)
        if not tail:
            break
        if zipname:
            zipname = os.path.join(tail, zipname)
        else:
            zipname = tail
        zpath = os.path.join(basedir, head + '.zip')
        if zipfile.is_zipfile(zpath):
            zfile = zipfile.ZipFile(zpath)
            try:
                fo = io.BytesIO()
                fo.write(zfile.read(os.path.join(
                    os.path.basename(head), zipname).replace(
                        os.sep, '/')))
                fo.seek(0)
                if pathinfo:
                    return fo, name
                return fo
            except Exception:
                pass
    # Not found
    if name.endswith('.rml'):
        raise IOError('Report %r doesn\'t exist or deleted' % basename)
    raise IOError('File not found: %s' % basename)


#----------------------------------------------------------
# iterables
#----------------------------------------------------------
def flatten(list):
    """Flatten a list of elements into a uniqu list
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
    r = []
    for e in list:
        if isinstance(e, (bytes, pycompat.text_type)) or not isinstance(e, collections.Iterable):
            r.append(e)
        else:
            r.extend(flatten(e))
    return r

def reverse_enumerate(l):
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
    return pycompat.izip(range(len(l)-1, -1, -1), reversed(l))

def partition(pred, elems):
    """ Return a pair equivalent to:
        ``filter(pred, elems), filter(lambda x: not pred(x), elems)` """
    yes, nos = [], []
    for elem in elems:
        (yes if pred(elem) else nos).append(elem)
    return yes, nos

def topological_sort(elems):
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


try:
    import xlwt

    # add some sanitizations to respect the excel sheet name restrictions
    # as the sheet name is often translatable, can not control the input
    class PatchedWorkbook(xlwt.Workbook):
        def add_sheet(self, name, cell_overwrite_ok=False):
            # invalid Excel character: []:*?/\
            name = re.sub(r'[\[\]:*?/\\]', '', name)

            # maximum size is 31 characters
            name = name[:31]
            return super(PatchedWorkbook, self).add_sheet(name, cell_overwrite_ok=cell_overwrite_ok)

    xlwt.Workbook = PatchedWorkbook

except ImportError:
    xlwt = None

try:
    import xlsxwriter

    # add some sanitizations to respect the excel sheet name restrictions
    # as the sheet name is often translatable, can not control the input
    class PatchedXlsxWorkbook(xlsxwriter.Workbook):

        # TODO when xlsxwriter bump to 0.9.8, add worksheet_class=None parameter instead of kw
        def add_worksheet(self, name=None, **kw):
            if name:
                # invalid Excel character: []:*?/\
                name = re.sub(r'[\[\]:*?/\\]', '', name)

                # maximum size is 31 characters
                name = name[:31]
            return super(PatchedXlsxWorkbook, self).add_worksheet(name, **kw)

    xlsxwriter.Workbook = PatchedXlsxWorkbook

except ImportError:
    xlsxwriter = None


def to_xml(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def get_iso_codes(lang):
    if lang.find('_') != -1:
        if lang.split('_')[0] == lang.split('_')[1].lower():
            lang = lang.split('_')[0]
    return lang

def scan_languages():
    """ Returns all languages supported by OpenERP for translation

    :returns: a list of (lang_code, lang_name) pairs
    :rtype: [(str, unicode)]
    """
    csvpath = odoo.modules.module.get_resource_path('base', 'res', 'res.lang.csv')
    try:
        # read (code, name) from languages in base/res/res.lang.csv
        with open(csvpath, 'rb') as csvfile:
            reader = pycompat.csv_reader(csvfile, delimiter=',', quotechar='"')
            fields = next(reader)
            code_index = fields.index("code")
            name_index = fields.index("name")
            result = [
                (row[code_index], row[name_index])
                for row in reader
            ]
    except Exception:
        _logger.error("Could not read %s", csvpath)
        result = []

    return sorted(result or [('en_US', u'English')], key=itemgetter(1))

def get_user_companies(cr, user):
    def _get_company_children(cr, ids):
        if not ids:
            return []
        cr.execute('SELECT id FROM res_company WHERE parent_id IN %s', (tuple(ids),))
        res = [x[0] for x in cr.fetchall()]
        res.extend(_get_company_children(cr, res))
        return res
    cr.execute('SELECT company_id FROM res_users WHERE id=%s', (user,))
    user_comp = cr.fetchone()[0]
    if not user_comp:
        return []
    return [user_comp] + _get_company_children(cr, [user_comp])

def mod10r(number):
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

def str2bool(s, default=None):
    s = ustr(s).lower()
    y = 'y yes 1 true t on'.split()
    n = 'n no 0 false f off'.split()
    if s not in (y + n):
        if default is None:
            raise ValueError('Use 0/1/yes/no/true/false/on/off')
        return bool(default)
    return s in y

def human_size(sz):
    """
    Return the size in a human readable format
    """
    if not sz:
        return False
    units = ('bytes', 'Kb', 'Mb', 'Gb')
    if isinstance(sz,pycompat.string_types):
        sz=len(sz)
    s, i = float(sz), 0
    while s >= 1024 and i < len(units)-1:
        s /= 1024
        i += 1
    return "%0.2f %s" % (s, units[i])

def logged(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from pprint import pformat

        vector = ['Call -> function: %r' % f]
        for i, arg in enumerate(args):
            vector.append('  arg %02d: %s' % (i, pformat(arg)))
        for key, value in kwargs.items():
            vector.append('  kwarg %10s: %s' % (key, pformat(value)))

        timeb4 = time.time()
        res = f(*args, **kwargs)

        vector.append('  result: %s' % pformat(res))
        vector.append('  time delta: %s' % (time.time() - timeb4))
        _logger.debug('\n'.join(vector))
        return res

    return wrapper

class profile(object):
    def __init__(self, fname=None):
        self.fname = fname

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            profile = cProfile.Profile()
            result = profile.runcall(f, *args, **kwargs)
            profile.dump_stats(self.fname or ("%s.cprof" % (f.__name__,)))
            return result

        return wrapper

def detect_ip_addr():
    """Try a very crude method to figure out a valid external
       IP or hostname for the current machine. Don't rely on this
       for binding to an interface, but it could be used as basis
       for constructing a remote URL to the server.
    """
    def _detect_ip_addr():
        from array import array
        from struct import pack, unpack

        try:
            import fcntl
        except ImportError:
            fcntl = None

        ip_addr = None

        if not fcntl: # not UNIX:
            host = socket.gethostname()
            ip_addr = socket.gethostbyname(host)
        else: # UNIX:
            # get all interfaces:
            nbytes = 128 * 32
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            names = array('B', '\0' * nbytes)
            #print 'names: ', names
            outbytes = unpack('iL', fcntl.ioctl( s.fileno(), 0x8912, pack('iL', nbytes, names.buffer_info()[0])))[0]
            namestr = names.tostring()

            # try 64 bit kernel:
            for i in range(0, outbytes, 40):
                name = namestr[i:i+16].split('\0', 1)[0]
                if name != 'lo':
                    ip_addr = socket.inet_ntoa(namestr[i+20:i+24])
                    break

            # try 32 bit kernel:
            if ip_addr is None:
                ifaces = [namestr[i:i+32].split('\0', 1)[0] for i in range(0, outbytes, 32)]

                for ifname in [iface for iface in ifaces if iface if iface != 'lo']:
                    ip_addr = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, pack('256s', ifname[:15]))[20:24])
                    break

        return ip_addr or 'localhost'

    try:
        ip_addr = _detect_ip_addr()
    except Exception:
        ip_addr = 'localhost'
    return ip_addr

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
    'H': 'HH',
    'I': 'hh',
    'j': 'DDD',
    'm': 'MM',
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

def posix_to_ldml(fmt, locale):
    """ Converts a posix/strftime pattern into an LDML date format pattern.

    :param fmt: non-extended C89/C90 strftime pattern
    :param locale: babel locale used for locale-specific conversions (e.g. %x and %X)
    :return: unicode
    """
    buf = []
    pc = False
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
            else: # look up format char in static mapping
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

def split_every(n, iterable, piece_maker=tuple):
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

def get_and_group_by_field(cr, uid, obj, ids, field, context=None):
    """ Read the values of ``field´´ for the given ``ids´´ and group ids by value.

       :param string field: name of the field we want to read and group by
       :return: mapping of field values to the list of ids that have it
       :rtype: dict
    """
    res = {}
    for record in obj.read(cr, uid, ids, [field], context=context):
        key = record[field]
        res.setdefault(key[0] if isinstance(key, tuple) else key, []).append(record['id'])
    return res

def get_and_group_by_company(cr, uid, obj, ids, context=None):
    return get_and_group_by_field(cr, uid, obj, ids, field='company_id', context=context)

# port of python 2.6's attrgetter with support for dotted notation
def resolve_attr(obj, attr):
    for name in attr.split("."):
        obj = getattr(obj, name)
    return obj

def attrgetter(*items):
    if len(items) == 1:
        attr = items[0]
        def g(obj):
            return resolve_attr(obj, attr)
    else:
        def g(obj):
            return tuple(resolve_attr(obj, attr) for attr in items)
    return g

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
    def __repr__(self):
        return self

class UnquoteEvalContext(defaultdict):
    """Defaultdict-based evaluation context that returns 
       an ``unquote`` string for any missing name used during
       the evaluation.
       Mostly useful for evaluating OpenERP domains/contexts that
       may refer to names that are unknown at the time of eval,
       so that when the context/domain is converted back to a string,
       the original names are preserved.

       **Warning**: using an ``UnquoteEvalContext`` as context for ``eval()`` or
       ``safe_eval()`` will shadow the builtins, which may cause other
       failures, depending on what is evaluated.

       Example (notice that ``section_id`` is preserved in the final
       result) :

       >>> context_str = "{'default_user_id': uid, 'default_section_id': section_id}"
       >>> eval(context_str, UnquoteEvalContext(uid=1))
       {'default_user_id': 1, 'default_section_id': section_id}

       """
    def __init__(self, *args, **kwargs):
        super(UnquoteEvalContext, self).__init__(None, *args, **kwargs)

    def __missing__(self, key):
        return unquote(key)


class mute_logger(object):
    """Temporary suppress the logging.
    Can be used as context manager or decorator.

        @mute_logger('odoo.plic.ploc')
        def do_stuff():
            blahblah()

        with mute_logger('odoo.foo.bar'):
            do_suff()

    """
    def __init__(self, *loggers):
        self.loggers = loggers

    def filter(self, record):
        return 0

    def __enter__(self):
        for logger in self.loggers:
            assert isinstance(logger, pycompat.string_types),\
                "A logger name must be a string, got %s" % type(logger)
            logging.getLogger(logger).addFilter(self)

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        for logger in self.loggers:
            logging.getLogger(logger).removeFilter(self)

    def __call__(self, func):
        @wraps(func)
        def deco(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return deco

_ph = object()
class CountingStream(object):
    """ Stream wrapper counting the number of element it has yielded. Similar
    role to ``enumerate``, but for use when the iteration process of the stream
    isn't fully under caller control (the stream can be iterated from multiple
    points including within a library)

    ``start`` allows overriding the starting index (the index before the first
    item is returned).

    On each iteration (call to :meth:`~.next`), increases its :attr:`~.index`
    by one.

    .. attribute:: index

        ``int``, index of the last yielded element in the stream. If the stream
        has ended, will give an index 1-past the stream
    """
    def __init__(self, stream, start=-1):
        self.stream = iter(stream)
        self.index = start
        self.stopped = False
    def __iter__(self):
        return self
    def next(self):
        if self.stopped: raise StopIteration()
        self.index += 1
        val = next(self.stream, _ph)
        if val is _ph:
            self.stopped = True
            raise StopIteration()
        return val
    __next__ = next

def stripped_sys_argv(*strip_args):
    """Return sys.argv with some arguments stripped, suitable for reexecution or subprocesses"""
    strip_args = sorted(set(strip_args) | set(['-s', '--save', '-u', '--update', '-i', '--init', '--i18n-overwrite']))
    assert all(config.parser.has_option(s) for s in strip_args)
    takes_value = dict((s, config.parser.get_option(s).takes_value()) for s in strip_args)

    longs, shorts = list(tuple(y) for _, y in groupby(strip_args, lambda x: x.startswith('--')))
    longs_eq = tuple(l + '=' for l in longs if takes_value[l])

    args = sys.argv[:]

    def strip(args, i):
        return args[i].startswith(shorts) \
            or args[i].startswith(longs_eq) or (args[i] in longs) \
            or (i >= 1 and (args[i - 1] in strip_args) and takes_value[args[i - 1]])

    return [x for i, x in enumerate(args) if not strip(args, i)]

class ConstantMapping(Mapping):
    """
    An immutable mapping returning the provided value for every single key.

    Useful for default value to methods
    """
    __slots__ = ['_value']
    def __init__(self, val):
        self._value = val

    def __len__(self):
        """
        defaultdict updates its length for each individually requested key, is
        that really useful?
        """
        return 0

    def __iter__(self):
        """
        same as len, defaultdict udpates its iterable keyset with each key
        requested, is there a point for this?
        """
        return iter([])

    def __getitem__(self, item):
        return self._value


def dumpstacks(sig=None, frame=None):
    """ Signal handler: dump a stack trace for each existing thread."""
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
                               'url': getattr(th, 'url', 'n/a')}
                    for th in threading.enumerate()}
    for threadId, stack in sys._current_frames().items():
        thread_info = threads_info.get(threadId, {})
        code.append("\n# Thread: %s (db:%s) (uid:%s) (url:%s)" %
                    (thread_info.get('repr', threadId),
                     thread_info.get('dbname', 'n/a'),
                     thread_info.get('uid', 'n/a'),
                     thread_info.get('url', 'n/a')))
        for line in extract_stack(stack):
            code.append(line)

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

    _logger.info("\n".join(code))

def freehash(arg):
    try:
        return hash(arg)
    except Exception:
        if isinstance(arg, Mapping):
            return hash(frozendict(arg))
        elif isinstance(arg, Iterable):
            return hash(frozenset(freehash(item) for item in arg))
        else:
            return id(arg)

class frozendict(dict):
    """ An implementation of an immutable dictionary. """
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
    def __hash__(self):
        return hash(frozenset((key, freehash(val)) for key, val in self.items()))

class Collector(Mapping):
    """ A mapping from keys to lists. This is essentially a space optimization
        for ``defaultdict(list)``.
    """
    __slots__ = ['_map']
    def __init__(self):
        self._map = {}
    def add(self, key, val):
        vals = self._map.setdefault(key, [])
        if val not in vals:
            vals.append(val)
    def __getitem__(self, key):
        return self._map.get(key, ())
    def __iter__(self):
        return iter(self._map)
    def __len__(self):
        return len(self._map)

class OrderedSet(MutableSet):
    """ A set collection that remembers the elements first insertion order. """
    __slots__ = ['_map']
    def __init__(self, elems=()):
        self._map = OrderedDict((elem, None) for elem in elems)
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

class LastOrderedSet(OrderedSet):
    """ A set collection that remembers the elements last insertion order. """
    def add(self, elem):
        OrderedSet.discard(self, elem)
        OrderedSet.add(self, elem)

def unique(it):
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

@contextmanager
def ignore(*exc):
    try:
        yield
    except exc:
        pass

# Avoid DeprecationWarning while still remaining compatible with werkzeug pre-0.9
if parse_version(getattr(werkzeug, '__version__', '0.0')) < parse_version('0.9.0'):
    def html_escape(text):
        return werkzeug.utils.escape(text, quote=True)
else:
    def html_escape(text):
        return werkzeug.utils.escape(text)

def formatLang(env, value, digits=None, grouping=True, monetary=False, dp=False, currency_obj=False):
    """
        Assuming 'Account' decimal.precision=3:
            formatLang(value) -> digits=2 (default)
            formatLang(value, digits=4) -> digits=4
            formatLang(value, dp='Account') -> digits=3
            formatLang(value, digits=5, dp='Account') -> digits=5
    """

    if digits is None:
        digits = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = env['decimal.precision']
            digits = decimal_precision_obj.precision_get(dp)
        elif currency_obj:
            digits = currency_obj.decimal_places
        elif (hasattr(value, '_field') and isinstance(value._field, (float_field, function_field)) and value._field.digits):
                digits = value._field.digits[1]
                if not digits and digits is not 0:
                    digits = DEFAULT_DIGITS

    if isinstance(value, pycompat.string_types) and not value:
        return ''

    lang = env.context.get('lang') or env.user.company_id.partner_id.lang or 'en_US'
    lang_objs = env['res.lang'].search([('code', '=', lang)])
    if not lang_objs:
        lang_objs = env['res.lang'].search([], limit=1)
    lang_obj = lang_objs[0]

    res = lang_obj.format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)

    if currency_obj and currency_obj.symbol:
        if currency_obj.position == 'after':
            res = '%s %s' % (res, currency_obj.symbol)
        elif currency_obj and currency_obj.position == 'before':
            res = '%s %s' % (currency_obj.symbol, res)
    return res

def format_date(env, value, lang_code=False, date_format=False):
    '''
        Formats the date in a given format.

        :param env: an environment.
        :param date, datetime or string value: the date to format.
        :param string lang_code: the lang code, if not specified it is extracted from the
            environment context.
        :param string date_format: the format or the date (LDML format), if not specified the
            default format of the lang.
        :return: date formatted in the specified format.
        :rtype: string
    '''
    if not value:
        return ''
    if isinstance(value, datetime.datetime):
        value = value.date()
    elif isinstance(value, pycompat.string_types):
        if len(value) < DATE_LENGTH:
            return ''
        value = value[:DATE_LENGTH]
        value = datetime.datetime.strptime(value, DEFAULT_SERVER_DATE_FORMAT).date()

    lang = env['res.lang']._lang_get(lang_code or env.context.get('lang') or 'en_US')
    locale = babel.Locale.parse(lang.code)
    if not date_format:
        date_format = posix_to_ldml(lang.date_format, locale=locale)

    return babel.dates.format_date(value, format=date_format, locale=locale)

def _consteq(str1, str2):
    """ Constant-time string comparison. Suitable to compare bytestrings of fixed,
        known length only, because length difference is optimized. """
    return len(str1) == len(str2) and sum(ord(x)^ord(y) for x, y in pycompat.izip(str1, str2)) == 0

consteq = getattr(passlib.utils, 'consteq', _consteq)

# forbid globals entirely: str/unicode, int/long, float, bool, tuple, list, dict, None
class Unpickler(pickle_.Unpickler, object):
    find_global = None # Python 2
    find_class = None # Python 3
def _pickle_load(stream, encoding='ASCII', errors=False):
    if sys.version_info[0] == 3:
        unpickler = Unpickler(stream, encoding=encoding)
    else:
        unpickler = Unpickler(stream)
    try:
        return unpickler.load()
    except Exception:
        _logger.warning('Failed unpickling data, returning default: %r',
                        errors, exc_info=True)
        return errors
pickle = types.ModuleType(__name__ + '.pickle')
pickle.load = _pickle_load
pickle.loads = lambda text, encoding='ASCII': _pickle_load(io.BytesIO(text), encoding=encoding)
pickle.dump = pickle_.dump
pickle.dumps = pickle_.dumps
