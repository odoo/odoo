# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.addons.event_sale.tests.common import TestEventSaleTicketWithPriceListCommon
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.tests.common import tagged, users
from odoo.tools import float_compare


class TestEventBoothSaleWData(TestEventBoothSaleCommon, TestSalesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleWData, cls).setUpClass()

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'auto_confirm': True,
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
                booth.contact_mobile, self.event_customer.mobile,
                "Booth contact mobile should be the same as sale order customer mobile.")
            self.assertEqual(
                booth.contact_phone, self.event_customer.phone,
                "Booth contact phone should be the same as sale order customer phone.")
            self.assertEqual(
                booth.state, 'unavailable',
                "Booth should not be available anymore.")


@tagged('post_install', '-at_install')
class TestEventBoothSaleWithPriceList(TestEventSaleTicketWithPriceListCommon):
    """Extensive test of booth sales using price list.

    As with tickets, multiple booths (with various prices) can be linked to a single product.
    This test verifies that the price is correctly computed for various configuration (price list, ...).
    See TestEventSaleTicketWithPriceList for more details as it is very similar.
    """
    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleWithPriceList, cls).setUpClass()
        # Reuse event_product and event_product_templ configured instances and adapt them
        cls.booth_product = cls.event_product
        cls.booth_product_templ = cls.event_product_templ
        cls.booth_product.write({'detailed_type': 'event_booth'})
        cls.booth_product_templ.write({'detailed_type': 'event_booth'})

        cls.booth_price = 100.0
        cls.booth_cat = cls.env['event.booth.category'].create({
            'name': 'Custom',
            'description': '<p>Custom</p>',
            'price': cls.booth_price,
        })
        cls.booth_0 = cls.env['event.booth'].create({
            'name': 'Event booth 0',
            'event_id': cls.event_0.id,
            'booth_category_id': cls.booth_cat.id,
        })
        cls.booth_1 = cls.env['event.booth'].create({
            'name': 'Event booth 1',
            'event_id': cls.event_0.id,
            'booth_category_id': cls.booth_cat.id,
        })

    def create_sale_order_booth(self, qty):
        """Create a sale order for the booth_0 if qty == 1 and for booth_0 and booth_1 if qty == 2 (booths are unique)

        :param int qty: number of booth ordered, must be 1 or 2
        :return: sale_order_line
        """
        if qty not in (1, 2):
            raise ValueError('Parameter qty must be 1 or 2')
        booths = self.booth_0
        if qty == 2:
            booths += self.booth_1
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'pricelist_id': self.price_list.id,
            'date_order': self.now,
            'company_id': self.env.company.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_or_template.product_variant_id.id,
            'order_id': so.id,
            'event_id': self.event_0.id,
            'event_booth_category_id': self.booth_cat.id,
            'event_booth_pending_ids': booths.mapped('id'),
            'product_uom_qty': 1,
        })
        return so

    def assert_amount_total(self, actual_sale_order, expected_1_unit_price, qty, msg):
        """ Assert that the sale order amount total and the booth cat price reduce tax incl have the expected value.

        The goal is to test the 2 ways of computing the price (based on the price list): through sale order and
        through booth category.

        Assert that actual_sale_order.amount_total = expected_amount_total
        Assert that amount total computed with booth category price reduce tax incl = expected_amount_total
       """
        with self.subTest(msg, actual_sale_order=actual_sale_order,
                          expected_1_unit_price=expected_1_unit_price, qty=qty):
            order_qty_msg = '(2 booths ordered at the same price each)' if qty == 2 else ''
            self.assertAlmostEqual(actual_sale_order.amount_total, expected_1_unit_price * qty,
                                   msg=f'Sale order: {msg} {order_qty_msg}',
                                   delta=self.precision_delta * qty)  # * qty because price_unit is rounded then mult by qty
            price_reduce_taxinc = self.booth_cat.currency_id._convert(
                self.booth_cat.with_context({'pricelist': self.price_list.id}).price_reduce_taxinc,
                self.price_list.currency_id, self.price_list.company_id or self.env.company, self.now, round=False)
            self.assertAlmostEqual(price_reduce_taxinc, expected_1_unit_price,
                                   msg=f'booth category price reduce tax included: {msg} {order_qty_msg}',
                                   delta=self.precision_delta * qty)  # * qty because price_unit is rounded then mult by qty

    def test_booth_price_with_price_list_extensive(self):
        # Only vary price list currency because product and booth currency are related to company.currency (see models)
        cases = [(currency, is_product_tpl, qty)
                 for currency in (self.usd_currency, self.eur_currency)
                 for is_product_tpl in (False, True)
                 for qty in (1, 2)]
        for currency, use_product_tpl, qty in cases:
            # For all tests, the following values are fixed by the setup:
            # booth_price = 100, product_lst_price = 10, product_standard_price = 30
            self.product_or_template = self.booth_product_templ if use_product_tpl else self.booth_product
            self.booth_cat.write({
                'product_id': self.product_or_template.product_variant_id.id,
                'price': self.booth_price, # If not written, the booth will get the price from the product
            })

            descr = f'(using {"product template" if use_product_tpl else "product"}, price list in {currency.name})'
            pricelist_config = dict(rule_type='formula', rule_amount=20.0, min_qty=2)
            self.configure_pricelist(price_list_currency=currency, **pricelist_config)
            sale_order = self.create_sale_order_booth(qty)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(110),
                                     qty,
                                     msg=f"Booth is $100 + 10% tax -> 110 {descr} (price list: {pricelist_config})")

            pricelist_config = dict(rule_type='formula', rule_amount=20.0, min_qty=1)
            self.configure_pricelist(price_list_currency=currency, **pricelist_config)
            sale_order = self.create_sale_order_booth(qty)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(88),
                                     qty,
                                     msg=f"Booth at $100 -20%  -> $80 + 10% tax -> 88 {descr} "
                                         f"(price list: {pricelist_config})")

            pricelist_config = dict(rule_type='fixed', rule_amount=10.0, min_qty=1)
            self.configure_pricelist(price_list_currency=currency, **pricelist_config)
            sale_order = self.create_sale_order_booth(qty)
            self.assert_amount_total(sale_order,
                                     11,  # No conversion because the price is expressed in price list currency
                                     qty,
                                     msg=f"Booth is $10 + 10% tax -> 11 {descr} (price list: {pricelist_config})")

            pricelist_config = dict(rule_type='percentage', rule_amount=20.0, min_qty=1)
            self.configure_pricelist(price_list_currency=currency, **pricelist_config)
            sale_order = self.create_sale_order_booth(qty)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(88),
                                     qty,
                                     msg=f"Booth at $100 -20%  -> $80 + 10% tax -> 88 {descr} "
                                         f"(price list: {pricelist_config})")

            pricelist_config = dict(rule_type='percentage', rule_amount=20.0, min_qty=1,
                                    rule_based_on='standard_price')
            self.configure_pricelist(price_list_currency=currency, **pricelist_config)
            sale_order = self.create_sale_order_booth(qty)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(26.4),
                                     qty,
                                     msg=f"Cost of booth at $30 -20%  -> $24 + 10% tax -> 26.4 {descr} "
                                         f"(price list: {pricelist_config})")


@tagged('post_install', '-at_install')
class TestEventBoothSaleInvoice(TestEventBoothSaleWData):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothSaleInvoice, cls).setUpClass()

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
