# -*- encoding: utf-8 -*-

#
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
#
# Disclaimer: Many of the functions below borrow code from the
#   python-webdav library (http://code.google.com/p/pywebdav/ ),
#   which they import and override to suit OpenERP functionality.
# python-webdav was written by: Simon Pamies <s.pamies@banality.de>
#                               Christian Scholz <mrtopf@webdav.de>
#                               Vince Spicer <vince@vince.ca>
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
from dav_fs import openerp_dav_handler
from tools.config import config
from DAV.WebDAVServer import DAVRequestHandler
from service.websrv_lib import HTTPDir, FixSendError, HttpOptions
from BaseHTTPServer import BaseHTTPRequestHandler
import urlparse
import urllib
import re
from string import atoi
from DAV.errors import *
from DAV.utils import IfParser, TagList
# from DAV.constants import DAV_VERSION_1, DAV_VERSION_2
from xml.dom import minidom

khtml_re = re.compile(r' KHTML/([0-9\.]+) ')

def OpenDAVConfig(**kw):
    class OpenDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

        def getboolean(self, word):
            return self.__dict__.get(word, False)

    class Config:
        DAV = OpenDAV(**kw)

    return Config()


class DAVHandler(HttpOptions, FixSendError, DAVRequestHandler):
    verbose = False
    protocol_version = 'HTTP/1.1'
    _HTTP_OPTIONS= { 'DAV' : ['1', '2'],
                    'Allow' : [ 'GET', 'HEAD', 'COPY', 'MOVE', 'POST', 'PUT',
                            'PROPFIND', 'PROPPATCH', 'OPTIONS', 'MKCOL',
                            'DELETE', 'TRACE', 'REPORT', ]
                    }

    def get_userinfo(self,user,pw):
        return False
    def _log(self, message):
        netsvc.Logger().notifyChannel("webdav",netsvc.LOG_DEBUG,message)

    def handle(self):
        self._init_buffer()

    def finish(self):
        pass

    def get_db_from_path(self, uri):
        # interface class will handle all cases.
        res =  self.IFACE_CLASS.get_db(uri, allow_last=True)
        return res

    def setup(self):
        self.davpath = '/'+config.get_misc('webdav','vdir','webdav')
        addr, port = self.server.server_name, self.server.server_port
        server_proto = getattr(self.server,'proto', 'http').lower()
        try:
            if hasattr(self.request, 'getsockname'):
                addr, port = self.request.getsockname()
        except Exception, e:
            self.log_error("Cannot calculate own address: %s" , e)
        # Too early here to use self.headers
        self.baseuri = "%s://%s:%d/"% (server_proto, addr, port)
        self.IFACE_CLASS  = openerp_dav_handler(self, self.verbose)

    def copymove(self, CLASS):
        """ Our uri scheme removes the /webdav/ component from there, so we
        need to mangle the header, too.
        """
        up = urlparse.urlparse(urllib.unquote(self.headers['Destination']))
        if up.path.startswith(self.davpath):
            self.headers['Destination'] = up.path[len(self.davpath):]
        else:
            raise DAV_Forbidden("Not allowed to copy/move outside webdav path")
        # TODO: locks
        DAVRequestHandler.copymove(self, CLASS)

    def get_davpath(self):
        return self.davpath

    def log_message(self, format, *args):
        netsvc.Logger().notifyChannel('webdav', netsvc.LOG_DEBUG_RPC, format % args)

    def log_error(self, format, *args):
        netsvc.Logger().notifyChannel('xmlrpc', netsvc.LOG_WARNING, format % args)

    def _prep_OPTIONS(self, opts):
        ret = opts
        dc=self.IFACE_CLASS
        uri=urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri=urllib.unquote(uri)
        try:
            ret = dc.prep_http_options(uri, opts)
        except DAV_Error, (ec,dd):
            pass
        except Exception,e:
            self.log_error("Error at options: %s", str(e))
            raise
        return ret

    def send_response(self, code, message=None):
        # the BufferingHttpServer will send Connection: close , while
        # the BaseHTTPRequestHandler will only accept int code.
        # workaround both of them.
        if self.command == 'PROPFIND' and int(code) == 404:
            kh = khtml_re.search(self.headers.get('User-Agent',''))
            if kh and (kh.group(1) < '4.5'):
                # There is an ugly bug in all khtml < 4.5.x, where the 404
                # response is treated as an immediate error, which would even
                # break the flow of a subsequent PUT request. At the same time,
                # the 200 response  (rather than 207 with content) is treated
                # as "path not exist", so we send this instead
                # https://bugs.kde.org/show_bug.cgi?id=166081
                code = 200
        BaseHTTPRequestHandler.send_response(self, int(code), message)

    def send_header(self, key, value):
        if key == 'Connection' and value == 'close':
            self.close_connection = 1
        DAVRequestHandler.send_header(self, key, value)

    def send_body(self, DATA, code = None, msg = None, desc = None, ctype='application/octet-stream', headers=None):
        if headers and 'Connection' in headers:
            pass
        elif self.request_version in ('HTTP/1.0', 'HTTP/0.9'):
            pass
        elif self.close_connection == 1: # close header already sent
            pass
        else:
            if headers is None:
                headers = {}
            if self.headers.get('Connection',False) == 'Keep-Alive':
                headers['Connection'] = 'keep-alive'

        DAVRequestHandler.send_body(self, DATA, code=code, msg=msg, desc=desc,
                    ctype=ctype, headers=headers)

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
                self._get_body()
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
                self._get_body()
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
        body=self._get_body()

        # locked resources are not allowed to be overwritten
        if self._l_isLocked(uri):
            return self.send_body(None, '423', 'Locked', 'Locked')

        ct=None
        if self.headers.has_key("Content-Type"):
            ct=self.headers['Content-Type']
        try:
            location = dc.put(uri, body, ct)
        except DAV_Error, (ec,dd):
            self.log_error("Cannot PUT to %s: %s", uri, dd)
            return self.send_status(ec)

        headers = {}
        etag = None
        if location and isinstance(location, tuple):
            etag = location[1]
            location = location[0]
            # note that we have allowed for > 2 elems
        if location:
            headers['Location'] = location
        else:
            try:
                if not etag:
                    etag = dc.get_prop(location or uri, "DAV:", "getetag")
                if etag:
                    headers['ETag'] = str(etag)
            except Exception:
                pass

        self.send_body(None, '201', 'Created', '', headers=headers)

    def _get_body(self):
        body = None
        if self.headers.has_key("Content-Length"):
            l=self.headers['Content-Length']
            body=self.rfile.read(atoi(l))
        return body

    def do_DELETE(self):
        try:
            DAVRequestHandler.do_DELETE(self)
        except DAV_Error, (ec, dd):
            return self.send_status(ec)

    def do_UNLOCK(self):
        """ Unlocks given resource """

        dc = self.IFACE_CLASS
        self.log_message('UNLOCKing resource %s' % self.headers)

        uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri = urllib.unquote(uri)

        token = self.headers.get('Lock-Token', False)
        if token:
            token = token.strip()
            if token[0] == '<' and token[-1] == '>':
                token = token[1:-1]
            else:
                token = False

        if not token:
            return self.send_status(400, 'Bad lock token')

        try:
            res = dc.unlock(uri, token)
        except DAV_Error, (ec, dd):
            return self.send_status(ec, dd)
        
        if res == True:
            self.send_body(None, '204', 'OK', 'Resource unlocked.')
        else:
            # We just differentiate the description, for debugging purposes
            self.send_body(None, '204', 'OK', 'Resource not locked.')

    def do_LOCK(self):
        """ Attempt to place a lock on the given resource.
        """

        dc = self.IFACE_CLASS
        lock_data = {}

        self.log_message('LOCKing resource %s' % self.headers)

        body = None
        if self.headers.has_key('Content-Length'):
            l = self.headers['Content-Length']
            body = self.rfile.read(atoi(l))

        depth = self.headers.get('Depth', 'infinity')

        uri = urlparse.urljoin(self.get_baseuri(dc), self.path)
        uri = urllib.unquote(uri)
        self.log_message('do_LOCK: uri = %s' % uri)

        ifheader = self.headers.get('If')

        if ifheader:
            ldif = IfParser(ifheader)
            if isinstance(ldif, list):
                if len(ldif) !=1 or (not isinstance(ldif[0], TagList)) \
                        or len(ldif[0].list) != 1:
                    raise DAV_Error(400, "Cannot accept multiple tokens")
                ldif = ldif[0].list[0]
                if ldif[0] == '<' and ldif[-1] == '>':
                    ldif = ldif[1:-1]

            lock_data['token'] = ldif

        if not body:
            lock_data['refresh'] = True
        else:
            lock_data['refresh'] = False
            lock_data.update(self._lock_unlock_parse(body))

        if lock_data['refresh'] and not lock_data.get('token', False):
            raise DAV_Error(400, 'Lock refresh must specify token')

        lock_data['depth'] = depth

        try:
            created, data, lock_token = dc.lock(uri, lock_data)
        except DAV_Error, (ec, dd):
            return self.send_status(ec, dd)

        headers = {}
        if not lock_data['refresh']:
            headers['Lock-Token'] = '<%s>' % lock_token

        if created:
            self.send_body(data, '201', 'Created',  ctype='text/xml', headers=headers)
        else:
            self.send_body(data, '200', 'OK', ctype='text/xml', headers=headers)

    def _lock_unlock_parse(self, body):
        # Override the python-webdav function, with some improvements
        # Unlike the py-webdav one, we also parse the owner minidom elements into
        # pure pythonic struct.
        doc = minidom.parseString(body)

        data = {}
        owners = []
        for info in doc.getElementsByTagNameNS('DAV:', 'lockinfo'):
            for scope in info.getElementsByTagNameNS('DAV:', 'lockscope'):
                for scc in scope.childNodes:
                    if scc.nodeType == info.ELEMENT_NODE \
                            and scc.namespaceURI == 'DAV:':
                        data['lockscope'] = scc.localName
                        break
            for ltype in info.getElementsByTagNameNS('DAV:', 'locktype'):
                for ltc in ltype.childNodes:
                    if ltc.nodeType == info.ELEMENT_NODE \
                            and ltc.namespaceURI == 'DAV:':
                        data['locktype'] = ltc.localName
                        break
            for own in info.getElementsByTagNameNS('DAV:', 'owner'):
                for ono in own.childNodes:
                    if ono.nodeType == info.TEXT_NODE:
                        if ono.data:
                            owners.append(ono.data)
                    elif ono.nodeType == info.ELEMENT_NODE \
                            and ono.namespaceURI == 'DAV:' \
                            and ono.localName == 'href':
                        href = ''
                        for hno in ono.childNodes:
                            if hno.nodeType == info.TEXT_NODE:
                                href += hno.data
                        owners.append(('href','DAV:', href))

            if len(owners) == 1:
                data['lockowner'] = owners[0]
            elif not owners:
                pass
            else:
                data['lockowner'] = owners
        return data

from service.http_server import reg_http_service,OpenERPAuthProvider

class DAVAuthProvider(OpenERPAuthProvider):
    def authenticate(self, db, user, passwd, client_address):
        """ authenticate, but also allow the False db, meaning to skip
            authentication when no db is specified.
        """
        if db is False:
            return True
        return OpenERPAuthProvider.authenticate(self, db, user, passwd, client_address)

try:

    if (config.get_misc('webdav','enable',True)):
        directory = '/'+config.get_misc('webdav','vdir','webdav')
        handler = DAVHandler
        verbose = config.get_misc('webdav','verbose',True)
        handler.debug = config.get_misc('webdav','debug',True)
        _dc = { 'verbose' : verbose,
                'directory' : directory,
                'lockemulation' : True,
                }

        conf = OpenDAVConfig(**_dc)
        handler._config = conf
        reg_http_service(HTTPDir(directory,DAVHandler,DAVAuthProvider()))
        netsvc.Logger().notifyChannel('webdav', netsvc.LOG_INFO, "WebDAV service registered at path: %s/ "% directory)
except Exception, e:
    logger = netsvc.Logger()
    logger.notifyChannel('webdav', netsvc.LOG_ERROR, 'Cannot launch webdav: %s' % e)

#eof



