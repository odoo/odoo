# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 OpenERP s.a. (<http://openerp.com>).
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

""" WSGI stuffs (proof of concept for now)

This module offers a WSGI interface to OpenERP.

"""

import httplib
import urllib
import xmlrpclib
import StringIO

import logging
import os
import signal
import sys
import threading
import time

import openerp
import openerp.tools.config as config
import service.websrv_lib as websrv_lib

def xmlrpc_return(start_response, service, method, params):
    """ Helper to call a service's method with some params, using a
    wsgi-supplied ``start_response`` callback."""
    # This mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for exception
    # handling.
    try:
        result = openerp.netsvc.dispatch_rpc(service, method, params)
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)
    except openerp.netsvc.OpenERPDispatcherException, e:
        fault = xmlrpclib.Fault(openerp.tools.exception_to_unicode(e.exception), e.traceback)
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        fault = xmlrpclib.Fault(1, "%s:%s" % (exc_type, exc_value))
        response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]

def wsgi_xmlrpc(environ, start_response):
    """ The main OpenERP WSGI handler."""
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/openerp/6.1/xmlrpc'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        params, method = xmlrpclib.loads(data)

        path = environ['PATH_INFO'][len('/openerp/6.1/xmlrpc'):]
        if path.startswith('/'): path = path[1:]
        if path.endswith('/'): p = path[:-1]
        path = path.split('/')

        # All routes are hard-coded.

        # No need for a db segment.
        if len(path) == 1:
            service = path[0]

            if service == 'common':
                if method in ('create_database', 'list', 'server_version'):
                    return xmlrpc_return(start_response, 'db', method, params)
                else:
                    return xmlrpc_return(start_response, 'common', method, params)
        # A db segment must be given.
        elif len(path) == 2:
            service, db_name = path
            params = (db_name,) + params

            if service == 'model':
                return xmlrpc_return(start_response, 'object', method, params)
            elif service == 'report':
                return xmlrpc_return(start_response, 'report', method, params)

        # TODO the body has been read, need to raise an exception (not return None).

def legacy_wsgi_xmlrpc(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)
        path = environ['PATH_INFO'][len('/xmlrpc/'):] # expected to be one of db, object, ...

        params, method = xmlrpclib.loads(data)
        return xmlrpc_return(start_response, path, method, params)

def wsgi_jsonrpc(environ, start_response):
    pass

def wsgi_webdav(environ, start_response):
    if environ['REQUEST_METHOD'] == 'OPTIONS' and environ['PATH_INFO'] == '*':
        return return_options(environ, start_response)

    http_dir = websrv_lib.find_http_service(environ['PATH_INFO'])
    if http_dir:
        path = environ['PATH_INFO'][len(http_dir.path):]
        if path.startswith('/'):
            environ['PATH_INFO'] = path
        else:
            environ['PATH_INFO'] = '/' + path
        return http_to_wsgi(http_dir)(environ, start_response)

def return_options(environ, start_response):
    # Microsoft specific header, see
    # http://www.ibm.com/developerworks/rational/library/2089.html
    if 'Microsoft' in environ.get('User-Agent', ''):
        option = [('MS-Author-Via', 'DAV')]
    else:
        option = []
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

        # Extract from the WSGI environment the necessary data.
        scheme = environ['wsgi.url_scheme']

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

def application(environ, start_response):
    """ WSGI entry point."""

    # Try all handlers until one returns some result (i.e. not None).
    wsgi_handlers = [
        wsgi_xmlrpc,
        wsgi_jsonrpc,
        legacy_wsgi_xmlrpc,
        wsgi_webdav
        ] + module_handlers
    for handler in wsgi_handlers:
        result = handler(environ, start_response)
        if result is None:
            continue
        return result

    # We never returned from the loop.
    response = 'No handler found.\n'
    start_response('404 Not Found', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
    return [response]

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
    try:
        import werkzeug.serving
        httpd = werkzeug.serving.make_server(interface, port, application, threaded=True)
        logging.getLogger('wsgi').info('HTTP service (werkzeug) running on %s:%s', interface, port)
    except ImportError, e:
        import wsgiref.simple_server
        logging.getLogger('wsgi').warn('Werkzeug module unavailable, falling back to wsgiref.')
        httpd = wsgiref.simple_server.make_server(interface, port, application)
        logging.getLogger('wsgi').info('HTTP service (wsgiref) running on %s:%s', interface, port)

    httpd.serve_forever()

def start_server():
    """ Call serve() in its own thread.

    The WSGI server can be shutdown with stop_server() below.
    """
    threading.Thread(target=openerp.wsgi.serve).start()

def stop_server():
    """ Initiate the shutdown of the WSGI server.

    The server is supposed to have been started by start_server() above.
    """
    if httpd:
        httpd.shutdown()

# Master process id, can be used for signaling.
arbiter_pid = None

# Application setup before we can spawn any worker process.
# This is suitable for e.g. gunicorn's on_starting hook.
def on_starting(server):
    global arbiter_pid
    arbiter_pid = os.getpid() # TODO check if this is true even after replacing the executable
    config = openerp.tools.config
    #openerp.tools.cache = kill_workers_cache
    openerp.netsvc.init_logger()
    openerp.osv.osv.start_object_proxy()
    openerp.service.web_services.start_web_services()

# Install our own signal handler on the master process.
def when_ready(server):
    # Hijack gunicorn's SIGWINCH handling; we can choose another one.
    signal.signal(signal.SIGWINCH, make_winch_handler(server))

# Our signal handler will signal a SGIQUIT to all workers.
def make_winch_handler(server):
    def handle_winch(sig, fram):
        server.kill_workers(signal.SIGQUIT) # This is gunicorn specific.
    return handle_winch

# Kill gracefuly the workers (e.g. because we want to clear their cache).
# This is done by signaling a SIGWINCH to the master process, so it can be
# called by the workers themselves.
def kill_workers():
    try:
        os.kill(arbiter_pid, signal.SIGWINCH)
    except OSError, e:
        if e.errno == errno.ESRCH: # no such pid
            return
        raise            

class kill_workers_cache(openerp.tools.ormcache):
    def clear(self, dbname, *args, **kwargs):
        kill_workers()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
