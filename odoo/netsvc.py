# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import logging.handlers
import os
import platform
import pprint
import release
import sys
import threading

import psycopg2

import odoo
import sql_db
import tools

_logger = logging.getLogger(__name__)

def log(logger, level, prefix, msg, depth=None):
    indent=''
    indent_after=' '*len(prefix)
    for line in (prefix + pprint.pformat(msg, depth=depth)).split('\n'):
        logger.log(level, indent+line)
        indent=indent_after

def LocalService(name):
    """
    The odoo.netsvc.LocalService() function is deprecated. It still works
    in two cases: workflows and reports. For workflows, instead of using
    LocalService('workflow'), odoo.workflow should be used (better yet,
    methods on odoo.osv.orm.Model should be used). For reports,
    odoo.report.render_report() should be used (methods on the Model should
    be provided too in the future).
    """
    assert odoo.conf.deprecation.allow_local_service
    _logger.warning("LocalService() is deprecated since march 2013 (it was called with '%s')." % name)

    if name == 'workflow':
        return odoo.workflow

    if name.startswith('report.'):
        report = odoo.report.interface.report_int._reports.get(name)
        if report:
            return report
        else:
            dbname = getattr(threading.currentThread(), 'dbname', None)
            if dbname:
                registry = odoo.registry(dbname)
                with registry.cursor() as cr:
                    return registry['ir.actions.report.xml']._lookup_report(cr, name[len('report.'):])

path_prefix = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))

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
        with tools.ignore(Exception), tools.mute_logger('odoo.sql_db'), sql_db.db_connect(dbname, allow_uri=True).cursor() as cr:
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

            val = ('server', ct_db, record.name, levelname, msg, record.pathname[len(path_prefix)+1:], record.lineno, record.funcName)
            cr.execute("""
                INSERT INTO ir_logging(create_date, type, dbname, name, level, message, path, line, func)
                VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s)
            """, val)

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, _NOTHING, DEFAULT = range(10)
#The background is set with 40 plus the number of the color, and the foreground with 30
#These are the sequences need to get colored ouput
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

class DBFormatter(logging.Formatter):
    def format(self, record):
        record.pid = os.getpid()
        record.dbname = getattr(threading.currentThread(), 'dbname', '?')
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

    logging.addLevelName(25, "INFO")
    logging.captureWarnings(True)

    from tools.translate import resetlocale
    resetlocale()

    # create a format for log messages and dates
    format = '%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: %(message)s'
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
            if tools.config['logrotate'] is not False:
                if tools.config['workers'] > 1:
                    # TODO: fallback to regular file logging in master for safe(r) defaults?
                    #
                    # Doing so here would be a good idea but also might break
                    # situations were people do log-shipping of rotated data?
                    _logger.warn("WARNING: built-in log rotation is not reliable in multi-worker scenarios and may incur significant data loss. "
                                 "It is strongly recommended to use an external log rotation utility or use system loggers (--syslog) instead.")
                handler = logging.handlers.TimedRotatingFileHandler(filename=logf, when='D', interval=1, backupCount=30)
            elif os.name == 'posix':
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

    if os.name == 'posix' and isinstance(handler, logging.StreamHandler) and is_a_tty(handler.stream):
        formatter = ColoredFormatter(format)
    else:
        formatter = DBFormatter(format)
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)

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
        loggername, level = logconfig_item.split(':')
        level = getattr(logging, level, logging.INFO)
        logger = logging.getLogger(loggername)
        logger.setLevel(level)

    for logconfig_item in logging_configurations:
        _logger.debug('logger level set: "%s"', logconfig_item)

DEFAULT_LOG_CONFIGURATION = [
    'odoo.workflow.workitem:WARNING',
    'odoo.http.rpc.request:INFO',
    'odoo.http.rpc.response:INFO',
    'odoo.addons.web.http:INFO',
    'odoo.sql_db:INFO',
    ':INFO',
]
PSEUDOCONFIG_MAPPER = {
    'debug_rpc_answer': ['odoo:DEBUG','odoo.http.rpc.request:DEBUG', 'odoo.http.rpc.response:DEBUG'],
    'debug_rpc': ['odoo:DEBUG','odoo.http.rpc.request:DEBUG'],
    'debug': ['odoo:DEBUG'],
    'debug_sql': ['odoo.sql_db:DEBUG'],
    'info': [],
    'warn': ['odoo:WARNING', 'werkzeug:WARNING'],
    'error': ['odoo:ERROR', 'werkzeug:ERROR'],
    'critical': ['odoo:CRITICAL', 'werkzeug:CRITICAL'],
}
