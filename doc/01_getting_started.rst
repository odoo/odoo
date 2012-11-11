========================================
Getting started with OpenERP development
========================================

.. toctree::
   :maxdepth: 1

Installation from sources
==========================

.. _getting_started_installation_source-link:

Source code is hosted on Launchpad_. In order to get the sources, you will need Bazaar_ to pull the source from Launchpad. Bazaar is a version control system that helps you track project history over time and collaborate efficiently. You may have to create an account on Launchpad to be able to collaborate on OpenERP development. Please refer to the Launchpad and Bazaar documentation to install and setup your development environment.

The running example of this section is based on an Ubuntu environment. You may have to adapt the steps according to your system. Once your working environment is ready, prepare a working directory that will contain the sources.  For a ``source`` base directory, type::

  mkdir source;cd source

OpenERP provides a setup script that automatizes the tasks of creating a shared repository and getting the source code. Get the setup script of OpenERP by typing::

  bzr cat -d lp:~openerp-dev/openerp-tools/trunk setup.sh | sh

This will create the following two files in your ``source`` directory::

  -rw-rw-r--  1 openerp openerp 5465 2012-04-17 11:05 Makefile
  -rw-rw-r--  1 openerp openerp 2902 2012-04-17 11:05 Makefile_helper.py

If you want some help about the available options, please type::

  make help

Next step is to initialize the shared repository and download the sources. Get the current trunk version of OpenERP by typing::

  make init-trunk

This will create the following structure inside your ``source`` directory, and fetch the latest source code from ``trunk``::

  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 addons
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 misc
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 server
  drwxrwxr-x  3 openerp openerp 4096 2012-04-17 11:10 web

Some dependencies are necessary to use OpenERP. Depending on your environment, you might have to install the following packages::

  sudo apt-get install graphviz ghostscript postgresql-client
 
  sudo apt-get install python-dateutil python-feedparser python-gdata
    python-ldap python-libxslt1 python-lxml python-mako, python-openid
    python-psycopg2 python-pybabel python-pychart python-pydot
    python-pyparsing python-reportlab python-simplejson python-tz
    python-vatnumber python-vobject python-webdav python-werkzeug python-xlwt
    python-yaml python-imaging python-matplotlib 

Next step is to initialize the database. This will create a new openerp role::

  make db-setup

Finally, launch the OpenERP server::

  make server

Testing your installation can be done on http://localhost:8069/ . You should see the OpenERP main login page.

.. _Launchpad: https://launchpad.net/
.. _Bazaar: http://bazaar.canonical.com/en/

Command line options
====================

Using the command ::

  ./openerp-server --help

gives you the available command line options. For OpenERP server at revision 4133, an output example is given in the `Command line options example`_. Here are a few interesting command line options.

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

Use these options to translate OpenERP to another language.See i18n section of the user manual. Option '-l' is mandatory.::
 
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

Some options were removed in OpenERP version 6. For example, ``price_accuracy`` is now
configured through the :ref:`decimal_accuracy` screen.

Configuration
==============

.. _getting_started_configuration-link:

Two configuration files are available:

    * one for the client: ``~/.openerprc``
    * one for the server: ``~/.openerp_serverrc``

If they are not found, the server and the client will start with a default configuration. Those files follow the convention used by python's ConfigParser module. Please note that lines beginning with "#" or ";" are comments. The client configuration file is automatically generated upon the first start. The sezrver configuration file can automatically be created using the command ::

  ./openerp-server -s or ./openerp-server --save

You can specify alternate configuration files with ::

  -c CONFIG, --config=CONFIG specify alternate config file

Start-up script
===============

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


Appendix
========

Command line options example
++++++++++++++++++++++++++++

Usage: openerp-server [options]

**Options**::

  --version             show program's version number and exit
  -h, --help            show this help message and exit

**Common options**::

    -c CONFIG, --config=CONFIG
                        specify alternate config file
    -s, --save          save configuration to ~/.openerp_serverrc
    -i INIT, --init=INIT
                        install one or more modules (comma-separated list, use
                        "all" for all modules), requires -d
    -u UPDATE, --update=UPDATE
                        update one or more modules (comma-separated list, use
                        "all" for all modules). Requires -d.
    --without-demo=WITHOUT_DEMO
                        disable loading demo data for modules to be installed
                        (comma-separated, use "all" for all modules). Requires
                        -d and -i. Default is none
    -P IMPORT_PARTIAL, --import-partial=IMPORT_PARTIAL
                        Use this for big data importation, if it crashes you
                        will be able to continue at the current state. Provide
                        a filename to store intermediate importation states.
    --pidfile=PIDFILE   file where the server pid will be stored
    --addons-path=ADDONS_PATH
                        specify additional addons paths (separated by commas).
    --load=SERVER_WIDE_MODULES
                        Comma-separated list of server-wide modules
                        default=web

