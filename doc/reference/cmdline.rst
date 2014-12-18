.. _reference/cmdline:

===============================
Command-line interface: odoo.py
===============================

.. _reference/cmdline/server:

Running the server
==================

.. program:: odoo.py

.. option:: -d <database>, --database=<database>

    database used when installing or updating modules.

.. option:: --db-filter=<filter>

    hides databases that do not match ``<filter>``. The filter is a
    `regular expression`_, with the additions that:

    - ``%h`` is replaced by the whole hostname the request is made on.
    - ``%d`` is replaced by the subdomain the request is made on, with the
      exception of ``www`` (so domain ``odoo.com`` and ``www.odoo.com`` both
      match the database ``odoo``)

.. option:: -i <modules>, --init=<modules>

    comma-separated list of modules to install before running the server
    (requires :option:`-d`).

.. option:: -u <modules>, --update=<modules>

    comma-separated list of modules to update before running the server
    (requires :option:`-d`).

.. option:: --addons-path=<directories>

    comma-separated list of directories in which modules are stored. These
    directories are scanned for modules (nb: when and why?)

.. option:: -c <config>, --config=<config>

    provide an alternate configuration file

.. option:: -s, --save

    saves the server configuration to the current configuration file
    (:file:`{$HOME}/.openerp_serverrc` by default, overridable using
    :option:`-c`)

.. option:: --test-enable

    runs tests after installing modules

.. option:: --debug

    when an unexpected error is raised (not a warning or an access error),
    automatically starts :mod:`python:pdb` before logging and returning the
    error

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
file.

The default configuration file is :file:`{$HOME}/.openerp_serverrc` which
can be overridden using :option:`--config <odoo.py -c>`. Specifying
:option:`--save <odoo.py -s>` will save the current configuration state back
to that file.

.. _jinja2: http://jinja.pocoo.org
.. _regular expression: https://docs.python.org/2/library/re.html
