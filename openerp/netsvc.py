# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import logging
import logging.handlers
import os
import release
import sys
import threading
import time
import types
from pprint import pformat
import psutil

import tools
import openerp

_logger = logging.getLogger(__name__)

def LocalService(name):
    """
    The openerp.netsvc.LocalService() function is deprecated. It still works
    in two cases: workflows and reports. For workflows, instead of using
    LocalService('workflow'), openerp.workflow should be used (better yet,
    methods on openerp.osv.orm.Model should be used). For reports,
    openerp.report.render_report() should be used (methods on the Model should
    be provided too in the future).
    """
    assert openerp.conf.deprecation.allow_local_service
    _logger.warning("LocalService() is deprecated since march 2013 (it was called with '%s')." % name)

    if name == 'workflow':
        return openerp.workflow

    if name.startswith('report.'):
        report = openerp.report.interface.report_int._reports.get(name)
        if report:
            return report
        else:
            dbname = getattr(threading.currentThread(), 'dbname', None)
            if dbname:
                registry = openerp.modules.registry.RegistryManager.get(dbname)
                with registry.cursor() as cr:
                    return registry['ir.actions.report.xml']._lookup_report(cr, name[len('report.'):])

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
        fg_color, bg_color = LEVEL_COLOR_MAPPING[record.levelno]
        record.levelname = COLOR_PATTERN % (30 + fg_color, 40 + bg_color, record.levelname)
        return DBFormatter.format(self, record)

_logger_init = False
def init_logger():
    global _logger_init
    if _logger_init:
        return
    _logger_init = True

    from tools.translate import resetlocale
    resetlocale()

    # create a format for log messages and dates
    format = '%(asctime)s %(pid)s %(levelname)s %(dbname)s %(name)s: %(message)s'

    if tools.config['syslog']:
        # SysLog Handler
        if os.name == 'nt':
            handler = logging.handlers.NTEventLogHandler("%s %s" % (release.description, release.version))
        else:
            handler = logging.handlers.SysLogHandler('/dev/log')
        format = '%s %s' % (release.description, release.version) \
                + ':%(dbname)s:%(levelname)s:%(name)s:%(message)s'

    elif tools.config['logfile']:
        # LogFile Handler
        logf = tools.config['logfile']
        try:
            dirname = os.path.dirname(logf)
            if dirname and not os.path.isdir(dirname):
                os.makedirs(dirname)
            if tools.config['logrotate'] is not False:
                handler = logging.handlers.TimedRotatingFileHandler(logf,'D',1,30)
            elif os.name == 'posix':
                handler = logging.handlers.WatchedFileHandler(logf)
            else:
                handler = logging.handlers.FileHandler(logf)
        except Exception:
            sys.stderr.write("ERROR: couldn't create the logfile directory. Logging to the standard output.\n")
            handler = logging.StreamHandler(sys.stdout)
    else:
        # Normal Handler on standard output
        handler = logging.StreamHandler(sys.stdout)

    # Check that handler.stream has a fileno() method: when running OpenERP
    # behind Apache with mod_wsgi, handler.stream will have type mod_wsgi.Log,
    # which has no fileno() method. (mod_wsgi.Log is what is being bound to
    # sys.stderr when the logging.StreamHandler is being constructed above.)
    if isinstance(handler, logging.StreamHandler) \
        and hasattr(handler.stream, 'fileno') \
        and os.isatty(handler.stream.fileno()):
        formatter = ColoredFormatter(format)
    else:
        formatter = DBFormatter(format)
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)

    # Configure handlers
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
    'openerp.workflow.workitem:WARNING',
    'openerp.netsvc.rpc.request:INFO',
    'openerp.netsvc.rpc.response:INFO',
    'openerp.addons.web.http:INFO',
    'openerp.sql_db:INFO',
    ':INFO',
]
PSEUDOCONFIG_MAPPER = {
    'debug_rpc_answer': ['openerp:DEBUG','openerp.netsvc.rpc.request:DEBUG', 'openerp.netsvc.rpc.response:DEBUG'],
    'debug_rpc': ['openerp:DEBUG','openerp.netsvc.rpc.request:DEBUG'],
    'debug': ['openerp:DEBUG'],
    'debug_sql': ['openerp.sql_db:DEBUG'],
    'info': [],
    'warn': ['openerp:WARNING'],
    'error': ['openerp:ERROR'],
    'critical': ['openerp:CRITICAL'],
}

