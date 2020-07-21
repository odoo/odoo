:banner: banners/cmdline.jpg

.. _reference/cmdline:

================================
Command-line interface: odoo-bin
================================

.. _reference/cmdline/server:

Running the server
==================

.. program:: odoo-bin

.. option:: -d <database>, --database <database>

    database(s) used when installing or updating modules.
    Providing a comma-separated list restrict access to databases provided in
    list.

    For advanced database options, take a look :ref:`below <reference/cmdline/server/database>`.

.. option:: -i <modules>, --init <modules>

    comma-separated list of modules to install before running the server
    (requires :option:`-d`).

.. option:: -u <modules>, --update <modules>

    comma-separated list of modules to update before running the server
    (requires :option:`-d`).

.. option:: --addons-path <directories>

    comma-separated list of directories in which modules are stored. These
    directories are scanned for modules.

    .. (nb: when and why?)

.. option:: -c <config>, --config <config>

    provide an alternate :ref:`configuration file <reference/cmdline/config>`

.. option:: -s, --save

    saves the server configuration to the current configuration file
    (:file:`{$HOME}/.odoorc` by default, and can be overridden using
    :option:`-c`).

.. option:: --without-demo

    disables demo data loading for modules installed
    comma-separated, use ``all`` for all modules.

.. option:: --test-enable

    runs tests after installing modules

.. option:: --test-tags 'tag_1,tag_2,...,-tag_n'

    select the tests to run by using tags.

.. option:: --screenshots

    Specify directory where to write screenshots when an HttpCase.browser_js test
    fails. It defaults to :file:`/tmp/odoo_tests/{db_name}/screenshots`

.. option:: --screencasts

    Enable screencasts and specify directory where to write screencasts files.
    The ``ffmpeg`` utility needs to be installed to encode frames into a video
    file. Otherwise frames will be kept instead of the video file.

.. _reference/cmdline/server/database:

Database
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
      match the database ``odoo``).

      These operations are case sensitive. Add option ``(?i)`` to match all
      databases (so domain ``odoo.com`` using ``(?i)%d`` matches the database
      ``Odoo``).

    Since version 11, it's also possible to restrict access to a given database
    listen by using the --database parameter and specifying a comma-separated
    list of databases

    When combining the two parameters, db-filter supersedes the comma-separated
    database list for restricting database list, while the comma-separated list
    is used for performing requested operations like upgrade of modules.

    .. code-block:: bash

        $ odoo-bin --db-filter ^11.*$

    Restrict access to databases whose name starts with 11

    .. code-block:: bash

        $ odoo-bin --database 11firstdatabase,11seconddatabase

    Restrict access to only two databases, 11firstdatabase and 11seconddatabase

    .. code-block:: bash

        $ odoo-bin --database 11firstdatabase,11seconddatabase -u base

    Restrict access to only two databases, 11firstdatabase and 11seconddatabase,
    and update base module on one database: 11firstdatabase.
    If database 11seconddatabase doesn't exist, the database is created and base modules
    is installed

    .. code-block:: bash

        $ odoo-bin --db-filter ^11.*$ --database 11firstdatabase,11seconddatabase -u base

    Restrict access to databases whose name starts with 11,
    and update base module on one database: 11firstdatabase.
    If database 11seconddatabase doesn't exist, the database is created and base modules
    is installed

.. option:: --db-template <template>

    when creating new databases from the database-management screens, use the
    specified `template database`_. Defaults to ``template0``.

.. option:: --pg_path </path/to/postgresql/binaries>

    Path to the PostgreSQL binaries that are used by the database manager to
    dump and restore databases. You have to specify this option only if these
    binaries are located in a non-standard directory.

.. option:: --no-database-list

    Suppresses the ability to list databases available on the system

.. option:: --db_sslmode

    Control the SSL security of the connection between Odoo and PostgreSQL.
    Value should bve one of 'disable', 'allow', 'prefer', 'require',
    'verify-ca' or 'verify-full'
    Default value is 'prefer'

.. _reference/cmdline/server/emails:

Emails
------

.. option:: --email-from <address>

    Email address used as <FROM> when Odoo needs to send mails

.. option:: --smtp <server>

    Address of the SMTP server to connect to in order to send mails

.. option:: --smtp-port <port>

.. option:: --smtp-ssl

    If set, odoo should use SSL/STARTSSL SMTP connections

.. option:: --smtp-user <name>

    Username to connect to the SMTP server

.. option:: --smtp-password <password>

    Password to connect to the SMTP server

.. _reference/cmdline/server/internationalisation:

Internationalisation
--------------------

Use these options to translate Odoo to another language. See i18n section of
the user manual. Option '-d' is mandatory. Option '-l' is mandatory in case
of importation

