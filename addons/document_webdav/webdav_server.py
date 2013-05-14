# -*- encoding: utf-8 -*-
############################################################################9
#
# Copyright P. Christeas <p_christ@hol.gr> 2008-2010
# Copyright OpenERP SA, 2010 (http://www.openerp.com )
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
# as published by the Free Software Foundation; either version 3
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


import logging
from openerp import netsvc
from dav_fs import openerp_dav_handler
from openerp.tools.config import config
try:
    from pywebdav.lib.WebDAVServer import DAVRequestHandler
    from pywebdav.lib.utils import IfParser, TagList
    from pywebdav.lib.errors import DAV_Error, DAV_Forbidden, DAV_NotFound
    from pywebdav.lib.propfind import PROPFIND
except ImportError:
    from DAV.WebDAVServer import DAVRequestHandler
    from DAV.utils import IfParser, TagList
    from DAV.errors import DAV_Error, DAV_Forbidden, DAV_NotFound
    from DAV.propfind import PROPFIND
from openerp.service import http_server
from openerp.service.websrv_lib import FixSendError, HttpOptions
from BaseHTTPServer import BaseHTTPRequestHandler
import urlparse
import urllib
import re
import time
from string import atoi
import addons
import socket
# from DAV.constants import DAV_VERSION_1, DAV_VERSION_2
from xml.dom import minidom
from redirect import RedirectHTTPHandler
_logger = logging.getLogger(__name__)
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


class DAVHandler(DAVRequestHandler, HttpOptions, FixSendError):
    verbose = False

    protocol_version = 'HTTP/1.1'
    _HTTP_OPTIONS= { 'DAV' : ['1', '2'],
                    'Allow' : [ 'GET', 'HEAD', 'COPY', 'MOVE', 'POST', 'PUT',
                            'PROPFIND', 'PROPPATCH', 'OPTIONS', 'MKCOL',
                            'DELETE', 'TRACE', 'REPORT', ]
                    }

    def __init__(self, request, client_address, server):
        self.request = request
        self.client_address = client_address
        self.server = server
        self.setup()

    def get_userinfo(self, user, pw):
        return False

    def _log(self, message):
        self._logger.debug(message)

    def handle(self):
        """Handle multiple requests if necessary."""
        self.close_connection = 1
        try:
            self.handle_one_request()
            while not self.close_connection:
                self.handle_one_request()
        except Exception as e:
            try:
                self.log_error("Request timed out: %r \n Trying old version of HTTPServer", e)
                self._init_buffer()
            except Exception as e:
                #a read or a write timed out.  Discard this connection
                self.log_error("Not working neither, closing connection\n %r", e)
                self.close_connection = 1

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
            raise DAV_Forbidden("Not allowed to copy/move outside webdav path.")
        # TODO: locks
        DAVRequestHandler.copymove(self, CLASS)

    def get_davpath(self):
        return self.davpath

    def log_message(self, format, *args):
        _logger.debug(format % args)

    def log_error(self, format, *args):
        _logger.warning(format % args)

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

    def send_body(self, DATA, code=None, msg=None, desc=None, ctype='application/octet-stream', headers=None):
        if headers and 'Connection' in headers:
            pass
        elif self.request_version in ('HTTP/1.0', 'HTTP/0.9'):
            pass
        elif self.close_connection == 1: # close header already sent
            pass
        elif headers and self.headers.get('Connection',False) == 'Keep-Alive':
            headers['Connection'] = 'keep-alive'

        if headers is None:
            headers = {}

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
                    raise DAV_Error(400, "Cannot accept multiple tokens.")
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
            raise DAV_Error(400, 'Lock refresh must specify token.')

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

from openerp.service.http_server import reg_http_service,OpenERPAuthProvider

class DAVAuthProvider(OpenERPAuthProvider):
    def authenticate(self, db, user, passwd, client_address):
        """ authenticate, but also allow the False db, meaning to skip
            authentication when no db is specified.
        """
        if db is False:
            return True
        return OpenERPAuthProvider.authenticate(self, db, user, passwd, client_address)


class dummy_dav_interface(object):
    """ Dummy dav interface """
    verbose = True

    PROPS={"DAV:" : ('creationdate',
                     'displayname',
                     'getlastmodified',
                     'resourcetype',
                     ),
           }

    M_NS={"DAV:" : "_get_dav", }

    def __init__(self, parent):
        self.parent = parent

    def get_propnames(self, uri):
        return self.PROPS

    def get_prop(self, uri, ns, propname):
        if self.M_NS.has_key(ns):
            prefix=self.M_NS[ns]
        else:
            raise DAV_NotFound
        mname=prefix+"_"+propname.replace('-', '_')
        try:
            m=getattr(self,mname)
            r=m(uri)
            return r
        except AttributeError:
            raise DAV_NotFound

    def get_data(self, uri, range=None):
        raise DAV_NotFound

    def _get_dav_creationdate(self, uri):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _get_dav_getlastmodified(self, uri):
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    def _get_dav_displayname(self, uri):
        return uri

    def _get_dav_resourcetype(self, uri):
        return ('collection', 'DAV:')

    def exists(self, uri):
        """ return 1 or None depending on if a resource exists """
        uri2 = uri.split('/')
        if len(uri2) < 3:
            return True
        _logger.debug("Requested uri: %s", uri)
        return None # no

    def is_collection(self, uri):
        """ return 1 or None depending on if a resource is a collection """
        return None # no

