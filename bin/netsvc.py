#!/usr/bin/python
# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################

import time
import threading

import SimpleXMLRPCServer, signal, sys, xmlrpclib
import SocketServer
import socket
import logging
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
        s = _service[name]
        self._service = s
        for m in s._method:
            setattr(self, m, s._method[m])


class ServiceUnavailable(Exception):
    pass


def service_exist(name):
    return (name in _service) and bool(_service[name])


def get_rpc_paths():
    return map(lambda s: '/xmlrpc/%s' % s, _service)

LOG_DEBUG = 'debug'
LOG_INFO = 'info'
LOG_WARNING = 'warn'
LOG_ERROR = 'error'
LOG_CRITICAL = 'critical'


def init_logger():
    from tools import config
    import os

    if config['logfile']:
        logf = config['logfile']
        # test if the directories exist, else create them
        try:
            handler = logging.handlers.TimedRotatingFileHandler(logf,'D',1,30)
        except:
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
    logging.getLogger().setLevel(logging.INFO)

    if isinstance(handler, logging.StreamHandler) and os.name != 'nt':
        # change color of level names
        # uses of ANSI color codes
        # see http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html
        # maybe use http://code.activestate.com/recipes/574451/
        colors = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', None, 'default']
        foreground = lambda f: 30 + colors.index(f)
        background = lambda f: 40 + colors.index(f)

        mapping = {
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
        getattr(log, level)(msg)


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


class RpcGateway(object):
    def __init__(self, name):
        self.name = name


class Dispatcher(object):
    def __init__(self):
        pass

    def monitor(self, signal):
        pass

    def run(self):
        pass


class xmlrpc(object):
    class RpcGateway(object):
        def __init__(self, name):
            self.name = name


class GenericXMLRPCRequestHandler:
    def _dispatch(self, method, params):
        #print 'TERP-CALL : ',method, params
        import traceback
        try:
            n = self.path.split("/")[-1]
            s = LocalService(n)
            m = getattr(s, method)
            s._service._response = None
            r = m(*params)
            res = s._service._response
            if res != None:
                r = res
            return r
        except Exception, e:
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(
                sys.exc_type, sys.exc_value, sys.exc_traceback))
            s = str(e)
            import tools
            if tools.config['debug_mode']:
                import pdb
                tb = sys.exc_info()[2]
                pdb.post_mortem(tb)
            raise xmlrpclib.Fault(s, tb_s)


class SimpleXMLRPCRequestHandler(GenericXMLRPCRequestHandler,
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.rpc_paths = get_rpc_paths()


class SimpleThreadedXMLRPCServer(SocketServer.ThreadingMixIn,
        SimpleXMLRPCServer.SimpleXMLRPCServer):

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.SOL_SOCKET,
                    socket.SO_REUSEADDR, 1)
            SimpleXMLRPCServer.SimpleXMLRPCServer.server_bind(self)
        except:
            sys.stderr.write("ERROR: address already in use\n")
            sys.exit(1)


class HttpDaemon(threading.Thread):

    def __init__(self, interface, port, secure=False):
        threading.Thread.__init__(self)
        self.__port = port
        self.__interface = interface
        self.secure = secure
        if secure:
            from ssl import SecureXMLRPCServer
            class SecureXMLRPCRequestHandler(GenericXMLRPCRequestHandler,
                    SecureXMLRPCServer.SecureXMLRPCRequestHandler):
                SecureXMLRPCServer.SecureXMLRPCRequestHandler.rpc_paths = get_rpc_paths()
            class SecureThreadedXMLRPCServer(SocketServer.ThreadingMixIn,
                    SecureXMLRPCServer.SecureXMLRPCServer):

                def server_bind(self):
                    try:
                        self.socket.setsockopt(socket.SOL_SOCKET,
                                socket.SO_REUSEADDR, 1)
                        SecureXMLRPCServer.SecureXMLRPCServer.server_bind(self)
                    except:
                        sys.stderr.write("ERROR: address already in use\n")
                        sys.exit(1)


            self.server = SecureThreadedXMLRPCServer((interface, port),
                    SecureXMLRPCRequestHandler, 0)
        else:
            self.server = SimpleThreadedXMLRPCServer((interface, port),
                    SimpleXMLRPCRequestHandler, 0)

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
                s = LocalService(msg[0])
                m = getattr(s, msg[1])
                s._service._response = None
                r = m(*msg[2:])
                res = s._service._response
                if res != None:
                    r = res
                ts.mysend(r)
            except Exception, e:
                tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                s = str(e)
                import tools
                if tools.config['debug_mode']:
                    import pdb
                    tb = sys.exc_info()[2]
                    pdb.post_mortem(tb)
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

