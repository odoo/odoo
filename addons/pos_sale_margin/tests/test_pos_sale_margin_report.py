# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSaleMarginReport(TestPoSCommon):

    def setUp(self):
        super(TestPoSSaleMarginReport, self).setUp()
        self.config = self.basic_config

    def test_pos_sale_margin_report(self):

        product1 = self.create_product('Product 1', self.categ_basic, 150, standard_price=50)

        self.open_new_session()
        session = self.pos_session

        self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product1.id,
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
        reports = self.env['sale.report'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 100)
