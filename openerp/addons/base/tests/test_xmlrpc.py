# -*- coding: utf-8 -*-
import time
import unittest2
import xmlrpclib

import openerp.tests.common

DB = openerp.tests.common.DB

class test_xmlrpc(openerp.tests.common.HttpCase):

    def test_01_xmlrpc_login(self):
        """ Try to login on the common service. """
        uid = self.xmlrpc_common.login(DB, 'admin', 'admin')
        self.assertTrue(uid == 1)

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        o = self.xmlrpc_object
        ids = o.execute(DB, 1, 'admin', 'ir.model', 'search', [])
        self.assertIsInstance(ids, list)
        ids = o.execute(DB, 1, 'admin', 'ir.model', 'search', [], {})
        self.assertIsInstance(ids, list)

    # This test was written to test the creation of a new RPC endpoint, not
    # really for the EDI itself.
    #def test_xmlrpc_import_edi_document(self):
    #    """ Try to call an EDI method. """
    #    msg_re = 'EDI Document is empty!'
    #    with self.assertRaisesRegexp(Exception, msg_re):
    #        self.proxy.edi_60.import_edi_document(DB, ADMIN_USER_ID, ADMIN_PASSWORD, {})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
