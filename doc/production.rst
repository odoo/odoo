Deploying OpenERP Web
=====================

.. After release one, add upgrade instructions if any

.. How about running the web client on alternative Python
.. implementations e.g. pypy or Jython? Since the only lib with C
.. accelerators we're using right now is SimpleJSON and it has a pure
.. Python base component, we should be able to test and deploy on
.. non-cpython no?

In-depth configuration
----------------------

SSL, basic proxy (link to relevant section), links to sections and
example files for various servers and proxies, WSGI
integration/explanation (if any), ...

Deployment Options
------------------

Serving via WSGI
~~~~~~~~~~~~~~~~

Apache mod_wsgi
+++++++++++++++

NGinx mod_wsgi
++++++++++++++

uWSGI
+++++

Gunicorn
++++++++

FastCGI, SCGI, or AJP
+++++++++++++++++++++

Behind a proxy
~~~~~~~~~~~~~~

Apache mod_proxy
++++++++++++++++

NGinx HttpProxy
+++++++++++++++
