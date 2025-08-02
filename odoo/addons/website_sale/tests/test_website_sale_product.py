# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import (
    TestSaleProductAttributeValueCommon,
)
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class WebsiteSaleProductTests(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        cls.website.company_id = cls.env.company

        cls.tax_5 = cls.env['account.tax'].create({
            'name': '5% Tax',
            'amount_type': 'percent',
            'amount': 5,
            'price_include': False,
            'include_base_amount': False,
            'type_tax_use': 'sale',
        })
        cls.tax_10 = cls.env['account.tax'].create({
            'name': '10% Tax',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': False,
            'include_base_amount': False,
            'type_tax_use': 'sale',
        })
        cls.tax_15 = cls.env['account.tax'].create({
            'name': '15% Tax',
            'amount_type': 'percent',
            'amount': 15,
            'price_include': False,
            'include_base_amount': False,
            'type_tax_use': 'sale',
        })
        cls.fiscal_country = cls.env['res.country'].create({
            'name': "Super Fiscal Position",
            'code': 'SFP',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Super Product',
            'list_price': 100.0,
        })

    def test_website_sale_contextual_price(self):
        contextual_price = self.computer._get_contextual_price()
        self.assertEqual(
            self.computer.list_price,
            contextual_price,
            "With no pricelist context, the contextual price should be the computer list price."
        )

        pricelist = self.env['product.pricelist'].create({
            'name': 'Base Pricelist',
            'sequence': 4,
        })

        # make sure the pricelist has a 10% discount
        self.env['product.pricelist.item'].create({
            'price_discount': 10,
            'compute_price': 'formula',
            'pricelist_id': pricelist.id,
        })
        discount_rate = 0.9
        currency_ratio = 2
        pricelist.currency_id = self._setup_currency(currency_ratio)
        with MockRequest(self.env, website=self.website):
            contextual_price = self.computer._get_contextual_price()
        self.assertEqual(
            2000.0 * currency_ratio * discount_rate, contextual_price,
            "With a website pricelist context, the contextual price should be the one defined for the website's pricelist."
        )

    def test_base_price_with_discount_on_pricelist_tax_included(self):
        """
        Tests that the base price of a product with tax included
        and discount from a price list is correctly displayed in the shop

        ex: A product with a price of $61.98 ($75 tax incl. of 21%) and a discount of 20%
        should display the base price of $75
        """
        self.env['res.config.settings'].create({                  # Set Settings:
            'show_line_subtotals_tax_selection': 'tax_included',  # Set "Tax Included" on the "Display Product Prices"
            'product_pricelist_setting': 'advanced',              # advanced pricelist (discounts, etc.)
            'group_product_price_comparison': True,               # price comparison
        }).execute()

        tax = self.env['account.tax'].create({
            'name': '21%',
            'type_tax_use': 'sale',
            'amount': 21,
        })
        product_tmpl = self.env['product.template'].create({
            'name': 'Test Product',
            'type': 'consu',
            'list_price': 61.98,  # 75 tax incl.
            'taxes_id': [(6, 0, [tax.id])],
            'is_published': True,
        })
        pricelist_item = self.env['product.pricelist.item'].create({
            'price_discount': 20,
            'compute_price': 'formula',
            'product_tmpl_id': product_tmpl.id,
        })
        current_website = self.env['website'].get_current_website()
        pricelist = current_website._get_current_pricelist()
        pricelist.item_ids = [(6, 0, [pricelist_item.id])]
        pricelist.discount_policy = 'without_discount'
        res = product_tmpl._get_sales_prices(pricelist, self.env['account.fiscal.position'])
        self.assertEqual(res[product_tmpl.id]['base_price'], 75)

    def test_get_contextual_price_tax_selection(self):
        """
        `_get_contextual_price_tax_selection` is used to display the price on the website (e.g. in the carousel).
        We test that the contextual price is correctly computed. That is, it is coherent with the price displayed on the product when in the cart.
        """
        param_main_product_tax_included = [True, False]
        param_show_line_subtotals_tax_selection = ['tax_included', 'tax_excluded']
        param_extra_tax = [False, 'included', 'excluded']
        param_fpos = [False, 'to_tax_excluded', 'to_tax_included']
        parameters = itertools.product(param_main_product_tax_included, param_show_line_subtotals_tax_selection, param_extra_tax, param_fpos)

        self.product.taxes_id = self.tax_15
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'Super Fiscal Position',
            'auto_apply': True,
            'country_id': self.fiscal_country.id,
            'tax_ids': [
                Command.create({
                    'tax_src_id': self.tax_15.id,
                    'tax_dest_id': self.tax_10.id,
                })
            ]
        })
        self.env.user.partner_id.country_id = self.fiscal_country

        self.WebsiteSaleController = WebsiteSale()
        for main_product_tax_included, show_line_subtotals_tax_selection, extra_tax, fpos in parameters:
            with self.subTest(main_product_tax_included=main_product_tax_included, show_line_subtotals_tax_selection=show_line_subtotals_tax_selection, extra_tax=extra_tax, fpos=fpos):
                # set "show_line_subtotals_tax_selection" parameter
                self.website.invalidate_recordset(['fiscal_position_id'], flush=False)
                config = self.env['res.config.settings'].create({})
                config.show_line_subtotals_tax_selection = show_line_subtotals_tax_selection
                config.execute()

                self.assertEqual(self.website.show_line_subtotals_tax_selection, show_line_subtotals_tax_selection)

                tax_ids = [self.tax_15.id]
                # set "main_product_tax_included" parameter
                if main_product_tax_included:
                    self.tax_15.price_include = True
                    self.tax_15.include_base_amount = True
                else:
                    self.tax_15.price_include = False
                    self.tax_15.include_base_amount = False

                # set "extra_tax" parameter
                if extra_tax:
                    if extra_tax == 'included':
                        self.tax_5.price_include = True
                        self.tax_5.include_base_amount = True
                    else:
                        self.tax_5.price_include = False
                        self.tax_5.include_base_amount = False

                    tax_ids.append(self.tax_5.id)

                self.product.taxes_id = tax_ids

                # set "fpos" parameter
                if fpos:
                    if fpos == 'to_tax_included':
                        self.tax_10.price_include = True
                        self.tax_10.include_base_amount = True
                    else:
                        self.tax_10.price_include = False
                        self.tax_10.include_base_amount = False

                    fiscal_position.action_unarchive()
                else:
                    fiscal_position.action_archive()

                with MockRequest(self.env, website=self.website):
                    self.assertEqual(
                        self.website.fiscal_position_id,
                        fpos and fiscal_position or self.env['account.fiscal.position']
                    )
                    contextual_price = self.product.with_context(
                        website_id=self.website.id,
                    )._get_contextual_price_tax_selection()
                    self.WebsiteSaleController.cart_update(product_id=self.product.id, add_qty=1)
                    sale_order = self.website.sale_get_order()

                self.assertEqual(sale_order.website_id, self.website)
                self.assertEqual(sale_order.company_id, self.website.company_id)
                self.assertEqual(sale_order.currency_id, self.website.currency_id)
                self.assertFalse(sale_order.pricelist_id)
                if fpos:
                    self.assertEqual(sale_order.fiscal_position_id, fiscal_position)
                else:
                    self.assertFalse(sale_order.fiscal_position_id)

                sol = sale_order.order_line
                if fpos:
                    self.assertEqual(sol.tax_id, fiscal_position.map_tax(self.product.taxes_id))
                else:
                    self.assertEqual(sol.tax_id, self.product.taxes_id)

                if show_line_subtotals_tax_selection == 'tax_included':
                    self.assertAlmostEqual(sol.price_reduce_taxinc, contextual_price)
                    self.assertAlmostEqual(sale_order.amount_total, contextual_price)
                else:
                    self.assertAlmostEqual(sol.price_reduce_taxexcl, contextual_price)
                    self.assertAlmostEqual(sale_order.amount_untaxed, contextual_price)
