.. _api:

OpenERP API Reference
=====================

.. image:: _static/openerp.png
   :alt: OpenERP framework logo
   :class: floatingflask

Welcome to OpenERP API reference.

.. _openerp library:

Server-side library
-------------------

.. automodule:: openerp
   :members:
   :undoc-members:

Start-up script
---------------

To run the OpenERP server, the conventional approach is to use the
`openerp-server` script.  It loads the :ref:`openerp library`, sets a few
configuration variables corresponding to command-line arguments, and starts to
listen to incoming connections from clients.

Depending on your deployment needs, you can write such a start-up script very
easily. We also recommend you take a look at an alternative tool called
`openerp-command` that can, among other things, launch the server.

.. versionadded:: 6.1

Yet another alternative is to use a WSGI-compatible HTTP server and let it call
into one of the WSGI entry points of the server.

.. versionadded:: 6.1

ORM and models
--------------

.. automodule:: openerp.osv.orm
   :members:
   :undoc-members:
