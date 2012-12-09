import logging
import optparse
import sys

import unittest2

import openerp
import openerp.addons.web.tests

_logger = logging.getLogger(__name__)

class TestJs(openerp.cli.Command):
    def run(self, args):
        self.parser = parser = optparse.OptionParser()
        parser.add_option("-d", "--database", dest="db_name", default=False, help="specify the database name")
        parser.add_option("--xmlrpc-port", dest="xmlrpc_port", default=8069, help="specify the TCP port for the XML-RPC protocol", type="int")
        # proably need to add both --superadmin-password and --database-admin-password
        self.parser.parse_args(args)

        # test ony uses db_name xmlrpc_port admin_passwd, so use the server one for the actual parsing

        config = openerp.tools.config
        config.parse_config(args)
        # needed until runbot is fixed
        config['db_password'] = config['admin_passwd']

        # run js tests
        openerp.netsvc.init_alternative_logger()
        suite = unittest2.TestSuite()
        suite.addTests(unittest2.TestLoader().loadTestsFromModule(openerp.addons.web.tests.test_js))
        r = unittest2.TextTestRunner(verbosity=2).run(suite)
        if r.errors or r.failures:
            sys.exit(1)

# vim:et:ts=4:sw=4:
