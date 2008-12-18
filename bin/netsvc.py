#!/usr/bin/python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import threading

import SimpleXMLRPCServer
import signal
import sys
import xmlrpclib
import SocketServer
import socket
import logging
import logging.handlers
import os

_service = {}
_group = {}
_res_id = 1
_res = {}


class ServiceEndPointCall(object):
    def __init__(self, id, method):
        self._id = id
        self._meth = method

    def __call__(self, *args):
        _res[self._id] = self._meth(*args)
        return self._id


class ServiceEndPoint(object):
    def __init__(self, name, id):
        self._id = id
        self._meth = {}
        s = _service[name]
        for m in s._method:
            self._meth[m] = s._method[m]

    def __getattr__(self, name):
        return ServiceEndPointCall(self._id, self._meth[name])


class Service(object):
    _serviceEndPointID = 0

    def __init__(self, name, audience=''):
        _service[name] = self
        self.__name = name
        self._method = {}
        self.exportedMethods = None
        self._response_process = None
        self._response_process_id = None
        self._response = None

    def joinGroup(self, name):
        if not name in _group:
            _group[name] = {}
        _group[name][self.__name] = self

    def exportMethod(self, m):
        if callable(m):
            self._method[m.__name__] = m

    def serviceEndPoint(self, s):
        if Service._serviceEndPointID >= 2**16:
            Service._serviceEndPointID = 0
        Service._serviceEndPointID += 1
        return ServiceEndPoint(s, self._serviceEndPointID)

    def conversationId(self):
        return 1

    def processResponse(self, s, id):
        self._response_process, self._response_process_id = s, id

    def processFailure(self, s, id):
        pass

    def resumeResponse(self, s):
        pass

    def cancelResponse(self, s):
        pass

    def suspendResponse(self, s):
        if self._response_process:
            self._response_process(self._response_process_id,
                                   _res[self._response_process_id])
        self._response_process = None
        self._response = s(self._response_process_id)

    def abortResponse(self, error, description, origin, details):
        import tools
        if not tools.config['debug_mode']:
            raise Exception("%s -- %s\n\n%s"%(origin, description, details))
        else:
            raise

    def currentFailure(self, s):
        pass


class LocalService(Service):
    def __init__(self, name):
        self.__name = name
        try:
            s = _service[name]
            self._service = s
            for m in s._method:
                setattr(self, m, s._method[m])
        except KeyError, keyError:
            Logger().notifyChannel('module', LOG_ERROR, 'This service does not exists: %s' % (str(keyError),) )
            raise



class ServiceUnavailable(Exception):
    pass


def service_exist(name):
    return (name in _service) and bool(_service[name])




LOG_DEBUG_RPC = 'debug_rpc'
LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'

# add new log level below DEBUG
logging.DEBUG_RPC = logging.DEBUG - 1

def init_logger():
    from tools import config
    import os

    if config['logfile']:
        logf = config['logfile']
        try:
            dirname = os.path.dirname(logf)
            if dirname and not os.path.isdir(dirname):
                os.makedirs(dirname)
            handler = logging.handlers.TimedRotatingFileHandler(logf,'D',1,30)
        except Exception, ex:
            sys.stderr.write("ERROR: couldn't create the logfile directory\n")
            handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.StreamHandler(sys.stdout)

    # create a format for log messages and dates
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s:%(name)s:%(message)s', '%a %b %d %H:%M:%S %Y')

    # tell the handler to use this format
    handler.setFormatter(formatter)

    # add the handler to the root logger
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(config['log_level'])

    
    if isinstance(handler, logging.StreamHandler) and os.name != 'nt':
        # change color of level names
        # uses of ANSI color codes
        # see http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html
        # maybe use http://code.activestate.com/recipes/574451/
        colors = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', None, 'default']
        foreground = lambda f: 30 + colors.index(f)
        background = lambda f: 40 + colors.index(f)

        mapping = {
            'DEBUG_RPC': ('blue', 'white'),
            'DEBUG': ('blue', 'default'),
            'INFO': ('green', 'default'),
            'WARNING': ('yellow', 'default'),
            'ERROR': ('red', 'default'),
            'CRITICAL': ('white', 'red'),
        }

        for level, (fg, bg) in mapping.items():
            msg = "\x1b[%dm\x1b[%dm%s\x1b[0m" % (foreground(fg), background(bg), level)
            logging.addLevelName(getattr(logging, level), msg)


