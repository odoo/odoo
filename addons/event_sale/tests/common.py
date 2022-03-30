# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command, fields
from odoo.addons.event.tests.common import EventCase
from odoo.addons.sales_team.tests.common import TestSalesCommon


class TestEventSaleCommon(EventCase, TestSalesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventSaleCommon, cls).setUpClass()

        product_values = {
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'standard_price': 30.0,
            'detailed_type': 'event',
        }
        cls.event_product = cls.env['product.product'].create(product_values)
        cls.event_product_templ = cls.env['product.template'].create(product_values)

        cls.event_type_tickets = cls.env['event.type'].create({
            'name': 'Update Type',
            'auto_confirm': True,
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [
                (0, 0, {'name': 'First Ticket',
                        'product_id': cls.event_product.id,
                        'seats_max': 5,
                       })
            ],
            'event_type_mail_ids': [],
        })

        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
        })


class TestEventSaleTicketWithPriceListCommon(TestEventSaleCommon):
    @classmethod
    def setUpClass(cls):
        super(TestEventSaleTicketWithPriceListCommon, cls).setUpClass()
        currencies = cls.env['res.currency'].with_context(active_test=False).search([('name', 'in', ['USD', 'EUR'])])
        cls.usd_currency = currencies.filtered(lambda r: r.name == 'USD')
        cls.eur_currency = currencies.filtered(lambda r: r.name == 'EUR')
        cls.company_currency = cls.env.company.currency_id
        cls.other_currency = cls.eur_currency if cls.company_currency != cls.eur_currency else cls.usd_currency
        cls.precision_delta = cls.other_currency.rounding
        cls.price_list = cls.env['product.pricelist'].create({
            'name': 'Sale pricelist',
            'discount_policy': 'with_discount',
        })
        cls.tax = cls.env['account.tax'].create({
            'name': "Tax 10",
            'amount': 10,
        })
        cls.event_product.write({'taxes_id': [Command.set([cls.tax.id])], })
        cls.event_product_templ.write({'taxes_id': [Command.set([cls.tax.id])], })
        cls.now = datetime.now()
        cls.rule_type_to_field = {  # define which field should be written for a given rule_type
            'fixed': 'fixed_price',
            'percentage': 'percent_price',
            'formula': 'price_discount',
        }
        cls.product_or_template = cls.event_product

    def configure_pricelist(self, rule_type, rule_amount, min_qty,
                            rule_based_on=None, price_list_currency=None):
        """ Configure price list currency and items.

        :param str rule_type: price list item compute_price (formula, fixed or percentage)
        :param float rule_amount: amount used for the rule_type (ex.: rule_type = fixed, it means the fixed price)
        :param int min_qty: minimum quantity for the rule to be applied
        :param str rule_based_on: by default on the ticket price (list_price), can be set to standard_price (cost)
        :param res_currency price_list_currency: currency of the price list
        """
        if price_list_currency:
            self.price_list.write({'currency_id': price_list_currency.id})

        pricelist_item_values = {
            'compute_price': rule_type,
            self.rule_type_to_field[rule_type]: rule_amount,
            'base': rule_based_on or 'list_price',
            'min_quantity': min_qty,
        }
        if self.product_or_template == self.event_product_templ:
            pricelist_item_values['product_tmpl_id'] = self.product_or_template.id
            pricelist_item_values['applied_on'] = '1_product'
        else:
            pricelist_item_values['product_id'] = self.product_or_template.id
            pricelist_item_values['applied_on'] = '0_product_variant'
        self.price_list.item_ids = self.env['product.pricelist.item'].create(pricelist_item_values)

    def convert_to_sale_order_currency(self, amount):
        # Sale order currency is the price list currency (see model)
        return self.company_currency._convert(amount, self.price_list.currency_id,
                                              self.env.company, self.now, round=False)