.. option:: --load-language <languages>

    specifies the languages (separated by commas) for the translations you
    want to be loaded

.. option:: -l, --language <language>

    specify the language of the translation file. Use it with --i18n-export
    or --i18n-import

.. option:: --i18n-export <filename>

    export all sentences to be translated to a CSV file, a PO file or a TGZ
    archive and exit.

.. option:: --i18n-import <filename>

    import a CSV or a PO file with translations and exit. The '-l' option is
    required.

.. option:: --i18n-overwrite

    overwrites existing translation terms on updating a module or importing
    a CSV or a PO file.

.. option:: --modules

    specify modules to export. Use in combination with --i18n-export

.. _reference/cmdline/advanced:

Advanced Options
----------------

.. _reference/cmdline/dev:

Developer features
''''''''''''''''''

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


.. _reference/cmdline/server/http:

HTTP
''''

.. option:: --no-http

    do not start the HTTP or long-polling workers (may still start :ref:`cron <reference/actions/cron>`
    workers)

    .. warning:: has no effect if :option:`--test-enable` is set, as tests
                 require an accessible HTTP server

.. option:: --http-interface <interface>

    TCP/IP address on which the HTTP server listens, defaults to ``0.0.0.0``
    (all addresses)

.. option:: --http-port <port>

    Port on which the HTTP server listens, defaults to 8069.

.. option:: --longpolling-port <port>

    TCP port for long-polling connections in multiprocessing or gevent mode,
    defaults to 8072. Not used in default (threaded) mode.

.. option:: --proxy-mode

    enables the use of ``X-Forwarded-*`` headers through `Werkzeug's proxy
    support`_.

    .. warning:: proxy mode *must not* be enabled outside of a reverse proxy
                 scenario

.. _reference/cmdline/server/logging:

Logging
'''''''

By default, Odoo displays all logging of level_ ``info`` except for workflow
logging (``warning`` only), and log output is sent to ``stdout``. Various
options are available to redirect logging to other destinations and to
customize the amount of logging output.

.. option:: --logfile <file>

    sends logging output to the specified file instead of stdout. On Unix, the
    file `can be managed by external log rotation programs
    <https://docs.python.org/3/library/logging.handlers.html#watchedfilehandler>`_
    and will automatically be reopened when replaced

.. option:: --syslog

    logs to the system's event logger: `syslog on unices <https://docs.python.org/3/library/logging.handlers.html#sysloghandler>`_
    and `the Event Log on Windows <https://docs.python.org/3/library/logging.handlers.html#nteventloghandler>`_.

    Neither is configurable

.. option:: --log-db <dbname>

    logs to the ``ir.logging`` model (``ir_logging`` table) of the specified
    database. The database can be the name of a database in the "current"
    PostgreSQL, or `a PostgreSQL URI`_ for e.g. log aggregation.

.. option:: --log-handler <handler-spec>

    :samp:`{LOGGER}:{LEVEL}`, enables ``LOGGER`` at the provided ``LEVEL``
    e.g. ``odoo.models:DEBUG`` will enable all logging messages at or above
    ``DEBUG`` level in the models.

    * The colon ``:`` is mandatory
    * The logger can be omitted to configure the root (default) handler
    * If the level is omitted, the logger is set to ``INFO``

    The option can be repeated to configure multiple loggers e.g.

    .. code-block:: console

        $ odoo-bin --log-handler :DEBUG --log-handler werkzeug:CRITICAL --log-handler odoo.fields:WARNING

.. option:: --log-request

    enable DEBUG logging for RPC requests, equivalent to
    ``--log-handler=odoo.http.rpc.request:DEBUG``

.. option:: --log-response

    enable DEBUG logging for RPC responses, equivalent to
    ``--log-handler=odoo.http.rpc.response:DEBUG``

.. option:: --log-web

    enables DEBUG logging of HTTP requests and responses, equivalent to
    ``--log-handler=odoo.http:DEBUG``

.. option:: --log-sql

    enables DEBUG logging of SQL querying, equivalent to
    ``--log-handler=odoo.sql_db:DEBUG``

.. option:: --log-level <level>

    Shortcut to more easily set predefined levels on specific loggers. "real"
    levels (``critical``, ``error``, ``warn``, ``debug``) are set on the
    ``odoo`` and ``werkzeug`` loggers (except for ``debug`` which is only
    set on ``odoo``).

    Odoo also provides debugging pseudo-levels which apply to different sets
    of loggers:

    ``debug_sql``
        sets the SQL logger to ``debug``

        equivalent to ``--log-sql``
    ``debug_rpc``
        sets the ``odoo`` and HTTP request loggers to ``debug``

        equivalent to ``--log-level debug --log-request``
    ``debug_rpc_answer``
        sets the ``odoo`` and HTTP request and response loggers to
        ``debug``

        equivalent to ``--log-level debug --log-request --log-response``

    .. note::

        In case of conflict between :option:`--log-level` and
        :option:`--log-handler`, the latter is used

.. _reference/cdmline/workers:

Multiprocessing
'''''''''''''''

