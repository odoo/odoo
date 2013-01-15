.. _adding-command:

Adding a new command
====================

``oe`` uses the argparse_ library to implement commands. Each
command lives in its own ``openerpcommand/<command>.py`` file.

.. _argparse: http://docs.python.org/2.7/library/argparse.html

To create a new command, probably the most simple way to get started is to
copy/paste an existing command, say ``openerpcommand/initialize.py`` to
``openerpcommand/foo.py``. In the newly created file, the important bits
are the ``run(args)`` and ``add_parser(subparsers)`` functions.

``add_parser``'s responsability is to create a (sub-)parser for the command,
i.e. describe the different options and flags. The last thing it does is to set
``run`` as the function to call when the command is invoked.

.. code-block:: python

  > def add_parser(subparsers):
  >     parser = subparsers.add_parser('<command-name>',
  >         description='...')
  >     parser.add_argument(...)
  >     ...
  >     parser.set_defaults(run=run)

``run(args)`` actually implements the command. It should be kept as simple as
possible and delegate most of its work to small functions (probably placed at
the top of the new file). In other words, its responsability is mainly to
deal with the presence/absence/pre-processing of ``argparse``'s arguments.

Finally, the module must be added to ``openerpcommand/__init__.py``.
