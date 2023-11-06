# coding: utf-8
import itertools

from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class WebsiteSaleProductTests(TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env.ref('website.default_website')

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
        self.assertEqual(0.0, contextual_price, "With no pricelist context, the contextual price should be 0.")

        current_website = self.env['website'].get_current_website()
        pricelist = current_website.get_current_pricelist()

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

    def test_get_contextual_price_tax_selection(self):
        """
        `_get_contextual_price_tax_selection` is used to display the price on the website (e.g. in the carousel).
        We test that the contextual price is correctly computed. That is, it is coherent with the price displayed on the product when in the cart.
        """
        param_main_product_tax_included = [True, False]
        param_show_line_subtotals_tax_selection = ['tax_included', 'tax_excluded']
        param_extra_tax = [False, 'included', 'excluded']
        param_fpos = [False, 'to_tax_excluded']
        parameters = itertools.product(param_main_product_tax_included, param_show_line_subtotals_tax_selection, param_extra_tax, param_fpos)

        for main_product_tax_included, show_line_subtotals_tax_selection, extra_tax, fpos in parameters:
            with self.subTest(main_product_tax_included=main_product_tax_included, show_line_subtotals_tax_selection=show_line_subtotals_tax_selection, extra_tax=extra_tax, fpos=fpos):
                # set "show_line_subtotals_tax_selection" parameter
                config = self.env['res.config.settings'].create({})
                config.show_line_subtotals_tax_selection = show_line_subtotals_tax_selection
                config.execute()

                # set "main_product_tax_included" parameter
                if main_product_tax_included:
                    self.tax_15.price_include = True
                    self.tax_15.include_base_amount = True
                self.product.taxes_id = self.tax_15
                tax_ids = [self.tax_15.id]

                # set "extra_tax" parameter
                if extra_tax:
                    if extra_tax == 'included':
                        self.tax_5.price_include = True
                        self.tax_5.include_base_amount = True
                    tax_ids.append(self.tax_5.id)

                # set "fpos" parameter
                if fpos:
                    if fpos == 'to_tax_included':
                        self.tax_10.price_include = True
                        self.tax_10.include_base_amount = True

                    fiscal_position = self.env['account.fiscal.position'].create({
                        'name': 'Super Fiscal Position',
                        'auto_apply': True,
                        'country_id': self.fiscal_country.id,
                    })
                    self.env['account.fiscal.position.tax'].create({
                        'position_id': fiscal_position.id,
                        'tax_src_id': self.tax_15.id,
                        'tax_dest_id': self.tax_10.id,
                    })
                    self.env.user.partner_id.country_id = self.fiscal_country

                # define the website pricelist
                current_website = self.env['website'].get_current_website()
                pricelist = current_website.get_current_pricelist()
                pricelist.currency_id = self.product.currency_id
                self.env['product.pricelist.item'].create({
                    'price_discount': 0,
                    'compute_price': 'formula',
                    'pricelist_id': pricelist.id,
                })

                with MockRequest(self.env, website=self.website, website_sale_current_pl=pricelist.id):
                    contextual_price = self.product._get_contextual_price_tax_selection()
                    self.WebsiteSaleController.cart_update_json(product_id=self.product.id, add_qty=1)
                    sale_order = self.website.sale_get_order()

                if show_line_subtotals_tax_selection == 'tax_included':
                    self.assertAlmostEqual(sale_order.amount_total, contextual_price)
                else:
                    self.assertAlmostEqual(sale_order.amount_untaxed, contextual_price)
