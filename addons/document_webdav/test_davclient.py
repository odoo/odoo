#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
# Copyright P. Christeas <p_christ@hol.gr> 2008,2009
# Copyright OpenERP SA. (http://www.openerp.com) 2010
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

""" A trivial HTTP/WebDAV client, used for testing the server
"""
# code taken from the 'http-client.py' script:
# http://git.hellug.gr/?p=xrg/openerp;a=history;f=tests/http-client.py;hb=refs/heads/xrg-60

import gzip
import logging
import xml.dom.minidom

import httplib

from tools import config
from xmlrpclib import Transport, ProtocolError
import StringIO
import base64

log = logging.getLogger('http-client')

class HTTP11(httplib.HTTP):
        _http_vsn = 11
        _http_vsn_str = 'HTTP/1.1'

class PersistentTransport(Transport):
    """Handles an HTTP transaction to an XML-RPC server, persistently."""

    def __init__(self, use_datetime=0):
        self._use_datetime = use_datetime
        self._http = {}
        log.debug("Using persistent transport")

    def make_connection(self, host):
        # create a HTTP connection object from a host descriptor
        if not self._http.has_key(host):
                host, extra_headers, x509 = self.get_host_info(host)
                self._http[host] = HTTP11(host)
                log.debug("New connection to %s", host)
        return self._http[host]

    def get_host_info(self, host):
        host, extra_headers, x509 = Transport.get_host_info(self,host)
        if extra_headers == None:
                extra_headers = []
                
        extra_headers.append( ( 'Connection', 'keep-alive' ))
        
        return host, extra_headers, x509

    def _parse_response(self, file, sock, response):
        """ read response from input file/socket, and parse it
            We are persistent, so it is important to only parse
            the right amount of input
        """

        p, u = self.getparser()

        if response.msg.get('content-encoding') == 'gzip':
            gzdata = StringIO.StringIO()
            while not response.isclosed():
                rdata = response.read(1024)
                if not rdata:
                    break
                gzdata.write(rdata)
            gzdata.seek(0)
            rbuffer = gzip.GzipFile(mode='rb', fileobj=gzdata)
            while True:
                respdata = rbuffer.read()
                if not respdata:
                    break
                p.feed(respdata)
        else:
            while not response.isclosed():
                rdata = response.read(1024)
                if not rdata:
                        break
                p.feed(rdata)
                if len(rdata)<1024:
                        break

        p.close()
        return u.close()

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)

        self.send_request(h, handler, request_body)
        self.send_host(h, host)
        self.send_user_agent(h)
        self.send_content(h, request_body)

        resp = h._conn.getresponse()
        # TODO: except BadStatusLine, e:
        
        errcode, errmsg, headers = resp.status, resp.reason, resp.msg
        

        if errcode != 200:
            raise ProtocolError(
                host + handler,
                errcode, errmsg,
                headers
                )

        self.verbose = verbose

        try:
            sock = h._conn.sock
        except AttributeError:
            sock = None

        return self._parse_response(h.getfile(), sock, resp)

class CompressedTransport(PersistentTransport):
    def send_content(self, connection, request_body):
        connection.putheader("Content-Type", "text/xml")
        
        if len(request_body) > 512 or True:
            buffer = StringIO.StringIO()
            output = gzip.GzipFile(mode='wb', fileobj=buffer)
            output.write(request_body)
            output.close()
            buffer.seek(0)
            request_body = buffer.getvalue()
            connection.putheader('Content-Encoding', 'gzip')

        connection.putheader("Content-Length", str(len(request_body)))
        connection.putheader("Accept-Encoding",'gzip')
        connection.endheaders()
        if request_body:
            connection.send(request_body)

    def send_request(self, connection, handler, request_body):
        connection.putrequest("POST", handler, skip_accept_encoding=1)

