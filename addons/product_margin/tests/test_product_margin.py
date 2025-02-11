# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProductMargin(AccountTestInvoicingCommon):

    def test_product_margin(self):
        ''' In order to test the product_margin module '''

        supplier = self.env['res.partner'].create({'name': 'Supplier'})
        customer = self.env['res.partner'].create({'name': 'Customer'})
        ipad = self.env['product.product'].create({
            'name': 'Ipad',
            'standard_price': 500.0,
            'list_price': 750.0,
        })

        invoices = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': supplier.id,
                'invoice_line_ids': [(0, 0, {'product_id': ipad.id, 'quantity': 10.0, 'price_unit': 300.0})],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': supplier.id,
                'invoice_line_ids': [(0, 0, {'product_id': ipad.id, 'quantity': 4.0, 'price_unit': 450.0})],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': customer.id,
                'invoice_line_ids': [(0, 0, {'product_id': ipad.id, 'quantity': 20.0, 'price_unit': 750.0})],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': customer.id,
                'invoice_line_ids': [(0, 0, {'product_id': ipad.id, 'quantity': 10.0, 'price_unit': 550.0})],
            },
        ])
        invoices.invoice_date = invoices[0].date
        invoices.action_post()

        result = ipad._compute_product_margin_fields_values()

        # Sale turnover ( Quantity * Price Subtotal / Quantity)
        sale_turnover = ((20.0 * 750.00) + (10.0 * 550.00))

        # Expected sale (Total quantity * Sale price)
        sale_expected = (750.00 * 30.0)

        # Purchase total cost (Quantity * Unit price)
        purchase_total_cost = ((10.0 * 300.00) + (4.0 * 450.00))

        # Purchase normal cost ( Total quantity * Cost price)
        purchase_normal_cost = (14.0 * 500.00)

        total_margin = sale_turnover - purchase_total_cost
        expected_margin = sale_expected - purchase_normal_cost

        # Check total margin
        self.assertEqual(result[ipad.id]['total_margin'], total_margin, "Wrong Total Margin.")

        # Check expected margin
        self.assertEqual(result[ipad.id]['expected_margin'], expected_margin, "Wrong Expected Margin.")

    def test_product_margin_negative_price_in_move_lines(self):
        """
        Test that product margins are calculated correctly when move lines
        include negative quantities or prices.
        """
        supplier = self.env['res.partner'].create({'name': 'Supplier'})
        customer = self.env['res.partner'].create({'name': 'Customer'})
        ipad = self.env['product.product'].create({
            'name': 'Ipad',
            'standard_price': 1000.0,
            'list_price': 1000.0,
        })

        customer_invoice = self.env['account.move'].create([{
                'move_type': 'out_invoice',
                'partner_id': customer.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': ipad.id,
                        'price_unit': 1000,
                        'quantity': 2,
                    }),
                    Command.create({
                        'product_id': ipad.id,
                        'price_unit': 1000,
                        'quantity': -1,
                    }),
                ],
            }])

        customer_invoice.action_post()

        results = ipad._compute_product_margin_fields_values()
        self.assertEqual(results[ipad.id]['turnover'], 1000)
        self.assertEqual(results[ipad.id]['total_margin'], 1000)

        vendor_bill = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': supplier.id,
            'invoice_date': '2025-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': ipad.id,
                    'price_unit': 250,
                    'quantity': 2,
                }),
                Command.create({
                    'product_id': ipad.id,
                    'price_unit': 250,
                    'quantity': -1,
                }),
            ],
        }])
        vendor_bill.action_post()

        results = ipad._compute_product_margin_fields_values()
        self.assertEqual(results[ipad.id]['total_cost'], 250)
        self.assertEqual(results[ipad.id]['total_margin'], 750)
