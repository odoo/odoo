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


import netsvc
import tools
from dav_fs import openerp_dav_handler
from tools.config import config
from DAV.WebDAVServer import DAVRequestHandler
from service.websrv_lib import HTTPDir,FixSendError
import urlparse
import urllib
from string import atoi,split
from DAV.errors import *

def OpenDAVConfig(**kw):
    class OpenDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

    class Config:
        DAV = OpenDAV(**kw)

    return Config()


class DAVHandler(FixSendError,DAVRequestHandler):
    verbose = False
    
    def get_userinfo(self,user,pw):
        print "get_userinfo"
        return False
    def _log(self, message):
        netsvc.Logger().notifyChannel("webdav",netsvc.LOG_DEBUG,message)
    
    def handle(self):
        self._init_buffer()

    def finish(self):
        pass

    def get_db_from_path(self, uri):
        if uri or uri == '/':
            dbs = self.IFACE_CLASS.db_list()
            res = len(dbs) and dbs[0] or False
        else:
            res =  self.IFACE_CLASS.get_db(uri)        
        return res

    def setup(self):
        davpath = '/'+config.get_misc('webdav','vdir','webdav')
        self.baseuri = "http://%s:%d/"% (self.server.server_name,self.server.server_port)
        self.IFACE_CLASS  = openerp_dav_handler(self, self.verbose)
        
    
    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('webdav',netsvc.LOG_DEBUG_RPC,format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('xmlrpc',netsvc.LOG_WARNING,format % args)

    def do_PUT(self):
        dc=self.IFACE_CLASS        
        uri=urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri=urllib.unquote(uri)
        # Handle If-Match
        if self.headers.has_key('If-Match'):
            test = False
            etag = None
            
            for match in self.headers['If-Match'].split(','):                
                if match == '*':
                    if dc.exists(uri):
                        test = True
                        break
                else:
                    if dc.match_prop(uri, match, "DAV:", "getetag"):
                        test = True
                        break
            if not test:
                self.send_status(412)
                return

        # Handle If-None-Match
        if self.headers.has_key('If-None-Match'):
            test = True
            etag = None            
            for match in self.headers['If-None-Match'].split(','):
                if match == '*':
                    if dc.exists(uri):
                        test = False
                        break
                else:
                    if dc.match_prop(uri, match, "DAV:", "getetag"):
                        test = False
                        break
            if not test:
                self.send_status(412)
                return

        # Handle expect
        expect = self.headers.get('Expect', '')
        if (expect.lower() == '100-continue' and
                self.protocol_version >= 'HTTP/1.1' and
                self.request_version >= 'HTTP/1.1'):
            self.send_status(100)
            self._flush()

        # read the body
        body=None
        if self.headers.has_key("Content-Length"):
            l=self.headers['Content-Length']
            body=self.rfile.read(atoi(l))

        # locked resources are not allowed to be overwritten
        if self._l_isLocked(uri):
            return self.send_body(None, '423', 'Locked', 'Locked')

        ct=None
        if self.headers.has_key("Content-Type"):
            ct=self.headers['Content-Type']
        try:
            location = dc.put(uri,body,ct)
        except DAV_Error, (ec,dd):
            return self.send_status(ec)

        headers = {}
        if location:
            headers['Location'] = location

        try:
            etag = dc.get_prop(location or uri, "DAV:", "getetag")
            headers['ETag'] = etag
        except:
            pass

        self.send_body(None, '201', 'Created', '', headers=headers)


try:
    from service.http_server import reg_http_service,OpenERPAuthProvider   

    if (config.get_misc('webdav','enable',True)):
        directory = '/'+config.get_misc('webdav','vdir','webdav') 
        handler = DAVHandler
        verbose = config.get_misc('webdav','verbose',True)
        handler.debug = config.get_misc('webdav','debug',True)
        _dc = { 'verbose' : verbose,
                'directory' : directory,
                'lockemulation' : False,
                    
                }

        conf = OpenDAVConfig(**_dc)
        handler._config = conf
        reg_http_service(HTTPDir(directory,DAVHandler,OpenERPAuthProvider()))
        netsvc.Logger().notifyChannel('webdav',netsvc.LOG_INFO,"WebDAV service registered at path: %s/ "% directory)
except Exception, e:
    logger = netsvc.Logger()
    logger.notifyChannel('webdav', netsvc.LOG_ERROR, 'Cannot launch webdav: %s' % e)

#eof



