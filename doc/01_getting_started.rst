========================================
Getting started with OpenERP development
========================================

.. toctree::
   :maxdepth: 1

Installation from sources
==========================

.. _getting_started_installation_source-link:

Source code is hosted on Launchpad_. In order to get the sources, you
will need Bazaar_ to pull the source from Launchpad. Bazaar is a
version control system that helps you track project history over time
and collaborate efficiently. You may have to create an account on
Launchpad to be able to collaborate on OpenERP development. Please
refer to the Launchpad and Bazaar documentation to install and setup
your development environment.

The running example of this section is based on an Ubuntu
environment. You may have to adapt the steps according to your
system. Once your working environment is ready, prepare a working
directory that will contain the sources.  For a ``source`` base
directory, type::

  mkdir source;cd source

OpenERP provides a setup script that automatizes the tasks of creating
a shared repository and getting the source code. Get the setup script
of OpenERP by typing::

  bzr cat -d lp:~openerp-dev/openerp-tools/trunk setup.sh | sh

This will create the following two files in your ``source`` directory::

  -rw-rw-r--  1 openerp openerp 5465 2012-04-17 11:05 Makefile
  -rw-rw-r--  1 openerp openerp 2902 2012-04-17 11:05 Makefile_helper.py

If you want some help about the available options, please type::

  make help

Next step is to initialize the shared repository and download the
sources. Get the current trunk version of OpenERP by typing::

  make init-trunk

This will create the following structure inside your ``source``
directory, and fetch the latest source code from ``trunk``::

  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 addons
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 misc
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 server
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 web

Some dependencies are necessary to use OpenERP. Depending on your
environment, you might have to install the following packages::

  sudo apt-get install graphviz ghostscript postgresql-client \
            python-dateutil python-feedparser python-gdata \
            python-ldap python-libxslt1 python-lxml python-mako \
            python-openid python-psycopg2 python-pybabel python-pychart \
            python-pydot python-pyparsing python-reportlab python-simplejson \
            python-tz python-vatnumber python-vobject python-webdav \
            python-werkzeug python-xlwt python-yaml python-imaging \
            python-matplotlib

Next step is to initialize the database. This will create a new openerp role::

  make db-setup

Finally, launch the OpenERP server::

  make server

Testing your installation can be done on http://localhost:8069/. You
should see the OpenERP main login page.

.. _Launchpad: https://launchpad.net/
.. _Bazaar: http://bazaar.canonical.com/en/

Command line options
====================

.. program:: openerp-server

Using the command ::

  ./openerp-server --help

General Options
+++++++++++++++

::

  --version                           show program version number and exit
  -h, --help                          show this help message and exit
  -c CONFIG, --config=CONFIG          specify alternate config file
  -s, --save                          save configuration to ~/.terp_serverrc
  -v, --verbose                       enable debugging
  --pidfile=PIDFILE                   file where the server pid will be stored
  --logfile=LOGFILE                   file where the server log will be stored
  -n INTERFACE, --interface=INTERFACE specify the TCP IP address
  -p PORT, --port=PORT                specify the TCP port
  --net_interface=NETINTERFACE        specify the TCP IP address for netrpc
  --net_port=NETPORT                  specify the TCP port for netrpc
  --no-netrpc                         disable netrpc
  --no-xmlrpc                         disable xmlrpc
  -i INIT, --init=INIT                init a module (use "all" for all modules)
  --without-demo=WITHOUT_DEMO         load demo data for a module (use "all" for all modules)
  -u UPDATE, --update=UPDATE          update a module (use "all" for all modules)
  --stop-after-init                   stop the server after it initializes
  --debug                             enable debug mode
  -S, --secure                        launch server over https instead of http
  --smtp=SMTP_SERVER                  specify the SMTP server for sending mail
 
Database related options
++++++++++++++++++++++++

::

  -d DB_NAME, --database=DB_NAME
                        specify the database name
  -r DB_USER, --db_user=DB_USER
                        specify the database user name
  -w DB_PASSWORD, --db_password=DB_PASSWORD
                        specify the database password
  --pg_path=PG_PATH   specify the pg executable path
  --db_host=DB_HOST   specify the database host
  --db_port=DB_PORT   specify the database port
 
Internationalization options
++++++++++++++++++++++++++++

Use these options to translate OpenERP to another language.See i18n
section of the user manual. Option '-l' is mandatory.::
 
  -l LANGUAGE, --language=LANGUAGE
                       specify the language of the translation file. Use it
                       with --i18n-export and --i18n-import
  --i18n-export=TRANSLATE_OUT
                       export all sentences to be translated to a CSV file
                       and exit
  --i18n-import=TRANSLATE_IN
                       import a CSV file with translations and exit
  --modules=TRANSLATE_MODULES
                       specify modules to export. Use in combination with
                       --i18n-export

Options from previous versions
++++++++++++++++++++++++++++++

Some options were removed in OpenERP version 6. For example,
``price_accuracy`` is now configured through the
:ref:`decimal_accuracy` screen.

Configuration
==============

.. _getting_started_configuration-link:

Two configuration files are available:

    * one for the client: ``~/.openerprc``
    * one for the server: ``~/.openerp_serverrc``

If they are not found, the server and the client will start with a
default configuration. Those files follow the convention used by
python's ConfigParser module. Please note that lines beginning with
"#" or ";" are comments. The client configuration file is
automatically generated upon the first start. The sezrver
configuration file can automatically be created using the command ::

  ./openerp-server -s or ./openerp-server --save

You can specify alternate configuration files with ::

  -c CONFIG, --config=CONFIG specify alternate config file

Configure addons locations
++++++++++++++++++++++++++

By default, the only directory of addons known by the server is
server/bin/addons. It is possible to add new addons by

 - copying them in server/bin/addons, or creating a symbolic link to
   each of them in this directory, or
 - specifying another directory containing addons to the server. The
   later can be accomplished either by running the server with the
   ``--addons-path=`` option, or by configuring this option in the
   openerp_serverrc file, automatically generated under Linux in your
   home directory by the server when executed with the ``--save``
   option. You can provide several addons to the ``addons_path`` =
   option, separating them using commas.

Start-up script
===============

.. versionadded:: 6.1

To run the OpenERP server, the conventional approach is to use the
`openerp-server` script.  It loads the :ref:`openerp library`, sets a
few configuration variables corresponding to command-line arguments,
and starts to listen to incoming connections from clients.

Depending on your deployment needs, you can write such a start-up script very
easily. We also recommend you take a look at an alternative tool called
`openerp-command` that can, among other things, launch the server.

Yet another alternative is to use a WSGI-compatible HTTP server and let it call
into one of the WSGI entry points of the server.


