# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import ProductCommon


class TestPricelistAutoCreation(ProductCommon):

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()

        # Only one currency enabled and used on companies (multi-curr disabled)
        cls.currency_euro = cls._enable_currency('EUR')
        cls.currency_usd = cls.env['res.currency'].search([('name', '=', "USD")])
        cls.env['res.company'].search([]).currency_id = cls.currency_euro
        cls.env['res.currency'].search([('name', '!=', 'EUR')]).action_archive()

        # Disabled pricelists feature
        cls.group_user = cls.env.ref('base.group_user').sudo()
        cls.group_product_pricelist = cls.env.ref('product.group_product_pricelist')
        cls.group_user._remove_group(cls.group_product_pricelist)
        cls.env['product.pricelist'].search([]).unlink()
        return res

    def test_inactive_curr_set_on_company(self):
        """Make sure that when setting an inactive currency on a company, the
        activation of the multi-currency group won't lead to the creation of a
        pricelist for the old currency
        """
        # no pricelists because we disabled the fuck out of all of them
        self.assertEqual(
            self.env['product.pricelist'].search_count([]),
            0,
        )

        self.assertFalse(self.currency_usd.active)
        self.env.company.currency_id = self.currency_usd
        self.assertTrue(self.currency_usd.active, "setting an inactive currency on a company should enable it")
        self.assertIn(
            self.env.ref('base.group_multi_currency'),
            self.group_user.trans_implied_ids,
            "activating a second currency should enable multi-currency",
        )
        self.assertIn(
            self.group_product_pricelist,
            self.group_user.trans_implied_ids,
            "enabling multi-currency should enable pricelists",
        )

        self.assertEqual(
            self.env['product.pricelist'].search_count([
                ('currency_id.name', '=', 'USD'),
                ('company_id', '=', self.env.company.id),
            ]),
            1,
            "setting a new currency on the company should have created "
            "a pricelist in that new currency",
        )
        self.assertTrue(self.currency_euro.active, "the old currency should still be active")
