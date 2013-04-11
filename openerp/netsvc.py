#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://www.openerp.com>)
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

#.apidoc title: Common Services: netsvc
#.apidoc module-mods: member-order: bysource

import errno
import logging
import logging.handlers
import os
import platform
import release
import socket
import sys
import threading
import time
import types
from pprint import pformat

try:
    import psutil
except ImportError:
    psutil = None

# TODO modules that import netsvc only for things from loglevels must be changed to use loglevels.
from loglevels import *
import tools
import openerp

_logger = logging.getLogger(__name__)


def close_socket(sock):
    """ Closes a socket instance cleanly

    :param sock: the network socket to close
    :type sock: socket.socket
    """
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except socket.error, e:
        # On OSX, socket shutdowns both sides if any side closes it
        # causing an error 57 'Socket is not connected' on shutdown
        # of the other side (or something), see
        # http://bugs.python.org/issue4397
        # note: stdlib fixed test, not behavior
        if e.errno != errno.ENOTCONN or platform.system() not in ['Darwin', 'Windows']:
            raise
    sock.close()

def abort_response(dummy_1, description, dummy_2, details):
    # TODO Replace except_{osv,orm} with these directly.
    raise openerp.osv.osv.except_osv(description, details)

class Service(object):
    """ Base class for Local services
    Functionality here is trusted, no authentication.
    Workflow engine and reports subclass this.
    """
    _services = {}
    def __init__(self, name):
        Service._services[name] = self
        self.__name = name

    @classmethod
    def exists(cls, name):
        return name in cls._services

    @classmethod
    def remove(cls, name):
        if cls.exists(name):
            cls._services.pop(name)

def LocalService(name):
    # Special case for addons support, will be removed in a few days when addons
    # are updated to directly use openerp.osv.osv.service.
    if name == 'object_proxy':
        return openerp.osv.osv.service

    return Service._services[name]

class ExportService(object):
    """ Proxy for exported services.

    Note that this class has no direct proxy, capable of calling
    eservice.method(). Rather, the proxy should call
    dispatch(method, params)
    """

    _services = {}
    
    def __init__(self, name):
        ExportService._services[name] = self
        self.__name = name
        _logger.debug("Registered an exported service: %s" % name)

    @classmethod
    def getService(cls,name):
        return cls._services[name]

    # Dispatch a RPC call w.r.t. the method name. The dispatching
    # w.r.t. the service (this class) is done by OpenERPDispatcher.
    def dispatch(self, method, params):
        raise Exception("stub dispatch at %s" % self.__name)

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
    logging.TEST: (WHITE, BLUE),
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

def init_logger():
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

    # Configure handlers
    default_config = [
        'openerp.netsvc.rpc.request:INFO',
        'openerp.netsvc.rpc.response:INFO',
        'openerp.addons.web.http:INFO',
        'openerp.sql_db:INFO',
        ':INFO',
    ]

    if tools.config['log_level'] == 'info':
        pseudo_config = []
    elif tools.config['log_level'] == 'debug_rpc':
        pseudo_config = ['openerp:DEBUG','openerp.netsvc.rpc.request:DEBUG']
    elif tools.config['log_level'] == 'debug_rpc_answer':
        pseudo_config = ['openerp:DEBUG','openerp.netsvc.rpc.request:DEBUG', 'openerp.netsvc.rpc.response:DEBUG']
    elif tools.config['log_level'] == 'debug':
        pseudo_config = ['openerp:DEBUG']
    elif tools.config['log_level'] == 'test':
        pseudo_config = ['openerp:TEST']
    elif tools.config['log_level'] == 'warn':
        pseudo_config = ['openerp:WARNING']
    elif tools.config['log_level'] == 'error':
        pseudo_config = ['openerp:ERROR']
    elif tools.config['log_level'] == 'critical':
        pseudo_config = ['openerp:CRITICAL']
    elif tools.config['log_level'] == 'debug_sql':
        pseudo_config = ['openerp.sql_db:DEBUG']
    else:
        pseudo_config = []

    logconfig = tools.config['log_handler']

    for logconfig_item in default_config + pseudo_config + logconfig:
        loggername, level = logconfig_item.split(':')
        level = getattr(logging, level, logging.INFO)
        logger = logging.getLogger(loggername)
        logger.handlers = []
        logger.setLevel(level)
        logger.addHandler(handler)
        if loggername != '':
            logger.propagate = False

    for logconfig_item in default_config + pseudo_config + logconfig:
        _logger.debug('logger level set: "%s"', logconfig_item)

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

    This is pure Python code, the actual marshalling (from/to XML-RPC or
    NET-RPC) is done in a upper layer.
    """
    try:
        rpc_request = logging.getLogger(__name__ + '.rpc.request')
        rpc_response = logging.getLogger(__name__ + '.rpc.response')
        rpc_request_flag = rpc_request.isEnabledFor(logging.DEBUG)
        rpc_response_flag = rpc_response.isEnabledFor(logging.DEBUG)
        if rpc_request_flag or rpc_response_flag:
            start_time = time.time()
            start_rss, start_vms = 0, 0
            if psutil:
                start_rss, start_vms = psutil.Process(os.getpid()).get_memory_info()
            if rpc_request and rpc_response_flag:
                log(rpc_request,logging.DEBUG,'%s.%s'%(service_name,method), replace_request_password(params))

        result = ExportService.getService(service_name).dispatch(method, params)

        if rpc_request_flag or rpc_response_flag:
            end_time = time.time()
            end_rss, end_vms = 0, 0
            if psutil:
                end_rss, end_vms = psutil.Process(os.getpid()).get_memory_info()
            logline = '%s.%s time:%.3fs mem: %sk -> %sk (diff: %sk)' % (service_name, method, end_time - start_time, start_vms / 1024, end_vms / 1024, (end_vms - start_vms)/1024)
            if rpc_response_flag:
                log(rpc_response,logging.DEBUG, logline, result)
            else:
                log(rpc_request,logging.DEBUG, logline, replace_request_password(params), depth=1)

        return result
    except openerp.exceptions.AccessError:
        raise
    except openerp.exceptions.AccessDenied:
        raise
    except openerp.exceptions.Warning:
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
