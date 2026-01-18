# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProductMargin(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.supplier = cls.env['res.partner'].create({'name': 'Supplier'})
        cls.customer = cls.env['res.partner'].create({'name': 'Customer'})
        cls.ipad = cls.env['product.product'].create({
            'name': 'Ipad',
            'standard_price': 500.0,
            'list_price': 750.0,
        })

        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': cls.supplier.id,
                'invoice_line_ids': [(0, 0, {'product_id': cls.ipad.id, 'quantity': 10.0, 'price_unit': 300.0})],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': cls.supplier.id,
                'invoice_line_ids': [(0, 0, {'product_id': cls.ipad.id, 'quantity': 4.0, 'price_unit': 450.0})],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': cls.customer.id,
                'invoice_line_ids': [(0, 0, {'product_id': cls.ipad.id, 'quantity': 20.0, 'price_unit': 750.0})],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': cls.customer.id,
                'invoice_line_ids': [(0, 0, {'product_id': cls.ipad.id, 'quantity': 10.0, 'price_unit': 550.0})],
            },
        ])
        cls.invoices.invoice_date = cls.invoices[0].date

    def test_aggregates(self):
        model = self.env['product.product']
        field_names = [
            'turnover', 'sale_avg_price', 'sale_num_invoiced', 'purchase_num_invoiced',
            'sales_gap', 'purchase_gap', 'total_cost', 'sale_expected', 'normal_cost',
            'total_margin', 'expected_margin', 'total_margin_rate', 'expected_margin_rate',
        ]
        self.assertEqual(
            model.fields_get(field_names, ['aggregator']),
            {field_name: {'aggregator': 'sum'} for field_name in field_names},
            f"Fields {', '.join(map(repr, field_names))} must be flagged as aggregatable.",
        )

    def test_product_margin(self):
        ''' In order to test the product_margin module '''

        self.invoices.action_post()

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
        self.assertEqual(self.ipad.total_margin, total_margin, "Wrong Total Margin.")

        # Check expected margin
        self.assertEqual(self.ipad.expected_margin, expected_margin, "Wrong Expected Margin.")

        # Check that read_group doesn't generate an UPDATE and returns the right answer
        self.ipad.invalidate_recordset()
        with patch.object(self.registry['product.product'], 'write') as write_method:
            total_margin_sum, expected_margin_sum = self.env['product.product']._read_group(
                [('id', '=', self.ipad.id)],
                aggregates=['total_margin:sum', 'expected_margin:sum'],
            )[0]
            self.assertEqual(total_margin_sum, total_margin)
            self.assertEqual(expected_margin_sum, expected_margin)
            write_method.assert_not_called()

    def test_product_margin_negative_price_in_move_lines(self):
        """
        Test that product margins are calculated correctly when move lines
        include negative quantities or prices.
        """
        self.ipad.write({
            'standard_price': 1000.0,
            'list_price': 1000.0,
        })

        customer_invoice = self.env['account.move'].create([{
                'move_type': 'out_invoice',
                'partner_id': self.customer.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.ipad.id,
                        'price_unit': 1000,
                        'quantity': 2,
                    }),
                    Command.create({
                        'product_id': self.ipad.id,
                        'price_unit': 1000,
                        'quantity': -1,
                    }),
                ],
            }])

        customer_invoice.action_post()

        results = self.ipad._compute_product_margin_fields_values()
        self.assertEqual(results[self.ipad.id]['turnover'], 1000)
        self.assertEqual(results[self.ipad.id]['total_margin'], 1000)

        vendor_bill = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.supplier.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.ipad.id,
                    'price_unit': 250,
                    'quantity': 2,
                }),
                Command.create({
                    'product_id': self.ipad.id,
                    'price_unit': 250,
                    'quantity': -1,
                }),
            ],
        }])
        vendor_bill.action_post()

        results = self.ipad._compute_product_margin_fields_values()
        self.assertEqual(results[self.ipad.id]['total_cost'], 250)
        self.assertEqual(results[self.ipad.id]['total_margin'], 750)

    def test_product_margin_read_grouping_sets(self):
        """
        Test that product margins are aggregated properly when using _read_grouping_sets.
        """
        self.invoices.action_post()

        # Create a category and two other products.
        categ_portable = self.env['product.category'].create({'name': 'Portable'})
        iphone, imac = self.env['product.product'].create([
            {
                'name': 'iPhone',
                'standard_price': 1000,
                'list_price': 1200,
                'uom_id': self.uom_dozen.id,
                'categ_id': categ_portable.id,
            },
            {
                'name': 'iMac',
                'standard_price': 1500,
                'list_price': 1800,
            },
        ])

        # Update products
        self.ipad.write({'categ_id': categ_portable.id})

        # Create invoices for iPhone and iMac
        invoices = self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'partner_id': self.supplier.id,
                'invoice_line_ids': [
                    Command.create({'product_id': iphone.id, 'quantity': 10.0, 'price_unit': 600.0}),
                    Command.create({'product_id': imac.id, 'quantity': 10.0, 'price_unit': 900.0}),
                ],
            },
            {
                'move_type': 'in_invoice',
                'partner_id': self.supplier.id,
                'invoice_line_ids': [
                    Command.create({'product_id': iphone.id, 'quantity': 4.0, 'price_unit': 900.0}),
                    Command.create({'product_id': imac.id, 'quantity': 4.0, 'price_unit': 1350.0}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.customer.id,
                'invoice_line_ids': [
                    Command.create({'product_id': iphone.id, 'quantity': 20.0, 'price_unit': 1500.0}),
                    Command.create({'product_id': imac.id, 'quantity': 20.0, 'price_unit': 2250.0}),
                ],
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.customer.id,
                'invoice_line_ids': [
                    Command.create({'product_id': iphone.id, 'quantity': 10.0, 'price_unit': 1100.0}),
                    Command.create({'product_id': imac.id, 'quantity': 10.0, 'price_unit': 1650.0}),
                ],
            },
        ])
        invoices.invoice_date = fields.Date.today()
        invoices.action_post()

        # Expected Values

        # ipad (Portable, Units):
        #   sale_turnover = (20 * 750) + (10 * 550) = 20500
        #   purchase_total_cost = (10 * 300) + (4 * 450) = 4800
        #   sale_expected = 750 * 30 = 22500
        #   purchase_expected = 14 * 500 = 7000
        #   total_margin = 20500 - 4800 = 15700
        #   expected_margin = 22500 - 7000 = 15500

        # iphone (Portable, Dozens):
        #   sale_turnover = (20 * 1500) + (10 * 1100) = 41000
        #   purchase_total_cost = (10 * 600) + (4 * 900) = 9600
        #   sale_expected = 1200 * 30 = 36000
        #   purchase_expected = 14 * 1000 = 14000
        #   total_margin = 41000 - 9600 = 31400
        #   expected_margin = 36000 - 14000 = 22000

        # imac (All, Units):
        #   sale_turnover = (20 * 2250) + (10 * 1650) = 61500
        #   purchase_total_cost = (10 * 900) + (4 * 1350) = 14400
        #   sale_expected = 1800 * 30 = 54000
        #   purchase_expected = 14 * 1500 = 21000
        #   total_margin = 61500 - 14400 = 47100
        #   expected_margin = 54000 - 21000 = 33000

        result = self.env['product.product']._read_grouping_sets(
            [('id', 'in', [iphone.id, imac.id, self.ipad.id])],
            grouping_sets=[['categ_id', 'uom_id'], ['categ_id'], ['uom_id'], []],
            aggregates=['total_margin:sum', 'expected_margin:sum'],
        )

        # 1. ['categ_id', 'uom_id']
        res_cat_uom = result[0]
        self.assertEqual(len(res_cat_uom), 3)
        map_cat_uom = {(r[0], r[1]): (r[2], r[3]) for r in res_cat_uom}
        self.assertEqual(map_cat_uom[categ_portable, self.uom_unit], (15700, 15500))
        self.assertEqual(map_cat_uom[categ_portable, self.uom_dozen], (31400, 22000))
        no_categ = self.env['product.category']
        self.assertEqual(map_cat_uom[no_categ, self.uom_unit], (47100, 33000))

        # 2. ['categ_id']
        res_cat = result[1]
        map_cat = {r[0]: (r[1], r[2]) for r in res_cat}
        self.assertEqual(map_cat[categ_portable], (47100, 37500))
        self.assertEqual(map_cat[no_categ], (47100, 33000))

        # 3. ['uom_id']
        res_uom = result[2]
        map_uom = {r[0]: (r[1], r[2]) for r in res_uom}
        self.assertEqual(map_uom[self.uom_unit], (62800, 48500))
        self.assertEqual(map_uom[self.uom_dozen], (31400, 22000))

        # 4. []
        res_all = result[3]
        self.assertEqual(res_all[0], (94200, 70500))
