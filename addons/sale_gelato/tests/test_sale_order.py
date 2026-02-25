# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestGelatoSaleOrder(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gelato_product = cls.env['product.product'].create({
            'name': 'Test Gelato Product',
            'gelato_product_uid': 'dummy_uid',
        })

        cls.gelato_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({'product_id': cls.gelato_product.id, 'product_uom_qty': 1})
            ],
        })

        cls.partner_missing_street = cls.env['res.partner'].create({
            'name': 'Test',
            'city': 'Leuven',
            'zip': '3001',
            'country_id': cls.env.ref('base.be').id,
            'email': 'test@test.com',
            'phone': '123123123',
        })

        cls.partner_street_too_long = cls.partner_missing_street.copy({
            'street': 'Rue de la Madeleine/Magdalenasteenweg'
        })

    def test_add_non_gelato_service_product_to_gelato_order(self):
        """Test that adding a non-gelato service product to Gelato order is possible."""
        self.env['sale.order.line'].create({
            'product_id': self.service_product.id,
            'order_id': self.gelato_order.id,
        })

        self.assertEqual(len(self.gelato_order.order_line.ids), 2)

    def test_add_non_gelato_goods_product_to_gelato_order(self):
        """Test that adding a non-gelato goods product to Gelato order is not possible."""
        with self.assertRaises(
            ValidationError, msg="It shouldn't be possible to mix gelato and non-gelato products"
        ):
            self.env['sale.order.line'].create({
                'product_id': self.product.id,
                'order_id': self.gelato_order.id,
            })

    def test_prevent_confirming_gelato_so_with_an_incomplete_partner_address(self):
        """Test that confirming Gelato SO with incomplete partner address is impossible."""
        self.gelato_order.write({'partner_id': self.partner_missing_street.id})
        with self.assertRaises(
            ValidationError,
            msg="It should not be possible to confirm Gelato SO with incomplete address.",
        ):
            self.gelato_order.action_confirm()

    def test_prevent_confirming_gelato_so_with_too_long_partner_address(self):
        """Test that confirming Gelato SO is impossible if partner shipping address is too long."""
        self.gelato_order.write({'partner_id': self.partner_street_too_long.id})
        with self.assertRaises(
            ValidationError,
            msg="It should not be possible to confirm Gelato SO with too long partner address.",
        ):
            self.gelato_order.action_confirm()
