:banner: banners/cmdline.jpg

.. _reference/cmdline:

===============================
Command-line interface: odoo.py
===============================

.. _reference/cmdline/env:

Installing Development Environment
==================================

    .. note:: This section applies to those developing within
              a linux environment.

One option for bootstrapping an Odoo 9 development environment goes as follows:
    .. code-block:: console

        $ wget -O- https://raw.githubusercontent.com/odoo/odoo/9.0/odoo.py | python


The preceding command will download the Odoo 9 branch, via wget; configure git,
such as finding the appropriate remotes; and setup Odoo's dependencies, including Postgres.


.. _reference/cmdline/scaffold:

Creating a Module Skeleton
==========================

.. program:: odoo.py scaffold

The scaffolding command helps developers simplify the process of creating
new modules. It does so by generating the appropriate files and file structure
needed by even the most basic of Odoo modules.

    .. note:: If you have experience with Django and it's "django-admin startproject"
              command, or even general Python experience, creating a module skeleton
              should be familiar to you.

Scaffolding is available via the :command:`odoo.py scaffold` subcommand.

    .. option:: -t <template>

        Specifies a template directory, which is passed through jinja2_ and then copied
        to the ``destination`` directory.

    .. option:: name

        Specifies the name of the module to be created. It may be munged in various
        manners to generate programmatic names (e.g. module directory name, model names, …)

    .. option:: destination

        Specifies the directory in which to create the new module.

        Defaults to the current directory.


.. _reference/cmdline/server:

Running the server from the Command-line
========================================

.. program:: odoo.py

The server may be ran from the command-line, via `odoo.py`, which takes the
options listed below.

configuration files
-------------------

    .. option:: -c <config>, --config <config>

        Specifies an alternate configuration file and its path.

    Defaults to :file:`{$HOME}/.openerp_serverrc`

    .. option:: -s, --save

        saves the server configuration to the current configuration file
        (:file:`{$HOME}/.openerp_serverrc` by default, and can be overridden using
        :option:`-c`)


Most of the command-line options can also be specified via a configuration
file. Most of the time, they use similar names with the prefix ``-`` removed
and other ``-`` are replaced by ``_`` e.g. :option:`--db-template` becomes
``db_template``.

Some conversions don't match the pattern:

* :option:`--db-filter` becomes ``dbfilter``
* :option:`--no-xmlrpc` corresponds to the ``xmlrpc`` boolean
* logging presets (all options starting with ``--log-`` except for
  :option:`--log-handler` and :option:`--log-db`) just add content to
  ``log_handler``, use that directly in the configuration file
* :option:`--smtp` is stored as ``smtp_server``
* :option:`--database` is stored as ``db_name``
* :option:`--debug` is stored as ``debug_mode`` (a boolean)
* :option:`--i18n-import` and :option:`--i18n-export` aren't available at all
  from configuration files


databases
---------

    .. option:: -d <database>, --database <database>

        Specifies the database to be used when installing or updating modules.

    .. option:: -r <user>, --db_user <user>

        Specifies the database username used to connect to PostgreSQL.

    .. option:: -w <password>, --db_password <password>

        Specifies the database password, if using `password authentication`_.

    .. option:: --db_host <hostname>

        Specifies the host for the database server.

        * ``localhost`` on Windows
        * UNIX socket otherwise

    .. option:: --db_port <port>

        Specifies the port that the database listens on, defaults to 5432

    .. option:: --db-filter <filter>

        Hides databases that do not match ``<filter>``. The filter is a
        `regular expression`_, with the additions that:

        - ``%h`` is replaced by the whole hostname the request is made on.
        - ``%d`` is replaced by the subdomain the request is made on, with the
          exception of ``www`` (so domain ``odoo.com`` and ``www.odoo.com`` both
          match the database ``odoo``)

    .. option:: --db-template <template>

        Specifies the database template to be used when creating new databases
        from the database-management screens, use the specified `template database`_.

        Defaults to ``template1``.

    .. option:: --import-partial <filename>

        Similar to a PID... Import-partial is used for big data importation.
        Intermediate importation states are passed to <filename>, which is used


developer options
-----------------

    .. option:: --dev <feature,feature,...,feature>

        * ``all``: all the features below are activated

        * ``xml``: read template qweb from xml file directly instead of database.
          Once a template has been modified in database, it will be not be read from
          the xml file until the next update/init.

        * ``reload``: restart server when python file are updated (may not be detected
          depending on the text editor used)

        * ``qweb``: break in the evaluation of qweb template when a node contains ``t-debug='debugger'``

        * ``(i)p(u)db``: start the chosen python debugger in the code when an
          unexpected error is raised before logging and returning the error.


