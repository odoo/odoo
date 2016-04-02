# -*- coding: utf-8 -*-
import unittest

from openerp.tests import common

class test_single_transaction_case(common.SingleTransactionCase):
    """
    Check the whole-class transaction behavior of SingleTransactionCase.
    """

    def test_00(self):
        """Create a partner."""
        cr, uid = self.cr, self.uid
        self.registry('res.partner').create(cr, uid, {'name': 'test_per_class_teardown_partner'})
        ids = self.registry('res.partner').search(cr, uid, [('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(ids), "Test partner not found.")

    def test_01(self):
        """Find the created partner."""
        cr, uid = self.cr, self.uid
        ids = self.registry('res.partner').search(cr, uid, [('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(ids), "Test partner not found.")

    def test_20a(self):
        """ Create a partner with a XML ID """
        cr, uid = self.cr, self.uid
        res_partner = self.registry('res.partner')
        ir_model_data = self.registry('ir.model.data')
        pid, _ = res_partner.name_create(cr, uid, 'Mr Blue')
        ir_model_data.create(cr, uid, {'name': 'test_partner_blue',
                                       'module': 'base',
                                       'model': 'res.partner',
                                       'res_id': pid})
    def test_20b(self):
        """ Resolve xml id with ref() and browse_ref() """
        cr, uid = self.cr, self.uid
        res_partner = self.registry('res.partner')
        xid = 'base.test_partner_blue'
        p_ref = self.ref(xid)
        self.assertTrue(p_ref, "ref() should resolve xid to database ID")
        partner = res_partner.browse(cr, uid, p_ref)
        p_browse_ref = self.browse_ref(xid)
        self.assertEqual(partner, p_browse_ref, "browse_ref() should resolve xid to browse records")
    


class test_transaction_case(common.TransactionCase):
    """
    Check the per-method transaction behavior of TransactionCase.
    """

    def test_00(self):
        """Create a partner."""
        cr, uid = self.cr, self.uid
        ids = self.registry('res.partner').search(cr, uid, [('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(0, len(ids), "Test partner found.")
        self.registry('res.partner').create(cr, uid, {'name': 'test_per_class_teardown_partner'})
        ids = self.registry('res.partner').search(cr, uid, [('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(ids), "Test partner not found.")

    def test_01(self):
        """Don't find the created partner."""
        cr, uid = self.cr, self.uid
        ids = self.registry('res.partner').search(cr, uid, [('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(0, len(ids), "Test partner found.")


    def test_20a(self):
        """ Create a partner with a XML ID then resolve xml id with ref() and browse_ref() """
        cr, uid = self.cr, self.uid
        res_partner = self.registry('res.partner')
        ir_model_data = self.registry('ir.model.data')
        pid, _ = res_partner.name_create(cr, uid, 'Mr Yellow')
        ir_model_data.create(cr, uid, {'name': 'test_partner_yellow',
                                       'module': 'base',
                                       'model': 'res.partner',
                                       'res_id': pid})
        xid = 'base.test_partner_yellow'
        p_ref = self.ref(xid)
        self.assertEquals(p_ref, pid, "ref() should resolve xid to database ID")
        partner = res_partner.browse(cr, uid, pid)
        p_browse_ref = self.browse_ref(xid)
        self.assertEqual(partner, p_browse_ref, "browse_ref() should resolve xid to browse records")

if __name__ == '__main__':
    unittest.main()
