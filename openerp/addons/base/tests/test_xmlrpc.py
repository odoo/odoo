# -*- coding: utf-8 -*-
import time
import unittest2
import xmlrpclib

from openerp.tests import common

DB = common.DB
ADMIN_USER = common.ADMIN_USER
ADMIN_USER_ID = common.ADMIN_USER_ID
ADMIN_PASSWORD = common.ADMIN_PASSWORD

class test_xmlrpc(common.HttpCase):

    def test_01_xmlrpc_login(self):
        """ Try to login on the common service. """
        uid = self.xmlrpc_common.login(DB, ADMIN_USER, ADMIN_PASSWORD)
        self.assertTrue(uid == ADMIN_USER_ID)

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        o = self.xmlrpc_object
        ids = o.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD, 'ir.model', 'search', [])
        self.assertIsInstance(ids, list)
        ids = o.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD, 'ir.model', 'search', [], {})
        self.assertIsInstance(ids, list)

    # This test was written to test the creation of a new RPC endpoint, not
    # really for the EDI itself.
    #def test_xmlrpc_import_edi_document(self):
    #    """ Try to call an EDI method. """
    #    msg_re = 'EDI Document is empty!'
    #    with self.assertRaisesRegexp(Exception, msg_re):
    #        self.proxy.edi_60.import_edi_document(DB, ADMIN_USER_ID, ADMIN_PASSWORD, {})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
