# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_event_sale.controllers.main import WebsiteEventSaleController
from odoo.addons.website_event_sale.tests.test_frontend_common import TestFrontendCommon
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestFrontendUnitPrice(TestFrontendCommon):
    """Test of the controller used to display the unit price in various configuration (price list, currency, ...)."""
    def setUp(self):
        super().setUp()
        self.controller = WebsiteEventSaleController()
        self.setup_tax_10(self.event_ticket_std)

    def assert_price(self, pricelist, expected_unit_price, expected_unit_price_not_reduced=None, quantity=1, msg=None):
        with self.subTest(msg, pricelist=pricelist, expected_unit_price=expected_unit_price,
                          expected_unit_price_not_reduced=expected_unit_price_not_reduced, quantity=quantity), \
                MockRequest(self.env, website=self.current_website, website_sale_current_pl=pricelist.id):
            msg_suffix = f': {msg}' if msg else ''
            currency_symbol = self.current_website.currency_id.symbol
            result = self.controller.render_ticket_unit_price(self.event_ticket_std.id, quantity=quantity)
            self.assertIn(expected_unit_price, result, msg=f'Price: {msg_suffix}')
            if expected_unit_price_not_reduced:
                self.assertIn(expected_unit_price_not_reduced, result, msg=f'Price not reduce: {msg_suffix}')
                self.assertIn(currency_symbol, result)
            else:
                self.assertNotIn('price_not_reduced_rendered', result,
                                 msg=f"Don't disclose not reduced price if not configured to: {msg_suffix}")
            self.assertIn(currency_symbol, result)

    def test_unit_price_currency_tax_excl(self):
        self.assert_price(self.ex_pricelist_without_discount, '9,000.00', quantity=1,
                          expected_unit_price_not_reduced='10,000.00', msg='1000 EUR * 10 = 10000 EX, -10% = 9000')

    def test_unit_price_currency_tax_incl(self):
        self.setup_display_tax_incl(self.ex_pricelist_without_discount)

        self.assert_price(self.ex_pricelist_without_discount, '9,900.00', quantity=1,
                          expected_unit_price_not_reduced='11,000.00',
                          msg='1000 EUR * 10 = 10000 EX, +10% tax = 11000, -10% discount = 9900')

    def test_unit_price_depending_on_quantity_tax_excl(self):
        self.assert_price(self.pricelist_min_qty_2_with_discount, '1,000.00', msg='Full price')
        self.assert_price(self.pricelist_min_qty_2_with_discount, '900.00', quantity=2,
                          msg='1000 - 10% = 900 because the quantity >= 2, configured to not show the full price')
        self.assert_price(self.pricelist_min_qty_2_without_discount,
                          '900.00', quantity=2, expected_unit_price_not_reduced='1,000.00',
                          msg='1000 - 25% = 750 because the quantity >= 2, configured to show the full price')

    def test_unit_price_depending_on_quantity_tax_incl(self):
        self.setup_display_tax_incl(self.pricelist_min_qty_2_without_discount)

        self.assert_price(self.pricelist_min_qty_2_with_discount, '1,100.00', msg='1000 + 10% tax')
        self.assert_price(self.pricelist_min_qty_2_with_discount, '990.00', quantity=2,
                          msg='1000 - 10% = 900 because the quantity >= 2, +10% tax = 990'
                              ', configured to not show the full price')
        self.assert_price(self.pricelist_min_qty_2_without_discount,
                          '990.00', quantity=2, expected_unit_price_not_reduced='1,100.00',
                          msg='1000 - 10% = 900 because the quantity >= 2, +10% tax = 990'
                              ', configured to show the full price (1000 + 10% tax = 1100)')

    def test_unit_price_without_pricelist(self):
        self.env['product.pricelist'].search([]).action_archive()
        self.assert_price(self.env['product.pricelist'], '1,000.00', quantity=2,
                          msg='No price list, we get full ticket price')
