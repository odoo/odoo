.. _openerp-command:

The ``oe`` script
=================

The ``oe`` script provides a set of command-line tools around the OpenERP
framework. It is meant to replace the older ``openerp-server`` script (which
is still available).

Using ``oe``
------------

In contrast to the previous ``openerp-server`` script, ``oe`` defines a few
commands, each with its own set of flags and options. You can get some
information for any of them with

::

  > oe <command> --help

For instance::

  > oe run-tests --help

Some ``oe`` options can be provided via environment variables. For instance::

  > export OPENERP_DATABASE=trunk
  > export OPENERP_HOST=127.0.0.1
  > export OPENERP_PORT=8069

Depending on your needs, you can group all of the above in one single script;
for instance here is a, say, ``test-trunk-view-validation.sh`` file::

  COMMAND_REPO=/home/thu/repos/command/trunk/
  SERVER_REPO=/home/thu/repos/server/trunk

  export PYTHONPATH=$SERVER_REPO:$COMMAND_REPO
  export PATH=$SERVER_REPO:$COMMAND_REPO:$PATH
  export OPENERP_DATABASE=trunk
  export OPENERP_HOST=127.0.0.1
  export OPENERP_PORT=8069

  # The -d ignored is actually needed by `oe` even though `test_view_validation`
  # itself does not need it.
  oe run-tests -d ignored -m openerp.test_view_validation

Available commands
-------------------

See the :doc:`commands` page.

Adding new commands
-------------------

See the :doc:`adding-command` page.

Bash completion
---------------

A preliminary ``oe-bash-completion`` file is provided. After sourcing it,

::

  > . oe-bash-completion

completion (using the TAB character) in Bash should work.
