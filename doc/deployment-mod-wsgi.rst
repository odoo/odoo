.. _using-mod-wsgi:

Deploying with ``mod_wsgi``
===========================

``mod_wsgi`` makes it possible to run a WSGI_ application (such as OpenERP)
under the Apache_ HTTP server.

.. _WSGI: http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface
.. _Apache: https://httpd.apache.org/

Summary
-------

Similarly to :doc:`deployment-gunicorn`, running OpenERP behind Apache with
``mod_wsgi`` requires to modify the sample ``openerp-wsgi.py`` script. Then
that Python script can be set in the Apache configuration.

Python (WSGI) application
-------------------------

Apache needs a Python script providing the WSGI application. By default the
symbol looked up by Apache is ``application`` but it can be overidden with the
``WSGICallableObject`` directive if necessary. A sample script
``openerp-wsgi.py`` is provided with OpenERP and you can adapt it to your
needs. For instance, make sure to correctly set the ``addons_path``
configuration (using absolute paths).

.. note ::
  The script provided to Apache has often the extension ``.wsgi`` but the
  ``openerp-wsgi.py`` script will do just as fine.

Apache Configuration
--------------------

In Apache's configuration, add the following line to activate ``mod_wsgi``::

  LoadModule wsgi_module modules/mod_wsgi.so

Then a possible (straightforward, with e.g. no virtual server) configuration is
as follow::

  WSGIScriptAlias / /home/thu/repos/server/trunk/openerp-wsgi.py
  WSGIDaemonProcess oe user=thu group=users processes=2 python-path=/home/thu/repos/server/trunk/ display-name=apache-openerp
  WSGIProcessGroup oe

  <Directory /home/thu/repos/server/trunk>
      Order allow,deny
      Allow from all
  </Directory>

The ``WSGIScriptAlias`` directive indicates that any URL matching ``/`` will
run the application defined in the ``openerp-wsgi.py`` script.

The ``WSGIDaemonProcess`` and ``WSGIProcessGroup`` directives create a process
configuration. The configuration makes it possible for isntance to specify
which user runs the OpenERP process. The ``display-name`` option will make the
processes appear as ``apache-openerp`` in ``ps`` (instead of the normal
``httpd``).

Finally, it is necessary to make sure the source directory where the script can
be found is allowed by Apache with the ``Directory`` block.

``mod_wsgi`` supports a lot of directives, please see this ``mod_wsgi`` wiki
page for more details:
http://code.google.com/p/modwsgi/wiki/ConfigurationDirectives.

Running
-------

When the Apache configuration changes, it is necessary to restart Apache, e.g. with::

  /etc/init.d/httpd restart
