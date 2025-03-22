# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields


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
        ])

    def assertInvoiceReportValues(self, expected_values_list):
        reports = self.env['account.invoice.report'].search([('company_id', '=', self.company_data['company'].id)], order='price_subtotal DESC, quantity ASC')
        expected_values_dict = [{
            'price_average': vals[0],
            'price_subtotal': vals[1],
            'quantity': vals[2],
        } for vals in expected_values_list]

        self.assertRecordValues(reports, expected_values_dict)

    def test_invoice_report_multiple_types(self):
        self.assertInvoiceReportValues([
            #price_average   price_subtotal  quantity
            [2000, 2000, 1],
            [1000, 1000, 1],
            [250, 750, 3],
            [6, 6, 1],
            [20, -20, -1],
            [20, -20, -1],
            [600, -600, -1],
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
