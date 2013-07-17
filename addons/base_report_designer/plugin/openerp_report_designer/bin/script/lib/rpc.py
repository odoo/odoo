# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import time
import socket
import xmlrpclib
#import tiny_socket
import re

class RPCGateway(object):
    def __init__(self, host, port, protocol):

        self.protocol = protocol
        self.host = host
        self.port = port

    def get_url(self):

        """Get the url
        """
        return "%s://%s:%s/"%(self.protocol, self.host, self.port)

    def listdb(self):
        """Get the list of databases.
        """
        pass

    def login(self, db, user, password):
        pass

    def execute(self, obj, method, *args):
        pass



class RPCSession(object):
    def __init__(self, url):

        m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$', url or '')

        host = m.group(2)
        port = m.group(3)
        protocol = m.group(1)
        if not m:
            return -1
        if protocol == 'http://' or protocol == 'http://':
            self.gateway = XMLRPCGateway(host, port, 'http')
        elif protocol == 'socket://':

            self.gateway = NETRPCGateway(host, port)

    def listdb(self):
        return self.gateway.listdb()

    def login(self, db, user, password):

        if password is None:
            return -1

        uid = self.gateway.login(db, user or '', password or '')

        if uid <= 0:
            return -1

        self.uid = uid
        self.db = db
        self.password = password
        self.open = True
        return uid


    def execute(self, obj, method, *args):
        try:
            result = self.gateway.execute(obj, method, *args)
            return self.__convert(result)
        except Exception,e:
          import traceback,sys
          info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))

    def __convert(self, result):

        if isinstance(result, basestring):
            # try to convert into unicode string
            try:
                return ustr(result)
            except Exception, e:
                return result

        elif isinstance(result, list):
            return [self.__convert(val) for val in result]

        elif isinstance(result, tuple):
            return tuple([self.__convert(val) for val in result])

        elif isinstance(result, dict):
            newres = {}
            for key, val in result.items():
                newres[key] = self.__convert(val)

            return newres

        else:
            return result

class XMLRPCGateway(RPCGateway):
    """XML-RPC implementation.
    """
    def __init__(self, host, port, protocol='http'):

        super(XMLRPCGateway, self).__init__(host, port, protocol)
        global rpc_url
        rpc_url =  self.get_url() + 'xmlrpc/'

    def listdb(self):
        global rpc_url
        sock = xmlrpclib.ServerProxy(rpc_url + 'db')
        try:
            return sock.list()
        except Exception, e:
            return -1

    def login(self, db, user, password):

        global rpc_url

        sock = xmlrpclib.ServerProxy(rpc_url + 'common')

        try:
            res = sock.login(db, user, password)
        except Exception, e:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            return -1

        return res

    def execute(self, sDatabase, UID, sPassword, obj, method, *args):
        global rpc_url

        sock = xmlrpclib.ServerProxy(rpc_url + 'object')

        return sock.execute(sDatabase,UID,sPassword, obj ,method,*args)



class NETRPCGateway(RPCGateway):
    def __init__(self, host, port):

        super(NETRPCGateway, self).__init__(host, port, 'socket')

    def listdb(self):
        sock = mysocket()
        try:
            sock.connect(self.host, self.port)
            sock.mysend(('db', 'list'))
            res = sock.myreceive()
            sock.disconnect()
            return res
        except Exception, e:
            return -1

    def login(self, db, user, password):
        sock =  mysocket()
        try:
            sock.connect(self.host, self.port)
            sock.mysend(('common', 'login', db, user, password))
            res = sock.myreceive()
            sock.disconnect()
        except Exception, e:
            return -1
        return res
    def execute(self,obj, method, *args):
        sock = mysocket()
        try:
            sock.connect(self.host, self.port)
            data=(('object', 'execute',obj,method,)+args)
            sock.mysend(data)
            res=sock.myreceive()
            sock.disconnect()
            return res

        except Exception,e:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
