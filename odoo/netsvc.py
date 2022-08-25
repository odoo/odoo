# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import logging
import logging.handlers
import os
import platform
import pprint
import sys
import threading
import time
import traceback
import warnings

from . import release
from . import sql_db
from . import tools

_logger = logging.getLogger(__name__)

def log(logger, level, prefix, msg, depth=None):
    indent=''
    indent_after=' '*len(prefix)
    for line in (prefix + pprint.pformat(msg, depth=depth)).split('\n'):
        logger.log(level, indent+line)
        indent=indent_after

class PostgreSQLHandler(logging.Handler):
    """ PostgreSQL Logging Handler will store logs in the database, by default
    the current database, can be set using --log-db=DBNAME
    """
    def emit(self, record):
        ct = threading.current_thread()
        ct_db = getattr(ct, 'dbname', None)
        dbname = tools.config['log_db'] if tools.config['log_db'] and tools.config['log_db'] != '%d' else ct_db
        if not dbname:
            return
        with contextlib.suppress(Exception), tools.mute_logger('odoo.sql_db'), sql_db.db_connect(dbname, allow_uri=True).cursor() as cr:
            # preclude risks of deadlocks
            cr.execute("SET LOCAL statement_timeout = 1000")
            msg = tools.ustr(record.msg)
            if record.args:
                msg = msg % record.args
            traceback = getattr(record, 'exc_text', '')
            if traceback:
                msg = "%s\n%s" % (msg, traceback)
            # we do not use record.levelname because it may have been changed by ColoredFormatter.
            levelname = logging.getLevelName(record.levelno)

            val = ('server', ct_db, record.name, levelname, msg, record.pathname, record.lineno, record.funcName)
            cr.execute("""
                INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s)
            """, val)

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, _NOTHING, DEFAULT = range(10)
#The background is set with 40 plus the number of the color, and the foreground with 30
#These are the sequences needed to get colored output
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"
COLOR_PATTERN = "%s%s%%s%s" % (COLOR_SEQ, COLOR_SEQ, RESET_SEQ)
LEVEL_COLOR_MAPPING = {
    logging.DEBUG: (BLUE, DEFAULT),
    logging.INFO: (GREEN, DEFAULT),
    logging.WARNING: (YELLOW, DEFAULT),
    logging.ERROR: (RED, DEFAULT),
    logging.CRITICAL: (WHITE, RED),
}

class PerfFilter(logging.Filter):
    def format_perf(self, query_count, query_time, remaining_time):
        return ("%d" % query_count, "%.3f" % query_time, "%.3f" % remaining_time)

    def filter(self, record):
        if hasattr(threading.current_thread(), "query_count"):
            query_count = threading.current_thread().query_count
            query_time = threading.current_thread().query_time
            perf_t0 = threading.current_thread().perf_t0
            remaining_time = time.time() - perf_t0 - query_time
            record.perf_info = '%s %s %s' % self.format_perf(query_count, query_time, remaining_time)
            delattr(threading.current_thread(), "query_count")
        else:
            record.perf_info = "- - -"
        return True

class ColoredPerfFilter(PerfFilter):
    def format_perf(self, query_count, query_time, remaining_time):
        def colorize_time(time, format, low=1, high=5):
            if time > high:
                return COLOR_PATTERN % (30 + RED, 40 + DEFAULT, format % time)
            if time > low:
                return COLOR_PATTERN % (30 + YELLOW, 40 + DEFAULT, format % time)
            return format % time
        return (
            colorize_time(query_count, "%d", 100, 1000),
            colorize_time(query_time, "%.3f", 0.1, 3),
            colorize_time(remaining_time, "%.3f", 1, 5)
            )

class DBFormatter(logging.Formatter):
    def format(self, record):
        record.pid = os.getpid()
        record.dbname = getattr(threading.current_thread(), 'dbname', '?')
        return logging.Formatter.format(self, record)

class ColoredFormatter(DBFormatter):
    def format(self, record):
        fg_color, bg_color = LEVEL_COLOR_MAPPING.get(record.levelno, (GREEN, DEFAULT))
        record.levelname = COLOR_PATTERN % (30 + fg_color, 40 + bg_color, record.levelname)
        return DBFormatter.format(self, record)