class SafePersistentTransport(PersistentTransport):
    def make_connection(self, host):
        # create a HTTP connection object from a host descriptor
        if not self._http.has_key(host):
                host, extra_headers, x509 = self.get_host_info(host)
                self._http[host] = httplib.HTTPS(host, None, **(x509 or {}))
                log.debug("New connection to %s", host)
        return self._http[host]

class AuthClient(object):
    def getAuth(self, atype, realm):
        raise NotImplementedError("Cannot authenticate for %s" % atype)
        
    def resolveFailedRealm(self, realm):
        """ Called when, using a known auth type, the realm is not in cache
        """
        raise NotImplementedError("Cannot authenticate for realm %s" % realm)

class BasicAuthClient(AuthClient):
    def __init__(self):
        self._realm_dict = {}

    def getAuth(self, atype, realm):
        if atype != 'Basic' :
            return super(BasicAuthClient,self).getAuth(atype, realm)

        if not self._realm_dict.has_key(realm):
            log.debug("realm dict: %r", self._realm_dict)
            log.debug("missing key: \"%s\"" % realm)
            self.resolveFailedRealm(realm)
        return 'Basic '+ self._realm_dict[realm]
        
    def addLogin(self, realm, username, passwd):
        """ Add some known username/password for a specific login.
            This function should be called once, for each realm
            that we want to authenticate against
        """
        assert realm
        auths = base64.encodestring(username + ':' + passwd)
        if auths[-1] == "\n":
            auths = auths[:-1]
        self._realm_dict[realm] = auths

class addAuthTransport:
    """ Intermediate class that authentication algorithm to http transport
    """
    
    def setAuthClient(self, authobj):
        """ Set the authentication client object.
            This method must be called before any request is issued, that
            would require http authentication
        """
        assert isinstance(authobj, AuthClient)
        self._auth_client = authobj
        

    def request(self, host, handler, request_body, verbose=0):
        # issue XML-RPC request

        h = self.make_connection(host)
        if verbose:
            h.set_debuglevel(1)
        
        tries = 0
        atype = None
        realm = None

        while(tries < 3):
            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            if atype:
                # This line will bork if self.setAuthClient has not
                # been issued. That is a programming error, fix your code!
                auths = self._auth_client.getAuth(atype, realm)
                log.debug("sending authorization: %s", auths)
                h.putheader('Authorization', auths)
            self.send_content(h, request_body)

            resp = h._conn.getresponse()
            #  except BadStatusLine, e:
            tries += 1
    
            if resp.status == 401:
                if 'www-authenticate' in resp.msg:
                    (atype,realm) = resp.msg.getheader('www-authenticate').split(' ',1)
                    data1 = resp.read()
                    if data1:
                        log.warning("Why have data on a 401 auth. message?")
                    if realm.startswith('realm="') and realm.endswith('"'):
                        realm = realm[7:-1]
                    log.debug("Resp: %r %r", resp.version,resp.isclosed(), resp.will_close)
                    log.debug("Want to do auth %s for realm %s", atype, realm)
                    if atype != 'Basic':
                        raise ProtocolError(host+handler, 403, 
                                        "Unknown authentication method: %s" % atype, resp.msg)
                    continue # with the outer while loop
                else:
                    raise ProtocolError(host+handler, 403,
                                'Server-incomplete authentication', resp.msg)

            if resp.status != 200:
                raise ProtocolError( host + handler,
                    resp.status, resp.reason, resp.msg )
    
            self.verbose = verbose
    
            try:
                sock = h._conn.sock
            except AttributeError:
                sock = None
    
            return self._parse_response(h.getfile(), sock, resp)

        raise ProtocolError(host+handler, 403, "No authentication",'')

class PersistentAuthTransport(addAuthTransport,PersistentTransport):
    pass

class PersistentAuthCTransport(addAuthTransport,CompressedTransport):
    pass