class DAVStaticHandler(http_server.StaticHTTPHandler):
    """ A variant of the Static handler, which will serve dummy DAV requests
    """

    verbose = False
    protocol_version = 'HTTP/1.1'
    _HTTP_OPTIONS= { 'DAV' : ['1', '2'],
                    'Allow' : [ 'GET', 'HEAD',
                            'PROPFIND', 'OPTIONS', 'REPORT', ]
                    }

    def send_body(self, content, code, message='OK', content_type='text/xml'):
        self.send_response(int(code), message)
        self.send_header("Content-Type", content_type)
        # self.send_header('Connection', 'close')
        self.send_header('Content-Length', len(content) or 0)
        self.end_headers()
        if hasattr(self, '_flush'):
            self._flush()

        if self.command != 'HEAD':
            self.wfile.write(content)

    def do_PROPFIND(self):
        """Answer to PROPFIND with generic data.

        A rough copy of python-webdav's do_PROPFIND, but hacked to work
        statically.
        """

        dc = dummy_dav_interface(self)

        # read the body containing the xml request
        # iff there is no body then this is an ALLPROP request
        body = None
        if self.headers.has_key('Content-Length'):
            l = self.headers['Content-Length']
            body = self.rfile.read(atoi(l))

        path = self.path.rstrip('/')
        uri = urllib.unquote(path)

        pf = PROPFIND(uri, dc, self.headers.get('Depth', 'infinity'), body)

        try:
            DATA = '%s\n' % pf.createResponse()
        except DAV_Error, (ec,dd):
            return self.send_error(ec,dd)
        except Exception:
            self.log_exception("Cannot PROPFIND")
            raise

        # work around MSIE DAV bug for creation and modified date
        # taken from Resource.py @ Zope webdav
        if (self.headers.get('User-Agent') ==
            'Microsoft Data Access Internet Publishing Provider DAV 1.1'):
            DATA = DATA.replace('<ns0:getlastmodified xmlns:ns0="DAV:">',
                                    '<ns0:getlastmodified xmlns:n="DAV:" xmlns:b="urn:uuid:c2f41010-65b3-11d1-a29f-00aa00c14882/" b:dt="dateTime.rfc1123">')
            DATA = DATA.replace('<ns0:creationdate xmlns:ns0="DAV:">',
                                    '<ns0:creationdate xmlns:n="DAV:" xmlns:b="urn:uuid:c2f41010-65b3-11d1-a29f-00aa00c14882/" b:dt="dateTime.tz">')

        self.send_body(DATA, '207','Multi-Status','Multiple responses')

    def not_get_baseuri(self):
        baseuri = '/'
        if self.headers.has_key('Host'):
            uparts = list(urlparse.urlparse('/'))
            uparts[1] = self.headers['Host']
            baseuri = urlparse.urlunparse(uparts)
        return baseuri

    def get_davpath(self):
        return ''


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
        reg_http_service(directory, DAVHandler, DAVAuthProvider)
        _logger.info("WebDAV service registered at path: %s/ "% directory)

        if not (config.get_misc('webdav', 'no_root_hack', False)):
            # Now, replace the static http handler with the dav-enabled one.
            # If a static-http service has been specified for our server, then
            # read its configuration and use that dir_path.
            # NOTE: this will _break_ any other service that would be registered
            # at the root path in future.
            base_path = False
            if config.get_misc('static-http','enable', False):
                base_path = config.get_misc('static-http', 'base_path', '/')
            if base_path and base_path == '/':
                dir_path = config.get_misc('static-http', 'dir_path', False)
            else:
                dir_path = addons.get_module_resource('document_webdav','public_html')
                # an _ugly_ hack: we put that dir back in tools.config.misc, so that
                # the StaticHttpHandler can find its dir_path.
                config.misc.setdefault('static-http',{})['dir_path'] = dir_path

            reg_http_service('/', DAVStaticHandler)

except Exception, e:
    _logger.error('Cannot launch webdav: %s' % e)


def init_well_known():
    reps = RedirectHTTPHandler.redirect_paths

    num_svcs = config.get_misc('http-well-known', 'num_services', '0')

    for nsv in range(1, int(num_svcs)+1):
        uri = config.get_misc('http-well-known', 'service_%d' % nsv, False)
        path = config.get_misc('http-well-known', 'path_%d' % nsv, False)
        if not (uri and path):
            continue
        reps['/'+uri] = path

    if int(num_svcs):
        reg_http_service('/.well-known', RedirectHTTPHandler)

init_well_known()

class PrincipalsRedirect(RedirectHTTPHandler):


    redirect_paths = {}

    def _find_redirect(self):
        for b, r in self.redirect_paths.items():
            if self.path.startswith(b):
                return r + self.path[len(b):]
        return False

def init_principals_redirect():
    """ Some devices like the iPhone will look under /principals/users/xxx for
    the user's properties. In OpenERP we _cannot_ have a stray /principals/...
    working path, since we have a database path and the /webdav/ component. So,
    the best solution is to redirect the url with 301. Luckily, it does work in
    the device. The trick is that we need to hard-code the database to use, either
    the one centrally defined in the config, or a "forced" one in the webdav
    section.
    """
    dbname = config.get_misc('webdav', 'principal_dbname', False)
    if (not dbname) and not config.get_misc('webdav', 'no_principals_redirect', False):
        dbname = config.get('db_name', False)
    if dbname:
        PrincipalsRedirect.redirect_paths[''] = '/webdav/%s/principals' % dbname
        reg_http_service('/principals', PrincipalsRedirect)
        _logger.info(
                "Registered HTTP redirect handler for /principals to the %s db.",
                dbname)

init_principals_redirect()

#eof




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
