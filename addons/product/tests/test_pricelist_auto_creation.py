# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.product.tests.common import ProductCommon


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
        """Make sure that when setting an inactive currency on a company, the activation of the
        multi-currency group won't
        """
        self.env.company.currency_id = self.currency_usd
        self.assertFalse(
            self.env['product.pricelist'].search([
                ('currency_id.name', '=', 'EUR'),
                ('company_id', '=', self.env.company.id),
            ])
        )
        self.assertTrue(self.currency_usd.active)
        self.assertTrue(
            self.env['product.pricelist'].search([
                ('currency_id.name', '=', 'USD'),
                ('company_id', '=', self.env.company.id),
            ])
        )
        # self.env.user.clear_caches()
        # self.group_user.invalidate_recordset()
        # self.assertTrue(
        #     self.group_product_pricelist in self.group_user.implied_ids
        # )
