# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) Stephane Wirtel
# Copyright (C) 2011 Nicolas Vanhoren
# Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met: 
# 
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer. 
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution. 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
##############################################################################

"""
OpenERP Client Library

Home page: http://pypi.python.org/pypi/openerp-client-lib
Code repository: https://code.launchpad.net/~niv-openerp/openerp-client-lib/trunk
"""

import xmlrpclib
import logging 
import socket
import sys

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

_logger = logging.getLogger(__name__)

def _getChildLogger(logger, subname):
    return logging.getLogger(logger.name + "." + subname)

#----------------------------------------------------------
# Exceptions
# TODO openerplib should raise those instead of xmlrpc faults:
#----------------------------------------------------------

class LibException(Exception):
    """ Base of all client lib exceptions """
    def __init__(self,code=None,message=None):
        self.code = code
        self.message = message

class ApplicationError(LibException):
    """ maps to code: 1, server side: Exception or openerp.exceptions.DeferredException"""

class Warning(LibException):
    """ maps to code: 2, server side: openerp.exceptions.Warning"""

class AccessError(LibException):
    """ maps to code: 3, server side:  openerp.exceptions.AccessError"""

class AccessDenied(LibException):
    """ maps to code: 4, server side: openerp.exceptions.AccessDenied"""

#----------------------------------------------------------
# Connectors
#----------------------------------------------------------

class Connector(object):
    """
    The base abstract class representing a connection to an OpenERP Server.
    """

    __logger = _getChildLogger(_logger, 'connector')

    def __init__(self, hostname, port):
        """
        Initilize by specifying an hostname and a port.
        :param hostname: Host name of the server.
        :param port: Port for the connection to the server.
        """
        self.hostname = hostname
        self.port = port

    def get_service(self, service_name):
        """
        Returns a Service instance to allow easy manipulation of one of the services offered by the remote server.

        :param service_name: The name of the service.
        """
        return Service(self, service_name)

class XmlRPCConnector(Connector):
    """
    A type of connector that uses the XMLRPC protocol.
    """
    PROTOCOL = 'xmlrpc'
    
    __logger = _getChildLogger(_logger, 'connector.xmlrpc')

    def __init__(self, hostname, port=8069):
        """
        Initialize by specifying the hostname and the port.
        :param hostname: The hostname of the computer holding the instance of OpenERP.
        :param port: The port used by the OpenERP instance for XMLRPC (default to 8069).
        """
        Connector.__init__(self, hostname, port)
        self.url = 'http://%s:%d/xmlrpc' % (self.hostname, self.port)

    def send(self, service_name, method, *args):
        url = '%s/%s' % (self.url, service_name)
        service = xmlrpclib.ServerProxy(url)
        # TODO should try except and wrap exception into LibException
        return getattr(service, method)(*args)

class XmlRPCSConnector(XmlRPCConnector):
    """
    A type of connector that uses the secured XMLRPC protocol.
    """
    PROTOCOL = 'xmlrpcs'

    __logger = _getChildLogger(_logger, 'connector.xmlrpcs')

    def __init__(self, hostname, port=8071):
        super(XmlRPCSConnector, self).__init__(hostname, port)
        self.url = 'https://%s:%d/xmlrpc' % (self.hostname, self.port)

class NetRPC_Exception(Exception):
    """
    Exception for NetRPC errors.
    """
    def __init__(self, faultCode, faultString):
        self.faultCode = faultCode
        self.faultString = faultString
        self.args = (faultCode, faultString)

