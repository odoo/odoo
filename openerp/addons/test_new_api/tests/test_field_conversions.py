# -*- coding: utf-8 -*-

from openerp import fields
from openerp.tests import common

class TestFieldToColumn(common.TransactionCase):
    def test_char(self):
        # create a field, initialize its attributes, and convert it to a column
        field = fields.Char(string="test string", required=True)
        field.setup_base(self.env['res.partner'], 'test')
        column = field.to_column()

        self.assertEqual(column.string, "test string")
        self.assertTrue(column.required)
