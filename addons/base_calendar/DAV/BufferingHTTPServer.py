#!/usr/bin/env python

"""
    Buffering HTTP Server
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

"""


from utils import VERSION, AUTHOR
__version__ = VERSION
__author__  = AUTHOR

from BaseHTTPServer import BaseHTTPRequestHandler
import os
class BufferedHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    Buffering HTTP Request Handler

    This class is an extension to the BaseHTTPRequestHandler
    class which buffers the whole output and sends it at once
    after the processing if the request is finished.

    This makes it possible to work together with some clients
    which otherwise would break (e.g. cadaver)

    """


    def _init_buffer(self):
        """initialize the buffer.

        If you override the handle() method remember to call
        this (see below)
        """
        self.__buffer=""
        self.__outfp=os.tmpfile()

    def _append(self,s):
        """ append a string to the buffer """
        self.__buffer=self.__buffer+s

    def _flush(self):
        """ flush the buffer to wfile """
        self.wfile.write(self.__buffer)
        self.__outfp.write(self.__buffer)
        self.__outfp.flush()
        self.wfile.flush()
        self.__buffer=""

    def handle(self):
        """ Handle a HTTP request """
        self._init_buffer()
        BaseHTTPRequestHandler.handle(self)
        self._flush()

    def send_header(self, keyword, value):
        """Send a MIME header."""
        if self.request_version != 'HTTP/0.9':
            self._append("%s: %s\r\n" % (keyword, value))

    def end_headers(self):
        """Send the blank line ending the MIME headers."""
        if self.request_version != 'HTTP/0.9':
            self._append("\r\n")

    def send_response(self, code, message=None):
        self.log_request(code)

        if message is None:
            if self.responses.has_key(code):
                message = self.responses[code][0]
            else:
                message = ''

        if self.request_version != 'HTTP/0.9':
            self._append("%s %s %s\r\n" %
                    (self.protocol_version, str(code), message))

        self.send_header('Server', self.version_string())
        self.send_header('Connection', 'close')
        self.send_header('Date', self.date_time_string())

    protocol_version="HTTP/1.1"

