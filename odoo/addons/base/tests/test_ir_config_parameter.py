# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install', 'icp')
class TestIrConfigParameter(TransactionCase):
    """
    Test that the ir.config_parameter return the expected value.
    """
    def setUp(self):
        super().setUp()
        self.ICP = self.env['ir.config_parameter'].sudo()

    def test_basic_value(self):
        self.ICP.set_param('foo', 'bar')
        res = self.ICP.get_param('foo')
        self.assertEqual(res, 'bar')

    def test_default_value(self):
        res = self.ICP.get_param('unexisting')
        self.assertEqual(res, False)

        res = self.ICP.get_param('unexisting', default='default')
        self.assertEqual(res, 'default')

        res = self.ICP.get_param('unexisting', default=False)
        self.assertEqual(res, False)

        res = self.ICP.get_param('unexisting', default=None)
        self.assertEqual(res, None)

    def test_falsy_value(self):
        self.ICP.set_param('Falsy', '')
        res = self.ICP.get_param('Falsy')
        self.assertEqual(res, '')

        res = self.ICP.get_param('Falsy', default='default')
        self.assertEqual(res, '')

        self.ICP.set_param('foo', 0)
        res = self.ICP.get_param('foo')
        self.assertEqual(res, '0')