_logger_init = False
def init_logger():
    global _logger_init
    if _logger_init:
        return
    _logger_init = True

    old_factory = logging.getLogRecordFactory()
    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.perf_info = ""
        return record
    logging.setLogRecordFactory(record_factory)

    # enable deprecation warnings (disabled by default)
    warnings.simplefilter('default', category=DeprecationWarning)
    # ignore deprecation warnings from invalid escape (there's a ton and it's
    # pretty likely a super low-value signal)
    warnings.filterwarnings('ignore', r'^invalid escape sequence \'?\\.', category=DeprecationWarning)
    # recordsets are both sequence and set so trigger warning despite no issue
    warnings.filterwarnings('ignore', r'^Sampling from a set', category=DeprecationWarning, module='odoo')
    # ignore a bunch of warnings we can't really fix ourselves
    for module in [
        'babel.util', # deprecated parser module, no release yet
        'zeep.loader',# zeep using defusedxml.lxml
        'reportlab.lib.rl_safe_eval',# reportlab importing ABC from collections
        'ofxparse',# ofxparse importing ABC from collections
        'astroid',  # deprecated imp module (fixed in 2.5.1)
        'requests_toolbelt', # importing ABC from collections (fixed in 0.9)
    ]:
        warnings.filterwarnings('ignore', category=DeprecationWarning, module=module)

    # the SVG guesser thing always compares str and bytes, ignore it
    warnings.filterwarnings('ignore', category=BytesWarning, module='odoo.tools.image')
    # reportlab does a bunch of bytes/str mixing in a hashmap
    warnings.filterwarnings('ignore', category=BytesWarning, module='reportlab.platypus.paraparser')

    from .tools.translate import resetlocale
    resetlocale()

    # create a format for log messages and dates
    format = '%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: %(message)s %(perf_info)s'
    # Normal Handler on stderr
    handler = logging.StreamHandler()

    if tools.config['syslog']:
        # SysLog Handler
        if os.name == 'nt':
            handler = logging.handlers.NTEventLogHandler("%s %s" % (release.description, release.version))
        elif platform.system() == 'Darwin':
            handler = logging.handlers.SysLogHandler('/var/run/log')
        else:
            handler = logging.handlers.SysLogHandler('/dev/log')
        format = '%s %s' % (release.description, release.version) \
                + ':%(dbname)s:%(levelname)s:%(name)s:%(message)s'

    elif tools.config['logfile']:
        # LogFile Handler
        logf = tools.config['logfile']
        try:
            # We check we have the right location for the log files
            dirname = os.path.dirname(logf)
            if dirname and not os.path.isdir(dirname):
                os.makedirs(dirname)
            if os.name == 'posix':
                handler = logging.handlers.WatchedFileHandler(logf)
            else:
                handler = logging.FileHandler(logf)
        except Exception:
            sys.stderr.write("ERROR: couldn't create the logfile directory. Logging to the standard output.\n")

    # Check that handler.stream has a fileno() method: when running OpenERP
    # behind Apache with mod_wsgi, handler.stream will have type mod_wsgi.Log,
    # which has no fileno() method. (mod_wsgi.Log is what is being bound to
    # sys.stderr when the logging.StreamHandler is being constructed above.)
    def is_a_tty(stream):
        return hasattr(stream, 'fileno') and os.isatty(stream.fileno())

    if os.name == 'posix' and isinstance(handler, logging.StreamHandler) and (is_a_tty(handler.stream) or os.environ.get("ODOO_PY_COLORS")):
        formatter = ColoredFormatter(format)
        perf_filter = ColoredPerfFilter()
    else:
        formatter = DBFormatter(format)
        perf_filter = PerfFilter()
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)
    logging.getLogger('werkzeug').addFilter(perf_filter)

    if tools.config['log_db']:
        db_levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL,
        }
        postgresqlHandler = PostgreSQLHandler()
        postgresqlHandler.setLevel(int(db_levels.get(tools.config['log_db_level'], tools.config['log_db_level'])))
        logging.getLogger().addHandler(postgresqlHandler)

    # Configure loggers levels
    pseudo_config = PSEUDOCONFIG_MAPPER.get(tools.config['log_level'], [])

    logconfig = tools.config['log_handler']

    logging_configurations = DEFAULT_LOG_CONFIGURATION + pseudo_config + logconfig
    for logconfig_item in logging_configurations:
        loggername, level = logconfig_item.strip().split(':')
        level = getattr(logging, level, logging.INFO)
        logger = logging.getLogger(loggername)
        logger.setLevel(level)

    for logconfig_item in logging_configurations:
        _logger.debug('logger level set: "%s"', logconfig_item)


DEFAULT_LOG_CONFIGURATION = [
    'odoo.http.rpc.request:INFO',
    'odoo.http.rpc.response:INFO',
    ':INFO',
]
PSEUDOCONFIG_MAPPER = {
    'debug_rpc_answer': ['odoo:DEBUG', 'odoo.sql_db:INFO', 'odoo.http.rpc:DEBUG'],
    'debug_rpc': ['odoo:DEBUG', 'odoo.sql_db:INFO', 'odoo.http.rpc.request:DEBUG'],
    'debug': ['odoo:DEBUG', 'odoo.sql_db:INFO'],
    'debug_sql': ['odoo.sql_db:DEBUG'],
    'info': [],
    'runbot': ['odoo:RUNBOT', 'werkzeug:WARNING'],
    'warn': ['odoo:WARNING', 'werkzeug:WARNING'],
    'error': ['odoo:ERROR', 'werkzeug:ERROR'],
    'critical': ['odoo:CRITICAL', 'werkzeug:CRITICAL'],
}

logging.RUNBOT = 25
logging.addLevelName(logging.RUNBOT, "INFO") # displayed as info in log
logging.captureWarnings(True)
# must be after `loggin.captureWarnings` so we override *that* instead of the
# other way around
showwarning = warnings.showwarning
IGNORE = {
    'Comparison between bytes and int', # a.foo != False or some shit, we don't care
}
def showwarning_with_traceback(message, category, filename, lineno, file=None, line=None):
    if category is BytesWarning and message.args[0] in IGNORE:
        return

    # find the stack frame maching (filename, lineno)
    filtered = []
    for frame in traceback.extract_stack():
        if 'importlib' not in frame.filename:
            filtered.append(frame)
        if frame.filename == filename and frame.lineno == lineno:
            break
    return showwarning(
        message, category, filename, lineno,
        file=file,
        line=''.join(traceback.format_list(filtered))
    )
warnings.showwarning = showwarning_with_traceback

def runbot(self, message, *args, **kws):
    self.log(logging.RUNBOT, message, *args, **kws)
logging.Logger.runbot = runbot
