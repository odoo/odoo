# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

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

    def test_report_pos_order_multiple_payment_methods(self):
        """An order split over several payment methods is reported once per method."""

        product1 = self.create_product('Product 1', self.categ_basic, 180)
        self.open_new_session()

        self.env['pos.order'].sync_from_ui([self.create_ui_order_data(
            [(product1, 2)],
            payments=[(self.cash_pm1, 100), (self.bank_pm1, 260)],
        )])

        report = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)])

        self.assertEqual(len(report), 2, "one row per payment method used by the order")
        self.assertEqual(report.mapped('payment_method_id'), self.cash_pm1 | self.bank_pm1)

        # the split does not change what the order as a whole weighs in the report
        self.assertAlmostEqual(sum(report.mapped('price_total')), 360)
        self.assertEqual(sum(report.mapped('product_qty')), 2, "the 2 units are counted once, not once per method")
        self.assertEqual(sum(report.mapped('nbr_lines')), 1)

        cash_row = report.filtered(lambda r: r.payment_method_id == self.cash_pm1)
        bank_row = report.filtered(lambda r: r.payment_method_id == self.bank_pm1)
        # amounts are prorated: each method carries what it actually paid
        self.assertAlmostEqual(cash_row.price_total, 100)
        self.assertAlmostEqual(bank_row.price_total, 260)
        # the goods are not split: they are all reported on the method that paid the most
        self.assertEqual(bank_row.product_qty, 2)
        self.assertEqual(bank_row.nbr_lines, 1)
        self.assertEqual(cash_row.product_qty, 0)
        self.assertEqual(cash_row.nbr_lines, 0)
        # a unit price is not a share of anything
        self.assertAlmostEqual(cash_row.average_price, 180)
        self.assertAlmostEqual(bank_row.average_price, 180)

    def test_report_pos_order_change_is_netted_out(self):
        """The change given back is a negative cash payment: it nets out of the cash share."""

        product1 = self.create_product('Product 2', self.categ_basic, 100)
        self.open_new_session()

        self.env['pos.order'].sync_from_ui([self.create_ui_order_data(
            [(product1, 1)],
            payments=[(self.cash_pm1, 150), (self.cash_pm1, -50)],
        )])

        report = self.env['report.pos.order'].sudo().search([('product_id', '=', product1.id)])

        self.assertEqual(len(report), 1, "the two cash payments are merged into a single row")
        self.assertEqual(report.payment_method_id, self.cash_pm1)
        self.assertAlmostEqual(report.price_total, 100)
        self.assertAlmostEqual(report.product_qty, 1)