class NetRPC(object):
    """
    Low level class for NetRPC protocol.
    """
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.settimeout(120)
    def connect(self, host, port=False):
        if not port:
            buf = host.split('//')[1]
            host, port = buf.split(':')
        self.sock.connect((host, int(port)))

    def disconnect(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

    def mysend(self, msg, exception=False, traceback=None):
        msg = pickle.dumps([msg,traceback])
        size = len(msg)
        self.sock.send('%8d' % size)
        self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent

    def myreceive(self):
        buf=''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
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
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            msg = msg + chunk
        msgio = StringIO.StringIO(msg)
        unpickler = pickle.Unpickler(msgio)
        unpickler.find_global = None
        res = unpickler.load()

        if isinstance(res[0],Exception):
            if exception:
                raise NetRPC_Exception(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]

class NetRPCConnector(Connector):
    """
    A type of connector that uses the NetRPC protocol.
    """

    PROTOCOL = 'netrpc'
    
    __logger = _getChildLogger(_logger, 'connector.netrpc')

    def __init__(self, hostname, port=8070):
        """
        Initialize by specifying the hostname and the port.
        :param hostname: The hostname of the computer holding the instance of OpenERP.
        :param port: The port used by the OpenERP instance for NetRPC (default to 8070).
        """
        Connector.__init__(self, hostname, port)

    def send(self, service_name, method, *args):
        socket = NetRPC()
        socket.connect(self.hostname, self.port)
        socket.mysend((service_name, method, )+args)
        result = socket.myreceive()
        socket.disconnect()
        return result

class LocalConnector(Connector):
    """
    A type of connector that uses the XMLRPC protocol.
    """
    PROTOCOL = 'local'
    
    __logger = _getChildLogger(_logger, 'connector.local')

    def __init__(self):
        pass

    def send(self, service_name, method, *args):
        import openerp
        import traceback
        try:
            result = openerp.netsvc.dispatch_rpc(service_name, method, args)
        except Exception,e:
        # TODO change the except to raise LibException instead of their emulated xmlrpc fault
            if isinstance(e, openerp.osv.osv.except_osv):
                fault = xmlrpclib.Fault('warning -- ' + e.name + '\n\n' + e.value, '')
            elif isinstance(e, openerp.exceptions.Warning):
                fault = xmlrpclib.Fault('warning -- Warning\n\n' + str(e), '')
            elif isinstance(e, openerp.exceptions.AccessError):
                fault = xmlrpclib.Fault('warning -- AccessError\n\n' + str(e), '')
            elif isinstance(e, openerp.exceptions.AccessDenied):
                fault = xmlrpclib.Fault('AccessDenied', str(e))
            elif isinstance(e, openerp.exceptions.DeferredException):
                info = e.traceback
                formatted_info = "".join(traceback.format_exception(*info))
                fault = xmlrpclib.Fault(openerp.tools.ustr(e.message), formatted_info)
            else:
                info = sys.exc_info()
                formatted_info = "".join(traceback.format_exception(*info))
                fault = xmlrpclib.Fault(openerp.tools.exception_to_unicode(e), formatted_info)
            raise fault
        return result

#----------------------------------------------------------
# Public api
#----------------------------------------------------------

class Service(object):
    """
    A class to execute RPC calls on a specific service of the remote server.
    """
    def __init__(self, connector, service_name):
        """
        :param connector: A valid Connector instance.
        :param service_name: The name of the service on the remote server.
        """
        self.connector = connector
        self.service_name = service_name
        self.__logger = _getChildLogger(_getChildLogger(_logger, 'service'),service_name)
        
    def __getattr__(self, method):
        """
        :param method: The name of the method to execute on the service.
        """
        self.__logger.debug('method: %r', method)
        def proxy(*args):
            """
            :param args: A list of values for the method
            """
            self.__logger.debug('args: %r', args)
            result = self.connector.send(self.service_name, method, *args)
            self.__logger.debug('result: %r', result)
            return result
        return proxy

class Connection(object):
    """
    A class to represent a connection with authentication to an OpenERP Server.
    It also provides utility methods to interact with the server more easily.
    """
    __logger = _getChildLogger(_logger, 'connection')

    def __init__(self, connector,
                 database=None,
                 login=None,
                 password=None,
                 user_id=None):
        """
        Initialize with login information. The login information is facultative to allow specifying
        it after the initialization of this object.

        :param connector: A valid Connector instance to send messages to the remote server.
        :param database: The name of the database to work on.
        :param login: The login of the user.
        :param password: The password of the user.
        :param user_id: The user id is a number identifying the user. This is only useful if you
        already know it, in most cases you don't need to specify it.
        """
        self.connector = connector

        self.set_login_info(database, login, password, user_id)

    def set_login_info(self, database, login, password, user_id=None):
        """
        Set login information after the initialisation of this object.

        :param connector: A valid Connector instance to send messages to the remote server.
        :param database: The name of the database to work on.
        :param login: The login of the user.
        :param password: The password of the user.
        :param user_id: The user id is a number identifying the user. This is only useful if you
        already know it, in most cases you don't need to specify it.
        """
        self.database, self.login, self.password = database, login, password

        self.user_id = user_id
        
    def check_login(self, force=True):
        """
        Checks that the login information is valid. Throws an AuthenticationError if the
        authentication fails.

        :param force: Force to re-check even if this Connection was already validated previously.
        Default to True.
        """
        if self.user_id and not force:
            return
        
        if not self.database or not self.login or self.password is None:
            raise AuthenticationError("Credentials not provided")
        
        self.user_id = self.get_service("common").login(self.database, self.login, self.password)
        if not self.user_id:
            raise AuthenticationError("Authentication failure")
        self.__logger.debug("Authenticated with user id %s", self.user_id)
    
    def get_model(self, model_name):
        """
        Returns a Model instance to allow easy remote manipulation of an OpenERP model.

        :param model_name: The name of the model.
        """
        return Model(self, model_name)

    def get_service(self, service_name):
        """
        Returns a Service instance to allow easy manipulation of one of the services offered by the remote server.
        Please note this Connection instance does not need to have valid authentication information since authentication
        is only necessary for the "object" service that handles models.

        :param service_name: The name of the service.
        """
        return self.connector.get_service(service_name)

class AuthenticationError(Exception):
    """
    An error thrown when an authentication to an OpenERP server failed.
    """
    pass

class Model(object):
    """
    Useful class to dialog with one of the models provided by an OpenERP server.
    An instance of this class depends on a Connection instance with valid authentication information.
    """

    def __init__(self, connection, model_name):
        """
        :param connection: A valid Connection instance with correct authentication information.
        :param model_name: The name of the model.
        """
        self.connection = connection
        self.model_name = model_name
        self.__logger = _getChildLogger(_getChildLogger(_logger, 'object'), model_name)

    def __getattr__(self, method):
        """
        Provides proxy methods that will forward calls to the model on the remote OpenERP server.

        :param method: The method for the linked model (search, read, write, unlink, create, ...)
        """
        def proxy(*args):
            """
            :param args: A list of values for the method
            """
            self.connection.check_login(False)
            self.__logger.debug(args)
            result = self.connection.get_service('object').execute(
                                                    self.connection.database,
                                                    self.connection.user_id,
                                                    self.connection.password,
                                                    self.model_name,
                                                    method,
                                                    *args)
            if method == "read":
                if isinstance(result, list) and len(result) > 0 and "id" in result[0]:
                    index = {}
                    for r in result:
                        index[r['id']] = r
                    result = [index[x] for x in args[0] if x in index]
            self.__logger.debug('result: %r', result)
            return result
        return proxy

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        """
        A shortcut method to combine a search() and a read().

        :param domain: The domain for the search.
        :param fields: The fields to extract (can be None or [] to extract all fields).
        :param offset: The offset for the rows to read.
        :param limit: The maximum number of rows to read.
        :param order: The order to class the rows.
        :param context: The context.
        :return: A list of dictionaries containing all the specified fields.
        """
        record_ids = self.search(domain or [], offset, limit or False, order or False, context or {})
        if not record_ids: return []
        if field == ['id']: return [{'id': record_id} for record_id in record_ids]
        records = self.read(record_ids, fields or [], context or {})
        return records

def get_connector(hostname=None, protocol="xmlrpc", port="auto"):
    """
    A shortcut method to easily create a connector to a remote server using XMLRPC or NetRPC.

    :param hostname: The hostname to the remote server.
    :param protocol: The name of the protocol, must be "xmlrpc" or "netrpc".
    :param port: The number of the port. Defaults to auto.
    """
    if port == 'auto':
        port = 8069 if protocol=="xmlrpc" else (8070 if protocol == "netrpc" else 8071)
    if protocol == "xmlrpc":
        return XmlRPCConnector(hostname, port)
    elif protocol == "xmlrpcs":
        return XmlRPCSConnector(hostname, port)
    elif protocol == "netrpc":
        return NetRPCConnector(hostname, port)
    elif protocol == "local":
        return LocalConnector()
    else:
        raise ValueError("You must choose xmlrpc(s), netrpc or local")

def get_connection(hostname=None, protocol="xmlrpc", port='auto', database=None,
                 login=None, password=None, user_id=None):
    """
    A shortcut method to easily create a connection to a remote OpenERP server.

    :param hostname: The hostname to the remote server.
    :param protocol: The name of the protocol, must be "xmlrpc" or "netrpc".
    :param port: The number of the port. Defaults to auto.
    :param connector: A valid Connector instance to send messages to the remote server.
    :param database: The name of the database to work on.
    :param login: The login of the user.
    :param password: The password of the user.
    :param user_id: The user id is a number identifying the user. This is only useful if you
    already know it, in most cases you don't need to specify it.
    """
    return Connection(get_connector(hostname, protocol, port), database, login, password, user_id)
        
