:banner: banners/cmdline.jpg

.. _reference/cmdline:

===============================
Command-line interface: odoo.py
===============================

.. _reference/cmdline/server:

Running the server
==================

.. program:: odoo.py

.. option:: -d <database>, --database <database>

    database used when installing or updating modules.

.. option:: -i <modules>, --init <modules>

    comma-separated list of modules to install before running the server
    (requires :option:`-d`).

.. option:: -u <modules>, --update <modules>

    comma-separated list of modules to update before running the server
    (requires :option:`-d`).

.. option:: --addons-path <directories>

    comma-separated list of directories in which modules are stored. These
    directories are scanned for modules (nb: when and why?)

.. option:: --workers <count>

    if ``count`` is not 0 (the default), enables multiprocessing and sets up
    the specified number of HTTP workers (sub-processes processing HTTP
    and RPC requests).

    .. note:: multiprocessing mode is only available on Unix-based systems

    A number of options allow limiting and recyling workers:

    .. option:: --limit-request <limit>

        Number of requests a worker will process before being recycled and
        restarted.

        Defaults to 8196.

    .. option:: --limit-memory-soft <limit>

        Maximum allowed virtual memory per worker. If the limit is exceeded,
        the worker is killed and recycled at the end of the current request.

        Defaults to 640MB.

    .. option:: --limit-memory-hard <limit>

        Hard limit on virtual memory, any worker exceeding the limit will be
        immediately killed without waiting for the end of the current request
        processing.

        Defaults to 768MB.

    .. option:: --limit-time-cpu <limit>

        Prevents the worker from using more than <limit> CPU seconds for each
        request. If the limit is exceeded, the worker is killed.

        Defaults to 60.

    .. option:: --limit-time-real <limit>

        Prevents the worker from taking longer than <limit> seconds to process
        a request. If the limit is exceeded, the worker is killed.

        Differs from :option:`--limit-time-cpu` in that this is a "wall time"
        limit including e.g. SQL queries.

        Defaults to 120.

.. option:: --max-cron-threads <count>

    number of workers dedicated to cron jobs. Defaults to 2. The workers are
    threads in multithreading mode and processes in multiprocessing mode.

    For multiprocessing mode, this is in addition to the HTTP worker
    processes.

.. option:: -c <config>, --config <config>

    provide an alternate configuration file

.. option:: -s, --save

    saves the server configuration to the current configuration file
    (:file:`{$HOME}/.openerp_serverrc` by default, overridable using
    :option:`-c`)

.. option:: --proxy-mode

    enables the use of ``X-Forwarded-*`` headers through `Werkzeug's proxy
    support`_.

    .. warning:: proxy mode *must not* be enabled outside of a reverse proxy
                 scenario

.. option:: --test-enable

    runs tests after installing modules

.. option:: --debug

    when an unexpected error is raised (not a warning or an access error),
    automatically starts :mod:`python:pdb` before logging and returning the
    error

.. _reference/cmdline/server/database:

database
--------

.. option:: -r <user>, --db_user <user>

    database username, used to connect to PostgreSQL.

.. option:: -w <password>, --db_password <password>

    database password, if using `password authentication`_.

.. option:: --db_host <hostname>

    host for the database server

    * ``localhost`` on Windows
    * UNIX socket otherwise

.. option:: --db_port <port>

    port the database listens on, defaults to 5432

.. option:: --db-filter <filter>

    hides databases that do not match ``<filter>``. The filter is a
    `regular expression`_, with the additions that:

    - ``%h`` is replaced by the whole hostname the request is made on.
    - ``%d`` is replaced by the subdomain the request is made on, with the
      exception of ``www`` (so domain ``odoo.com`` and ``www.odoo.com`` both
      match the database ``odoo``)

.. option:: --db-template <template>

    when creating new databases from the database-management screens, use the
    specified `template database`_. Defaults to ``template1``.

built-in HTTP
-------------

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

logging
-------

By default, Odoo displays all logging of level_ ``info`` except for workflow
logging (``warning`` only), and log output is sent to ``stdout``. Various
options are available to redirect logging to other destinations and to
customize the amout of logging output

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

    enable DEBUG logging for RPC requests, equivalent to
    ``--log-handler=openerp.http.rpc.request:DEBUG``

.. option:: --log-response

    enable DEBUG logging for RPC responses, equivalent to
    ``--log-handler=openerp.http.rpc.response:DEBUG``

.. option:: --log-web

    enables DEBUG logging of HTTP requests and responses, equivalent to
    ``--log-handler=openerp.http:DEBUG``

.. option:: --log-sql

    enables DEBUG logging of SQL querying, equivalent to
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

Advanced options
----------------

.. option:: --auto-reload

    enable auto-reloading of python files and xml files without having to
    restart the server. Requires pyinotify_.

.. _reference/cmdline/scaffold:

Scaffolding
===========

.. program:: odoo.py scaffold

Scaffolding is the automated creation of a skeleton structure to simplify
bootstrapping (of new modules, in the case of Odoo). While not necessary it
avoids the tedium of setting up basic structures and looking up what all
starting requirements are.

Scaffolding is available via the :command:`odoo.py scaffold` subcommand.

.. option:: -t <template>

    a template directory, files are passed through jinja2_ then copied to
    the ``destination`` directory

.. option:: name

    the name of the module to create, may munged in various manners to
    generate programmatic names (e.g. module directory name, model names, …)

.. option:: destination

    directory in which to create the new module, defaults to the current
    directory

.. _reference/cmdline/config:

Configuration file
==================

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

The default configuration file is :file:`{$HOME}/.openerp_serverrc` which
can be overridden using :option:`--config <odoo.py -c>`. Specifying
:option:`--save <odoo.py -s>` will save the current configuration state back
to that file.

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