**XML-RPC Configuration**::

    --xmlrpc-interface=XMLRPC_INTERFACE
                        Specify the TCP IP address for the XML-RPC protocol.
                        The empty string binds to all interfaces.
    --xmlrpc-port=XMLRPC_PORT
                        specify the TCP port for the XML-RPC protocol
    --no-xmlrpc         disable the XML-RPC protocol
    --proxy-mode        Enable correct behavior when behind a reverse proxy

**XML-RPC Secure Configuration**::

    --xmlrpcs-interface=XMLRPCS_INTERFACE
                        Specify the TCP IP address for the XML-RPC Secure
                        protocol. The empty string binds to all interfaces.
    --xmlrpcs-port=XMLRPCS_PORT
                        specify the TCP port for the XML-RPC Secure protocol
    --no-xmlrpcs        disable the XML-RPC Secure protocol
    --cert-file=SECURE_CERT_FILE
                        specify the certificate file for the SSL connection
    --pkey-file=SECURE_PKEY_FILE
                        specify the private key file for the SSL connection

**NET-RPC Configuration**::

    --netrpc-interface=NETRPC_INTERFACE
                        specify the TCP IP address for the NETRPC protocol
    --netrpc-port=NETRPC_PORT
                        specify the TCP port for the NETRPC protocol
    --no-netrpc         disable the NETRPC protocol

**Web interface Configuration**::

    --db-filter=REGEXP  Filter listed database

**Static HTTP service**::

    --static-http-enable
                        enable static HTTP service for serving plain HTML
                        files
    --static-http-document-root=STATIC_HTTP_DOCUMENT_ROOT
                        specify the directory containing your static HTML
                        files (e.g '/var/www/')
    --static-http-url-prefix=STATIC_HTTP_URL_PREFIX
                        specify the URL root prefix where you want web
                        browsers to access your static HTML files (e.g '/')

**Testing Configuration**::

    --test-file=TEST_FILE
                        Launch a YML test file.
    --test-report-directory=TEST_REPORT_DIRECTORY
                        If set, will save sample of all reports in this
                        directory.
    --test-enable       Enable YAML and unit tests.
    --test-commit       Commit database changes performed by YAML or XML
                        tests.

**Logging Configuration**::

    --logfile=LOGFILE   file where the server log will be stored
    --no-logrotate      do not rotate the logfile
    --syslog            Send the log to the syslog server
    --log-handler=PREFIX:LEVEL
                        setup a handler at LEVEL for a given PREFIX. An empty
                        PREFIX indicates the root logger. This option can be
                        repeated. Example: "openerp.orm:DEBUG" or
                        "werkzeug:CRITICAL" (default: ":INFO")
    --log-request       shortcut for --log-
                        handler=openerp.netsvc.rpc.request:DEBUG
    --log-response      shortcut for --log-
                        handler=openerp.netsvc.rpc.response:DEBUG
    --log-web           shortcut for --log-
                        handler=openerp.addons.web.common.http:DEBUG
    --log-sql           shortcut for --log-handler=openerp.sql_db:DEBUG
    --log-level=LOG_LEVEL
                        specify the level of the logging. Accepted values:
                        ['info', 'debug_rpc', 'warn', 'test', 'critical',
                        'debug_sql', 'error', 'debug', 'debug_rpc_answer',
                        'notset'] (deprecated option).

**SMTP Configuration**::

    --email-from=EMAIL_FROM
                        specify the SMTP email address for sending email
    --smtp=SMTP_SERVER  specify the SMTP server for sending email
    --smtp-port=SMTP_PORT
                        specify the SMTP port
    --smtp-ssl          specify the SMTP server support SSL or not
    --smtp-user=SMTP_USER
                        specify the SMTP username for sending email
    --smtp-password=SMTP_PASSWORD
                        specify the SMTP password for sending email

**Database related options**::

    -d DB_NAME, --database=DB_NAME
                        specify the database name
    -r DB_USER, --db_user=DB_USER
                        specify the database user name
    -w DB_PASSWORD, --db_password=DB_PASSWORD
                        specify the database password
    --pg_path=PG_PATH   specify the pg executable path
    --db_host=DB_HOST   specify the database host
    --db_port=DB_PORT   specify the database port
    --db_maxconn=DB_MAXCONN
                        specify the the maximum number of physical connections
                        to posgresql
    --db-template=DB_TEMPLATE
                        specify a custom database template to create a new
                        database

