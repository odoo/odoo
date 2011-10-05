#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP SA (<http://www.openerp.com>)
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
import traceback
import types
from pprint import pformat

# TODO modules that import netsvc only for things from loglevels must be changed to use loglevels.
from loglevels import *
import tools
import openerp

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
        if e.errno != errno.ENOTCONN or platform.system() != 'Darwin':
            raise
    sock.close()


#.apidoc title: Common Services: netsvc
#.apidoc module-mods: member-order: bysource

def abort_response(dummy_1, description, dummy_2, details):
    # TODO Replace except_{osv,orm} with these directly.
    raise openerp.osv.osv.except_osv(description, details)

class Service(object):
    """ Base class for *Local* services

        Functionality here is trusted, no authentication.
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
    _logger = logging.getLogger('web-services')
    
    def __init__(self, name):
        ExportService._services[name] = self
        self.__name = name
        self._logger.debug("Registered an exported service: %s" % name)

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
    logging.DEBUG_SQL: (WHITE, MAGENTA),
    logging.DEBUG_RPC: (BLUE, WHITE),
    logging.DEBUG_RPC_ANSWER: (BLUE, WHITE),
    logging.DEBUG: (BLUE, DEFAULT),
    logging.INFO: (GREEN, DEFAULT),
    logging.TEST: (WHITE, BLUE),
    logging.WARNING: (YELLOW, DEFAULT),
    logging.ERROR: (RED, DEFAULT),
    logging.CRITICAL: (WHITE, RED),
}

class DBFormatter(logging.Formatter):
    def format(self, record):
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
    format = '[%(asctime)s][%(dbname)s] %(levelname)s:%(name)s:%(message)s'

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

    if isinstance(handler, logging.StreamHandler) and os.isatty(handler.stream.fileno()):
        formatter = ColoredFormatter(format)
    else:
        formatter = DBFormatter(format)
    handler.setFormatter(formatter)

    # add the handler to the root logger
    logger = logging.getLogger()
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(int(tools.config['log_level'] or '0'))

# A alternative logging scheme for automated runs of the
# server intended to test it.
def init_alternative_logger():
    class H(logging.Handler):
      def emit(self, record):
        if record.levelno > 20:
          print record.levelno, record.pathname, record.msg
    handler = H()
    logger = logging.getLogger()
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.ERROR)

class Server:
    """ Generic interface for all servers with an event loop etc.
        Override this to impement http, net-rpc etc. servers.

        Servers here must have threaded behaviour. start() must not block,
        there is no run().
    """
    __is_started = False
    __servers = []
    __starter_threads = []

    # we don't want blocking server calls (think select()) to
    # wait forever and possibly prevent exiting the process,
    # but instead we want a form of polling/busy_wait pattern, where
    # _server_timeout should be used as the default timeout for
    # all I/O blocking operations
    _busywait_timeout = 0.5


    __logger = logging.getLogger('server')

    def __init__(self):
        Server.__servers.append(self)
        if Server.__is_started:
            # raise Exception('All instances of servers must be inited before the startAll()')
            # Since the startAll() won't be called again, allow this server to
            # init and then start it after 1sec (hopefully). Register that
            # timer thread in a list, so that we can abort the start if quitAll
            # is called in the meantime
            t = threading.Timer(1.0, self._late_start)
            t.name = 'Late start timer for %s' % str(self.__class__)
            Server.__starter_threads.append(t)
            t.start()

    def start(self):
        self.__logger.debug("called stub Server.start")

    def _late_start(self):
        self.start()
        for thr in Server.__starter_threads:
            if thr.finished.is_set():
                Server.__starter_threads.remove(thr)

    def stop(self):
        self.__logger.debug("called stub Server.stop")

    def stats(self):
        """ This function should return statistics about the server """
        return "%s: No statistics" % str(self.__class__)

    @classmethod
    def startAll(cls):
        if cls.__is_started:
            return
        cls.__logger.info("Starting %d services" % len(cls.__servers))
        for srv in cls.__servers:
            srv.start()
        cls.__is_started = True

    @classmethod
    def quitAll(cls):
        if not cls.__is_started:
            return
        cls.__logger.info("Stopping %d services" % len(cls.__servers))
        for thr in cls.__starter_threads:
            if not thr.finished.is_set():
                thr.cancel()
            cls.__starter_threads.remove(thr)

        for srv in cls.__servers:
            srv.stop()
        cls.__is_started = False

    @classmethod
    def allStats(cls):
        res = ["Servers %s" % ('stopped', 'started')[cls.__is_started]]
        res.extend(srv.stats() for srv in cls.__servers)
        return '\n'.join(res)

    def _close_socket(self):
        close_socket(self.socket)

def replace_request_password(args):
    # password is always 3rd argument in a request, we replace it in RPC logs
    # so it's easier to forward logs for diagnostics/debugging purposes...
    args = list(args)
    if len(args) > 2:
        args[2] = '*'
    return args

def log(title, msg, channel=logging.DEBUG_RPC, depth=None, fn=""):
    logger = logging.getLogger(title)
    if logger.isEnabledFor(channel):
        indent=''
        indent_after=' '*len(fn)
        for line in (fn+pformat(msg, depth=depth)).split('\n'):
            logger.log(channel, indent+line)
            indent=indent_after

def dispatch_rpc(service_name, method, params):
    """ Handle a RPC call.

    This is pure Python code, the actual marshalling (from/to XML-RPC or
    NET-RPC) is done in a upper layer.
    """
    def _log(title, msg, channel=logging.DEBUG_RPC, depth=None, fn=""):
        log(title, msg, channel=channel, depth=depth, fn=fn)
    try:
        logger = logging.getLogger('result')
        start_time = end_time = 0
        if logger.isEnabledFor(logging.DEBUG_RPC_ANSWER):
            _log('service', tuple(replace_request_password(params)), depth=None, fn='%s.%s'%(service_name,method))
        if logger.isEnabledFor(logging.DEBUG_RPC):
            start_time = time.time()
        result = ExportService.getService(service_name).dispatch(method, params)
        if logger.isEnabledFor(logging.DEBUG_RPC):
            end_time = time.time()
        if not logger.isEnabledFor(logging.DEBUG_RPC_ANSWER):
            _log('service (%.3fs)' % (end_time - start_time), tuple(replace_request_password(params)), depth=1, fn='%s.%s'%(service_name,method))
        _log('execution time', '%.3fs' % (end_time - start_time), channel=logging.DEBUG_RPC_ANSWER)
        _log('result', result, channel=logging.DEBUG_RPC_ANSWER)
        return result
    except openerp.exceptions.AccessError:
        raise
    except openerp.exceptions.AccessDenied:
        raise
    except openerp.exceptions.Warning:
        raise
    except openerp.exceptions.DeferredException, e:
        _log('exception', tools.exception_to_unicode(e))
        post_mortem(e.traceback)
        raise
    except Exception, e:
        _log('exception', tools.exception_to_unicode(e))
        post_mortem(sys.exc_info())
        raise

def post_mortem(info):
    if tools.config['debug_mode'] and isinstance(info[2], types.TracebackType):
        import pdb
        pdb.post_mortem(info[2])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
