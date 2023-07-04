# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from odoo.tests.common import TransactionCase


class TestResConfig(TransactionCase):
    def test_view_company_rate_label(self):
        """Tests the label of the company_rate and inverse_company_rate fields
        are well set according to the company currency in the currency form view and the currency rate list view.
        e.g. in the currency rate list view of a company using EUR, the company_rate label must be `Unit per EUR`"""
        company_foo, company_bar = self.env['res.company'].create([
            {'name': 'foo', 'currency_id': self.env.ref('base.EUR').id},
            {'name': 'bar', 'currency_id': self.env.ref('base.USD').id},
        ])
        for company, expected_currency in [(company_foo, 'EUR'), (company_bar, 'USD')]:
            for model, view_type in [('res.currency', 'form'), ('res.currency.rate', 'tree')]:
                arch = self.env[model].with_company(company).get_view(view_type=view_type)['arch']
                tree = etree.fromstring(arch)
                node_company_rate = tree.xpath('//field[@name="company_rate"]')[0]
                node_inverse_company_rate = tree.xpath('//field[@name="inverse_company_rate"]')[0]
                self.assertEqual(node_company_rate.get('string'), f'Unit per {expected_currency}')
                self.assertEqual(node_inverse_company_rate.get('string'), f'{expected_currency} per Unit')

class TestDisplaySymbol(TransactionCase):
    def test_symbol_adaptation(self):
        """Testing that the displaid symbol of the currencies adapts itself to the following rules:
        If a single currency with a said curr_symbol is active, its symbol is its curr_symbol
        If a second currency is activated with the same curr_symbol, both currencies have their symbol changed for their name (ISO)
        If a third or more currencies with the same curr_symbol are activated, their symbol is changed for their name (ISO)
        When deactivating a currency resulting in two or more currencies with the same curr_symbol remaining, only the currency
                that is deactivated has its symbol reversed to its original symbol (curr_symbol).
        When deactivating one of the two last active currencies sharing the same curr_symbol, both their symbol are
                reversed to their original symbol (curr_symbol).
        """
        def test_activate_second_dollar(self, USD, CAD):
            """Testing that when a second currency with '$' as curr_symbol is activated, both the newly activated currency
            and the original one (USD is activated by default after the setup) have their symbol changed
            from their curr_symbol to their ISO code"""
            self.assertTrue(USD.symbol == "$")
            self.assertTrue(CAD.symbol == "$")

            self.assertFalse(CAD.active)
            CAD.write({'active': 'True'})
            self.assertTrue(CAD.active)

            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")

        def test_activate_third_dollar(self, USD, CAD, AUD):
            """Testing that when a third currency with '$' as curr_symbol is activated, both the newly activated currency
            and the two others have their ISO code as symbol"""
            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")

            AUD.write({'active': True})
            self.assertTrue(AUD.active)

            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")
            self.assertTrue(AUD.symbol == "AUD")

        def test_deactivate_third_dollar(self, USD, CAD, AUD):
            """Testing that when the third currency sharing the same curr_symbol is deactivated, only that one has its
            symbol reversed to its original symbol"""
            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")
            self.assertTrue(AUD.symbol == "AUD")

            AUD.write({'active': False})
            self.assertFalse(AUD.active)

            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")
            self.assertTrue(AUD.symbol == "$")

        def test_deactivate_second_dollar(self, USD, CAD):
            """Testing that when one of two last active currencies sharing the same curr_symbol is deactivated, both those
            currencies have their symbol reversed to their original symbol"""
            self.assertTrue(USD.symbol == "USD")
            self.assertTrue(CAD.symbol == "CAD")

            CAD.write({'active': False})
            self.assertFalse(CAD.active)

            self.assertTrue(USD.symbol == "$")
            self.assertTrue(CAD.symbol == "$")

        USD = self.env['res.currency'].search([('name', '=', 'USD')])
        CAD = self.env['res.currency'].sudo().search([('name', '=', 'CAD'), ('active', '=', False)])
        AUD = self.env['res.currency'].sudo().search([('name', '=', 'AUD'), ('active', '=', False)])

        test_activate_second_dollar(self, USD, CAD)
        test_activate_third_dollar(self, USD, CAD, AUD)
        test_deactivate_third_dollar(self, USD, CAD, AUD)
        test_deactivate_second_dollar(self, USD, CAD)