# A alternative logging scheme for automated runs of the
# server intended to test it.
def init_alternative_logger():
    class H(logging.Handler):
        def emit(self, record):
            if record.levelno > 20:
                print record.levelno, record.pathname, record.msg
    handler = H()
    # Add the handler to the 'openerp' logger.
    logger = logging.getLogger('openerp')
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

def replace_request_password(args):
    # password is always 3rd argument in a request, we replace it in RPC logs
    # so it's easier to forward logs for diagnostics/debugging purposes...
    if len(args) > 2:
        args = list(args)
        args[2] = '*'
    return tuple(args)

def log(logger, level, prefix, msg, depth=None):
    indent=''
    indent_after=' '*len(prefix)
    for line in (prefix+pformat(msg, depth=depth)).split('\n'):
        logger.log(level, indent+line)
        indent=indent_after

def dispatch_rpc(service_name, method, params):
    """ Handle a RPC call.

    This is pure Python code, the actual marshalling (from/to XML-RPC) is done
    in a upper layer.
    """
    try:
        rpc_request = logging.getLogger(__name__ + '.rpc.request')
        rpc_response = logging.getLogger(__name__ + '.rpc.response')
        rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
        rpc_response_flag = rpc_response.isEnabledFor(logging.DEBUG)
        if rpc_request_flag or rpc_response_flag:
            start_time = time.time()
            start_rss, start_vms = 0, 0
            start_rss, start_vms = psutil.Process(os.getpid()).get_memory_info()
            if rpc_request and rpc_response_flag:
                log(rpc_request,logging.DEBUG,'%s.%s'%(service_name,method), replace_request_password(params))

        threading.current_thread().uid = None
        threading.current_thread().dbname = None
        if service_name == 'common':
            dispatch = openerp.service.common.dispatch
        elif service_name == 'db':
            dispatch = openerp.service.db.dispatch
        elif service_name == 'object':
            dispatch = openerp.service.model.dispatch
        elif service_name == 'report':
            dispatch = openerp.service.report.dispatch
        else:
            dispatch = openerp.service.wsgi_server.rpc_handlers.get(service_name)
        result = dispatch(method, params)

        if rpc_request_flag or rpc_response_flag:
            end_time = time.time()
            end_rss, end_vms = 0, 0
            end_rss, end_vms = psutil.Process(os.getpid()).get_memory_info()
            logline = '%s.%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % (service_name, method, end_time - start_time, start_vms / 1024, end_vms / 1024, (end_vms - start_vms)/1024)
            if rpc_response_flag:
                log(rpc_response,logging.DEBUG, logline, result)
            else:
                log(rpc_request,logging.DEBUG, logline, replace_request_password(params), depth=1)

        return result
    except openerp.osv.orm.except_orm:
        raise
    except openerp.exceptions.AccessError:
        raise
    except openerp.exceptions.AccessDenied:
        raise
    except openerp.exceptions.Warning:
        raise
    except openerp.exceptions.RedirectWarning:
        raise
    except openerp.exceptions.DeferredException, e:
        _logger.exception(tools.exception_to_unicode(e))
        post_mortem(e.traceback)
        raise
    except Exception, e:
        _logger.exception(tools.exception_to_unicode(e))
        post_mortem(sys.exc_info())
        raise

def post_mortem(info):
    if tools.config['debug_mode'] and isinstance(info[2], types.TracebackType):
        import pdb
        pdb.post_mortem(info[2])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