**Internationalisation options**::

    Use these options to translate OpenERP to another language.See i18n
    section of the user manual. Option '-d' is mandatory.Option '-l' is
    mandatory in case of importation

    --load-language=LOAD_LANGUAGE
                        specifies the languages for the translations you want
                        to be loaded
    -l LANGUAGE, --language=LANGUAGE
                        specify the language of the translation file. Use it
                        with --i18n-export or --i18n-import
    --i18n-export=TRANSLATE_OUT
                        export all sentences to be translated to a CSV file, a
                        PO file or a TGZ archive and exit
    --i18n-import=TRANSLATE_IN
                        import a CSV or a PO file with translations and exit.
                        The '-l' option is required.
    --i18n-overwrite    overwrites existing translation terms on updating a
                        module or importing a CSV or a PO file.
    --modules=TRANSLATE_MODULES
                        specify modules to export. Use in combination with
                        --i18n-export

**Security-related options**::

    --no-database-list  disable the ability to return the list of databases

**Advanced options**::

    --cache-timeout=CACHE_TIMEOUT
                        set the timeout for the cache system
    --debug             enable debug mode
    --stop-after-init   stop the server after its initialization
    -t TIMEZONE, --timezone=TIMEZONE
                        specify reference timezone for the server (e.g.
                        Europe/Brussels
    --osv-memory-count-limit=OSV_MEMORY_COUNT_LIMIT
                        Force a limit on the maximum number of records kept in
                        the virtual osv_memory tables. The default is False,
                        which means no count-based limit.
    --osv-memory-age-limit=OSV_MEMORY_AGE_LIMIT
                        Force a limit on the maximum age of records kept in
                        the virtual osv_memory tables. This is a decimal value
                        expressed in hours, and the default is 1 hour.
    --max-cron-threads=MAX_CRON_THREADS
                        Maximum number of threads processing concurrently cron
                        jobs.
    --virtual-memory-limit=VIRTUAL_MEMORY_LIMIT
                        Maximum allowed virtual memory per Gunicorn process.
                        When the limit is reached, any memory allocation will
                        fail.
    --virtual-memory-reset=VIRTUAL_MEMORY_RESET
                        Maximum allowed virtual memory per Gunicorn process.
                        When the limit is reached, the worker will be reset
                        after the current request.
    --cpu-time-limit=CPU_TIME_LIMIT
                        Maximum allowed CPU time per Gunicorn process. When
                        the limit is reached, an exception is raised.
    --unaccent          Use the unaccent function provided by the database
                        when available.

Server configuration file
+++++++++++++++++++++++++

::

  [options]
  addons_path = /home/openerp/workspace/openerp-dev/addons/trunk,/home/openerp/workspace/openerp-dev/web/trunk/addons
  admin_passwd = admin
  cache_timeout = 100000
  cpu_time_limit = 60
  csv_internal_sep = ,
  db_host = False
  db_maxconn = 64
  db_name = False
  db_password = False
  db_port = False
  db_template = template0
  db_user = openerp
  dbfilter = .*
  debug_mode = False
  demo = {}
  email_from = False
  import_partial = 
  list_db = True
  log_handler = [':INFO']
  log_level = info
  logfile = False
  login_message = False
  logrotate = True
  max_cron_threads = 4
  netrpc = True
  netrpc_interface = 
  netrpc_port = 8070
  osv_memory_age_limit = 1.0
  osv_memory_count_limit = False
  pg_path = None
  pidfile = False
  proxy_mode = False
  reportgz = False
  secure_cert_file = server.cert
  secure_pkey_file = server.pkey
  server_wide_modules = None
  smtp_password = False
  smtp_port = 25
  smtp_server = localhost
  smtp_ssl = False
  smtp_user = False
  static_http_document_root = None
  static_http_enable = False
  static_http_url_prefix = None
  syslog = False
  test_commit = False
  test_enable = False
  test_file = False
  test_report_directory = False
  timezone = False
  translate_modules = ['all']
  unaccent = False
  virtual_memory_limit = 805306368
  virtual_memory_reset = 671088640
  without_demo = False
  xmlrpc = True
  xmlrpc_interface = 
  xmlrpc_port = 8069
  xmlrpcs = True
  xmlrpcs_interface = 
  xmlrpcs_port = 8071
