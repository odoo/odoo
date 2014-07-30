.. _core/cmdline:

===============================
Command-line interface: oodo.py
===============================

.. _core/cmdline/server:

Running the server
==================

.. program:: odoo.py

.. option:: -d <database>, --database=<database>

    database used when installing or updating modules.

.. option:: -i <modules>, --init=<modules>

    comma-separated list of modules to :ref:`install
    <core/module/lifecycle/install>` before running the server.

.. option:: -u <modules>, --update=<modules>

    comma-separated list of modules to :ref:`update
    <core/module/lifecycle/update>` before running the server.

.. option:: --addons-path <directories>

    comma-separated list of directories in which modules are stored. These
    directories are scanned for modules (nb: when and why?)

.. _core/cmdline/scaffold:

Scaffolding
===========

.. program:: odoo.py scaffold

Scaffolding is the automated creation of a skeleton structure to simplify
bootstrapping (of new modules, in the case of Odoo). While not necessary it
avoids the tedium of setting up basic structures and looking up what all
starting requirements are.

.. option:: -t <template>

    a template directory, files are passed through jinja2_ then copied to
    the :option:`destination` directory

.. option:: name

    the name of the module to create, may munged in various manners to
    generate programmatic names (e.g. module directory name, model names, …)

.. option:: destination

    directory in which to create the new module, defaults to the current
    directory

.. _jinja2: http://jinja.pocoo.org
