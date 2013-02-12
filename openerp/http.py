# -*- coding: utf-8 -*-

"""
``openerp.http`` offers decorators to register WSGI and RPC endpoints handlers.
See :ref:`routing`.
"""

from . import service

def handler():
    """
    Decorator to register a WSGI handler. The handler must return None if it
    does not handle the request.
    """
    def decorator(f):
        service.wsgi_server.register_wsgi_handler(f)
    return decorator

def route(url):
    """
    Same as then handler() decorator but register the handler under a specific
    url. Not yet implemented.
    """
    def decorator(f):
        pass # TODO
    return decorator

def rpc(endpoint):
    """
    Decorator to register a RPC endpoint handler. The handler will receive
    already unmarshalled RCP arguments.
    """
    def decorator(f):
        service.wsgi_server.register_rpc_endpoint(endpoint, f)
    return decorator

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
