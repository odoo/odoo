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

class StaticHTTPHandler(HttpLogHandler, FixSendError, HttpOptions, HTTPHandler):
    _logger = logging.getLogger('httpd')
    _HTTP_OPTIONS = { 'Allow': ['OPTIONS', 'GET', 'HEAD'] }

    def __init__(self,request, client_address, server):
        HTTPHandler.__init__(self,request,client_address,server)
        document_root = tools.config.get('static_http_document_root', False)
        assert document_root, "Please specify static_http_document_root in configuration, or disable static-httpd!"
        self.__basepath = document_root

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        path = self.__basepath
        for word in words:
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

def init_static_http():
    if not tools.config.get('static_http_enable', False):
        return
    
    document_root = tools.config.get('static_http_document_root', False)
    assert document_root, "Document root must be specified explicitly to enable static HTTP service (option --static-http-document-root)"
    
    base_path = tools.config.get('static_http_url_prefix', '/')
    
    reg_http_service(base_path, StaticHTTPHandler)
    
    logging.getLogger("web-services").info("Registered HTTP dir %s for %s" % \
                        (document_root, base_path))

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
