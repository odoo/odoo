# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 OpenERP s.a. (<http://openerp.com>).
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

"""

WSGI stack, common code.

"""

import httplib
import urllib
import xmlrpclib
import StringIO

import errno
import logging
import os
import signal
import sys
import threading
import traceback

import werkzeug.serving
import werkzeug.contrib.fixers

import openerp
import openerp.modules
import openerp.tools.config as config
import websrv_lib

_logger = logging.getLogger(__name__)

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``openerp.exceptions`` (not
# create directly ``xmlrpclib.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

# The new (6.1) versioned RPC paths.
XML_RPC_PATH = '/openerp/xmlrpc'
XML_RPC_PATH_1 = '/openerp/xmlrpc/1'
JSON_RPC_PATH = '/openerp/jsonrpc'
JSON_RPC_PATH_1 = '/openerp/jsonrpc/1'

def xmlrpc_return(start_response, service, method, params, legacy_exceptions=False):
    """
    Helper to call a service's method with some params, using a wsgi-supplied
    ``start_response`` callback.

    This is the place to look at to see the mapping between core exceptions
    and XML-RPC fault codes.
    """
    # Map OpenERP core exceptions to XML-RPC fault codes. Specific exceptions
    # defined in ``openerp.exceptions`` are mapped to specific fault codes;
    # all the other exceptions are mapped to the generic
    # RPC_FAULT_CODE_APPLICATION_ERROR value.
    # This also mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for
    # exception handling.
    try:
        def fix(res):
            """
            This fix is a minor hook to avoid xmlrpclib to raise TypeError exception: 
            - To respect the XML-RPC protocol, all "int" and "float" keys must be cast to string to avoid
              TypeError, "dictionary key must be string"
            - And since "allow_none" is disabled, we replace all None values with a False boolean to avoid
              TypeError, "cannot marshal None unless allow_none is enabled"
            """
            if res is None:
                return False
            elif type(res) == dict:
                return dict((str(key), fix(value)) for key, value in res.items())
            else:
                return res
            
        result = fix(openerp.netsvc.dispatch_rpc(service, method, params))
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)
    except Exception, e:
        if legacy_exceptions:
            response = xmlrpc_handle_exception_legacy(e)
        else:
            response = xmlrpc_handle_exception(e)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]

def xmlrpc_handle_exception(e):
    if isinstance(e, openerp.osv.osv.except_osv): # legacy
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, openerp.tools.ustr(e.value))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.Warning):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance (e, openerp.exceptions.AccessError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.AccessDenied):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.DeferredException):
        info = e.traceback
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = openerp.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    else:
        if hasattr(e, 'message') and e.message == 'AccessDenied': # legacy
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
            response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
        else:
            info = sys.exc_info()
            # Which one is the best ?
            formatted_info = "".join(traceback.format_exception(*info))
            #formatted_info = openerp.tools.exception_to_unicode(e) + '\n' + info
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
            response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
    return response

