# -*- coding: utf-8 -*-
#
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
# Copyright 2010 OpenERP SA. (http://www.openerp.com)
#
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

#.apidoc title: HTTP and XML-RPC Server

""" This module offers the family of HTTP-based servers. These are not a single
    class/functionality, but a set of network stack layers, implementing
    extendable HTTP protocols.

    The OpenERP server defines a single instance of a HTTP server, listening at
    the standard 8069, 8071 ports (well, it is 2 servers, and ports are 
    configurable, of course). This "single" server then uses a `MultiHTTPHandler`
    to dispatch requests to the appropriate channel protocol, like the XML-RPC,
    static HTTP, DAV or other.
"""

from websrv_lib import *
import openerp.netsvc as netsvc
import errno
import threading
import openerp.tools as tools
import posixpath
import urllib
import os
import select
import socket
import xmlrpclib
import logging

from SimpleXMLRPCServer import SimpleXMLRPCDispatcher

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from ssl import SSLError
except ImportError:
    class SSLError(Exception): pass

class ThreadedHTTPServer(ConnThreadingMixIn, SimpleXMLRPCDispatcher, HTTPServer):
    """ A threaded httpd server, with all the necessary functionality for us.

        It also inherits the xml-rpc dispatcher, so that some xml-rpc functions
        will be available to the request handler
    """
    encoding = None
    allow_none = False
    allow_reuse_address = 1
    _send_traceback_header = False
    i = 0

    def __init__(self, addr, requestHandler, proto='http',
                 logRequests=True, allow_none=False, encoding=None, bind_and_activate=True):
        self.logRequests = logRequests

        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)
        HTTPServer.__init__(self, addr, requestHandler)
        
        self.numThreads = 0
        self.proto = proto
        self.__threadno = 0

        # [Bug #1222790] If possible, set close-on-exec flag; if a
        # method spawns a subprocess, the subprocess shouldn't have
        # the listening socket open.
        if fcntl is not None and hasattr(fcntl, 'FD_CLOEXEC'):
            flags = fcntl.fcntl(self.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(self.fileno(), fcntl.F_SETFD, flags)

    def handle_error(self, request, client_address):
        """ Override the error handler
        """
        
        logging.getLogger("init").exception("Server error in request from %s:" % (client_address,))

    def _mark_start(self, thread):
        self.numThreads += 1

    def _mark_end(self, thread):
        self.numThreads -= 1


    def _get_next_name(self):
        self.__threadno += 1
        return 'http-client-%d' % self.__threadno
class HttpLogHandler:
    """ helper class for uniform log handling
    Please define self._logger at each class that is derived from this
    """
    _logger = None
    
    def log_message(self, format, *args):
        self._logger.debug(format % args) # todo: perhaps other level

    def log_error(self, format, *args):
        self._logger.error(format % args)
        
    def log_exception(self, format, *args):
        self._logger.exception(format, *args)

    def log_request(self, code='-', size='-'):
        self._logger.log(netsvc.logging.DEBUG_RPC, '"%s" %s %s',
                        self.requestline, str(code), str(size))
    
class MultiHandler2(HttpLogHandler, MultiHTTPHandler):
    _logger = logging.getLogger('http')


class SecureMultiHandler2(HttpLogHandler, SecureMultiHTTPHandler):
    _logger = logging.getLogger('https')

    def getcert_fnames(self):
        tc = tools.config
        fcert = tc.get('secure_cert_file', 'server.cert')
        fkey = tc.get('secure_pkey_file', 'server.key')
        return (fcert,fkey)

class BaseHttpDaemon(threading.Thread, netsvc.Server):
    _RealProto = '??'

    def __init__(self, interface, port, handler):
        threading.Thread.__init__(self, name='%sDaemon-%d'%(self._RealProto, port))
        netsvc.Server.__init__(self)
        self.__port = port
        self.__interface = interface

        try:
            self.server = ThreadedHTTPServer((interface, port), handler, proto=self._RealProto)
            self.server.logRequests = True
            self.server.timeout = self._busywait_timeout
            logging.getLogger("web-services").info(
                        "starting %s service at %s port %d" %
                        (self._RealProto, interface or '0.0.0.0', port,))
        except Exception, e:
            logging.getLogger("httpd").exception("Error occured when starting the server daemon.")
            raise

    @property
    def socket(self):
        return self.server.socket

    def attach(self, path, gw):
        pass

    def stop(self):
        self.running = False
        self._close_socket()

    def run(self):
        self.running = True
        while self.running:
            try:
                self.server.handle_request()
            except (socket.error, select.error), e:
                if self.running or e.args[0] != errno.EBADF:
                    raise
        return True

    def stats(self):
        res = "%sd: " % self._RealProto + ((self.running and "running") or  "stopped")
        if self.server:
            res += ", %d threads" % (self.server.numThreads,)
        return res

# No need for these two classes: init_server() below can initialize correctly
# directly the BaseHttpDaemon class.
class HttpDaemon(BaseHttpDaemon):
    _RealProto = 'HTTP'
    def __init__(self, interface, port):
        super(HttpDaemon, self).__init__(interface, port,
                                         handler=MultiHandler2)

class HttpSDaemon(BaseHttpDaemon):
    _RealProto = 'HTTPS'
    def __init__(self, interface, port):
        try:
            super(HttpSDaemon, self).__init__(interface, port,
                                              handler=SecureMultiHandler2)
        except SSLError, e:
            logging.getLogger('httpsd').exception( \
                        "Can not load the certificate and/or the private key files")
            raise

httpd = None
httpsd = None

def init_servers():
    global httpd, httpsd
    if tools.config.get('xmlrpc'):
        httpd = HttpDaemon(tools.config.get('xmlrpc_interface', ''),
                           int(tools.config.get('xmlrpc_port', 8069)))

    if tools.config.get('xmlrpcs'):
        httpsd = HttpSDaemon(tools.config.get('xmlrpcs_interface', ''),
                             int(tools.config.get('xmlrpcs_port', 8071)))

import SimpleXMLRPCServer
class XMLRPCRequestHandler(FixSendError,HttpLogHandler,SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    rpc_paths = []
    protocol_version = 'HTTP/1.1'
    _logger = logging.getLogger('xmlrpc')

    def _dispatch(self, method, params):
        try:
            service_name = self.path.split("/")[-1]
            auth = getattr(self, 'auth_provider', None)
            return netsvc.dispatch_rpc(service_name, method, params, auth)
        except netsvc.OpenERPDispatcherException, e:
            raise xmlrpclib.Fault(tools.exception_to_unicode(e.exception), e.traceback)

    def handle(self):
        pass

    def finish(self):
        pass

    def setup(self):
        self.connection = dummyconn()
        self.rpc_paths = map(lambda s: '/%s' % s, netsvc.ExportService._services.keys())

def init_xmlrpc():
    if tools.config.get('xmlrpc', False):
        # Example of http file serving:
        # reg_http_service('/test/', HTTPHandler)
        reg_http_service('/xmlrpc/', XMLRPCRequestHandler)
        logging.getLogger("web-services").info("Registered XML-RPC over HTTP")

    if tools.config.get('xmlrpcs', False) \
            and not tools.config.get('xmlrpc', False):
        # only register at the secure server
        reg_http_service('/xmlrpc/', XMLRPCRequestHandler, secure_only=True)
        logging.getLogger("web-services").info("Registered XML-RPC over HTTPS only")

import security

class OpenERPAuthProvider(AuthProvider):
    """ Require basic authentication."""
    def __init__(self,realm='OpenERP User'):
        self.realm = realm
        self.auth_creds = {}
        self.auth_tries = 0
        self.last_auth = None

    def authenticate(self, db, user, passwd, client_address):
        try:
            uid = security.login(db,user,passwd)
            if uid is False:
                return False
            return (user, passwd, db, uid)
        except Exception,e:
            logging.getLogger("auth").debug("Fail auth: %s" % e )
            return False

    def log(self, msg, lvl=logging.INFO):
        logging.getLogger("auth").log(lvl,msg)

    def checkRequest(self,handler,path, db=False):        
        auth_str = handler.headers.get('Authorization',False)
        try:
            if not db:
                db = handler.get_db_from_path(path)
        except Exception:
            if path.startswith('/'):
                path = path[1:]
            psp= path.split('/')
            if len(psp)>1:
                db = psp[0]
            else:
                #FIXME!
                self.log("Wrong path: %s, failing auth" %path)
                raise AuthRejectedExc("Authorization failed. Wrong sub-path.") 
        if self.auth_creds.get(db):
            return True 
        if auth_str and auth_str.startswith('Basic '):
            auth_str=auth_str[len('Basic '):]
            (user,passwd) = base64.decodestring(auth_str).split(':')
            self.log("Found user=\"%s\", passwd=\"***\" for db=\"%s\"" %(user,db))
            acd = self.authenticate(db,user,passwd,handler.client_address)
            if acd != False:
                self.auth_creds[db] = acd
                self.last_auth = db
                return True
        if self.auth_tries > 5:
            self.log("Failing authorization after 5 requests w/o password")
            raise AuthRejectedExc("Authorization failed.")
        self.auth_tries += 1
        raise AuthRequiredExc(atype='Basic', realm=self.realm)

#eof
