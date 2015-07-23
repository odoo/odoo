# -*- coding: utf-8 -*-
import argparse
import contextlib
import logging
import textwrap
import threading
import uuid
import os
import sys

from .. import api, netsvc
from .command import Command
from ..modules import get_modules, get_module_path, initialize_sys_path, registry
from ..sql_db import db_connect, close_db

logger = logging.getLogger('openerp.tests')
class Test(Command):
    """
    Runs Odoo tests.

    * positional arguments are forwarded to py.test, module names can be
      provided and will be converted to paths before forwarding
    * most optional arguments are forwarded as-is to py.test as well

    see py.test help for information about positional arguments

    If no database is specified, generates a randomly-named ones to execute
    tests in and deletes it afterwards.
    """
    def run(self, args):
        parser = argparse.ArgumentParser(
            usage="{} test [options] [modules_or_files_or_dirs...]".format(
                sys.argv[0].split(os.path.sep)[-1]),
            description=textwrap.dedent(self.__doc__),
            add_help=False,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument('-h', '--help', action='store_true',
                            help="show this help message and exit")
        parser.add_argument(
            '-d', '--database',
            help="Database to use instead of randomly generating one. "
                 "Named test databases are automatically created if they do "
                 "not already exist, but they are not deleted after testing "
                 "and can be reused.")
        options, pytest_args = parser.parse_known_args(args=args)

        import pytest
        from openerp.tests import support, fixtures

        if options.help:
            parser.print_help()
            print
            print " py.test help ".center(80, '=')
            print
            pytest.main(['-h'], plugins=[fixtures])
            parser.exit()

        db = options.database or 'test_{}'.format(uuid.uuid4().hex[:25])
        # for openerp.tests.common.get_db_name()
        threading.current_thread().dbname = db

        # FIXME: less crappy logging would be nice
        netsvc.init_logger()

        dblogger = logger.getChild(db)

        with contextlib.closing(db_connect('postgres').cursor()) as cr:
            cr.autocommit(True)

             # if the database was specified explicitly, it may already exist
             # and not need to be created
            to_create = True
            if options.database:
                cr.execute('SELECT 1 FROM pg_database WHERE datname=%s', (db,))
                to_create = not cr.fetchone()

            if to_create:
                dblogger.info('Creating db...')
                cr.execute('CREATE DATABASE %s' % db)
            else:
                dblogger.info('Using existing db...')

        initialize_sys_path()
        try:
            modules = set(get_modules())

            # converts module names to FS paths, leaves other parameters
            # (either pytest options or file paths) as-is
            params = [
                get_module_path(param) if param in modules else param
                for param in pytest_args
            ]

            dblogger.info("Running tests...")
            # TODO: duplicates RegistryManager.new something fierce
            with registry.RegistryManager.lock(), api.Environment.manage():
                registry.RegistryManager.delete(db)
                reg = registry.RegistryManager.registries[db] = registry.Registry(db)
                # no multiprocess
                pytest.main(params, plugins=[
                    support.OdooTests(reg),
                    fixtures,
                ])
        finally:
            # only drop implicitly created databass
            if not options.database:
                dblogger.info("Dropping db...")
                close_db(db)
                with contextlib.closing(db_connect('postgres').cursor()) as cr:
                    cr.autocommit(True)
                    cr.execute('DROP DATABASE %s' % db)
