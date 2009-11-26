# -*- encoding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
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

""" This file contains instance of the http server.

    
"""
from websrv_lib import *
import netsvc
import threading
import tools
import os
import socket
import xmlrpclib

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

    def __init__(self, addr, requestHandler,
                 logRequests=True, allow_none=False, encoding=None, bind_and_activate=True):
        self.logRequests = logRequests

        SimpleXMLRPCDispatcher.__init__(self, allow_none, encoding)
        HTTPServer.__init__(self, addr, requestHandler)

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
        import traceback
        netsvc.Logger().notifyChannel("init", netsvc.LOG_ERROR,"Server error in request from %s:\n%s" %
            (client_address,traceback.format_exc()))

class MultiHandler2(MultiHTTPHandler):
    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('http',netsvc.LOG_DEBUG,format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('http',netsvc.LOG_ERROR,format % args)


class SecureMultiHandler2(SecureMultiHTTPHandler):
    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('https',netsvc.LOG_DEBUG,format % args)

    def getcert_fnames(self):
        tc = tools.config
        fcert = tc.get_misc('httpsd','sslcert', 'ssl/server.cert')
        fkey = tc.get_misc('httpsd','sslkey', 'ssl/server.key')
        return (fcert,fkey)

    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('http',netsvc.LOG_DEBUG,format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('http',netsvc.LOG_ERROR,format % args)

class HttpDaemon(threading.Thread, netsvc.Server):
    def __init__(self, interface, port):
        threading.Thread.__init__(self)
        netsvc.Server.__init__(self)
        self.__port = port
        self.__interface = interface

        try:
            self.server = ThreadedHTTPServer((interface, port), MultiHandler2)
            self.server.vdirs = []
            self.server.logRequests = True
            netsvc.Logger().notifyChannel("web-services", netsvc.LOG_INFO, 
                "starting HTTP service at %s port %d" % (interface or '0.0.0.0', port,))
        except Exception, e:
            netsvc.Logger().notifyChannel('httpd', netsvc.LOG_CRITICAL, "Error occur when starting the server daemon: %s" % (e,))
            raise


    def attach(self, path, gw):
        pass

    def stop(self):
        self.running = False
        if os.name != 'nt':
            self.server.socket.shutdown( hasattr(socket, 'SHUT_RDWR') and socket.SHUT_RDWR or 2 )
        self.server.socket.close()

    def run(self):
        #self.server.register_introspection_functions()

        self.running = True
        while self.running:
            self.server.handle_request()
        return True

class HttpSDaemon(threading.Thread, netsvc.Server):
    def __init__(self, interface, port):
        threading.Thread.__init__(self)
        netsvc.Server.__init__(self)
        self.__port = port
        self.__interface = interface

        try:
            self.server = ThreadedHTTPServer((interface, port), SecureMultiHandler2)
            self.server.vdirs = []
            self.server.logRequests = True
            netsvc.Logger().notifyChannel("web-services", netsvc.LOG_INFO, 
                "starting HTTPS service at %s port %d" % (interface or '0.0.0.0', port,))
        except SSLError, e:
            netsvc.Logger().notifyChannel('httpd-ssl', netsvc.LOG_CRITICAL, "Can not load the certificate and/or the private key files")
            raise
        except Exception, e:
            netsvc.Logger().notifyChannel('httpd-ssl', netsvc.LOG_CRITICAL, "Error occur when starting the server daemon: %s" % (e,))
            raise

    def attach(self, path, gw):
        pass

    def stop(self):
        self.running = False
        if os.name != 'nt':
            self.server.socket.shutdown( hasattr(socket, 'SHUT_RDWR') and socket.SHUT_RDWR or 2 )
        self.server.socket.close()

    def run(self):
        #self.server.register_introspection_functions()

        self.running = True
        while self.running:
            self.server.handle_request()
        return True

httpd = None
httpsd = None

def init_servers():
    global httpd, httpsd
    if tools.config.get_misc('httpd','enable', True):
        httpd = HttpDaemon(tools.config.get_misc('httpd','interface', ''), \
            tools.config.get_misc('httpd','port', int(tools.config.get('port',8069))))

    if tools.config.get_misc('httpsd','enable', False):
        httpsd = HttpSDaemon(tools.config.get_misc('httpsd','interface', ''), \
            tools.config.get_misc('httpsd','port', 8071))

def reg_http_service(hts, secure_only = False):
    """ Register some handler to httpd.
        hts must be an HTTPDir
    """
    global httpd, httpsd
    if not isinstance(hts, HTTPDir):
        raise Exception("Wrong class for http service")
    
    if httpd and not secure_only:
        httpd.server.vdirs.append(hts)
    
    if httpsd:
        httpsd.server.vdirs.append(hts)
    
    if (not httpd) and (not httpsd):
        netsvc.Logger().notifyChannel('httpd',netsvc.LOG_WARNING,"No httpd available to register service %s" % hts.path)
    return

import SimpleXMLRPCServer
class XMLRPCRequestHandler(netsvc.OpenERPDispatcher,FixSendError,SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    rpc_paths = [] 
    protocol_version = 'HTTP/1.1'
    def _dispatch(self, method, params):
        try:
            service_name = self.path.split("/")[-1]
            return self.dispatch(service_name, method, params)
        except netsvc.OpenERPDispatcherException, e:
            raise xmlrpclib.Fault(tools.exception_to_unicode(e.exception), e.traceback)

    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('xmlrpc',netsvc.LOG_DEBUG_RPC,format % args)

    def handle(self):
        pass

    def finish(self):
        pass

    def setup(self):
        self.connection = dummyconn()
        if not len(XMLRPCRequestHandler.rpc_paths):
            XMLRPCRequestHandler.rpc_paths = map(lambda s: '/%s' % s, netsvc.ExportService._services.keys())
        pass


def init_xmlrpc():
    if not tools.config.get_misc('xmlrpc','enable', True):
        return
    reg_http_service(HTTPDir('/xmlrpc/',XMLRPCRequestHandler))
    # Example of http file serving:
    # reg_http_service(HTTPDir('/test/',HTTPHandler))
    netsvc.Logger().notifyChannel("web-services", netsvc.LOG_INFO, 
            "Registered XML-RPC over HTTP")
            

class OerpAuthProxy(AuthProxy):
    """ Require basic authentication..
    
        This is a copy of the BasicAuthProxy, which however checks/caches the db
        as well.
    """
    def __init__(self,provider):
        AuthProxy.__init__(self,provider)
        self.auth_creds = {}
        self.auth_tries = 0
        self.last_auth = None

    def checkRequest(self,handler,path = '/'):
        if self.auth_creds:
            return True
        auth_str = handler.headers.get('Authorization',False)
        try:
            db = handler.get_db_from_path(path)
            print "Got db:",db
        except:
            if path.startswith('/'):
                path = path[1:]
            psp= path.split('/')
            if len(psp)>1:
                db = psp[0]
            else:
                #FIXME!
                self.provider.log("Wrong path: %s, failing auth" %path)
                raise AuthRejectedExc("Authorization failed. Wrong sub-path.")

        if auth_str and auth_str.startswith('Basic '):
            auth_str=auth_str[len('Basic '):]
            (user,passwd) = base64.decodestring(auth_str).split(':')
            self.provider.log("Found user=\"%s\", passwd=\"***\" for db=\"%s\"" %(user,db))
            acd = self.provider.authenticate(db,user,passwd,handler.client_address)
            if acd != False:
                self.auth_creds[db] = acd
                self.last_auth=db
                return True
        if self.auth_tries > 5:
            self.provider.log("Failing authorization after 5 requests w/o password")
            raise AuthRejectedExc("Authorization failed.")
        self.auth_tries += 1
        raise AuthRequiredExc(atype = 'Basic', realm=self.provider.realm)

import security
class OpenERPAuthProvider(AuthProvider):
    def __init__(self,realm = 'OpenERP User'):
        self.realm = realm

    def setupAuth(self, multi, handler):
        if not multi.sec_realms.has_key(self.realm):
            multi.sec_realms[self.realm] = OerpAuthProxy(self)
        handler.auth_proxy = multi.sec_realms[self.realm]

    def authenticate(self, db, user, passwd, client_address):
        try:
            uid = security.login(db,user,passwd)
            if uid is False:
                return False
            return (user, passwd, db, uid)
        except Exception,e:
            netsvc.Logger().notifyChannel("auth",netsvc.LOG_DEBUG,"Fail auth:"+ str(e))
            return False
        
    def log(self, msg):
        netsvc.Logger().notifyChannel("auth",netsvc.LOG_INFO,msg)

#eof
