# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from datetime import timedelta

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestReportPoSOrder(TestPoSCommon):

    def setUp(self):
        super(TestReportPoSOrder, self).setUp()
        self.config = self.basic_config

    def test_report_pos_order_0(self):
        """Test the margin and price_total of a PoS Order with no taxes."""
        product1 = self.create_product('Product 1', self.categ_basic, 150)
        self.categ_all = self.env['pos.category'].search([])
        product1.write({'pos_categ_ids': [odoo.Command.set(self.categ_all.ids)]})

        self.open_new_session()
        session = self.pos_session
        self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [
                (0, 0, {
                    'name': "OL/0001",
                    'product_id': product1.id,
                    'price_unit': 150,
                    'discount': 0,
                    'qty': 1.0,
                    'price_subtotal': 150,
                    'price_subtotal_incl': 150,
                })
            ],
            'amount_total': 150.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })
        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(len(reports.ids), 1)
        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_total, 150)

    def test_report_pos_order_1(self):
        """Test the margin and price_total of a PoS Order with taxes."""

        product1 = self.create_product('Product 1', self.categ_basic, 150, self.taxes['tax10'].id)

        self.open_new_session()
        session = self.pos_session

        self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': product1.id,
                'price_unit': 150,
                'discount': 0,
                'qty': 1.0,
                'price_subtotal': 150,
                'price_subtotal_incl': 165,
            }),],
            'amount_total': 165.0,
            'amount_tax': 15.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_total, 165)

    def test_report_pos_order_2(self):
        """Test the margin and price_total of a PoS Order with discount and no taxes"""

        product1 = self.create_product('Product 1', self.categ_basic, 150)

        self.open_new_session()
        session = self.pos_session

        self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [
                (0, 0, {
                    'name': "OL/0001",
                    'product_id': product1.id,
                    'price_unit': 150,
                    'discount': 10,
                    'qty': 1.0,
                    'price_subtotal': 135,
                    'price_subtotal_incl': 135,
                })
            ],
            'amount_total': 135.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # PoS Orders have negative IDs to avoid conflict, so reports[0] will correspond to the newest order
        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 135)
        self.assertEqual(reports[0].price_total, 135)

    def test_report_pos_order_margin_other_currency(self):
        """Test that the currency_rate set on the order is correctly taken into account when generating the report"""

        product1 = self.create_product('Product 1', self.categ_basic, 150)
        self.open_new_session()
        session = self.pos_session

        self.env['pos.order'].create({
         'session_id': session.id,
            'lines': [
                (0, 0, {
                    'name': "OL/0001",
                    'product_id': product1.id,
                    'price_unit': 300,
                    'discount': 0,
                    'qty': 1.0,
                    'price_subtotal': 300,
                    'price_subtotal_incl': 300,
                })
            ],
            'amount_total': 300.0,
            'amount_tax': 0.0,
            'amount_paid': 300.0,
            'amount_return': 0.0,
            'currency_rate': 2
        })

        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)], order='id')

        self.assertEqual(reports[0].margin, 150)
        self.assertEqual(reports[0].price_subtotal_excl, 150)
        self.assertEqual(reports[0].price_total, 150)

    def test_report_pos_order_future_preset_order_config(self):
        """A future preset order detached from its session on closing keeps its point of sale in the report."""
        product1 = self.create_product('Product 1', self.categ_basic, 150)
        self.open_new_session()
        session = self.pos_session

        def create_order(preset_time):
            return self.env['pos.order'].create({
                'session_id': session.id,
                'lines': [(0, 0, {
                    'name': "OL/0001",
                    'product_id': product1.id,
                    'price_unit': 150,
                    'qty': 1.0,
                    'price_subtotal': 150,
                    'price_subtotal_incl': 150,
                })],
                'amount_total': 150.0,
                'amount_tax': 0.0,
                'amount_paid': 0.0,
                'amount_return': 0.0,
                'preset_time': preset_time,
            })

        future_order = create_order(odoo.fields.Datetime.now() + timedelta(days=2))
        cancelled_order = create_order(odoo.fields.Datetime.now() - timedelta(days=2))
        cancelled_order.action_pos_order_cancel()

        session.close_session_from_ui()
        self.assertEqual(session.state, 'closed')
        self.assertFalse(future_order.session_id)

        reports = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)])
        self.assertRecordValues(reports.sorted(lambda r: r.order_id.id), [
            {'order_id': future_order.id, 'session_id': False, 'config_id': self.config.id},
            {'order_id': cancelled_order.id, 'session_id': session.id, 'config_id': self.config.id},
        ])
