# -*- coding: utf-8 -*-
import openerp.tests.common


class test_xmlrpc(openerp.tests.common.HttpCase):
    at_install = False
    post_install = True

    def test_01_xmlrpc_login(self):
        """ Try to login on the common service. """
        db_name = openerp.tests.common.get_db_name()
        uid = self.xmlrpc_common.login(db_name, 'admin', 'admin')
        self.assertEqual(uid, 1)

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        o = self.xmlrpc_object
        db_name = openerp.tests.common.get_db_name()
        ids = o.execute(db_name, 1, 'admin', 'ir.model', 'search', [])
        self.assertIsInstance(ids, list)
        ids = o.execute(db_name, 1, 'admin', 'ir.model', 'search', [], {})
        self.assertIsInstance(ids, list)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
