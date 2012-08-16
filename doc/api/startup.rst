
Start-up script
---------------

.. versionadded:: 6.1

To run the OpenERP server, the conventional approach is to use the
`openerp-server` script.  It loads the :ref:`openerp library`, sets a few
configuration variables corresponding to command-line arguments, and starts to
listen to incoming connections from clients.

Depending on your deployment needs, you can write such a start-up script very
easily. We also recommend you take a look at an alternative tool called
`openerp-command` that can, among other things, launch the server.

Yet another alternative is to use a WSGI-compatible HTTP server and let it call
into one of the WSGI entry points of the server.



