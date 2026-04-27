# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError
from ..models.fedex_request import FedexRequest


class TestDeliveryFedexInternal(TransactionCase):
    """Unit tests for the delivery_fedex module that don't require external access"""
    def setUp(self):
        super().setUp()
        self.carrier = self.env.ref('delivery_fedex.delivery_carrier_fedex_inter')
        SaleOrder = self.env['sale.order']
        self.currency_usd_id = self.env.ref("base.USD")
        self.currency_gbp_id = self.env.ref("base.GBP")
        self.currency_eur_id = self.env.ref("base.EUR")
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_gbp_id.id,
            'rate': 0.5,
            'name': '2001-01-01'})
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_eur_id.id,
            'rate': 0.8,
            'name': '2001-01-01'})
        self.cr.execute("UPDATE res_company SET currency_id = %s", [self.currency_gbp_id.id])
        self.env['res.company'].invalidate_model(['currency_id'])
        self.cr.execute("UPDATE res_currency SET active = true where name in ('EUR', 'GBP', 'USD')")
        self.env['res.currency'].invalidate_model(['active'])

        self.uom_unit = self.env.ref('uom.product_uom_unit')
        test_product = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        test_customer = self.env['res.partner'].create({'name': 'Vlad the Impaler'})
        sol_vals = {'product_id': test_product.id,
                    'name': test_product.name,
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'currency_id': self.currency_usd_id.id,
                    'price_unit': 123}

        so_vals = {'partner_id': test_customer.id,
                    'carrier_id': self.env.ref('delivery_fedex.delivery_carrier_fedex_us').id,
                    'order_line': [(0, None, sol_vals)]}

        self.sale_order = SaleOrder.create(so_vals)

    def test_get_request_price_order_currency(self):
        price = self.carrier._get_request_price({ 'USD': 1.234, 'UKL': 999 }, self.sale_order, self.currency_usd_id)
        self.assertEqual(1.234, price)

    def test_get_request_price_company_currency(self):
        # case where Fedex returns the price in the company currency
        # we want to convert it to the order currency (without consideration for other currencies present)
        price = self.carrier._get_request_price({ 'UKL': 4, 'EUR': 999 }, self.sale_order, self.currency_usd_id)
        self.assertEqual(4 * 2, price)

    def test_get_request_price_other_currency(self):
        # case where Fedex returns another currency altogether
        # we want to convert it to the order currency
        price = self.carrier._get_request_price({ 'EUR': 4 }, self.sale_order, self.currency_usd_id)
        self.assertEqual(4 / .8, price)

    def test_get_request_price_other_currency_iso(self):
        # case where Fedex returns GBP instead of UKL
        price = self.carrier._get_request_price({ 'GBP': 4 }, self.sale_order, self.currency_usd_id)
        self.assertEqual(4 * 2, price)