class HTTPSConnection(httplib.HTTPSConnection):
        certs_file = None
        def connect(self):
            "Connect to a host on a given (SSL) port. check the certificate"
            import socket, ssl

            if HTTPSConnection.certs_file:
                ca_certs = HTTPSConnection.certs_file
                cert_reqs = ssl.CERT_REQUIRED
            else:
                ca_certs = None
                cert_reqs = ssl.CERT_NONE
            sock = socket.create_connection((self.host, self.port), self.timeout)
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                ca_certs=ca_certs,
                                cert_reqs=cert_reqs)
        

        def getpeercert(self):
                import ssl
                cert = None
                if self.sock:
                        cert =  self.sock.getpeercert()
                else:
                        cert = ssl.get_server_certificate((self.host,self.port),
                                ssl_version=ssl.PROTOCOL_SSLv23 )
                        lf = (len(ssl.PEM_FOOTER)+1)
                        if cert[0-lf] != '\n':
                                cert = cert[:0-lf]+'\n'+cert[0-lf:]
                        log.debug("len-footer: %s cert: %r", lf, cert[0-lf])
                
                return cert


class DAVClient(object):
    """An instance of a WebDAV client, connected to the OpenERP server
    """
    
    def __init__(self, user=None, passwd=None, dbg=0, use_ssl=False, useragent=False, timeout=None):
        if use_ssl:
            self.host = config.get_misc('httpsd', 'interface', False)
            self.port = config.get_misc('httpsd', 'port', 8071)
            if not self.host:
                self.host = config.get('xmlrpcs_interface')
                self.port = config.get('xmlrpcs_port')
        else:
            self.host = config.get_misc('httpd', 'interface')
            self.port = config.get_misc('httpd', 'port', 8069)
            if not self.host:
                self.host = config.get('xmlrpc_interface')
                self.port = config.get('xmlrpc_port') or self.port
        if self.host == '0.0.0.0' or not self.host:
            self.host = '127.0.0.1'
        self.port = int(self.port)
        if not config.get_misc('webdav','enable',True):
            raise Exception("WebDAV is disabled, cannot continue")
        self.davpath = '/' + config.get_misc('webdav','vdir','webdav')
        self.user = user
        self.passwd = passwd
        self.dbg = dbg
        self.timeout = timeout or 5.0 # seconds, tests need to respond pretty fast!
        self.hdrs = {}
        if useragent:
            self.set_useragent(useragent)

    def get_creds(self, obj, cr, uid):
        """Read back the user credentials from cr, uid
        
        @param obj is any orm object, in order to use its pool
        @param uid is the numeric id, which we will try to reverse resolve
        
        note: this is a hackish way to get the credentials. It is expected
        to break if "base_crypt" is used.
        """
        ruob = obj.pool.get('res.users')
        res = ruob.read(cr, 1, [uid,], ['login', 'password'])
        assert res, "uid %s not found" % uid
        self.user = res[0]['login']
        self.passwd = res[0]['password']
        if self.passwd.startswith('$1$'):
            # md5 by base crypt. We cannot decode, wild guess 
            # that passwd = login
            self.passwd = self.user
        return True

    def set_useragent(self, uastr):
        """ Set the user-agent header to something meaningful.
        Some shorthand names will be replaced by stock strings.
        """
        if uastr in ('KDE4', 'Korganizer'):
            self.hdrs['User-Agent'] = "Mozilla/5.0 (compatible; Konqueror/4.4; Linux) KHTML/4.4.3 (like Gecko)"
        elif uastr == 'iPhone3':
            self.hdrs['User-Agent'] = "DAVKit/5.0 (765); iCalendar/5.0 (79); iPhone/4.1 8B117"
        elif uastr == "MacOS":
            self.hdrs['User-Agent'] = "WebDAVFS/1.8 (01808000) Darwin/9.8.0 (i386)"
        else:
            self.hdrs['User-Agent'] = uastr

    def _http_request(self, path, method='GET', hdrs=None, body=None):
        if not hdrs:
            hdrs = {}
        import base64
        dbg = self.dbg
        hdrs.update(self.hdrs)
        log.debug("Getting %s http://%s:%d/%s", method, self.host, self.port, path)
        conn = httplib.HTTPConnection(self.host, port=self.port, timeout=self.timeout)
        conn.set_debuglevel(dbg)
        if not path:
            path = "/index.html"
        if not hdrs.has_key('Connection'):
                hdrs['Connection']= 'keep-alive'
        conn.request(method, path, body, hdrs )
        try:
                r1 = conn.getresponse()
        except httplib.BadStatusLine, bsl:
                log.warning("Bad status line: %s", bsl.line)
                raise Exception('Bad status line')
        if r1.status == 401: # and r1.headers:
                if 'www-authenticate' in r1.msg:
                        (atype,realm) = r1.msg.getheader('www-authenticate').split(' ',1)
                        data1 = r1.read()
                        if not self.user:
                                raise Exception('Must auth, have no user/pass!')
                        log.debug("Ver: %s, closed: %s, will close: %s", r1.version,r1.isclosed(), r1.will_close)
                        log.debug("Want to do auth %s for realm %s", atype, realm)
                        if atype == 'Basic' :
                                auths = base64.encodestring(self.user + ':' + self.passwd)
                                if auths[-1] == "\n":
                                        auths = auths[:-1]
                                hdrs['Authorization']= 'Basic '+ auths 
                                #sleep(1)
                                conn.request(method, path, body, hdrs )
                                r1 = conn.getresponse()
                        else:
                                raise Exception("Unknown auth type %s" %atype)
                else:
                        log.warning("Got 401, cannot auth")
                        raise Exception('No auth')

        log.debug("Reponse: %s %s",r1.status, r1.reason)
        data1 = r1.read()
        if method != 'GET':
            log.debug("Body:\n%s\nEnd of body", data1)
            try:
                ctype = r1.msg.getheader('content-type')
                if ctype and ';' in ctype:
                    ctype, encoding = ctype.split(';',1)
                if ctype == 'text/xml':
                    doc = xml.dom.minidom.parseString(data1)
                    log.debug("XML Body:\n %s", doc.toprettyxml(indent="\t"))
            except Exception:
                log.warning("could not print xml", exc_info=True)
                pass
        conn.close()
        return r1.status, r1.msg, data1

    def _assert_headers(self, expect, msg):
        """ Assert that the headers in msg contain the expect values
        """
        for k, v in expect.items():
            hval = msg.getheader(k)
            if not hval:
                raise AssertionError("Header %s not defined in http response" % k)
            if isinstance(v, (list, tuple)):
                delim = ','
                hits = map(str.strip, hval.split(delim))
                mvits= []
                for vit in v:
                    if vit not in hits:
                        mvits.append(vit)
                if mvits:
                    raise AssertionError("HTTP header \"%s\" is missing: %s" %(k, ', '.join(mvits)))
            else:
                if hval.strip() != v.strip():
                    raise AssertionError("HTTP header \"%s: %s\"" % (k, hval))

    def gd_options(self, path='*', expect=None):
        """ Test the http options functionality
            If a dictionary is defined in expect, those options are
            asserted.
        """
        if path != '*':
            path = self.davpath + path
        hdrs = { 'Content-Length': 0
                }
        s, m, d = self._http_request(path, method='OPTIONS', hdrs=hdrs)
        assert s == 200, "Status: %r" % s
        assert 'OPTIONS' in m.getheader('Allow')
        log.debug('Options: %r', m.getheader('Allow'))
        
        if expect:
            self._assert_headers(expect, m)
    
    def _parse_prop_response(self, data):
        """ Parse a propfind/propname response
        """
        def getText(node):
            rc = []
            for node in node.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    rc.append(node.data)
            return ''.join(rc)
        
        def getElements(node, namespaces=None, strict=False):
            for cnod in node.childNodes:
                if cnod.nodeType != node.ELEMENT_NODE:
                    if strict:
                        log.debug("Found %r inside <%s>", cnod, node.tagName)
                    continue
                if namespaces and (cnod.namespaceURI not in namespaces):
                    log.debug("Ignoring <%s> in <%s>", cnod.tagName, node.localName)
                    continue
                yield cnod

        nod = xml.dom.minidom.parseString(data)
        nod_r = nod.documentElement
        res = {}
        assert nod_r.localName == 'multistatus', nod_r.tagName
        for resp in nod_r.getElementsByTagNameNS('DAV:', 'response'):
            href = None
            status = 200
            res_nss = {}
            for cno in getElements(resp, namespaces=['DAV:',]):
                if cno.localName == 'href':
                    assert href is None, "Second href in same response"
                    href = getText(cno)
                elif cno.localName == 'propstat':
                    for pno in getElements(cno, namespaces=['DAV:',]):
                        rstatus = None
                        if pno.localName == 'prop':
                            for prop in getElements(pno):
                                key = prop.localName
                                tval = getText(prop).strip()
                                val = tval or (True, rstatus or status)
                                if prop.namespaceURI == 'DAV:' and prop.localName == 'resourcetype':
                                    val = 'plain'
                                    for rte in getElements(prop, namespaces=['DAV:',]):
                                        # Note: we only look at DAV:... elements, we
                                        # actually expect only one DAV:collection child
                                        val = rte.localName
                                res_nss.setdefault(prop.namespaceURI,{})[key] = val
                        elif pno.localName == 'status':
                            rstr = getText(pno)
                            htver, sta, msg = rstr.split(' ', 3)
                            assert htver == 'HTTP/1.1'
                            rstatus = int(sta)
                        else:
                            log.debug("What is <%s> inside a <propstat>?", pno.tagName)
                    
                else:
                    log.debug("Unknown node: %s", cno.tagName)
                
            res.setdefault(href,[]).append((status, res_nss))

        return res

    def gd_propfind(self, path, props=None, depth=0):
        if not props:
            propstr = '<allprop/>'
        else:
            propstr = '<prop>'
            nscount = 0
            for p in props:
                ns = None
                if isinstance(p, tuple):
                    p, ns = p
                if ns is None or ns == 'DAV:':
                    propstr += '<%s/>' % p
                else:
                    propstr += '<ns%d:%s xmlns:ns%d="%s" />' %(nscount, p, nscount, ns)
                    nscount += 1
            propstr += '</prop>'
                
        body="""<?xml version="1.0" encoding="utf-8"?>
            <propfind xmlns="DAV:">%s</propfind>""" % propstr
        hdrs = { 'Content-Type': 'text/xml; charset=utf-8',
                'Accept': 'text/xml',
                'Depth': depth,
                }

        s, m, d = self._http_request(self.davpath + path, method='PROPFIND', 
                                    hdrs=hdrs, body=body)
        assert s == 207, "Bad status: %s" % s
        ctype = m.getheader('Content-Type').split(';',1)[0]
        assert ctype == 'text/xml', m.getheader('Content-Type')
        res = self._parse_prop_response(d)
        if depth == 0:
            assert len(res) == 1
            res = res.values()[0]
        else:
            assert len(res) >= 1
        return res
        

    def gd_propname(self, path, depth=0):
        body="""<?xml version="1.0" encoding="utf-8"?>
            <propfind xmlns="DAV:"><propname/></propfind>"""
        hdrs = { 'Content-Type': 'text/xml; charset=utf-8',
                'Accept': 'text/xml',
                'Depth': depth
                }
        s, m, d = self._http_request(self.davpath + path, method='PROPFIND', 
                                    hdrs=hdrs, body=body)
        assert s == 207, "Bad status: %s" % s
        ctype = m.getheader('Content-Type').split(';',1)[0]
        assert ctype == 'text/xml', m.getheader('Content-Type')
        res = self._parse_prop_response(d)
        if depth == 0:
            assert len(res) == 1
            res = res.values()[0]
        else:
            assert len(res) >= 1
        return res

    def gd_getetag(self, path, depth=0):
        return self.gd_propfind(path, props=['getetag',], depth=depth)

    def gd_lsl(self, path):
        """ Return a list of 'ls -l' kind of data for a folder
        
            This is based on propfind.
        """

        lspairs = [ ('name', 'displayname', 'n/a'), ('size', 'getcontentlength', '0'),
                ('type', 'resourcetype', '----------'), ('uid', 'owner', 'nobody'),
                ('gid', 'group', 'nogroup'), ('mtime', 'getlastmodified', 'n/a'),
                ('mime', 'getcontenttype', 'application/data'), ]

        propnames = [ l[1] for l in lspairs]
        propres = self.gd_propfind(path, props=propnames, depth=1)
        
        res = []
        for href, pr in propres.items():
            lsline = {}
            for st, nsdic in pr:
                davprops = nsdic['DAV:']
                if st == 200:
                    for lsp in lspairs:
                        if lsp[1] in davprops:
                            if lsp[1] == 'resourcetype':
                                if davprops[lsp[1]] == 'collection':
                                    lsline[lsp[0]] = 'dr-xr-x---'
                                else:
                                    lsline[lsp[0]] = '-r-xr-x---'
                            else:
                                lsline[lsp[0]] = davprops[lsp[1]]
                elif st in (404, 403):
                    for lsp in lspairs:
                        if lsp[1] in davprops:
                            lsline[lsp[0]] = lsp[2]
                else:
                    log.debug("Strange status: %s", st)
            
            res.append(lsline)
            
        return res

    def gd_get(self, path, crange=None, mime=None, compare=None):
        """ HTTP GET for path, supporting Partial ranges
        """
        hdrs = { 'Accept': mime or '*/*', }
        if crange:
            if isinstance(crange, tuple):
                crange = [crange,]
            if not isinstance(crange, list):
                raise TypeError("Range must be a tuple or list of tuples")
            rs = []
            for r in crange:
                rs.append('%d-%d' % r)
            hdrs['Range'] = 'bytes='+ (','.join(rs))
        s, m, d = self._http_request(self.davpath + path, method='GET', hdrs=hdrs)
        assert s in (200, 206), "Bad status: %s" % s
        ctype = m.getheader('Content-Type')
        if ctype and ';' in ctype:
            ctype = ctype.split(';',1)[0]
        if mime:
            assert ctype == mime, m.getheader('Content-Type')
        rrange = None
        rrh = m.getheader('Content-Range')
        if rrh:
            assert rrh.startswith('bytes '), rrh
            rrh=rrh[6:].split('/',1)[0]
            rrange = map(int, rrh.split('-',1))
        if compare:
            # we need to compare the returned data with that of compare
            fd = open(compare, 'rb')
            d2 = fd.read()
            fd.close()
            if crange:
                if len(crange) > 1:
                    raise NotImplementedError
                r = crange[0]
                d2 = d2[r[0]:r[1]+1]
            assert d2 == d, "Data does not match"
        return ctype, rrange, d

    def gd_put(self, path, body=None, srcpath=None, mime=None, noclobber=False, ):
        """ HTTP PUT 
            @param noclobber will prevent overwritting a resource (If-None-Match)
            @param mime will set the content-type
        """
        hdrs = { }
        if not (body or srcpath):
            raise ValueError("PUT must have something to send")
        if (not body) and srcpath:
            fd = open(srcpath, 'rb')
            body = fd.read()
            fd.close()
        if mime:
            hdrs['Content-Type'] = mime
        if noclobber:
            hdrs['If-None-Match'] = '*'
        s, m, d = self._http_request(self.davpath + path, method='PUT', 
                            hdrs=hdrs, body=body)
        assert s == (201), "Bad status: %s" % s
        etag = m.getheader('ETag')
        return etag or True

#eof