.. option:: --workers <count>

    if ``count`` is not 0 (the default), enables multiprocessing and sets up
    the specified number of HTTP workers (sub-processes processing HTTP
    and RPC requests).

    .. note:: multiprocessing mode is only available on Unix-based systems

    A number of options allow limiting and recycling workers:

    .. option:: --limit-request <limit>

        Number of requests a worker will process before being recycled and
        restarted.

        Defaults to *8196*.

    .. option:: --limit-memory-soft <limit>

        Maximum allowed virtual memory per worker. If the limit is exceeded,
        the worker is killed and recycled at the end of the current request.

        Defaults to *2048MiB*.

    .. option:: --limit-memory-hard <limit>

        Hard limit on virtual memory, any worker exceeding the limit will be
        immediately killed without waiting for the end of the current request
        processing.

        Defaults to *2560MiB*.

    .. option:: --limit-time-cpu <limit>

        Prevents the worker from using more than <limit> CPU seconds for each
        request. If the limit is exceeded, the worker is killed.

        Defaults to *60*.

    .. option:: --limit-time-real <limit>

        Prevents the worker from taking longer than <limit> seconds to process
        a request. If the limit is exceeded, the worker is killed.

        Differs from :option:`--limit-time-cpu` in that this is a "wall time"
        limit including e.g. SQL queries.

        Defaults to *120*.

.. option:: --max-cron-threads <count>

    number of workers dedicated to :ref:`cron <reference/actions/cron>` jobs. Defaults to *2*.
    The workers are threads in multi-threading mode and processes in multi-processing mode.

    For multi-processing mode, this is in addition to the HTTP worker processes.

.. _reference/cmdline/config:

Configuration file
==================

.. program:: odoo-bin

Most of the command-line options can also be specified via a configuration
file. Most of the time, they use similar names with the prefix ``-`` removed
and other ``-`` are replaced by ``_`` e.g. :option:`--db-template` becomes
``db_template``.

Some conversions don't match the pattern:

* :option:`--db-filter` becomes ``dbfilter``
* :option:`--no-http` corresponds to the ``http_enable`` boolean
* logging presets (all options starting with ``--log-`` except for
  :option:`--log-handler` and :option:`--log-db`) just add content to
  ``log_handler``, use that directly in the configuration file
* :option:`--smtp` is stored as ``smtp_server``
* :option:`--database` is stored as ``db_name``
* :option:`--i18n-import` and :option:`--i18n-export` aren't available at all
  from configuration files

The default configuration file is :file:`{$HOME}/.odoorc` which
can be overridden using :option:`--config <odoo-bin -c>`. Specifying
:option:`--save <odoo-bin -s>` will save the current configuration state back
to that file.

.. _jinja2: http://jinja.pocoo.org
.. _regular expression: https://docs.python.org/3/library/re.html
.. _password authentication:
    https://www.postgresql.org/docs/9.3/static/auth-methods.html#AUTH-PASSWORD
.. _template database:
    https://www.postgresql.org/docs/9.3/static/manage-ag-templatedbs.html
.. _level:
    https://docs.python.org/3/library/logging.html#logging.Logger.setLevel
.. _a PostgreSQL URI:
    https://www.postgresql.org/docs/9.2/static/libpq-connect.html#AEN38208
.. _Werkzeug's proxy support:
    http://werkzeug.pocoo.org/docs/contrib/fixers/#werkzeug.contrib.fixers.ProxyFix
.. _pyinotify: https://github.com/seb-m/pyinotify/wiki


Shell
=====

Odoo command-line also allows to launch odoo as a python console environment.
This enables direct interaction with the :ref:`orm <reference/orm>` and its functionalities.


.. code-block:: console

   $ odoo_bin shell

.. option:: --shell-interface (ipython|ptpython|bpython|python)

    Specify a preferred REPL to use in shell mode.


.. _reference/cmdline/scaffold:

Scaffolding
===========

.. program:: odoo-bin scaffold

Scaffolding is the automated creation of a skeleton structure to simplify
bootstrapping (of new modules, in the case of Odoo). While not necessary it
avoids the tedium of setting up basic structures and looking up what all
starting requirements are.

Scaffolding is available via the :command:`odoo-bin scaffold` subcommand.

.. option:: name (required)

    the name of the module to create, may munged in various manners to
    generate programmatic names (e.g. module directory name, model names, …)

