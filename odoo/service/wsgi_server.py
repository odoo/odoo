# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""

WSGI stack, common code.

"""

import httplib
import urllib
import xmlrpclib
import StringIO

import errno
import logging
import platform
import socket
import sys
import threading
import traceback

import werkzeug.serving
import werkzeug.contrib.fixers

import odoo
import odoo.tools.config as config

_logger = logging.getLogger(__name__)

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``odoo.exceptions`` (not
# create directly ``xmlrpclib.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

def xmlrpc_return(start_response, service, method, params, string_faultcode=False):
    """
    Helper to call a service's method with some params, using a wsgi-supplied
    ``start_response`` callback.

    This is the place to look at to see the mapping between core exceptions
    and XML-RPC fault codes.
    """
    # Map OpenERP core exceptions to XML-RPC fault codes. Specific exceptions
    # defined in ``odoo.exceptions`` are mapped to specific fault codes;
    # all the other exceptions are mapped to the generic
    # RPC_FAULT_CODE_APPLICATION_ERROR value.
    # This also mimics SimpleXMLRPCDispatcher._marshaled_dispatch() for
    # exception handling.
    try:
        result = odoo.http.dispatch_rpc(service, method, params)
        response = xmlrpclib.dumps((result,), methodresponse=1, allow_none=False, encoding=None)
    except Exception, e:
        if string_faultcode:
            response = xmlrpc_handle_exception_string(e)
        else:
            response = xmlrpc_handle_exception_int(e)
    start_response("200 OK", [('Content-Type','text/xml'), ('Content-Length', str(len(response)))])
    return [response]

def xmlrpc_handle_exception_int(e):
    if isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, odoo.tools.ustr(e.value))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_WARNING, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance (e, odoo.exceptions.AccessError):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.DeferredException):
        info = e.traceback
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = odoo.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    else:
        if hasattr(e, 'message') and e.message == 'AccessDenied': # legacy
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
            response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
        #InternalError
        else:
            info = sys.exc_info()
            # Which one is the best ?
            formatted_info = "".join(traceback.format_exception(*info))
            #formatted_info = odoo.tools.exception_to_unicode(e) + '\n' + info
            fault = xmlrpclib.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
            response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
    return response

def xmlrpc_handle_exception_string(e):
    if isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpclib.Fault('warning -- %s\n\n%s' % (e.name, e.value), '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpclib.Fault('warning -- Warning\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpclib.Fault('warning -- MissingError\n\n' + str(e), '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpclib.Fault('warning -- AccessError\n\n' + str(e), '')
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpclib.Fault('AccessDenied', str(e))
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    elif isinstance(e, odoo.exceptions.DeferredException):
        info = e.traceback
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(odoo.tools.ustr(e.message), formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=False, encoding=None)
    #InternalError
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpclib.Fault(odoo.tools.exception_to_unicode(e), formatted_info)
        response = xmlrpclib.dumps(fault, allow_none=None, encoding=None)
    return response

def wsgi_xmlrpc(environ, start_response):
    """ Two routes are available for XML-RPC

    /xmlrpc/<service> route returns faultCode as strings. This is a historic
    violation of the protocol kept for compatibility.

    /xmlrpc/2/<service> is a new route that returns faultCode as int and is
    therefore fully compliant.
    """
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'].startswith('/xmlrpc/'):
        length = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(length)

        # Distinguish betweed the 2 faultCode modes
        string_faultcode = True
        if environ['PATH_INFO'].startswith('/xmlrpc/2/'):
            service = environ['PATH_INFO'][len('/xmlrpc/2/'):]
            string_faultcode = False
        else:
            service = environ['PATH_INFO'][len('/xmlrpc/'):]

        params, method = xmlrpclib.loads(data)
        return xmlrpc_return(start_response, service, method, params, string_faultcode)

def application_unproxied(environ, start_response):
    """ WSGI entry point."""
    # cleanup db/uid trackers - they're set at HTTP dispatch in
    # web.session.OpenERPSession.send() and at RPC dispatch in
    # odoo.service.web_services.objects_proxy.dispatch().
    # /!\ The cleanup cannot be done at the end of this `application`
    # method because werkzeug still produces relevant logging afterwards 
    if hasattr(threading.current_thread(), 'uid'):
        del threading.current_thread().uid
    if hasattr(threading.current_thread(), 'dbname'):
        del threading.current_thread().dbname
    if hasattr(threading.current_thread(), 'url'):
        del threading.current_thread().url

    with odoo.api.Environment.manage():
        # Try all handlers until one returns some result (i.e. not None).
        for handler in [wsgi_xmlrpc, odoo.http.root]:
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
