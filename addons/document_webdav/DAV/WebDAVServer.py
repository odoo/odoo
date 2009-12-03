"""
    Python WebDAV Server.
    Copyright (C) 1999 Christian Scholz (ruebe@aachen.heimat.de)

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Library General Public
    License as published by the Free Software Foundation; either
    version 2 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Library General Public License for more details.

    You should have received a copy of the GNU Library General Public
    License along with this library; if not, write to the Free
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

This module builds on AuthServer by implementing the standard DAV
methods.

Subclass this class and specify an IFACE_CLASS. See example.

"""

DEBUG=None

from utils import VERSION, AUTHOR
__version__ = VERSION
__author__  = AUTHOR


import os
import sys
import time
import socket
import string
import posixpath
import base64
import urlparse
import urllib

from propfind import PROPFIND
from delete import DELETE
from davcopy import COPY
from davmove import MOVE

from string import atoi,split
from status import STATUS_CODES
from errors import *

import BaseHTTPServer

class DAVRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Simple DAV request handler with

    - GET
    - HEAD
    - PUT
    - OPTIONS
    - PROPFIND
    - PROPPATCH
    - MKCOL

    It uses the resource/collection classes for serving and
    storing content.

    """

    server_version = "DAV/" + __version__
    protocol_version = 'HTTP/1.1'

    ### utility functions
    def _log(self, message):
        pass

    def _append(self,s):
        """ write the string to wfile """
        self.wfile.write(s)

    def send_body(self,DATA,code,msg,desc,ctype='application/octet-stream',headers=None):
        """ send a body in one part """

	if not headers:
		headers = {}
        self.send_response(code,message=msg)
        self.send_header("Connection", "keep-alive")
        self.send_header("Accept-Ranges", "bytes")

        for a,v in headers.items():
            self.send_header(a,v)

        if DATA:
            self.send_header("Content-Length", str(len(DATA)))
            self.send_header("Content-Type", ctype)
        else:
            self.send_header("Content-Length", "0")

        self.end_headers()
        if DATA:
            self._append(DATA)

    def send_body_chunks(self,DATA,code,msg,desc,ctype='text/xml; encoding="utf-8"'):
        """ send a body in chunks """

        self.responses[207]=(msg,desc)
        self.send_response(code,message=msg)
        self.send_header("Content-type", ctype)
        self.send_header("Connection", "keep-alive")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        self._append(hex(len(DATA))[2:]+"\r\n")
        self._append(DATA)
        self._append("\r\n")
        self._append("0\r\n")
        self._append("\r\n")

    ### HTTP METHODS

    def do_OPTIONS(self):
        """return the list of capabilities """
        self.send_response(200)
        self.send_header("Allow", "GET, HEAD, COPY, MOVE, POST, PUT, PROPFIND, PROPPATCH, OPTIONS, MKCOL, DELETE, TRACE")
        self.send_header("Content-Type", "text/plain")
	self.send_header("Connection", "keep-alive")
        self.send_header("DAV", "1")
        self.end_headers()

    def do_PROPFIND(self):

        dc=self.IFACE_CLASS
        # read the body
        body=None
        if self.headers.has_key("Content-Length"):
            l=self.headers['Content-Length']
            body=self.rfile.read(atoi(l))
        alt_body = """<?xml version="1.0" encoding="utf-8"?>
                    <propfind xmlns="DAV:"><prop>
                    <getcontentlength xmlns="DAV:"/>
                    <getlastmodified xmlns="DAV:"/>
                    <getcreationdate xmlns="DAV:"/>
                    <checked-in xmlns="DAV:"/>
                    <executable xmlns="http://apache.org/dav/props/"/>
                    <displayname xmlns="DAV:"/>
                    <resourcetype xmlns="DAV:"/>
                    <checked-out xmlns="DAV:"/>
                    </prop></propfind>"""
        #self.wfile.write(body)

        # which Depth?
        if self.headers.has_key('Depth'):
            d=self.headers['Depth']
        else:
            d="infinity"

        uri=self.geturi()
        pf=PROPFIND(uri,dc,d)

        if body:
            pf.read_propfind(body)

        try:
            DATA=pf.createResponse()
            DATA=DATA+"\n"
	    # print "Data:", DATA
	except DAV_NotFound,(ec,dd):
	    return self.send_notFound(dd, uri)
        except DAV_Error, (ec,dd):
            return self.send_error(ec,dd)

        self.send_body_chunks(DATA,207,"Multi-Status","Multiple responses")

    def geturi(self):
        buri = self.IFACE_CLASS.baseuri
	if buri[-1] == '/':
		return urllib.unquote(buri[:-1]+self.path)
	else:
		return urllib.unquote(buri+self.path)

    def do_GET(self):
        """Serve a GET request."""
        dc=self.IFACE_CLASS
        uri=self.geturi()

        # get the last modified date
        try:
            lm=dc.get_prop(uri,"DAV:","getlastmodified")
        except:
            lm="Sun, 01 Dec 2014 00:00:00 GMT"  # dummy!
        headers={"Last-Modified":lm , "Connection": "keep-alive"}

        # get the content type
        try:
            ct=dc.get_prop(uri,"DAV:","getcontenttype")
        except:
            ct="application/octet-stream"

        # get the data
        try:
            data=dc.get_data(uri)
        except DAV_Error, (ec,dd):
            self.send_status(ec)
            return

        # send the data
        self.send_body(data,200,"OK","OK",ct,headers)

    def do_HEAD(self):
        """ Send a HEAD response """
        dc=self.IFACE_CLASS
        uri=self.geturi()
	
        # get the last modified date
        try:
            lm=dc.get_prop(uri,"DAV:","getlastmodified")
        except:
            lm="Sun, 01 Dec 2014 00:00:00 GMT"  # dummy!

        headers={"Last-Modified":lm, "Connection": "keep-alive"}

        # get the content type
        try:
            ct=dc.get_prop(uri,"DAV:","getcontenttype")
        except:
            ct="application/octet-stream"

        try:
            data=dc.get_data(uri)
            headers["Content-Length"]=str(len(data))
        except DAV_NotFound:
            self.send_body(None,404,"Not Found","")
            return

        self.send_body(None,200,"OK","OK",ct,headers)

    def do_POST(self):
        self.send_error(404,"File not found")

    def do_MKCOL(self):
        """ create a new collection """

        dc=self.IFACE_CLASS
        uri=self.geturi()
        try:
            res = dc.mkcol(uri)
	    if res:
		self.send_body(None,201,"Created",'')
	    else:
		self.send_body(None,415,"Cannot create",'')
	    #self.send_header("Connection", "keep-alive")
	    # Todo: some content, too
        except DAV_Error, (ec,dd):
            self.send_body(None,int(ec),dd,dd)

    def do_DELETE(self):
        """ delete an resource """
        dc=self.IFACE_CLASS
        uri=self.geturi()
        dl=DELETE(uri,dc)
        if dc.is_collection(uri):
            res=dl.delcol()
        else:
            res=dl.delone()

        if res:
            self.send_status(207,body=res)
        else:
            self.send_status(204)

    def do_PUT(self):
        dc=self.IFACE_CLASS

        # read the body
        body=None
        if self.headers.has_key("Content-Length"):
            l=self.headers['Content-Length']
            body=self.rfile.read(atoi(l))
        uri=self.geturi()

        ct=None
        if self.headers.has_key("Content-Type"):
            ct=self.headers['Content-Type']
        try:
            dc.put(uri,body,ct)
        except DAV_Error, (ec,dd):
            self.send_status(ec)
            return
        self.send_status(201)

    def do_COPY(self):
        """ copy one resource to another """
        try:
            self.copymove(COPY)
        except DAV_Error, (ec,dd):
            self.send_status(ec)

    def do_MOVE(self):
        """ move one resource to another """
        try:
            self.copymove(MOVE)
        except DAV_Error, (ec,dd):
            self.send_status(ec)

    def copymove(self,CLASS):
        """ common method for copying or moving objects """
        dc=self.IFACE_CLASS

        # get the source URI
        source_uri=self.geturi()

        # get the destination URI
        dest_uri=self.headers['Destination']
        dest_uri=urllib.unquote(dest_uri)

        # Overwrite?
        overwrite=1
        result_code=204
        if self.headers.has_key("Overwrite"):
            if self.headers['Overwrite']=="F":
                overwrite=None
                result_code=201

        # instanciate ACTION class
        cp=CLASS(dc,source_uri,dest_uri,overwrite)

        # Depth?
        d="infinity"
        if self.headers.has_key("Depth"):
            d=self.headers['Depth']

            if d!="0" and d!="infinity":
                self.send_status(400)
                return

            if d=="0":
                res=cp.single_action()
                self.send_status(res)
                return

        # now it only can be "infinity" but we nevertheless check for a collection
        if dc.is_collection(source_uri):
            try:
                res=cp.tree_action()
            except DAV_Error, (ec,dd):
                self.send_status(ec)
                return
        else:
            try:
                res=cp.single_action()
            except DAV_Error, (ec,dd):
                self.send_status(ec)
                return

        if res:
            self.send_body_chunks(res,207,STATUS_CODES[207],STATUS_CODES[207],
                            ctype='text/xml; charset="utf-8"')
        else:
            self.send_status(result_code)

    def get_userinfo(self,user,pw):
        """ Dummy method which lets all users in """

        return 1

    def send_status(self,code=200,mediatype='text/xml;  charset="utf-8"', \
                                msg=None,body=None):

        if not msg: msg=STATUS_CODES[code]
        self.send_body(body,code,STATUS_CODES[code],msg,mediatype)

    def send_notFound(self,descr,uri):
        body = """<?xml version="1.0" encoding="utf-8" ?>
	<D:response xmlns:D="DAV:">
		<D:href>%s</D:href>
		<D:error/>
		<D:responsedescription>%s</D:responsedescription>
	</D:response>
	"""
	return self.send_status(404,descr, body=body % (uri,descr))
