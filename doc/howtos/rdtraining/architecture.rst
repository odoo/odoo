.. _howto/rdtraining/architecture:

=====================
Architecture Overview
=====================

Multi-tier application
======================


Odoo modules
============

THE FOLLOWING IS JUST A COPY-PASTE OF THE EXISING DOC. IT NEEDS CLEANING.

Both server and client extensions are packaged as *modules* which are
optionally loaded in a *database*.

Odoo modules can either add brand new business logic to an Odoo system, or
alter and extend existing business logic: a module can be created to add your
country's accounting rules to Odoo's generic accounting support, while the
next module adds support for real-time visualisation of a bus fleet.

Everything in Odoo thus starts and ends with modules.

Composition of a module
-----------------------

An Odoo module can contain a number of elements:

Business objects
    Declared as Python classes, these resources are automatically persisted
    by Odoo based on their configuration

:ref:`Object views <reference/views>`
    Definition of business objects UI display

:ref:`Data files <reference/data>`
    XML or CSV files declaring the model metadata :

    * :ref:`views <reference/views>` or :ref:`reports <reference/reports>`,
    * configuration data (modules parametrization, :ref:`security rules <reference/security>`),
    * demonstration data
    * and more

:ref:`Web controllers <reference/controllers>`
    Handle requests from web browsers

Static web data
    Images, CSS or javascript files used by the web interface or website

Module structure
----------------

Each module is a directory within a *module directory*. Module directories
are specified by using the :option:`--addons-path <odoo-bin --addons-path>`
option.

.. tip::
    :class: aphorism

    most command-line options can also be set using :ref:`a configuration
    file <reference/cmdline/config>`

An Odoo module is declared by its :ref:`manifest <reference/module/manifest>`.
See the :ref:`manifest documentation <reference/module/manifest>` about it.

A module is also a
`Python package <http://docs.python.org/2/tutorial/modules.html#packages>`_
with a ``__init__.py`` file, containing import instructions for various Python
files in the module.

For instance, if the module has a single ``mymodule.py`` file ``__init__.py``
might contain::

    from . import mymodule

Odoo provides a mechanism to help set up a new module, :ref:`odoo-bin
<reference/cmdline/server>` has a subcommand :ref:`scaffold
<reference/cmdline/scaffold>` to create an empty module:

.. code-block:: console

    $ odoo-bin scaffold <module name> <where to put it>

The command creates a subdirectory for your module, and automatically creates a
bunch of standard files for a module. Most of them simply contain commented code
or XML. The usage of most of those files will be explained along this tutorial.

.. exercise:: Module creation

    Use the command line above to  create an empty module Open Academy, and
    install it in Odoo.

    .. only:: solutions

        #. Invoke the command ``odoo-bin scaffold openacademy addons``.
        #. Adapt the manifest file to your module.
        #. Don't bother about the other files.