def xmlrpc_handle_exception_legacy(e):
    if isinstance(e, openerp.osv.osv.except_osv):
        fault = xmlrpclib.Fault('warning -- ' + e.name + '\n\n' + e.value, '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.Warning):
        fault = xmlrpclib.Fault('warning -- Warning\n\n' + str(e), '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.AccessError):
        fault = xmlrpclib.Fault('warning -- AccessError\n\n' + str(e), '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.AccessDenied):
        fault = xmlrpclib.Fault('AccessDenied', str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, openerp.exceptions.DeferredException):
        info = e.traceback
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(openerp.tools.ustr(e.message), formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(openerp.tools.exception_to_unicode(e), formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
    return response

def wsgi_xmlrpc_1(environ, start_response):
    """ The main OpenERP WSGI handler."""
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith(XML_RPC_PATH_1):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        params, method = xmlrpclib.loads(data)

        path = environ['PATH_INFO'][len(XML_RPC_PATH_1):]
        if path.startswith('/'): path = path[1:]
        if path.endswith('/'): path = path[:-1]
        path = path.split('/')

        # All routes are hard-coded.

        # No need for a db segment.
        if len(path) == 1:
            service = path[0]

            if service == 'common':
                if method in ('server_version',):
                    service = 'db'
            return xmlrpc_return(start_response, service, method, params)

        # A db segment must be given.
        elif len(path) == 2:
            service, db_name = path
            params = (db_name,) + params

            return xmlrpc_return(start_response, service, method, params)

        # A db segment and a model segment must be given.
        elif len(path) == 3 and path[0] == 'model':
            service, db_name, model_name = path
            params = (db_name,) + params[:2] + (model_name,) + params[2:]
            service = 'object'
            return xmlrpc_return(start_response, service, method, params)

        # The body has been read, need to raise an exception (not return None).
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_CLIENT_ERROR, '')
        response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
        start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
        return [response]

def wsgi_xmlrpc(environ, start_response):
    """ WSGI handler to return the versions."""
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith(XML_RPC_PATH):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        params, method = xmlrpclib.loads(data)

        path = environ['PATH_INFO'][len(XML_RPC_PATH):]
        if path.startswith('/'): path = path[1:]
        if path.endswith('/'): path = path[:-1]
        path = path.split('/')

        # All routes are hard-coded.

        if len(path) == 1 and path[0] == '' and method in ('version',):
            return xmlrpc_return(start_response, 'common', method, ())

        # The body has been read, need to raise an exception (not return None).
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_CLIENT_ERROR, '')
        response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
        start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
        return [response]

def wsgi_xmlrpc_legacy(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)
        path = environ['PATH_INFO'][len('/xmlrpc/'):] # expected to be one of db, object, ...

        params, method = xmlrpclib.loads(data)
        return xmlrpc_return(start_response, path, method, params, True)

def wsgi_webdav(environ, start_response):
    pi = environ['PATH_INFO']
    if environ['REQUEST_METHOD'] == 'OPTIONS' and pi in ['*','/']:
        return return_options(environ, start_response)
    elif pi.startswith('/webdav'):
        http_dir = websrv_lib.find_http_service(pi)
        if http_dir:
            path = pi[len(http_dir.path):]
            if path.startswith('/'):
                environ['PATH_INFO'] = path
            else:
                environ['PATH_INFO'] = '/' + path
            return http_to_wsgi(http_dir)(environ, start_response)

def return_options(environ, start_response):
    # Microsoft specific header, see
    # http://www.ibm.com/developerworks/rational/library/2089.html
    if 'Microsoft' in environ.get('User-Agent', ''):
        options = [('MS-Author-Via', 'DAV')]
    else:
        options = []
    options += [('DAV', '1 2'), ('Allow', 'GET HEAD PROPFIND OPTIONS REPORT')]
    start_response("200 OK", [('Content-Length', str(0))] + options)
    return []

def http_to_wsgi(http_dir):
    """
    Turn a BaseHTTPRequestHandler into a WSGI entry point.

    Actually the argument is not a bare BaseHTTPRequestHandler but is wrapped
    (as a class, so it needs to be instanciated) in a HTTPDir.

    This code is adapted from wbsrv_lib.MultiHTTPHandler._handle_one_foreign().
    It is a temporary solution: the HTTP sub-handlers (in particular the
    document_webdav addon) have to be WSGIfied.
    """
    def wsgi_handler(environ, start_response):

        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:].replace('_', '-').title()
                headers[key] = value
            if key == 'CONTENT_LENGTH':
                key = key.replace('_', '-').title()
                headers[key] = value
        if environ.get('Content-Type'):
            headers['Content-Type'] = environ['Content-Type']

        path = urllib.quote(environ.get('PATH_INFO', ''))
        if environ.get('QUERY_STRING'):
            path += '?' + environ['QUERY_STRING']

        request_version = 'HTTP/1.1' # TODO
        request_line = "%s %s %s\n" % (environ['REQUEST_METHOD'], path, request_version)

        class Dummy(object):
            pass

        # Let's pretend we have a server to hand to the handler.
        server = Dummy()
        server.server_name = environ['SERVER_NAME']
        server.server_port = int(environ['SERVER_PORT'])

        # Initialize the underlying handler and associated auth. provider.
        con = openerp.service.websrv_lib.noconnection(environ['wsgi.input'])
        handler = http_dir.instanciate_handler(con, environ['REMOTE_ADDR'], server)

        # Populate the handler as if it is called by a regular HTTP server
        # and the request is already parsed.
        handler.wfile = StringIO.StringIO()
        handler.rfile = environ['wsgi.input']
        handler.headers = headers
        handler.command = environ['REQUEST_METHOD']
        handler.path = path
        handler.request_version = request_version
        handler.close_connection = 1
        handler.raw_requestline = request_line
        handler.requestline = request_line

        # Handle authentication if there is an auth. provider associated to
        # the handler.
        if hasattr(handler, 'auth_provider'):
            try:
                handler.auth_provider.checkRequest(handler, path)
            except websrv_lib.AuthRequiredExc, ae:
                # Darwin 9.x.x webdav clients will report "HTTP/1.0" to us, while they support (and need) the
                # authorisation features of HTTP/1.1 
                if request_version != 'HTTP/1.1' and ('Darwin/9.' not in handler.headers.get('User-Agent', '')):
                    start_response("403 Forbidden", [])
                    return []
                start_response("401 Authorization required", [
                    ('WWW-Authenticate', '%s realm="%s"' % (ae.atype,ae.realm)),
                    # ('Connection', 'keep-alive'),
                    ('Content-Type', 'text/html'),
                    ('Content-Length', 4), # len(self.auth_required_msg)
                    ])
                return ['Blah'] # self.auth_required_msg
            except websrv_lib.AuthRejectedExc,e:
                start_response("403 %s" % (e.args[0],), [])
                return []

        method_name = 'do_' + handler.command

        # Support the OPTIONS method even when not provided directly by the
        # handler. TODO I would prefer to remove it and fix the handler if
        # needed.
        if not hasattr(handler, method_name):
            if handler.command == 'OPTIONS':
                return return_options(environ, start_response)
            start_response("501 Unsupported method (%r)" % handler.command, [])
            return []

        # Finally, call the handler's method.
        try:
            method = getattr(handler, method_name)
            method()
            # The DAV handler buffers its output and provides a _flush()
            # method.
            getattr(handler, '_flush', lambda: None)()
            response = parse_http_response(handler.wfile.getvalue())
            response_headers = response.getheaders()
            body = response.read()
            start_response(str(response.status) + ' ' + response.reason, response_headers)
            return [body]
        except (websrv_lib.AuthRejectedExc, websrv_lib.AuthRequiredExc):
            raise
        except Exception, e:
            start_response("500 Internal error", [])
            return []

    return wsgi_handler

def parse_http_response(s):
    """ Turn a HTTP response string into a httplib.HTTPResponse object."""
    class DummySocket(StringIO.StringIO):
        """
        This is used to provide a StringIO to httplib.HTTPResponse
        which, instead of taking a file object, expects a socket and
        uses its makefile() method.
        """
        def makefile(self, *args, **kw):
            return self
    response = httplib.HTTPResponse(DummySocket(s))
    response.begin()
    return response

# WSGI handlers registered through the register_wsgi_handler() function below.
module_handlers = []

def register_wsgi_handler(handler):
    """ Register a WSGI handler.

    Handlers are tried in the order they are added. We might provide a way to
    register a handler for specific routes later.
    """
    module_handlers.append(handler)

def application_unproxied(environ, start_response):
    """ WSGI entry point."""
    # cleanup db/uid trackers - they're set at HTTP dispatch in
    # web.session.OpenERPSession.send() and at RPC dispatch in
    # openerp.service.web_services.objects_proxy.dispatch().
    # /!\ The cleanup cannot be done at the end of this `application`
    # method because werkzeug still produces relevant logging afterwards 
    if hasattr(threading.current_thread(), 'uid'):
        del threading.current_thread().uid
    if hasattr(threading.current_thread(), 'dbname'):
        del threading.current_thread().dbname

    openerp.service.start_internal()

    # Try all handlers until one returns some result (i.e. not None).
    wsgi_handlers = [wsgi_xmlrpc_1, wsgi_xmlrpc, wsgi_xmlrpc_legacy, wsgi_webdav]
    wsgi_handlers += module_handlers
    for handler in wsgi_handlers:
        result = handler(environ, start_response)
        if result is None:
            continue
        return result

    # We never returned from the loop.
    response = 'No handler found.\n'
    start_response('404 Not Found', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
    return [response]

def application(environ, start_response):
    if config['proxy_mode'] and 'HTTP_X_FORWARDED_HOST' in environ:
        return werkzeug.contrib.fixers.ProxyFix(application_unproxied)(environ, start_response)
    else:
        return application_unproxied(environ, start_response)

# The WSGI server, started by start_server(), stopped by stop_server().
httpd = None

def serve():
    """ Serve HTTP requests via werkzeug development server.

    If werkzeug can not be imported, we fall back to wsgiref's simple_server.

    Calling this function is blocking, you might want to call it in its own
    thread.
    """

    global httpd

    # TODO Change the xmlrpc_* options to http_*
    interface = config['xmlrpc_interface'] or '0.0.0.0'
    port = config['xmlrpc_port']
    httpd = werkzeug.serving.make_server(interface, port, application, threaded=True)
    _logger.info('HTTP service (werkzeug) running on %s:%s', interface, port)
    httpd.serve_forever()

def start_service():
    """ Call serve() in its own thread.

    The WSGI server can be shutdown with stop_server() below.
    """
    threading.Thread(target=serve).start()

def stop_service():
    """ Initiate the shutdown of the WSGI server.

    The server is supposed to have been started by start_server() above.
    """
    if httpd:
        httpd.shutdown()
        openerp.netsvc.close_socket(httpd.socket)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
