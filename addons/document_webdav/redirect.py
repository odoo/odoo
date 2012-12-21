# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 OpenERP s.a. (<http://openerp.com>).
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
import urlparse
from openerp.service.websrv_lib import FixSendError, HTTPHandler, HttpOptions
from openerp.service.http_server import HttpLogHandler
_logger = logging.getLogger(__name__)
class RedirectHTTPHandler(HttpLogHandler, FixSendError, HttpOptions, HTTPHandler):
    
    _HTTP_OPTIONS = { 'Allow': ['OPTIONS', 'GET', 'HEAD', 'PROPFIND'] }
    redirect_paths = {}

    def __init__(self, request, client_address, server):
        HTTPHandler.__init__(self,request,client_address,server)

    def send_head(self):
        """Common code for GET and HEAD commands.

        It will either send the correct redirect (Location) response
        or a 404.
        """

        if self.path.endswith('/'):
            self.path = self.path[:-1]
        
        if not self.path:
            # Return an empty page
            self.send_response(200)
            self.send_header("Content-Length", 0)
            self.end_headers()
            return None
        
        redir_path = self._find_redirect()
        if redir_path is False:
            self.send_error(404, "File not found")
            return None
        elif redir_path is None:
            return None

        server_proto = getattr(self.server, 'proto', 'http').lower()
        addr, port = self.server.server_name, self.server.server_port
        try:
            addr, port = self.request.getsockname()
        except Exception, e:
            self.log_error("Cannot calculate own address:" , e)
        
        if self.headers.has_key('Host'):
            uparts = list(urlparse.urlparse("%s://%s:%d"% (server_proto, addr,port)))
            uparts[1] = self.headers['Host']
            baseuri = urlparse.urlunparse(uparts)
        else:
            baseuri = "%s://%s:%d"% (server_proto, addr, port )


        location = baseuri + redir_path
        # relative uri: location = self.redirect_paths[self.path]

        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", 0)
        self.end_headers()
        # Do we need a Cache-content: header here?
        _logger.debug("redirecting %s to %s", self.path, redir_path)
        return None

    def do_PROPFIND(self):
        self._get_ignore_body()
        return self.do_HEAD()

    def _find_redirect(self):
        """ Locate self.path among the redirects we can handle
        @return The new path, False for 404 or None for already sent error
        """
        return self.redirect_paths.get(self.path, False)

    def _get_ignore_body(self):
        if not self.headers.has_key("content-length"):
            return
        max_chunk_size = 10*1024*1024
        size_remaining = int(self.headers["content-length"])
        got = ''
        while size_remaining:
            chunk_size = min(size_remaining, max_chunk_size)
            got = self.rfile.read(chunk_size)
            size_remaining -= len(got)

#eof


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
