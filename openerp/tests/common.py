# -*- coding: utf-8 -*-
import os
import time
import unittest2
import xmlrpclib

import openerp

# The openerp library is supposed already configured.
ADDONS_PATH = openerp.tools.config['addons_path']
PORT = openerp.tools.config['xmlrpc_port']
DB = openerp.tools.config['db_name']

HOST = '127.0.0.1'

ADMIN_USER = 'admin'
ADMIN_USER_ID = 1
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

class TransactionCase(unittest2.TestCase):
    """
    Subclass of TestCase with a single transaction, rolled-back at the end of
    the tests.
    """

    def setUp(self):
        self.cr = openerp.modules.registry.RegistryManager.get(DB).db.cursor()
        self.uid = openerp.SUPERUSER_ID

    def tearDown(self):
        self.cr.rollback()
        self.cr.close()

    def registry(self, model):
        return openerp.modules.registry.RegistryManager.get(DB)[model]

class RpcCase(unittest2.TestCase):
    """
    Subclass of TestCase with a few XML-RPC proxies.
    """

    def __init__(self, name):
        super(RpcCase, self).__init__(name)

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
        self.proxy.translation_61 = xmlrpclib.ServerProxy(url_61 + 'translation')

    @classmethod
    def generate_database_name(cls):
        if hasattr(cls, '_database_id'):
            cls._database_id += 1
        else:
            cls._database_id = 0
        return '_fresh_name_' + str(cls._database_id) + '_'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
