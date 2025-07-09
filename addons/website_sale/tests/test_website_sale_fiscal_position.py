# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleFiscalPosition(ProductCommon, HttpCaseWithUserPortal):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.env.ref('base.us')
        cls._use_currency('USD')

        cls.website = cls.env.ref('website.default_website')
        cls.website.company_id = cls.env.company

        cls.env['account.tax'].search([('company_id', '=', cls.env.company.id)]).action_archive()

        # Create a fiscal position with a mapping of taxes
        cls.tax_15_excl = cls.env['account.tax'].create({
            'name': "15% excl",
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
            'price_include': False,
            'include_base_amount': False,
        })
        cls.tax_0 = cls.env['account.tax'].create({
            'name': "0%",
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 0,
        })
        belgium = cls.env.ref('base.be')
        cls.fpos_be = cls.env['account.fiscal.position'].create({
            'name': "Fiscal Position BE",
            'auto_apply': True,
            'country_id': belgium.id,
            'tax_ids': [Command.create({
                'tax_src_id': cls.tax_15_excl.id,
                'tax_dest_id': cls.tax_0.id,
            })],
        })
        cls.partner_portal.country_id = belgium

    def test_shop_fiscal_position_products_template(self):
        """
            The `website_sale.products` template is computationally intensive
            and therefore uses the cache.
            The goal of this test is to check that this template
            is up to date with the fiscal position detected.
        """
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_pricelist').id)]})
        self.env.company.country_id = self.env.ref('base.us')
        # Set setting to display tax included on the website
        config = self.env['res.config.settings'].create({})
        config.show_line_subtotals_tax_selection = "tax_included"
        config.execute()
        # Create a pricelist which will be automatically detected
        self.env['product.pricelist'].create([{
            'name': 'EUROPE EUR',
            'selectable': True,
            'website_id': self.website.id,
            'country_group_ids': [Command.link(self.env.ref('base.europe').id)],
            'sequence': 1,
            'currency_id': self.env.ref('base.EUR').id,
        }, {
            'name': 'Christmas List',
            'selectable': False,
            'website_id': self.website.id,
            'country_group_ids': [Command.link(self.env.ref('base.europe').id)],
            'sequence': 20,
            'currency_id': self.env.ref('base.EUR').id,
        }])
        # Create the product to be used for analysis
        self.env["product.product"].create({
            'name': "Super product",
            'list_price': 40.00,
            'taxes_id': self.tax_15_excl.ids,
            'website_published': True,
        })
        # Create a conversion rate (1 USD <=> 2 EUR)
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'company_id': self.env.company.id,
            'currency_id': self.env.ref('base.EUR').id,
            'company_rate': 2,
            'name': '2023-01-01',
        })

        self.partner_portal.country_id = self.env.ref('base.be')

        # [1]   By going to the shop page with the portal user,
        #       a t-cache key `pricelist,products` + `fiscal_position_id` is generated
        self.start_tour("/shop", 'website_sale_fiscal_position_portal_tour', login="portal")
        # [2]   If we return to the page with a public user
        #       and take the portal user's pricelist,
        #       the prices must not be those previously calculated for the portal user.
        #       Because the fiscal position differs from that of the public user.
        self.start_tour("/shop", 'website_sale_fiscal_position_public_tour', login="")

    def test_recompute_taxes_on_address_change(self):
        tax_15_incl = self.tax_15_excl.copy({'name': "15% incl", 'price_include': True})
        self.fpos_be.tax_ids.tax_src_id = self.product.taxes_id = tax_15_incl
        self.product.website_published = True
        cart = self.env['sale.order'].create({
            'partner_id': self.partner_portal.id,
            'website_id': self.website.id,
            'order_line': [Command.create({'product_id': self.product.id})],
        })
        amount_untaxed = cart.amount_untaxed
        self.assertEqual(cart.fiscal_position_id, self.fpos_be)
        self.assertEqual(cart.order_line.tax_id, self.tax_0)

        self.partner_portal.country_id = self.env.ref('base.us')
        self.assertNotEqual(cart.fiscal_position_id, self.fpos_be)
        self.assertEqual(cart.order_line.tax_id, tax_15_incl)
        self.assertEqual(cart.amount_untaxed, amount_untaxed, "Untaxed amount should not change")

        cart.action_confirm()
        self.partner_portal.country_id = self.env.ref('base.be')
        self.assertEqual(
            cart.order_line.tax_id,
            tax_15_incl,
            "Tax should no longer change after order confirmation",
        )