class Logger(object):
    def notifyChannel(self, name, level, msg):
        log = logging.getLogger(name)

        if level == LOG_DEBUG_RPC and not hasattr(log, level):
            fct = lambda msg, *args, **kwargs: log.log(logging.DEBUG_RPC, msg, *args, **kwargs)
            setattr(log, LOG_DEBUG_RPC, fct)

        level_method = getattr(log, level)

        result = str(msg).strip().split('\n')
        if len(result)>1:
            for idx, s in enumerate(result):
                level_method('[%02d]: %s' % (idx+1, s,))
        elif result:
            level_method(result[0])

init_logger()

class Agent(object):
    _timers = []
    _logger = Logger()

    def setAlarm(self, fn, dt, args=None, kwargs=None):
        if not args:
            args = []
        if not kwargs:
            kwargs = {}
        wait = dt - time.time()
        if wait > 0:
            self._logger.notifyChannel('timers', LOG_DEBUG, "Job scheduled in %s seconds for %s.%s" % (wait, fn.im_class.__name__, fn.func_name))
            timer = threading.Timer(wait, fn, args, kwargs)
            timer.start()
            self._timers.append(timer)
        for timer in self._timers[:]:
            if not timer.isAlive():
                self._timers.remove(timer)

    def quit(cls):
        for timer in cls._timers:
            timer.cancel()
    quit = classmethod(quit)

class xmlrpc(object):
    class RpcGateway(object):
        def __init__(self, name):
            self.name = name


class GenericXMLRPCRequestHandler:
    def log(self, title, msg):
        from pprint import pformat
        Logger().notifyChannel('XMLRPC-%s' % title, LOG_DEBUG_RPC, pformat(msg))

    def _dispatch(self, method, params):
        import traceback
        traceback.print_stack()
        try:
            self.log('method', method)
            self.log('params', params)
            n = self.path.split("/")[-1]
            s = LocalService(n)
            m = getattr(s, method)
            s._service._response = None
            r = m(*params)
            self.log('result', r)
            res = s._service._response
            if res is not None:
                r = res
            self.log('res',r)
            return r
        except Exception, e:
            self.log('exception', e)
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            s = str(e)
            import tools
            if tools.config['debug_mode']:
                import pdb
                tb = sys.exc_info()[2]
                pdb.post_mortem(tb)
            raise xmlrpclib.Fault(s, tb_s)


#### XML-RPC SSL ####
from ssl import SecureXMLRPCServer
class SecureXMLRPCRequestHandler(GenericXMLRPCRequestHandler, SecureXMLRPCServer.SecureXMLRPCRequestHandler):
    SecureXMLRPCServer.SecureXMLRPCRequestHandler.rpc_paths = map(lambda s: '/xmlrpc/%s' % s, _service)

