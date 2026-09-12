# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPricelistAutoCreation(ProductCommon):

    _test_user_groups = (
        'product.group_product_manager',
    )

    _test_user_name = 'Test Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Only one currency enabled and used on companies (multi-curr disabled)
        cls.currency_euro = cls._enable_currency('EUR')
        cls.currency_usd = cls.env['res.currency'].search([('name', '=', "USD")])
        cls.env['res.company'].search([]).currency_id = cls.currency_euro
        cls.env['res.currency'].search([('name', '!=', 'EUR')]).action_archive()

        # Disabled pricelists feature
        cls.group_user = cls.env.ref('base.group_user').sudo()
        cls.group_user._remove_group(cls.group_product_pricelist)
        cls.env['product.pricelist'].search([]).unlink()

    def test_inactive_curr_set_on_company(self):
        """Make sure that setting an inactive currency on a company activates the multi-currency
        group without enabling the pricelist feature.
        """
        self.env.company.sudo().currency_id = self.currency_usd

        self.assertTrue(self.currency_usd.active)
        self.assertTrue(self.env.user.has_group('base.group_multi_currency'))
        self.assertFalse(self.env.user.has_group('product.group_product_pricelist'))
        self.assertFalse(
            self.env['product.pricelist'].search([('company_id', '=', self.env.company.id)])
        )
