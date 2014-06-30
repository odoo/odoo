# -*- coding: utf-8 -*-
#
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
###############################################################################


""" Framework for generic http servers

    This library contains *no* OpenERP-specific functionality. It should be
    usable in other projects, too.
"""

import logging
import SocketServer
from BaseHTTPServer import *
from SimpleHTTPServer import SimpleHTTPRequestHandler

_logger = logging.getLogger(__name__)

class AuthRequiredExc(Exception):
    def __init__(self,atype,realm):
        Exception.__init__(self)
        self.atype = atype
        self.realm = realm

class AuthRejectedExc(Exception):
    pass

class AuthProvider:
    def __init__(self,realm):
        self.realm = realm

    def authenticate(self, user, passwd, client_address):
        return False

    def log(self, msg):
        print msg

    def checkRequest(self,handler,path = '/'):
        """ Check if we are allowed to process that request
        """
        pass

class HTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self,request, client_address, server):
        SimpleHTTPRequestHandler.__init__(self,request,client_address,server)
        # print "Handler for %s inited" % str(client_address)
        self.protocol_version = 'HTTP/1.1'
        self.connection = dummyconn()

    def handle(self):
        """ Classes here should NOT handle inside their constructor
        """
        pass

    def finish(self):
        pass

    def setup(self):
        pass

# A list of HTTPDir.
handlers = []

class HTTPDir:
    """ A dispatcher class, like a virtual folder in httpd
    """
    def __init__(self, path, handler, auth_provider=None, secure_only=False):
        self.path = path
        self.handler = handler
        self.auth_provider = auth_provider
        self.secure_only = secure_only

    def matches(self, request):
        """ Test if some request matches us. If so, return
            the matched path. """
        if request.startswith(self.path):
            return self.path
        return False

    def instanciate_handler(self, request, client_address, server):
        handler = self.handler(noconnection(request), client_address, server)
        if self.auth_provider:
            handler.auth_provider = self.auth_provider()
        return handler

def reg_http_service(path, handler, auth_provider=None, secure_only=False):
    """ Register a HTTP handler at a given path.

    The auth_provider will be instanciated and set on the handler instances.
    """
    global handlers
    service = HTTPDir(path, handler, auth_provider, secure_only)
    pos = len(handlers)
    lastpos = pos
    while pos > 0:
        pos -= 1
        if handlers[pos].matches(service.path):
            lastpos = pos
        # we won't break here, but search all way to the top, to
        # ensure there is no lesser entry that will shadow the one
        # we are inserting.
    handlers.insert(lastpos, service)

def list_http_services(protocol=None):
    global handlers
    ret = []
    for svc in handlers:
        if protocol is None or protocol == 'http' or svc.secure_only:
            ret.append((svc.path, str(svc.handler)))
    
    return ret

def find_http_service(path, secure=False):
    global handlers
    for vdir in handlers:
        p = vdir.matches(path)
        if p == False or (vdir.secure_only and not secure):
            continue
        return vdir
    return None

class noconnection(object):
    """ a class to use instead of the real connection
    """
    def __init__(self, realsocket=None):
        self.__hidden_socket = realsocket

    def makefile(self, mode, bufsize):
        return None

    def close(self):
        pass

    def getsockname(self):
        """ We need to return info about the real socket that is used for the request
        """
        if not self.__hidden_socket:
            raise AttributeError("No-connection class cannot tell real socket")
        return self.__hidden_socket.getsockname()

class dummyconn:
    def shutdown(self, tru):
        pass

def _quote_html(html):
    return html.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class FixSendError:
    #error_message_format = """ """
    def send_error(self, code, message=None):
        #overriden from BaseHTTPRequestHandler, we also send the content-length
        try:
            short, long = self.responses[code]
        except KeyError:
            short, long = '???', '???'
        if message is None:
            message = short
        explain = long
        _logger.error("code %d, message %s", code, message)
        # using _quote_html to prevent Cross Site Scripting attacks (see bug #1100201)
        content = (self.error_message_format %
                   {'code': code, 'message': _quote_html(message), 'explain': explain})
        self.send_response(code, message)
        self.send_header("Content-Type", self.error_content_type)
        self.send_header('Connection', 'close')
        self.send_header('Content-Length', len(content) or 0)
        self.end_headers()
        if hasattr(self, '_flush'):
            self._flush()
        
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(content)

class HttpOptions:
    _HTTP_OPTIONS = {'Allow': ['OPTIONS' ] }

    def do_OPTIONS(self):
        """return the list of capabilities """

        opts = self._HTTP_OPTIONS
        nopts = self._prep_OPTIONS(opts)
        if nopts:
            opts = nopts

        self.send_response(200)
        self.send_header("Content-Length", 0)
        if 'Microsoft' in self.headers.get('User-Agent', ''):
            self.send_header('MS-Author-Via', 'DAV') 
            # Microsoft's webdav lib ass-umes that the server would
            # be a FrontPage(tm) one, unless we send a non-standard
            # header that we are not an elephant.
            # http://www.ibm.com/developerworks/rational/library/2089.html

        for key, value in opts.items():
            if isinstance(value, basestring):
                self.send_header(key, value)
            elif isinstance(value, (tuple, list)):
                self.send_header(key, ', '.join(value))
        self.end_headers()

    def _prep_OPTIONS(self, opts):
        """Prepare the OPTIONS response, if needed
        
        Sometimes, like in special DAV folders, the OPTIONS may contain
        extra keywords, perhaps also dependant on the request url. 
        :param opts: MUST be copied before being altered
        :returns: the updated options.

        """
        return opts


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