.. option:: destination (default=current directory)

    directory in which to create the new module, defaults to the current
    directory

.. option:: -t <template>

    a template directory, files are passed through jinja2_ then copied to
    the ``destination`` directory

.. code-block:: console

    $ odoo_bin scaffold my_module /addons/

This will create module *my_module* in directory */addons/*.


Cloc
====

.. program:: odoo-bin cloc

Odoo Cloc is a tool to count the number of relevant lines written in
Python, Javascript or XML. This can be used as a rough metric for pricing
maintenance of extra modules.

Command-line options
--------------------
.. option:: -d <database>, --database <database>

| Process the code of all extra modules installed on the provided database,
  and of all server actions and computed fields manually created in the provided
  database.
| The :option:`--addons-path` option is required to specify the path(s) to the
  module folder(s).
| If combined with :option:`--path`, the count will be that of the sum of both
  options' results (with possible overlaps). At least one of these two options is
  required to specify which code to process.

.. code-block:: console

   $ odoo-bin cloc --addons-path=addons -d my_database

.. seealso::
   - :ref:`reference/cmdline/cloc/database-option`


.. option:: -p <path>, --path <path>

| Process the files in the provided path.
| If combined with :option:`--database`, the count will be that of the sum of both
  options' results (with possible overlaps). At least one of these two options is
  required to specify which code to process.

.. code-block:: console

   $ odoo-bin cloc -p addons/account


Multiple paths can be provided by repeating the option.

.. code-block:: console

   $ odoo-bin cloc -p addons/account -p addons/sale

.. seealso::
   - :ref:`reference/cmdline/cloc/path-option`


.. option:: --addons-path <directories>

| Comma-separated list of directories in which modules are stored. These directories
  are scanned for modules.
| Required if the :option:`--database` option is used.


.. option:: -c <directories>

Specify a configuration file to use in place of the :option:`--addons-path` option.

.. code-block:: console

    $ odoo-bin cloc -c config.conf -d my_database


.. option:: -v, --verbose

Show the details of lines counted for each file.


Processed files
---------------

.. _reference/cmdline/cloc/database-option:

With the :option:`--database` option
''''''''''''''''''''''''''''''''''''

Odoo Cloc counts the lines in each file of extra installed modules in a
given database. In addition, it counts the Python lines of server actions and
custom computed fields that have been directly created in the database or
imported.

Some files are excluded from the count by default:

- The manifest (:file:`__manifest__.py` or :file:`__openerp__.py`)
- The contents of the folder :file:`static/lib`
- The tests defined in the folder :file:`tests` and :file:`static/tests`
- The migrations scripts defined in the folder :file:`migrations`
- The XML files declared in the ``demo`` or ``demo_xml`` sections of the manifest

For special cases, a list of files that should be ignored by Odoo Cloc can be defined
per module. This is specified by the ``cloc_exclude`` entry of the manifest:

.. code-block:: python

    "cloc_exclude": [
        "lib/common.py", # exclude a single file
        "data/*.xml",    # exclude all XML files in a specific folder
        "example/**/*",  # exclude all files in a folder hierarchy recursively
    ]

| The pattern ``**/*`` can be used to ignore an entire module. This can be useful
  to exclude a module from maintenance service costs.
| For more information about the pattern syntax, see `glob
  <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_.



.. _reference/cmdline/cloc/path-option:

With the :option:`--path` option
''''''''''''''''''''''''''''''''

This method works the same as with the :ref:`--database option
<reference/cmdline/cloc/database-option>` if a manifest file is present in the given
folder. Otherwise, it counts all files.


Identifying Extra Modules
-------------------------

To distinguish between standard and extra modules, Odoo Cloc uses the following heuristic:
modules that are located (real file system path, after following symbolic links)
in the same parent directory as the ``base``, ``web`` or ``web_enterprise``
standard modules are considered standard. Other modules are treated as extra modules.


Error Handling
--------------

Some file cannot be counted by Odoo Cloc.
Those file are reported at the end of the output.

Max file size exceeded
''''''''''''''''''''''

Odoo Cloc rejects any file larger than 25MB. Usually, source files are smaller
than 1 MB. If a file is rejected, it may be:

- A generated XML file that contains lots of data. It should be excluded in the manifest.
- A JavaScript library that should be placed in the :file:`static/lib` folder.

Syntax Error
''''''''''''

Odoo Cloc cannot count the lines of code of a Python file with a syntax problem.
If an extra module contains such files, they should be fixed to allow the module to
load. If the module works despite the presence of those files, they are probably
not loaded and should therefore be removed from the module, or at least excluded
in the manifest via ``cloc_exclude``.
