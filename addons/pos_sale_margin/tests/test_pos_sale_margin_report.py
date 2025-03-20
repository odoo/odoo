# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleMarginReport(TestPointOfSaleDataHttpCommon):
    def test_pos_sale_margin_report(self):
        self.pos_config.open_ui()
        self.product_awesome_item.product_variant_id.write({
            'categ_id': self.product_category.id,
            'lst_price': 150,
            'list_price': 50,
        })

        self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_awesome_item.product_variant_id.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 1.0,
                'price_subtotal': 150,
                'price_subtotal_incl': 150,
                'total_cost': 50,
            }),],
            'amount_total': 150.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['sale.report'].sudo().search([
            ('product_id', '=', self.product_awesome_item.product_variant_id.id)], order='id')

        self.assertEqual(reports[0].margin, 100)
