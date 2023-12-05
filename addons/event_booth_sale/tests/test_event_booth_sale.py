# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import tagged, users
from odoo.tools import float_compare


class TestEventBoothSaleWData(TestEventBoothSaleCommon, TestSalesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleWData, cls).setUpClass()

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })

        cls.booth_1, cls.booth_2 = cls.env['event.booth'].create([
            {
                'name': 'Test Booth 1',
                'booth_category_id': cls.event_booth_category_1.id,
                'event_id': cls.event_0.id,
            }, {
                'name': 'Test Booth 2',
                'booth_category_id': cls.event_booth_category_1.id,
                'event_id': cls.event_0.id,
            }
        ])

        cls.event_booth_product.taxes_id = cls.tax_10


class TestEventBoothSale(TestEventBoothSaleWData):

    @users('user_sales_salesman')
    def test_event_booth_prices_with_sale_order(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'pricelist_id': self.test_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.event_booth_product.id,
                    'event_id': self.event_0.id,
                    'event_booth_category_id': self.event_booth_category_1.id,
                    'event_booth_pending_ids': (self.booth_1 + self.booth_2).ids
                })
            ]
        })

        self.assertEqual(self.booth_1.price, self.event_booth_product.list_price,
                         "Booth price should be equal from product price.")
        self.assertEqual(self.event_booth_category_1.with_context(pricelist=self.test_pricelist.id).price_reduce_taxinc, 22.0,
                         "Booth price reduce tax should be equal to its price with 10% taxes ($20.0 + $2.0)")
        # Here we expect the price to be the sum of the booth ($40.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 40.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices ($40.0).")
        self.assertEqual(float_compare(sale_order.amount_total, 44.0, precision_rounding=0.1), 0,
                         "Total amount should be the sum of the booths prices with 10% taxes ($40.0 + $4.0)")

        self.event_booth_category_1.write({'price': 100.0})
        sale_order._recompute_prices()

        self.assertNotEqual(self.booth_1.price, self.event_booth_product.list_price,
                            "Booth price should be different from product price.")
        self.assertEqual(self.event_booth_category_1.with_context(pricelist=self.test_pricelist.id).price_reduce_taxinc, 110.0,
                         "Booth price reduce tax should be equal to its price with 10% taxes ($100.0 + $10.0)")
        # Here we expect the price to be the sum of the booth ($200.0)
        self.assertEqual(float_compare(sale_order.amount_untaxed, 200.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices ($200.0).")
        self.assertEqual(float_compare(sale_order.amount_total, 220.0, precision_rounding=0.1), 0,
                         "Total amount should be the sum of the booths prices with 10% taxes ($200.0 + $20.0).")

        sale_order.pricelist_id = self.test_pricelist_with_discount_included
        sale_order._recompute_prices()

        self.assertEqual(float_compare(sale_order.amount_untaxed, 180.0, precision_rounding=0.1), 0,
                         "Untaxed amount should be the sum of the booths prices with discount 10% ($180.0).")
        self.assertEqual(float_compare(sale_order.amount_total, 198.0, precision_rounding=0.1), 0,
                         "Total amount should be the sum of the booths prices with 10% taxes ($180.0 + $18.0).")

        # Confirm the SO.
        sale_order.action_confirm()

        for booth in self.booth_1 + self.booth_2:
            self.assertEqual(
                booth.sale_order_id.id, sale_order.id,
                "Booth sale order should be the same as the original sale order.")
            self.assertEqual(
                booth.sale_order_line_id.id, sale_order.order_line[0].id,
                "Booth sale order line should the same as the order line in the original sale order.")
            self.assertEqual(
                booth.partner_id.id, self.event_customer.id,
                "Booth partner should be the same as sale order customer.")
            self.assertEqual(
                booth.contact_email, self.event_customer.email,
                "Booth contact email should be the same as sale order customer email.")
            self.assertEqual(
                booth.contact_name, self.event_customer.name,
                "Booth contact name should be the same as sale order customer name.")
            self.assertEqual(
                booth.contact_phone, self.event_customer.phone,
                "Booth contact phone should be the same as sale order customer phone.")
            self.assertEqual(
                booth.state, 'unavailable',
                "Booth should not be available anymore.")


@tagged('post_install', '-at_install')
class TestEventBoothSaleInvoice(AccountTestInvoicingCommon, TestEventBoothSaleWData):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Add group `group_account_invoice` to user_sales_salesman to allow to pay the invoice
        cls.user_sales_salesman.groups_id += cls.env.ref('account.group_account_invoice')

    @users('user_sales_salesman')
    def test_event_booth_with_invoice(self):
        booth = self.booth_1.with_env(self.env)
        self.assertEqual(booth.state, 'available')

        sale_order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'pricelist_id': self.test_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.event_booth_product.id,
                    'event_id': self.event_0.id,
                    'event_booth_pending_ids': booth.ids
                })
            ]
        })
        sale_order.action_confirm()
        self.assertEqual(booth.state, 'unavailable')
        self.assertFalse(booth.is_paid)

        # Create and check that the invoice was created
        invoice = sale_order._create_invoices()
        self.assertEqual(len(sale_order.invoice_ids), 1, "Invoice not created.")

        # Confirm the invoice and check SO invoice status
        invoice.action_post()
        self.assertEqual(
            sale_order.invoice_status, 'invoiced',
            f"Order is in '{sale_order.invoice_status}' status while it should be 'invoiced'.")
        # Pay the invoice.
        journal = self.env['account.journal'].search([('type', '=', 'cash'), ('company_id', '=', sale_order.company_id.id)], limit=1)

        register_payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'journal_id': journal.id,
        })
        register_payments._create_payments()

        # Check the invoice payment state after paying the invoice
        in_payment_state = invoice._get_invoice_in_payment_state()
        self.assertEqual(invoice.payment_state, in_payment_state,
            f"Invoice payment is in '{invoice.payment_state}' status while it should be '{in_payment_state}'.")

        self.assertEqual(booth.state, 'unavailable')
        self.assertTrue(booth.is_paid)