HTTP and long-polling
---------------------

    .. option:: --no-xmlrpc

        do not start the HTTP or long-polling workers (may still start cron
        workers)

    .. warning:: has no effect if :option:`--test-enable` is set, as tests
                 require an accessible HTTP server

    .. option:: --xmlrpc-interface <interface>

        TCP/IP address on which the HTTP server listens, defaults to ``0.0.0.0``
        (all addresses)

    .. option:: --xmlrpc-port <port>

        Port on which the HTTP server listens, defaults to 8069.

    .. option:: --longpolling-port <port>

        TCP port for long-polling connections in multiprocessing or gevent mode,
        defaults to 8072. Not used in default (threaded) mode.

    .. option:: --proxy-mode

        enables the use of ``X-Forwarded-*`` headers through `Werkzeug's proxy support`_.

    .. warning:: Proxy mode *must not* be enabled outside of a reverse proxy
                 scenario

logging
-------

By default, Odoo displays all logging of level_ ``info`` except for workflow
logging (``warning`` only), and log output is sent to ``stdout``. Various
options are available to redirect logging to other destinations and to
customize the amount of logging output

    .. option:: --logfile <file>

        sends logging output to the specified file instead of stdout. On Unix, the
        file `can be managed by external log rotation programs
        <https://docs.python.org/2/library/logging.handlers.html#watchedfilehandler>`_
        and will automatically be reopened when replaced

    .. option:: --logrotate

        enables `log rotation <https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler>`_
        daily, keeping 30 backups. Log rotation frequency and number of backups is
        not configurable.

    .. option:: --syslog

        logs to the system's event logger: `syslog on unices <https://docs.python.org/2/library/logging.handlers.html#sysloghandler>`_
        and `the Event Log on Windows <https://docs.python.org/2/library/logging.handlers.html#nteventloghandler>`_.

        Neither is configurable

    .. option:: --log-db <dbname>

        logs to the ``ir.logging`` model (``ir_logging`` table) of the specified
        database. The database can be the name of a database in the "current"
        PostgreSQL, or `a PostgreSQL URI`_ for e.g. log aggregation

    .. option:: --log-handler <handler-spec>

        :samp:`{LOGGER}:{LEVEL}`, enables ``LOGGER`` at the provided ``LEVEL``
        e.g. ``openerp.models:DEBUG`` will enable all logging messages at or above
        ``DEBUG`` level in the models.

        * The colon ``:`` is mandatory
        * The logger can be omitted to configure the root (default) handler
        * If the level is omitted, the logger is set to ``INFO``

        The option can be repeated to configure multiple loggers e.g.

    .. code-block:: console

        $ odoo.py --log-handler :DEBUG --log-handler werkzeug:CRITICAL --log-handler openerp.fields:WARNING

    .. option:: --log-request

        Enables DEBUG logging for RPC requests, equivalent to
        ``--log-handler=openerp.http.rpc.request:DEBUG``

    .. option:: --log-response

        enable DEBUG logging for RPC responses, equivalent to
        ``--log-handler=openerp.http.rpc.response:DEBUG``

    .. option:: --log-web

        Enables DEBUG logging of HTTP requests and responses, equivalent to
        ``--log-handler=openerp.http:DEBUG``

    .. option:: --log-sql

        Enables DEBUG logging of SQL querying, equivalent to
        ``--log-handler=openerp.sql_db:DEBUG``

    .. option:: --log-level <level>

        Shortcut to more easily set predefined levels on specific loggers. "real"
        levels (``critical``, ``error``, ``warn``, ``debug``) are set on the
        ``openerp`` and ``werkzeug`` loggers (except for ``debug`` which is only
        set on ``openerp``).

        Odoo also provides debugging pseudo-levels which apply to different sets
        of loggers:

        ``debug_sql``
            sets the SQL logger to ``debug``

            equivalent to ``--log-sql``

        ``debug_rpc``
            sets the ``openerp`` and HTTP request loggers to ``debug``

            equivalent to ``--log-level debug --log-request``

        ``debug_rpc_answer``
            sets the ``openerp`` and HTTP request and response loggers to
            ``debug``

        equivalent to ``--log-level debug --log-request --log-response``

    .. note::

        In case of conflict between :option:`--log-level` and
        :option:`--log-handler`, the latter is used


modules
-------

    .. option:: --load <modules>

        A comma-separated list of server-wide modules.

    .. option:: -i <modules>, --init <modules>

        A comma-separated list of modules to be installed before running the server.
        (requires :option:`-d`).

    .. option:: -u <modules>, --update <modules>

        A comma-separated list of modules to updated before running the server
        (requires :option:`-d`).

    .. option:: --addons-path <directories>

        A comma-separated list of directories to be scanned for modules.

    .. option:: --test-enable

        Runs tests after installing modules

    .. option:: --without-demo

        Disables loading demo data for a comma-separated list modules to be installed.
        Use "all" for all modules.

        Requires options :option:`-d` and :option:`-i`


