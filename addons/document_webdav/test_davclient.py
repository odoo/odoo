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

import imp
import sys
import os
import glob
import subprocess
import re
import gzip
import logging
import xml.dom.minidom

import httplib

# from xmlrpclib import Transport 

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

def http_request(host, path, user=None, method='GET', hdrs=None, body=None, dbg=2):
        if not hdrs:
            hdrs = {}
        passwd=None
        if user:
            import getpass
            passwd = getpass.getpass("Password for %s@%s: " %(user,host))
        import base64
        log.debug("Getting %s http://%s/%s", method, host , path)
        conn = httplib.HTTPConnection(host)
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
                return
        if r1.status == 401: # and r1.headers:
                if 'www-authenticate' in r1.msg:
                        (atype,realm) = r1.msg.getheader('www-authenticate').split(' ',1)
                        data1 = r1.read()
                        if not user:
                                raise Exception('Must auth, have no user/pass!')
                        log.debug("Ver: %s, closed: %s, will close: %s", r1.version,r1.isclosed(), r1.will_close)
                        log.debug("Want to do auth %s for realm %s", atype, realm)
                        if atype == 'Basic' :
                                auths = base64.encodestring(user + ':' + passwd)
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
        did_print = False
        log.debug("Body:\n%s\nEnd of body\n", data1)
        try:
            ctype = r1.msg.getheader('content-type')
            if ctype and ';' in ctype:
                ctype, encoding = ctype.split(';',1)
            if ctype == 'text/xml':
                doc = xml.dom.minidom.parseString(data1)
                log.debug("XML Body:\n %s", doc.toprettyxml(indent="\t"))
                did_print = True
        except Exception, e:
            log.warning("could not print xml", exc_info=True)
            pass
        conn.close()
