# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestSingleTransactionCase(common.SingleTransactionCase):
    """
    Check the whole-class transaction behavior of SingleTransactionCase.
    """

    def test_00(self):
        """ Create a test record. """
        self.env['test_base.model'].create({'name': 'test_per_class_teardown_record'})
        record = self.env['test_base.model'].search([('name', '=', 'test_per_class_teardown_record')])
        self.assertEqual(1, len(record), "Test record not found.")

    def test_01(self):
        """ Find the created record. """
        record = self.env['test_base.model'].search([('name', '=', 'test_per_class_teardown_record')])
        self.assertEqual(1, len(record), "Test record not found.")

    def test_20a(self):
        """ Create a record with a XML ID """
        pid, _ = self.env['test_base.model'].name_create('Mr Blue')
        self.env['ir.model.data'].create({'name': 'test_record_blue',
                                          'module': 'test_base',
                                          'model': 'test_base.model',
                                          'res_id': pid})

    def test_20b(self):
        """ Resolve xml id with ref() and browse_ref() """
        xid = 'test_base.test_record_blue'
        record = self.env.ref(xid)
        pid = self.ref(xid)
        self.assertTrue(pid, "ref() should resolve xid to database ID")
        self.assertEqual(pid, record.id, "ref() is not consistent with env.ref()")
        record2 = self.browse_ref(xid)
        self.assertEqual(record, record2, "browse_ref() should resolve xid to browse records")


class TestTransactionCase(common.TransactionCase):
    """
    Check the per-method transaction behavior of TransactionCase.
    """

    def test_00(self):
        """ Create a record. """
        records = self.env['test_base.model'].search([('name', '=', 'test_per_class_teardown_record')])
        self.assertEqual(0, len(records), "Test record found.")
        self.env['test_base.model'].create({'name': 'test_per_class_teardown_record'})
        records = self.env['test_base.model'].search([('name', '=', 'test_per_class_teardown_record')])
        self.assertEqual(1, len(records), "Test record not found.")

    def test_01(self):
        """ Don't find the created record. """
        records = self.env['test_base.model'].search([('name', '=', 'test_per_class_teardown_record')])
        self.assertEqual(0, len(records), "Test record found.")

    def test_20a(self):
        """ Create a record with a XML ID then resolve xml id with ref() and browse_ref() """
        pid, _ = self.env['test_base.model'].name_create('Mr Yellow')
        self.env['ir.model.data'].create({'name': 'test_record_yellow',
                                          'module': 'test_base',
                                          'model': 'test_base.model',
                                          'res_id': pid})
        xid = 'test_base.test_record_yellow'
        record = self.env.ref(xid)
        pid = self.ref(xid)
        self.assertEquals(pid, record.id, "ref() should resolve xid to database ID")
        record2 = self.browse_ref(xid)
        self.assertEqual(record, record2, "browse_ref() should resolve xid to browse records")