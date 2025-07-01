# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
from odoo import Command
from odoo.tests.common import TransactionCase


class TestResCurrency(TransactionCase):
    def test_view_company_rate_label(self):
        """Tests the label of the company_rate and inverse_company_rate fields
        are well set according to the company currency in the currency form view and the currency rate list view.
        e.g. in the currency rate list view of a company using EUR, the company_rate label must be `Unit per EUR`"""
        company_foo, company_bar = self.env['res.company'].create([
            {'name': 'foo', 'currency_id': self.env.ref('base.EUR').id},
            {'name': 'bar', 'currency_id': self.env.ref('base.USD').id},
        ])
        for company, expected_currency in [(company_foo, 'EUR'), (company_bar, 'USD')]:
            for model, view_type in [('res.currency', 'form'), ('res.currency.rate', 'list')]:
                arch = self.env[model].with_company(company).get_view(view_type=view_type)['arch']
                tree = etree.fromstring(arch)
                node_company_rate = tree.find('.//field[@name="company_rate"]')
                node_inverse_company_rate = tree.find('.//field[@name="inverse_company_rate"]')
                self.assertEqual(node_company_rate.get('string'), f'Unit per {expected_currency}')
                self.assertEqual(node_inverse_company_rate.get('string'), f'{expected_currency} per Unit')

    def test_currency_cache(self):
        currencyA, currencyB = self.env['res.currency'].create([{
            'name': 'AAA',
            'symbol': 'AAA',
            'rate_ids': [Command.create({'name': '2009-09-09', 'rate': 1})]
        }, {
            'name': 'BBB',
            'symbol': 'BBB',
            'rate_ids': [
                Command.create({'name': '2009-09-09', 'rate': 1}),
                Command.create({'name': '2011-11-11', 'rate': 2}),
            ],
        }])

        self.assertEqual(currencyA._convert(
            from_amount=100,
            to_currency=currencyB,
            company=self.env.company,
            date='2010-10-10',
        ), 100)

        # update the (cached) rate of the to_currency used in the previous query
        self.env['res.currency.rate'].search([
            ('currency_id', '=', currencyB.id),
            ('name', '=', '2009-09-09')]
        ).rate = 3

        # repeat _convert call
        # the cached conversion rate is invalid due to the rate change -> query
        with self.assertQueryCount(1):
            self.assertEqual(currencyA._convert(
                from_amount=100,
                to_currency=currencyB,
                company=self.env.company,
                date='2010-10-10',
            ), 300)

        # create a new rate of the to_currency for the date used in the previous query
        self.env['res.currency.rate'].create({
            'name': '2010-10-10',
            'rate': 4,
            'currency_id': currencyB.id,
            'company_id': self.env.company.id,
        })

        # repeat _convert call
        # the cached conversion rate is invalid due to the new rate of the to_currency -> query
        with self.assertQueryCount(1):
            self.assertEqual(currencyA._convert(
                from_amount=100,
                to_currency=currencyB,
                company=self.env.company,
                date='2010-10-10',
            ), 400)

        # only one query is done when changing the convert params
        with self.assertQueryCount(1):
            self.assertEqual(currencyA._convert(
                from_amount=100,
                to_currency=currencyB,
                company=self.env.company,
                date='2011-11-11',
            ), 200)

        # cache holds multiple values
        with self.assertQueryCount(0):
            self.assertEqual(currencyA._convert(
                from_amount=100,
                to_currency=currencyB,
                company=self.env.company,
                date='2010-10-10',
            ), 400)
            self.assertEqual(currencyA._convert(
                from_amount=100,
                to_currency=currencyB,
                company=self.env.company,
                date='2011-11-11',
            ), 200)

    def test_res_currency_name_search(self):
        currency_A, currency_B = self.env["res.currency"].create([
            {"name": "cuA", "symbol": "A"},
            {"name": "cuB", "symbol": "B"},
        ])
        self.env["res.currency.rate"].create([
            {"name": "1971-01-01", "rate": 2.0, "currency_id": currency_A.id},
            {"name": "1971-01-01", "rate": 1.5, "currency_id": currency_B.id},
            {"name": "1972-01-01", "rate": 0.69, "currency_id": currency_B.id},
        ])
        # should not try to match field 'name' (date field)
        self.assertEqual(self.env["res.currency"].search_count([["rate_ids", "=", "1971-01-01"]]), 2)
        # should not try to match field 'rate' (float field)
        self.assertEqual(self.env["res.currency"].search_count([["rate_ids", "=", "0.69"]]), 1)
        # should not try to match any of 'name' and 'rate'
        self.assertEqual(self.env["res.currency"].search_count([["rate_ids", "=", "irrelevant"]]), 0)
