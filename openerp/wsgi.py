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

from wsgiref.simple_server import make_server
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
import httplib
import urllib
import xmlrpclib
import StringIO

import os
import signal
import sys
import time

import openerp
import openerp.tools.config as config

def xmlrpc_return(start_response, service, method, params):
    """ Helper to call a service's method with some params, using a
    wsgi-supplied ``start_response`` callback."""
    # This mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for exception
    # handling.
    try:
        result = openerp.netsvc.dispatch_rpc(service, method, params, None) # TODO auth
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
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/openerp/xmlrpc'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        params, method = xmlrpclib.loads(data)

        path = environ['PATH_INFO'][len('/openerp/xmlrpc'):]
        if path.startswith('/'): path = path[1:]
        if path.endswith('/'): p = path[:-1]
        path = path.split('/')

        # All routes are hard-coded. Need a way to register addons-supplied handlers.

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

def wsgi_modules(environ, start_response):
    """ WSGI handler dispatching to addons-provided entry points."""
    pass

def wsgi_webdav(environ, start_response):
    if environ['REQUEST_METHOD'] == 'OPTIONS' and environ['PATH_INFO'] == '*':
        return return_options(start_response)
    if environ['PATH_INFO'].startswith('/webdav'): # TODO depends on config
        environ['PATH_INFO'] = '/' + environ['PATH_INFO'][len('/webdav'):]
        return wsgi_to_http(environ, start_response)

def return_options(start_response):
    # TODO Microsoft specifi header, see websrv_lib do_OPTIONS 
    options = [('DAV', '1 2'), ('Allow', 'GET HEAD PROPFIND OPTIONS REPORT')]
    start_response("200 OK", [('Content-Length', str(0))] + options)
    return []

webdav = None

def wsgi_to_http(environ, start_response):
    """
    Forward a WSGI request to a BaseHTTPRequestHandler.

    This code is adapted from wbsrv_lib.MultiHTTPHandler._handle_one_foreign().
    It is a temporary solution: the HTTP sub-handlers (in particular the
    document_webdav addon) have to be WSGIfied.
    """
    global webdav
    # Make sure the addons are loaded in the registry, so they have a chance
    # to register themselves in the 'service' layer.
    openerp.pooler.get_db_and_pool('xx', update_module=[], pooljobs=False)

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

    class Dummy():
        pass
    server = Dummy()
    server.server_name = environ['SERVER_NAME']
    server.server_port = int(environ['SERVER_PORT'])
    con = openerp.service.websrv_lib.noconnection(environ['gunicorn.socket']) # None
    fore = webdav.handler(openerp.service.websrv_lib.noconnection(con), environ['REMOTE_ADDR'], server)

    # let's pretend we are a Multi handler
    class M():
        def __init__(self):
            self.sec_realms = {}
            self.shared_headers = []
            self.shared_response = ''
            self.shared_body = ''
        def send_error(self, code, msg):
            self.shared_response = str(code) + ' ' + msg
        def send_response(self, code, msg):
            self.shared_response = str(code) + ' ' + msg
        def send_header(self, a, b):
            self.shared_headers.append((a, b))
        def end_headers(self, *args, **kwargs):
            pass

    multi = M()

    webdav.auth_provider.setupAuth(multi, fore)

    request_version = 'HTTP/1.1' # TODO
    fore.wfile = StringIO.StringIO()
    fore.rfile = environ['wsgi.input']
    fore.headers = headers
    fore.command = environ['REQUEST_METHOD']
    fore.path = path
    fore.request_version = request_version
    fore.close_connection = 1

    fore.raw_requestline = "%s %s %s\n" % (environ['REQUEST_METHOD'], path, request_version)
    fore.requestline = fore.raw_requestline

    from openerp.service.websrv_lib import AuthRequiredExc, AuthRejectedExc

    def go():
        auth_provider = webdav.auth_provider
        if auth_provider and auth_provider.realm:
            try:
                multi.sec_realms[auth_provider.realm].checkRequest(fore, path)
            except AuthRequiredExc, ae:
                # Darwin 9.x.x webdav clients will report "HTTP/1.0" to us, while they support (and need) the
                # authorisation features of HTTP/1.1 
                if request_version != 'HTTP/1.1' and ('Darwin/9.' not in fore.headers.get('User-Agent', '')):
                    print 'self.log_error("Cannot require auth at %s", self.request_version)'
                    multi.send_error(403)
                    return
                #self._get_ignore_body(fore) # consume any body that came, not loose sync with input
                multi.send_response(401,'Authorization required')
                multi.send_header('WWW-Authenticate','%s realm="%s"' % (ae.atype,ae.realm))
                multi.send_header('Connection', 'keep-alive')
                multi.send_header('Content-Type','text/html')
                multi.send_header('Content-Length', 4) # len(self.auth_required_msg))
                multi.end_headers()
                #self.wfile.write(self.auth_required_msg)
                multi.shared_body = 'Blah'
                return
            except AuthRejectedExc,e:
                print '("Rejected auth: %s" % e.args[0])'
                multi.send_error(403,e.args[0])
                return
        mname = 'do_' + fore.command
        if not hasattr(fore, mname):
            if fore.command == 'OPTIONS':
                return return_options(start_response)
            multi.send_error(501, "Unsupported method (%r)" % fore.command)
            return
        method = getattr(fore, mname)
        try:
            method()
            if hasattr(fore, '_flush'):
                fore._flush()
            response = fore.wfile.getvalue()
            class DummySocket(StringIO.StringIO):
                """
                This is used to provide a StringIO to httplib.HTTPResponse
                which, instead of taking a file object, expects a socket and
                uses its makefile() method.
                """
                def makefile(self, *args, **kw):
                    return self
            response = httplib.HTTPResponse(DummySocket(response))
            response.begin()
            response_headers = response.getheaders()
            body = response.read()
            start_response(str(response.status) + ' ' + response.reason, response_headers)
            return [body]
        except (AuthRejectedExc, AuthRequiredExc):
            raise
        except Exception, e:
            multi.send_error(500, "Internal error")
            return
    res = go()
    if res is None:
        start_response(multi.shared_response, multi.shared_headers)
        return [multi.shared_body]
    else:
        return res

# WSGI handlers provided by modules loaded with the --load command-line option.
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
        #wsgi_xmlrpc,
        #wsgi_jsonrpc,
        #legacy_wsgi_xmlrpc,
        #wsgi_modules,
        wsgi_webdav
        ] #+ module_handlers
    for handler in wsgi_handlers:
        result = handler(environ, start_response)
        if result is None:
            continue
        return result

    # We never returned from the loop. Needs something else than 200 OK.
    response = 'No handler found.\n'
    start_response('200 OK', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
    return [response]

def serve():
    """ Serve XMLRPC requests via wsgiref's simple_server.

    Blocking, should probably be called in its own process.
    """
    httpd = make_server('localhost', config['xmlrpc_port'], application)
    httpd.serve_forever()

# Master process id, can be used for signaling.
arbiter_pid = None

# Application setup before we can spawn any worker process.
# This is suitable for e.g. gunicorn's on_starting hook.
def on_starting(server):
    global arbiter_pid
    arbiter_pid = os.getpid() # TODO check if this is true even after replacing the executable
    config = openerp.tools.config
    config['addons_path'] = '/home/openerp/repos/addons/trunk-xmlrpc' # need a config file
    #config['log_level'] = 10 # debug
    #openerp.tools.cache = kill_workers_cache
    openerp.netsvc.init_logger()
    openerp.osv.osv.start_object_proxy()
    openerp.service.web_services.start_web_services()
    test_in_thread()

def test_in_thread():
    def f():
        import time
        time.sleep(2)
        print ">>>> test thread"
        cr = openerp.sql_db.db_connect('xx').cursor()
        module_name = 'document_webdav'
        fp = openerp.tools.file_open('/home/openerp/repos/addons/trunk-xmlrpc/document_webdav/test/webdav_test1.yml')
        openerp.tools.convert_yaml_import(cr, module_name, fp, {}, 'update', True)
        cr.close()
        print "<<<< test thread"
    import threading
    threading.Thread(target=f).start()

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
