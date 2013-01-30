.. _commands:

Available commands
==================

This page explain some of the available ``oe`` commands. For an overview about
``oe``, see :doc:`openerp-command`.

Keep in mind that ``oe --help`` and ``oe <command> --help`` already give a lot
of information about the commands and their options and flags.

``web``
-------

The ``web`` command is used to create a single OpenERP server process to handle
regular HTTP requests and XML-RPC requests. It is possible to execute such
process multiple times, possibly on different machines.

It is possible to chose the ``--threaded`` or ``--gevent`` flags. It is
recommanded to use ``--threaded`` only when running a single process.
``--gevent`` is experimental; it is planned to use it for the embedded chat
feature.

Example invocation::

  > oe web --addons ../../addons/trunk:../../web/trunk/addons --threaded

``cron``
--------

The ``cron`` command is used to create a single OpenERP process to execute
so-called cron jobs, also called scheduled tasks in the OpenERP interface. As
for the ``web`` command, multiple cron processes can be run side by side.

It is necessary to specify on the command-line which database need to be
watched by the cron process with the ``--database`` option.

Example invocation::

  > oe cron --addons ../../addons/trunk:../../web/trunk/addons --database production
