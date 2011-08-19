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

This module offers an WSGI interface to OpenERP.

"""

from wsgiref.simple_server import make_server
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
import xmlrpclib

import sys

import openerp
import openerp.tools.config as config

def wsgi_xmlrpc(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)
        path = environ['PATH_INFO'][len('/xmlrpc/'):] # expected to be one of db, object, ... TODO should we expect a possible trailing '/' ?

        # TODO see SimpleXMLRPCDispatcher._marshaled_dispatch() for some necessary handling.
        # TODO see OpenERPDispatcher for some othe handling (in particular, auth things).
        params, method = xmlrpclib.loads(data)
        result = openerp.netsvc.ExportService.getService(path).dispatch(method, None, params)
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)

        start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
        return [response]

def wsgi_jsonrpc(environ, start_response):
    pass

def application(environ, start_response):

    # Try all handlers until one returns some result (i.e. not None).
    wsgi_handlers = [wsgi_xmlrpc, wsgi_jsonrpc]
    for handler in wsgi_handlers:
        result = handler(environ, start_response)
        if result is None:
            continue
        return result

    # We never returned from the loop.
    else:
        response = 'No handler found.\n'
        start_response('200 OK', [('Content-Type', 'text/plain'), ('Content-Length', str(len(response)))])
        return [response]

# Serve XMLRPC via wsgiref's simple_server.
# Blocking, should probably be called in its own process.
def serve():
    httpd = make_server('localhost', config['xmlrpc_port'], application)
    httpd.serve_forever()

# Application setup be fore we can spawn any worker process.
# This is suitable for e.g. gunicorn's on_starting hook.
def on_starting(server):
    config = openerp.tools.config
    config['addons_path'] = '/home/openerp/repos/addons/trunk/' # need a config file
    openerp.netsvc.init_logger()
    openerp.osv.osv.start_object_proxy()
    openerp.service.web_services.start_web_services()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
