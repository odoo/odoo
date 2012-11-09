# -*- coding: utf-8 -*-
"""
The module :mod:`openerp.tests.common` provides a few helpers and classes to write
tests.
"""
import threading
import time
import unittest2
import xmlrpclib

import openerp

# The openerp library is supposed already configured.
ADDONS_PATH = openerp.tools.config['addons_path']
PORT = openerp.tools.config['xmlrpc_port']
DB = openerp.tools.config['db_name']

# If the database name is not provided on the command-line,
# use the one on the thread (which means if it is provided on
# the command-line, this will break when installing another
# database from XML-RPC).
if not DB and hasattr(threading.current_thread(), 'dbname'):
    DB = threading.current_thread().dbname

HOST = '127.0.0.1'

ADMIN_USER = 'admin'
ADMIN_USER_ID = openerp.SUPERUSER_ID
ADMIN_PASSWORD = 'admin'

def start_openerp():
    """
    Start the OpenERP server similary to the openerp-server script.
    """
    openerp.service.start_services()

    # Ugly way to ensure the server is listening.
    time.sleep(2)

def stop_openerp():
    """
    Shutdown the OpenERP server similarly to a single ctrl-c.
    """
    openerp.service.stop_services()

class BaseCase(unittest2.TestCase):
    """
    Subclass of TestCase for common OpenERP-specific code.
    
    This class is abstract and expects self.cr and self.uid to be initialized by subclasses.
    """

    @classmethod
    def cursor(self):
        return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

    @classmethod
    def registry(self, model):
        return openerp.modules.registry.RegistryManager.get(DB)[model]

    @classmethod
    def ref(self, xid):
        """ Returns database ID corresponding to a given identifier.

            :param xid: fully-qualified record identifier, in the form ``module.identifier``
            :raise: ValueError if not found
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        _, id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, module, xid)
        return id

    @classmethod
    def browse_ref(self, xid):
        """ Returns a browsable record for the given identifier.

            :param xid: fully-qualified record identifier, in the form ``module.identifier``
            :raise: ValueError if not found
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        return self.registry('ir.model.data').get_object(self.cr, self.uid, module, xid)


class TransactionCase(BaseCase):
    """
    Subclass of BaseCase with a single transaction, rolled-back at the end of
    each test (method).
    """

    def setUp(self):
        # Store cr and uid in class variables, to allow ref() and browse_ref to be BaseCase @classmethods
        # and still access them
        TransactionCase.cr = self.cursor()
        TransactionCase.uid = openerp.SUPERUSER_ID

    def tearDown(self):
        self.cr.rollback()
        self.cr.close()


class SingleTransactionCase(BaseCase):
    """
    Subclass of BaseCase with a single transaction for the whole class,
    rolled-back after all the tests.
    """

    @classmethod
    def setUpClass(cls):
        cls.cr = cls.cursor()
        cls.uid = openerp.SUPERUSER_ID

    @classmethod
    def tearDownClass(cls):
        cls.cr.rollback()
        cls.cr.close()


class RpcCase(unittest2.TestCase):
    """
    Subclass of TestCase with a few XML-RPC proxies.
    """

    def __init__(self, methodName='runTest'):
        super(RpcCase, self).__init__(methodName)

        class A(object):
            pass
        self.proxy = A()

        # Use the old (pre 6.1) API.
        self.proxy.url_60 = url_60 = 'http://%s:%d/xmlrpc/' % (HOST, PORT)
        self.proxy.common_60 = xmlrpclib.ServerProxy(url_60 + 'common')
        self.proxy.db_60 = xmlrpclib.ServerProxy(url_60 + 'db')
        self.proxy.object_60 = xmlrpclib.ServerProxy(url_60 + 'object')

        # Use the new (6.1) API.
        self.proxy.url_61 = url_61 = 'http://%s:%d/openerp/xmlrpc/1/' % (HOST, PORT)
        self.proxy.common_61 = xmlrpclib.ServerProxy(url_61 + 'common')
        self.proxy.db_61 = xmlrpclib.ServerProxy(url_61 + 'db')
        self.proxy.model_61 = xmlrpclib.ServerProxy(url_61 + 'model/' + DB)

    @classmethod
    def generate_database_name(cls):
        if hasattr(cls, '_database_id'):
            cls._database_id += 1
        else:
            cls._database_id = 0
        return '_fresh_name_' + str(cls._database_id) + '_'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