class SecureThreadedXMLRPCServer(SocketServer.ThreadingMixIn, SecureXMLRPCServer.SecureXMLRPCServer):
    def server_bind(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            SecureXMLRPCServer.SecureXMLRPCServer.server_bind(self)
        except:
            Logger().notifyChannel('init', LOG_CRITICAL, 'Address already in use')
            sys.exit(1)

#### XML-RPC ####
class SimpleXMLRPCRequestHandler(GenericXMLRPCRequestHandler, SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.rpc_paths = map(lambda s: '/xmlrpc/%s' % s, _service)

class SimpleThreadedXMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
    def server_bind(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            SimpleXMLRPCServer.SimpleXMLRPCServer.server_bind(self)
        except:
            Logger().notifyChannel('init', LOG_CRITICAL, 'Address already in use')
            sys.exit(1)

class HttpDaemon(threading.Thread):
    def __init__(self, interface, port, secure=False):
        threading.Thread.__init__(self)
        self.__port = port
        self.__interface = interface
        self.secure = secure
        if self.secure:
            handler_class = SecureXMLRPCRequestHandler
            server_class = SecureThreadedXMLRPCServer
        else:
            handler_class = SimpleXMLRPCRequestHandler
            server_class = SimpleThreadedXMLRPCServer
        self.server = server_class((interface, port), handler_class, 0)

    def attach(self, path, gw):
        pass

    def stop(self):
        self.running = False
        if os.name != 'nt':
            if hasattr(socket, 'SHUT_RDWR'):
                if self.secure:
                    self.server.socket.sock_shutdown(socket.SHUT_RDWR)
                else:
                    self.server.socket.shutdown(socket.SHUT_RDWR)
            else:
                if self.secure:
                    self.server.socket.sock_shutdown(2)
                else:
                    self.server.socket.shutdown(2)
        self.server.socket.close()

    def run(self):
        self.server.register_introspection_functions()

        self.running = True
        while self.running:
            self.server.handle_request()
        return True

        # If the server need to be run recursively
        #
        #signal.signal(signal.SIGALRM, self.my_handler)
        #signal.alarm(6)
        #while True:
        #   self.server.handle_request()
        #signal.alarm(0)          # Disable the alarm

import tiny_socket
class TinySocketClientThread(threading.Thread):
    def __init__(self, sock, threads):
        threading.Thread.__init__(self)
        self.sock = sock
        self.threads = threads
        self._logger = Logger()

    def log(self, msg):
        self._logger.notifyChannel('NETRPC', LOG_DEBUG_RPC, msg)

    def run(self):
        import traceback
        import time
        import select
        self.running = True
        try:
            ts = tiny_socket.mysocket(self.sock)
        except:
            self.sock.close()
            self.threads.remove(self)
            return False
        while self.running:
            try:
                msg = ts.myreceive()
            except:
                self.sock.close()
                self.threads.remove(self)
                return False
            try:
                self.log(msg)
                s = LocalService(msg[0])
                m = getattr(s, msg[1])
                s._service._response = None
                r = m(*msg[2:])
                res = s._service._response
                if res != None:
                    r = res
                self.log(r)
                ts.mysend(r)
            except Exception, e:
                tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                import tools
                if tools.config['debug_mode']:
                    import pdb
                    tb = sys.exc_info()[2]
                    pdb.post_mortem(tb)
                e = Exception(str(e))
                self.log(str(e))
                ts.mysend(e, exception=True, traceback=tb_s)
            except:
                pass
            self.sock.close()
            self.threads.remove(self)
            return True

    def stop(self):
        self.running = False


class TinySocketServerThread(threading.Thread):
    def __init__(self, interface, port, secure=False):
        threading.Thread.__init__(self)
        self.__port = port
        self.__interface = interface
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.__interface, self.__port))
        self.socket.listen(5)
        self.threads = []

    def run(self):
        import select
        try:
            self.running = True
            while self.running:
                (clientsocket, address) = self.socket.accept()
                ct = TinySocketClientThread(clientsocket, self.threads)
                self.threads.append(ct)
                ct.start()
            self.socket.close()
        except Exception, e:
            self.socket.close()
            return False

    def stop(self):
        self.running = False
        for t in self.threads:
            t.stop()
        try:
            if hasattr(socket, 'SHUT_RDWR'):
                self.socket.shutdown(socket.SHUT_RDWR)
            else:
                self.socket.shutdown(2)
            self.socket.close()
        except:
            return False




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

