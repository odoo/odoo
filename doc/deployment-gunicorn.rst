.. _using-gunicorn:

Deploying with Gunicorn
=======================

Starting with OpenERP 6.1, the server and web addons are WSGI_ compliant. In
particular, support for the Gunicorn_ HTTP server is available. For some
background information and motivation, please read http://www.openerp.com/node/1106.
To install Gunicorn, please refer to Gunicorn's website.

.. _Gunicorn: http://gunicorn.org/
.. _WSGI: http://en.wikipedia.org/wiki/Web_Server_Gateway_Interface

Summary
-------

Configuring and starting an OpenERP server with Gunicorn is straightfoward. The
different sections below give more details but the following steps are all it
takes:

1. Use a configuration file, passing it to ``gunicorn`` using the ``-c``
   option.
2. Within the same configuration file, also configure OpenERP.
3. Run ``gunicorn openerp:service.wsgi_server.application -c openerp-wsgi.py``.

Sample configuration file
-------------------------

A sample ``openerp-wsgi.py`` configuration file for WSGI servers can be found
in the OpenERP server source tree. It is fairly well commented and easily
customizable for your own usage. While reading the remaining of this page, it
is advised you take a look at the sample ``openerp-wsgi.py`` file as it makes
things easier to follow.

Configuration
-------------

Gunicorn can be configured by a configuration file and/or command-line
arguments. For a list of available options, you can refer to the official
Gunicorn documentation http://docs.gunicorn.org/en/latest/configure.html.

When the OpenERP server is started on its own, by using the ``openerp-server``
script, it can also be configured by a configuration file or its command-line
arguments. But when it is run via Gunicorn, it is no longer the case. Instead,
as the Gunicorn configuration file is a full-fledged Python file, we can
``import openerp`` in it and configure directly the server.

The principle can be summarized with this three lines (although they are spread
across the whole sample ``openerp-wsgi.py`` file)::

  import openerp
  conf = openerp.tools.config
  conf['addons_path'] = '/home/openerp/addons/trunk,/home/openerp/web/trunk/addons'

The above three lines first import the ``openerp`` library (i.e. the one
containing the OpenERP server implementation). The second one is really to
shorten repeated usage of the same variable. The third one sets a parameter, in
this case the equivalent of the ``--addons-path`` command-line option.

Running
-------

Once a proper configuration file is available, running the OpenERP server with
Gunicorn can be done with the following command::

  > gunicorn openerp:service.wsgi_server.application -c openerp-wsgi.py

``openerp`` must be importable by Python. The simplest way is to run the above
command from the server source directory (i.e. the directory containing the
``openerp`` module). Alternatively, the module can be installed on your machine
as a regular Python library or added to your ``PYTHONPATH``.