multi-processing
----------------

    .. danger:: Multiprocessing mode is only available on Unix-based systems


    .. option:: --workers <count>

        Specifies the number of HTTP workers to be used for processing HTTP and
        RPC requests. Can be set as high as [ number of cores ] + 1 on Unix-based
        systems, where multi-processing is supported.

        Defaults to 0 to accommodate Windows, where multi-processing
        is not currently supported.

        A number of options allow limiting and recycling workers:

    .. option:: --limit-request <limit>

        Specifies number of HTTP and RPC requests to be processed by each worker,
        before being recycled and restarted.

        Defaults to 8196 requests.

    .. option:: --limit-memory-soft <limit>

        Specifies a *soft limit* on amount of RAM allotted to each worker. If a
        particular worker should exceed this limit, that worker is killed and
        recycled, **but** not until the *end of the current request*.

        Defaults to 640MB.

    .. option:: --limit-memory-hard <limit>

        Specifies a *hard limit* on the amount of RAM allocated to each worker.
        If a particular worker should exceed this limit, that worker will be
        killed **immediately**, *before the end* of the current request being
        processed.

        Defaults to 768MB.

    .. option:: --limit-time-cpu <limit>

        Specifies the amount of *CPU time*, or time spent by *the CPU* on any
        given worker's request, before that worker and it's request are killed.

        See `--limit-time-real`, because it is not measured as seconds on a
        wall clock ("wall time"): it is not concerned with the time a worker
        spends in queue.

        Defaults to 60.

    .. option:: --limit-time-real <limit>

        Specifies the number of *seconds* given to workers to process
        a request. If the limit is exceeded, that worker is killed.

        Differs from :option:`--limit-time-cpu` in that this is a "wall time"
        limit including e.g. SQL queries.

        Defaults to 120 seconds.

    .. option:: --max-cron-threads <count>

        Specifies the number of workers to be dedicated to cron jobs.

        * If in multi-threading mode (`--workers 0`), these workers are threads.
        * If in multi-processing mode (`--workers` >= 1), these workers are
          processes

        * For multi-processing mode, this is in addition to the HTTP worker
          processes.

        Defaults to 2 workers.


.. _reference/cmdline/config:

Configuration file
==================

The default configuration file is :file:`{$HOME}/.openerp_serverrc` which
can be overridden using :option:`--config <odoo.py -c>`. Specifying
:option:`--save <odoo.py -s>` will save the current configuration state back
to that file.

    .. option:: addons_path

    .. option:: admin_passwd

    .. option:: csv_internal_sep

    .. option:: data_dir

    .. option:: db_host

    .. option:: db_maxconn

    .. option:: db_name

    .. option:: db_password

    .. option:: db_port

    .. option:: db_template

    .. option:: db_user

    .. option:: db_filter

    .. option:: debug_mode

    .. option:: demo

    .. option:: dev_mode

    .. option:: email_from

    .. option:: geoip_database

    .. option:: import_partial

    .. option:: limit_memory_hard

    .. option:: limit_memory_soft

    .. option:: limit_request

    .. option:: limit_time_cpu

    .. option:: limit_time_real

    .. option:: limit_time_real_cron

    .. option:: list_db

    .. option:: log_db

    .. option:: log_handler

    .. option:: log_level

    .. option:: logfile

    .. option:: logrotate

    .. option:: longpolling_port

    .. option:: max_cron_thread

    .. option:: osv_memory_age_limit

    .. option:: osv_memory_count_limit

    .. option:: pg_path

    .. option:: pidfile

    .. option:: proxy_mode

    .. option:: reportgz

    .. option:: server_wide_modules

    .. option:: smtp_password

    .. option:: smtp_port

    .. option:: smtp_server

    .. option:: smtp_ssl

    .. option:: smtp_user

    .. option:: syslog

    .. option:: test_commit

    .. option:: test_enable

    .. option:: test_file

    .. option:: test_report_directory

    .. option:: translate_modules

    .. option:: unaccent

    .. option:: without_demo

    .. option:: workers

    .. option:: xmlrpc

    .. option:: xmlrpc_interface

    .. option:: xmlrpc_port


.. _jinja2: http://jinja.pocoo.org
.. _regular expression: https://docs.python.org/2/library/re.html
.. _password authentication:
    http://www.postgresql.org/docs/9.3/static/auth-methods.html#AUTH-PASSWORD
.. _template database:
    http://www.postgresql.org/docs/9.3/static/manage-ag-templatedbs.html
.. _level:
    https://docs.python.org/2/library/logging.html#logging.Logger.setLevel
.. _a PostgreSQL URI:
    http://www.postgresql.org/docs/9.2/static/libpq-connect.html#AEN38208
.. _Werkzeug's proxy support:
    http://werkzeug.pocoo.org/docs/0.9/contrib/fixers/#werkzeug.contrib.fixers.ProxyFix
.. _pyinotify: https://github.com/seb-m/pyinotify/wiki
