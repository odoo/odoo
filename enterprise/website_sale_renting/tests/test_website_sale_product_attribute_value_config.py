# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.addons.website.tools import MockRequest


@tagged('post_install', '-at_install', 'product_attribute')
class TestWebsiteSaleRentingProductAttributeValueConfig(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.computer.rent_ok = True
        cls.website = cls.env['website'].get_current_website()
        cls.website.company_id = cls.env.company

        recurrence_3_hour, recurrence_week = cls.env['sale.temporal.recurrence'].create([
            {
                'duration': 3,
                'unit': 'hour',
            },
            {
                'duration': 1,
                'unit': 'week',
            },
        ])
        cls.price_3_hours = 5.
        cls.price_1_week = 25.
        cls.env['product.pricing'].create([
            {
                'recurrence_id': recurrence_3_hour.id,
                'price': cls.price_3_hours,
                'product_template_id': cls.computer.id,
            }, {
                'recurrence_id': recurrence_week.id,
                'price': cls.price_1_week,
                'product_template_id': cls.computer.id,
            },
        ])

    def test_product_tax_included_get_combination_info(self):
        config = self.env['res.config.settings'].create({})
        config.show_line_subtotals_tax_selection = 'tax_included'
        config.execute()

        tax_percent = 15.0
        tax_15_incl = self.env['account.tax'].create({
            'name': 'VAT 5 perc Incl',
            'amount_type': 'percent',
            'amount': tax_percent,
            'price_include_override': 'tax_excluded',
        })
        self.computer.write({
            'taxes_id': [Command.set([tax_15_incl.id])],
        })
        factor = 1 + tax_percent / 100
        price_3_hours = self.website.currency_id.round(self.price_3_hours * factor)
        price_1_week = self.website.currency_id.round(self.price_1_week * factor)
        with MockRequest(self.env, website=self.website):
            computer = self.computer.with_context(website_id=self.website.id)
            combination_info = computer._get_combination_info()
            self.assertEqual(combination_info['price'], price_3_hours)
            self.assertEqual(combination_info['list_price'], price_3_hours)
            self.assertEqual(
                combination_info['price_extra'], self.website.currency_id.round(222 * factor)
            )
            self.assertEqual(combination_info['has_discounted_price'], False)
            self.assertEqual(combination_info['current_rental_price'], price_3_hours)
            self.assertEqual(combination_info['current_rental_duration'], 3)
            self.assertEqual(str(combination_info['current_rental_unit']), 'Hours')
            self.assertEqual(
                combination_info['pricing_table'],
                [('3 Hours', f'$\xa0{price_3_hours}'), ('1 Week', f'$\xa0{price_1_week}')],
            )

    def test_product_attribute_value_config_get_combination_info(self):
        pricelist = self.env['product.pricelist'].create({
            'name': 'Website Pricelist',
            'website_id': self.website.id,
        })

        # make sure the pricelist has a 10% discount
        self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
            'pricelist_id': pricelist.id,
        })

        discount_rate = 1 # No discount should apply on rental products (functional choice)

        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)

        computer = self.computer.with_context(website_id=self.website.id)
        price_3_hours = self.website.currency_id.round(
            self.price_3_hours * discount_rate * currency_ratio
        )
        price_1_week = self.website.currency_id.round(
            self.price_1_week * discount_rate * currency_ratio
        )
        with MockRequest(self.env, website=self.website):
            combination_info = computer._get_combination_info()
            self.assertEqual(combination_info['price'], price_3_hours)
            self.assertEqual(combination_info['list_price'], price_3_hours)
            self.assertEqual(combination_info['price_extra'], 222 * currency_ratio)
            self.assertEqual(combination_info['has_discounted_price'], False)
            self.assertEqual(combination_info['current_rental_price'], price_3_hours)
            self.assertEqual(combination_info['current_rental_duration'], 3)
            self.assertEqual(str(combination_info['current_rental_unit']), 'Hours')

        with MockRequest(self.env, website=self.website):
            now = fields.Datetime.now()
            combination_info = computer.with_context(
                start_date=now, end_date=now + relativedelta(days=6)
            )._get_combination_info()
            self.assertEqual(combination_info['price'], price_3_hours)
            self.assertEqual(combination_info['list_price'], price_3_hours)
            self.assertEqual(combination_info['price_extra'], 222 * currency_ratio)
            self.assertEqual(combination_info['has_discounted_price'], False)
            self.assertEqual(combination_info['current_rental_price'], price_1_week)
            self.assertEqual(combination_info['current_rental_duration'], 1)
            self.assertEqual(str(combination_info['current_rental_unit']), 'Week')
