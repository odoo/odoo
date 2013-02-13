.. _routing:

Routing
=======

.. versionchanged:: 7.1

The OpenERP framework, as an HTTP server, serves a few hard-coded URLs
(``models``, ``db``, ...) to expose RPC endpoints. When running the web addons
(which is almost always the case), it also serves URLs without them being RPC
endpoints.

In older version of OpenERP, adding RPC endpoints was done by subclassing the
``openerp.netsvc.ExportService`` class. Adding WSGI handlers was done by
registering them with the :py:func:`openerp.wsgi.register_wsgi_handler`
function.

Starting with OpenERP 7.1, exposing a new arbitrary WSGI handler is done with
the :py:func:`openerp.http.handler` decorator while adding an RPC endpoint is
done with the :py:func:`openerp.http.rpc` decorator.

.. _routing-decorators:

Routing decorators
------------------

.. automodule:: openerp.http
   :members:
   :undoc-members:
