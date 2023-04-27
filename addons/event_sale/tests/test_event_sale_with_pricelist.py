# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo.addons.event_sale.tests.common import TestEventSaleTicketWithPriceListCommon
from odoo.tests import tagged


@tagged('event_flow')
class TestEventSaleTicketWithPriceList(TestEventSaleTicketWithPriceListCommon):
    """Extensive test of event ticket sales using price list.

    Multiple event tickets (with various prices) can be linked to a single product.
    To easily integrate price list (which is based on product) features into event ticket, we override through
    a context variable the product price during the computation of the price.
    The goal of this test is to verify that the price is correctly computed with this mechanism using various
    configuration of the price list.
    Note that as this mechanism is duplicated in product and product template, we test both of them.
    """
    @classmethod
    def setUpClass(cls):
        super(TestEventSaleTicketWithPriceList, cls).setUpClass()
        cls.ticket_price = 100.0
        cls.event_ticket = cls.env['event.event.ticket'].create({
            'name': 'Event ticket',
            'price': cls.ticket_price,
            'event_id': cls.event_0.id,
            'product_id': cls.event_product.product_variant_id.id,
        })

    def create_sale_order(self, qty):
        """Create a sale order for qty of the event_ticket.

        :param int qty: number of ticket ordered
        :return: (sale_order, sale_order_line)
        """
        so = self.env['sale.order'].create({
            'partner_id': self.env.user.partner_id.id,
            'pricelist_id': self.price_list.id,
            'date_order': self.now,
        })
        sol = self.env['sale.order.line'].create({
            'product_id': self.product_or_template.product_variant_id.id,
            'order_id': so.id,
            'event_id': self.event_0.id,
            'event_ticket_id': self.event_ticket.id,
            'product_uom_qty': qty,
        })
        return so, sol

    def assert_amount_total(self, actual_sale_order, expected_amount_total, qty, msg):
        """ Assert that the sale order amount total and the ticket price reduce tax incl have the expected value.

        The goal is to test the 2 ways of computing the price (based on the price list): through sale order and
        through ticket.

        Assert that actual_sale_order.amount_total = expected_amount_total
        Assert that amount total computed with ticket price reduce tax incl = expected_amount_total
        """
        with self.subTest(msg, actual_sale_order=actual_sale_order,
                          expected_amount_total=expected_amount_total, qty=qty):
            order_qty_msg = f'(qty: {qty})'
            self.assertAlmostEqual(actual_sale_order.amount_total, expected_amount_total,
                                   msg=f'Sale order amount total: {msg} {order_qty_msg}',
                                   delta=self.precision_delta * qty)  # because price_unit is rounded then mult by qty
            amount_total_computed_with_price_reduce = self.event_ticket.currency_id._convert(
                self.event_ticket.with_context({
                'pricelist': self.price_list.id,
                'quantity': qty}).price_reduce_taxinc * qty,
                self.price_list.currency_id, self.price_list.company_id or self.env.company, self.now, round=False)
            self.assertAlmostEqual(amount_total_computed_with_price_reduce, expected_amount_total,
                                   msg=f'Amount total computed with price reduce tax incl: {msg} {order_qty_msg}',
                                   delta=self.precision_delta * qty)

    def test_ticket_price_with_price_list_extensive(self):
        # Only vary price list currency because product and event currency are related to company.currency (see models)
        for currency, use_product_tpl in itertools.product((self.usd_currency, self.eur_currency), (False, True)):
            # For all tests, the following values are fixed by the setup:
            # ticket_price = 100, product_lst_price = 10, product_standard_price = 30
            self.product_or_template = self.event_product_templ if use_product_tpl else self.event_product
            self.event_ticket.write({
                'product_id': self.product_or_template.product_variant_id.id,
                'price': self.ticket_price,  # If not written, the ticket will get the price from the product
            })

            descr = f'(using {"product template" if use_product_tpl else "product"}, price list in {currency.name})'
            self.configure_pricelist(rule_type='formula', rule_amount=20.0, min_qty=2,
                                     price_list_currency=currency)
            sale_order, sale_order_line = self.create_sale_order(qty=1)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(110),
                                     qty=1,
                                     msg=f"Ticket is $100 + 10% tax -> 110 {descr}")
            sale_order_line.write({'product_uom_qty': 2})
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(176),
                                     qty=2,
                                     msg=f"2 tickets at $100 -20%  -> $80 -> $160 + 10% tax -> 176 {descr}")

            self.configure_pricelist(rule_type='formula', rule_amount=20.0, min_qty=1,
                                     price_list_currency=currency)
            sale_order, sale_order_line = self.create_sale_order(qty=1)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(88),
                                     msg=f"Ticket at $100 -20%  -> $80 + 10% tax -> 88 {descr}",
                                     qty=1)

            self.configure_pricelist(rule_type='fixed', rule_amount=10.0, min_qty=2,
                                     price_list_currency=currency)
            sale_order, sale_order_line = self.create_sale_order(qty=1)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(110),
                                     msg=f"Ticket is $100 + 10% tax -> 110 {descr}",
                                     qty=1)
            sale_order_line.write({'product_uom_qty': 2})
            ten_currency = '$10' if currency == self.usd_currency else '10€'
            self.assert_amount_total(sale_order,
                                     22,  # No conversion because the price is expressed in price list currency
                                     msg=f"2 tickets at {ten_currency} +10% -> 22 {descr}",
                                     qty=2)

            self.configure_pricelist(rule_type='percentage', rule_amount=20.0, min_qty=1,
                                     price_list_currency=currency)
            sale_order, sale_order_line = self.create_sale_order(qty=1)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(88),
                                     msg=f"Ticket at $100 -20%  -> $80 + 10% tax -> 88 {descr}",
                                     qty=1)

            self.configure_pricelist(rule_type='percentage', rule_amount=20.0, min_qty=1,
                                     rule_based_on='standard_price',
                                     price_list_currency=currency)
            sale_order, sale_order_line = self.create_sale_order(qty=1)
            self.assert_amount_total(sale_order,
                                     self.convert_to_sale_order_currency(26.4),
                                     msg=f"Cost of ticket at $30 -20%  -> $24 + 10% tax -> 26.4 {descr}",
                                     qty=1)
