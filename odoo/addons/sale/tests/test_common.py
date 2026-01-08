# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleCommon(SaleCommon):

    def test_common(self):
        self.assertFalse(self.empty_order.order_line)
        self.assertEqual(self.empty_order.amount_total, 0.0)

        self.assertEqual(self.empty_order.partner_id, self.partner)
        self.assertEqual(self.empty_order.partner_invoice_id, self.partner)
        self.assertEqual(self.empty_order.partner_shipping_id, self.partner)
        self.assertEqual(self.empty_order.pricelist_id, self.pricelist)
        self.assertEqual(self.empty_order.currency_id.name, self.currency.name)
        self.assertEqual(self.empty_order.team_id, self.sale_team)
        self.assertEqual(self.empty_order.state, 'draft')

        self.assertEqual(self.sale_order.partner_id, self.partner)
        self.assertEqual(self.sale_order.partner_invoice_id, self.partner)
        self.assertEqual(self.sale_order.partner_shipping_id, self.partner)
        self.assertEqual(self.sale_order.pricelist_id, self.pricelist)
        self.assertEqual(self.sale_order.currency_id.name, self.currency.name)
        self.assertEqual(self.sale_order.team_id, self.sale_team)
        self.assertEqual(self.sale_order.state, 'draft')

        consumable_line, service_line = self.sale_order.order_line

        self.assertFalse(consumable_line.pricelist_item_id)
        self.assertEqual(consumable_line.price_unit, 20.0)
        self.assertFalse(consumable_line.discount)
        self.assertEqual(consumable_line.product_uom, self.uom_unit)
        self.assertEqual(consumable_line.price_total, 5.0 * 20.0)

        self.assertFalse(service_line.pricelist_item_id)
        self.assertEqual(service_line.price_unit, 50.0)
        self.assertFalse(service_line.discount)
        self.assertEqual(service_line.product_uom, self.uom_unit)
        self.assertEqual(service_line.price_total, 12.5 * 50)

        self.assertEqual(self.sale_order.amount_total, 725.0)
