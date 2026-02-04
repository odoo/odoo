# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command, fields


@tagged('post_install', '-at_install')
class TestAccountInvoiceReport(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 3,
                        'price_unit': 750,
                    }),
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 3000,
                    }),
                ]
            },
            {
                'move_type': 'out_receipt',
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 6000,
                    }),
                ]
            },
            {
                'move_type': 'out_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 1200,
                    }),
                ]
            },
            {
                'move_type': 'in_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 60,
                    }),
                ]
            },
            {
                'move_type': 'in_receipt',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 60,
                    }),
                ]
            },
            {
                'move_type': 'in_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 12,
                    }),
                ]
            },
            {
                'move_type': 'out_refund',
                'partner_id': cls.partner_a.id,
                'invoice_date': fields.Date.from_string('2017-01-01'),
                'currency_id': cls.currency_data['currency'].id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': cls.product_a.id,
                        'quantity': 1,
                        'price_unit': 2400,
                    }),
                ]
            },
        ])

    def assertInvoiceReportValues(self, expected_values_list):
        reports = self.env['account.invoice.report'].search([('company_id', '=', self.company_data['company'].id)], order='price_subtotal DESC, quantity ASC')
        expected_values_dict = [{
            'price_average': vals[0],
            'price_subtotal': vals[1],
            'quantity': vals[2],
            'price_margin': vals[3],
            'inventory_value': vals[4],
        } for vals in expected_values_list]

        self.assertRecordValues(reports, expected_values_dict)

    def test_invoice_report_multiple_types(self):
        self.assertInvoiceReportValues([
            # pylint: disable=bad-whitespace
            # price_average, price_subtotal, quantity, price_margin, inventory_value
            [          2000,           2000,        1,         1200,            -800], # price_unit = 6000, currency.rate = 3.0
            [          1000,           1000,        1,          200,            -800], # price_unit = 3000, currency.rate = 3.0
            [           250,            750,        3,        -1650,           -2400], # price_unit = 750,  currency.rate = 2.0
            [             6,              6,        1,            0,            -800], # price_unit = 12,   currency.rate = 2.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [           600,           -600,       -1,          200,             800],  # price_unit = 1200, currency.rate = 2.0
            [          1200,          -1200,       -1,         -400,             800],  # price_unit = 2400, currency.rate = 2.0
        ])

    def test_invoice_report_multicompany_product_cost(self):
        """
        In a multicompany environment, if you define one product with different standard price per company
        the invoice analysis report should only display the product from the company
        Standard Price in Company A: 800 (default setup)
        Standard Price in Company B: 700
        -> invoice report for Company A should remain the same
        """
        self.product_a.with_company(self.company_data_2.get('company')).write({'standard_price': 700.0})
        self.assertInvoiceReportValues([
            # pylint: disable=bad-whitespace
            # price_average, price_subtotal, quantity, price_margin, inventory_value
            [          2000,           2000,        1,         1200,            -800], # price_unit = 6000, currency.rate = 3.0
            [          1000,           1000,        1,          200,            -800], # price_unit = 3000, currency.rate = 3.0
            [           250,            750,        3,        -1650,           -2400], # price_unit = 750,  currency.rate = 2.0
            [             6,              6,        1,            0,            -800], # price_unit = 12,   currency.rate = 2.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [            20,            -20,       -1,            0,             800], # price_unit = 60,   currency.rate = 3.0
            [           600,           -600,       -1,          200,             800],  # price_unit = 1200, currency.rate = 2.0
            [          1200,          -1200,       -1,         -400,             800],  # price_unit = 2400, currency.rate = 2.0
        ])

    def test_avg_price_calculation(self):
        """
        Check that the average is correctly calculated based on the total price and quantity:
            3 lines:
                - 10 units * 10$
                -  5 units *  5$
                - 20 units *  2$
            Total quantity: 35
            Total price: 165$
            Average: 165 / 35 = 4.71
        """
        product = self.product_a.copy()
        invoice = self.env["account.move"].create({
            'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': self.env.company.currency_id.id,
                'invoice_line_ids': [
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 10,
                        'price_unit': 10,
                    }),
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 5,
                        'price_unit': 5,
                    }),
                    (0, None, {
                        'product_id': product.id,
                        'quantity': 20,
                        'price_unit': 2,
                    }),
                ]
        })
        invoice.action_post()

        report = self.env['account.invoice.report'].read_group(
            [('product_id', '=', product.id)],
            ['price_subtotal:sum', 'quantity:sum', 'price_average:avg'],
            [],
        )
        self.assertEqual(report[0]['quantity'], 35)
        self.assertEqual(report[0]['price_subtotal'], 165)
        self.assertEqual(round(report[0]['price_average'], 2), 4.71)

        # ensure that it works with only 'price_average:avg' in fields
        report = self.env['account.invoice.report'].read_group(
            [('product_id', '=', product.id)],
            ['price_average:avg'],
            [],
        )
        self.assertEqual(round(report[0]['price_average'], 2), 4.71)

        def _apply_combination_on_report_pivot(combination):
            report = self.env['account.invoice.report'].read_group(
                [],
                combination,
                [],
            )
            for field in combination:
                self.assertTrue(field.split(':')[0] in report[0])

        _apply_combination_on_report_pivot(['price_average:avg', 'price_subtotal:sum'])
        _apply_combination_on_report_pivot(['price_average:avg', 'quantity:sum'])

    def test_inventory_margin_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 750,
                }),
            ],
        })
        egy_company = self.env['res.company'].create({
            'name': 'Egyptian Company',
            'currency_id': self.env.ref('base.EGP').id,
            'user_ids': [Command.set(self.env.user.ids)],
        })
        report = self.env['account.invoice.report'].search(
            [('move_id', '=', invoice.id)],
        )
        self.assertEqual(report.inventory_value, -800)
        self.assertEqual(report.price_margin, -50)
        self.env['res.currency.rate'].create({
            'name': '2017-11-03',
            'rate': 2,
            'currency_id': self.env.ref('base.EGP').id,
            'company_id': egy_company.id,
        })
        self.env.flush_all()
        self.env.user.company_id = egy_company
        self.env['account.invoice.report'].invalidate_model()
        report = self.env['account.invoice.report'].search(
            [('move_id', '=', invoice.id)],
        )
        self.assertEqual(report.inventory_value, -1600)
        self.assertEqual(report.price_margin, -100)
