# -*- coding: utf-8 -*-
import unittest2

import openerp
import common

class test_per_class_teardown(common.SingleTransactionCase):
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

class test_per_method_teardown(common.TransactionCase):
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

if __name__ == '__main__':
    unittest2.main()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
