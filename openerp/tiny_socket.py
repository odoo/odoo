# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import socket
import cPickle
import cStringIO
import marshal

import netsvc

#.apidoc title: Net-RPC classes

class Myexception(Exception):
    """
    custom exception object store
    * faultcode
    * faulestring
    * args
    """
    
    def __init__(self, faultCode, faultString):
        self.faultCode = faultCode
        self.faultString = faultString
        self.args = (faultCode, faultString)

class mysocket:

    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        # self.sock.settimeout(120)
        # prepare this socket for long operations: it may block for infinite
        # time, but should exit as soon as the net is down
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
    def connect(self, host, port=False):
        if not port:
            protocol, buf = host.split('//')
            host, port = buf.split(':')
        self.sock.connect((host, int(port)))
        
    def disconnect(self):
        netsvc.close_socket(self.sock)
        
    def mysend(self, msg, exception=False, traceback=None):
        msg = cPickle.dumps([msg,traceback])
        self.sock.sendall('%8d%s%s' % (len(msg), exception and "1" or "0", msg))
            
    def myreceive(self):
        buf=''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if not chunk:
                raise socket.timeout
            buf += chunk
        size = int(buf)
        buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            chunk = self.sock.recv(size-len(msg))
            if not chunk:
                raise socket.timeout
            msg = msg + chunk
        msgio = cStringIO.StringIO(msg)
        unpickler = cPickle.Unpickler(msgio)
        unpickler.find_global = None
        res = unpickler.load()

        if isinstance(res[0],Exception):
            if exception:
                raise Myexception(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]
