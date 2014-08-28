# -*- coding: utf-8 -*-
import unittest2
from openerp import models, fields

class TestFieldToColumn(unittest2.TestCase):
    def test_char(self):
        # create a field, initialize its attributes, and convert it to a column
        field = fields.Char(string="test string", required=True)
        field.set_class_name(models.Model, 'test')
        column = field.to_column()

        self.assertEqual(column.string, "test string")
        self.assertTrue(column.required)
