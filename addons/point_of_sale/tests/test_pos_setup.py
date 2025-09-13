# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import ValidationError

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSetup(TestPoSCommon):
    """ This group of tests is for sanity check in setting up global records which will be used
    in each testing.

    If a test fails here, then it means there are inconsistencies in what we expect in the setup.
    """
    def setUp(self):
        super(TestPoSSetup, self).setUp()

        self.config = self.basic_config
        self.products = [
            self.create_product('Product 1', self.categ_basic, lst_price=10.0, standard_price=5),
            self.create_product('Product 2', self.categ_basic, lst_price=20.0, standard_price=10),
            self.create_product('Product 3', self.categ_basic, lst_price=30.0, standard_price=15),
        ]

    def test_basic_config_values(self):

        config = self.basic_config
        self.assertEqual(config.currency_id, self.company_currency)
        self.assertEqual(config.pricelist_id.currency_id, self.company_currency)

    def test_other_currency_config_values(self):
        config = self.other_currency_config
        self.assertEqual(config.currency_id, self.other_currency)
        self.assertEqual(config.pricelist_id.currency_id, self.other_currency)

    def test_product_categories(self):
        # check basic product category
        # it is expected to have standard and manual_periodic valuation
        self.assertEqual(self.categ_basic.property_cost_method, 'standard')
        self.assertEqual(self.categ_basic.property_valuation, 'manual_periodic')
        # check anglo saxon product category
        # this product categ is expected to have fifo and real_time valuation
        self.assertEqual(self.categ_anglo.property_cost_method, 'fifo')
        self.assertEqual(self.categ_anglo.property_valuation, 'real_time')

    def test_product_price(self):
        def get_price(pricelist, product):
            return pricelist._get_product_price(product, 1)


        # check usd pricelist
        pricelist = self.basic_config.pricelist_id
        for product in self.products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price)

        # check eur pricelist
        # exchange rate to the other currency is set to 0.5, thus, lst_price
        # is expected to have half its original value.
        pricelist = self.other_currency_config.pricelist_id
        for product in self.products:
            self.assertAlmostEqual(get_price(pricelist, product), product.lst_price * 0.5)

    def test_taxes(self):
        tax7 = self.taxes['tax7']
        self.assertEqual(tax7.name, 'Tax 7%')
        self.assertAlmostEqual(tax7.amount, 7)
        self.assertEqual(tax7.invoice_repartition_line_ids.mapped('account_id').id, self.tax_received_account.id)
        tax10 = self.taxes['tax10']
        self.assertEqual(tax10.name, 'Tax 10%')
        self.assertAlmostEqual(tax10.amount, 10)
        self.assertEqual(tax10.price_include, True)
        self.assertEqual(tax10.invoice_repartition_line_ids.mapped('account_id').id, self.tax_received_account.id)
        tax_group_7_10 = self.taxes['tax_group_7_10']
        self.assertEqual(tax_group_7_10.name, 'Tax 7+10%')
        self.assertEqual(tax_group_7_10.amount_type, 'group')
        self.assertEqual(sorted(tax_group_7_10.children_tax_ids.ids), sorted((tax7 | tax10).ids))

    def test_archive_used_journal(self):
        journal = self.env['account.journal'].create({
            'name': 'BANKOS',
            'company_id': self.company.id,
            'code': 'BANKOS',
            'type': 'bank',
            'invoice_reference_type': 'none',
            'invoice_reference_model': 'odoo'
        })
        payment_method = self.env['pos.payment.method'].create({'name': 'Lets Pay for Tests', 'journal_id': journal.id})
        self.basic_config.write({'payment_method_ids': [payment_method.id]})
        journal.write({'pos_payment_method_ids': [payment_method.id]})
        session = self.env['pos.session'].create(
            {
                'name': 'lets sell some tests',
                'config_id': self.basic_config.id,
                'user_id': self.env.user.id,
                'state': 'opened'
            }
        )
        order = self.env['pos.order'].create(
            {
                'name': 'MIX',
                'amount_tax': 0,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_return': 0,
                'company_id': self.company.id,
                'pricelist_id': self.currency_pricelist.id,
                'session_id': session.id
            }
        )
        self.env['pos.payment'].create(
            {
                'amount': 100,
                'payment_date': '2025-01-01',
                'payment_method_id': payment_method.id,
                'pos_order_id': order.id
            }
        )
        with self.assertRaises(ValidationError):
            journal.action_archive()
