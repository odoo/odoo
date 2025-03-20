# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportPoSOrder(TestPointOfSaleDataHttpCommon):
    def test_report_pos_order_0(self):
        """Test the margin and price_total of a PoS Order with no taxes."""
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 150,
        })
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 150},
        ], False, False, self.partner_one)

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')
        self.assertEqual(len(reports.ids), 1)
        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_total, 150)

    def test_report_pos_order_1(self):
        """Test the margin and price_total of a PoS Order with taxes."""
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 150,
            'taxes_id': [(6, 0, self.tax_10_include.ids)],
        })
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 150},
        ], False, False, self.partner_one)

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')

        self.assertEqual(reports[0].margin, 136.36)
        self.assertEqual(reports[0].price_total, 150)

    def test_report_pos_order_2(self):
        """Test the margin and price_total of a PoS Order with discount and no taxes"""
        """Test the margin and price_total of a PoS Order with no taxes."""
        self.pos_config.open_ui()
        self.product_awesome_item.write({
            'categ_id': self.product_category.id,
            'list_price': 150,
        })
        self.create_order([
            {'product_id': self.product_awesome_item.product_variant_id, 'qty': 1, 'discount': 10},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 135},
        ], False, False, self.partner_one)

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')

        self.assertEqual(reports[0].margin, 135)
        self.assertEqual(reports[0].price_total, 135)
