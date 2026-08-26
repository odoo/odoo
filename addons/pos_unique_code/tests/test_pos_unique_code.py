# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestPosUniqueCode(TransactionCase):
    def setUp(self):
        super().setUp()
        self.code = self.env['pos.unique.code'].create({'unique_code': '12345'})

    def test_code_has_no_default(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['pos.unique.code'].create({})

    def test_code_must_be_five_digits(self):
        with self.assertRaises(ValidationError):
            self.env['pos.unique.code'].create({'unique_code': '1234'})
        with self.assertRaises(ValidationError):
            self.env['pos.unique.code'].create({'unique_code': '1234a'})

    def test_codes_are_unique(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.env['pos.unique.code'].create({'unique_code': '12345'})

    def test_consume_unknown_code(self):
        result = self.env['pos.unique.code'].consume_code('99999')
        self.assertFalse(result['success'])
        self.assertFalse(self.code.is_used)

    def test_consume_marks_code_as_used(self):
        result = self.env['pos.unique.code'].consume_code('12345')
        self.assertTrue(result['success'])
        self.assertTrue(self.code.is_used)

    def test_consume_twice_is_rejected(self):
        self.env['pos.unique.code'].consume_code('12345')
        result = self.env['pos.unique.code'].consume_code('12345')
        self.assertFalse(result['success'])
        self.assertTrue(self.code.is_used)

    def test_consume_ignores_surrounding_spaces(self):
        result = self.env['pos.unique.code'].consume_code('  12345 ')
        self.assertTrue(result['success'])
        self.assertTrue(self.code.is_used)
