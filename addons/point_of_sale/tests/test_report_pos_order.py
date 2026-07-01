# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo import Command
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

    def test_report_pos_order_round_globally_total(self):
        """Ensure report total matches order total when taxes are rounded globally."""
        company = self.env.company
        company.tax_calculation_rounding_method = 'round_globally'

        tax8 = self.taxes['tax8']
        tax7 = self.taxes['tax7']
        product_tax8_a = self.create_product('Product tax8 a', self.categ_basic, 25.99, tax_ids=tax8.ids)
        product_tax8_b = self.create_product('Product tax8 b', self.categ_basic, 16.73, tax_ids=tax8.ids)
        product_tax7_a = self.create_product('Product tax7 a', self.categ_basic, 13.07, tax_ids=tax7.ids)
        product_tax7_b = self.create_product('Product tax7 b', self.categ_basic, 5.07, tax_ids=tax7.ids)

        self.open_new_session()
        session = self.pos_session
        currency = session.currency_id

        order = self.env['pos.order'].create({
            'session_id': session.id,
            'lines': [Command.create({
                    'name': "OL/0001",
                    'product_id': product_tax8_a.id,
                    'price_unit': 25.99,
                    'discount': 0,
                    'qty': 2.0,
                    'tax_ids': [Command.set(tax8.ids)],
                    'price_subtotal': 51.98,
                    'price_subtotal_incl': 56.14,
                }), Command.create({
                    'name': "OL/0002",
                    'product_id': product_tax7_a.id,
                    'price_unit': 13.08,
                    'discount': 0,
                    'qty': 1.0,
                    'tax_ids': [Command.set(tax7.ids)],
                    'price_subtotal': 13.08,
                    'price_subtotal_incl': 14.00,
                }), Command.create({
                    'name': "OL/0003",
                    'product_id': product_tax8_b.id,
                    'price_unit': 16.73,
                    'discount': 0,
                    'qty': 3.0,
                    'tax_ids': [Command.set(tax8.ids)],
                    'price_subtotal': 50.19,
                    'price_subtotal_incl': 54.21,
                }), Command.create({
                    'name': "OL/0004",
                    'product_id': product_tax7_b.id,
                    'price_unit': 5.08,
                    'discount': 0,
                    'qty': 1.0,
                    'tax_ids': [Command.set(tax7.ids)],
                    'price_subtotal': 5.08,
                    'price_subtotal_incl': 5.44,
                }),
            ],
            'amount_total': 129.77,
            'amount_tax': 9.44,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        self.env.flush_all()

        reports = self.env['report.pos.order'].sudo().search([('order_id', '=', order.id)], order='id')
        report_total = currency.round(sum(reports.mapped('price_total')))

        tax7_group_total = currency.round((order.lines[1].price_subtotal + order.lines[3].price_subtotal) * 1.07)
        tax8_group_total = currency.round((order.lines[0].price_subtotal + order.lines[2].price_subtotal) * 1.08)

        def _assert_group_total(tax, product_ids):
            expected_total = tax7_group_total if tax == tax7 else tax8_group_total
            report_group_total = currency.round(sum(
                reports.filtered(lambda r: r.product_id.id in product_ids).mapped('price_total'),
            ))
            self.assertAlmostEqual(report_group_total, expected_total, places=2)

        _assert_group_total(tax8, [product_tax8_a.id, product_tax8_b.id])
        _assert_group_total(tax7, [product_tax7_a.id, product_tax7_b.id])
        self.assertAlmostEqual(report_total, order.amount_total, places=2)
