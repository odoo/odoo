# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestResCurrency(TransactionCase):
    def test_currency_cache(self):
        currencyA, currencyB = self.env['res.currency'].create([{
            'name': 'AAA',
            'symbol': 'AAA',
            'rate_ids': [Command.create({'name': '2009-09-08', 'rate': 1})],
        }, {
            'name': 'BBB',
            'symbol': 'BBB',
            'rate_ids': [
                Command.create({'name': '2009-09-08', 'rate': 1}),
                Command.create({'name': '2011-11-10', 'rate': 2}),
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
            ('name', '=', '2009-09-08')],
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
            'name': '2010-10-09',
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

    def test_amount_to_text_10(self):
        """ verify that amount_to_text works as expected """
        currency = self.env.ref('base.EUR')

        amount_target = currency.amount_to_text(0.29)
        amount_test = currency.amount_to_text(0.28)
        self.assertNotEqual(amount_test, amount_target,
                            "Amount in text should not depend on float representation")

    def test_rounding_04(self):
        """ check that proper rounding is performed for float persistence """
        currency = self.env.ref('base.EUR')
        currency_rate = self.env['res.currency.rate']

        def try_roundtrip(value, expected, date):
            rate = currency_rate.create({'name': date,
                                         'rate': value,
                                         'currency_id': currency.id})
            self.assertEqual(rate.rate, expected,
                             'Roundtrip error: got %s back from db, expected %s' % (rate, expected))

        # res.currency.rate no more uses 6 digits of precision by default, it now uses whatever precision it gets
        try_roundtrip(10000.999999, 10000.999999, '2000-01-03')

        #TODO re-enable those tests when tests are made on dedicated models
        # (res.currency.rate don't accept negative value anymore)
        #try_roundtrip(-2.6748955, -2.674896, '2000-01-02')
        #try_roundtrip(-10000.999999, -10000.999999, '2000-01-04')
