# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class WebsiteSaleShopPriceListCompareListPriceDispayTests(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ProductTemplate = cls.env['product.template']
        Pricelist = cls.env['product.pricelist']

        cls.env['website'].search([]).write({'sequence': 1000})
        website = cls.env['website'].create({
            'name': "Test website",
            'company_id': cls.env.company.id,
            'sequence': 1,
        })

        cls.test_product_default = ProductTemplate.create({
            'name': 'test_product_default',
            'website_published': True,
            'list_price': 1000,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_compare_list_price',
            'website_published': True,
            'list_price': 2000,
            'compare_list_price': 2500,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_pricelist = ProductTemplate.create({
            'name': 'test_product_with_pricelist',
            'website_published': True,
            'list_price': 2000,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_pricelist_and_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_pricelist_and_compare_list_price',
            'website_published': True,
            'list_price': 4000,
            'compare_list_price': 4500,
            'company_id': cls.env.company.id,
        })

        # Three pricelists
        Pricelist.search([]).write({'sequence': 1000})
        cls.pricelist_default = Pricelist.create({
            'name': 'pricelist_default',
            'website_id': website.id,
            'company_id': cls.env.company.id,
            'selectable': True,
            'sequence': 1,
        })
        cls.pricelist_with_discount = Pricelist.create({
            'name': 'pricelist_with_discount',
            'website_id': website.id,
            'company_id': cls.env.company.id,
            'selectable': True,
            'sequence': 2,
            'item_ids': [
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.test_product_with_pricelist.id,
                    'compute_price': 'fixed',
                    'fixed_price': 1500,
                }),
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.test_product_with_pricelist_and_compare_list_price.id,
                    'compute_price': 'percentage',
                    'percent_price': 12.5,
                })
            ]
        })
        cls.pricelist_without_discount = Pricelist.create({
            'name': 'pricelist_without_discount',
            'website_id': website.id,
            'company_id': cls.env.company.id,
            'selectable': True,
            'sequence': 3,
            'item_ids': [
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.test_product_with_pricelist.id,
                    'compute_price': 'percentage',
                    'percent_price': 25,
                }),
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.test_product_with_pricelist_and_compare_list_price.id,
                    'compute_price': 'percentage',
                    'percent_price': 12.5,
                })
            ]
        })

    def test_compare_list_price_strikethrough_visibility(self):
        self.env.user.write({
            "groups_id": [
                Command.link(self.env.ref("website_sale.group_product_price_comparison").id)
            ]
        })
        mapping = {"detail": {"display_currency": self.env.company.currency_id}}

        # compare_list_price == price: no strikethrough
        self.test_product_with_compare_list_price.compare_list_price = 2000
        combination_info = self.test_product_with_compare_list_price._get_combination_info()
        _, list_price = self.test_product_with_compare_list_price._search_render_results_prices(
            mapping, combination_info
        )
        self.assertFalse(list_price, "No strikethrough when compare_list_price equals price")

        # compare_list_price > price: strikethrough shown
        self.test_product_with_compare_list_price.compare_list_price = 2500
        combination_info = self.test_product_with_compare_list_price._get_combination_info()
        _, list_price = self.test_product_with_compare_list_price._search_render_results_prices(
            mapping, combination_info
        )
        self.assertTrue(
            list_price, "Strikethrough shown when compare_list_price is greater than price"
        )

    def test_compare_list_price_price_list_display(self):
        self.env.user.write({
            'groups_id': [Command.link(
                self.env.ref('website_sale.group_product_price_comparison').id
            )],
        })
        self.start_tour("/", 'compare_list_price_price_list_display', login=self.env.user.login)

    def test_pricelist_discount_strikethrough_respects_comparison_price_setting(self):
        """Test that pricelist discount strikethroughs are hidden when comparison price setting is disabled."""
        public_user = self.env.ref('base.public_user')
        comparison_group = self.env.ref('website_sale.group_product_price_comparison')
        website = self.env['website'].get_current_website()

        # Create a selectable pricelist with a 10% discount rule
        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Discount Pricelist',
            'selectable': True,
            'website_id': website.id,
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'percent_price': 10,
                'applied_on': '3_global',
            })],
        })

        product_template = self.product.product_tmpl_id
        product_template.is_published = True

        public_user.sudo().write({'groups_id': [(3, comparison_group.id)]})
        self.env.invalidate_all()
        self.env.registry.clear_cache()

        price_info_disabled = product_template.with_user(public_user).with_context(
            website_sale_pricelist=pricelist.id
        )._get_sales_prices(website)

        self.assertFalse(
            price_info_disabled[product_template.id].get('base_price'),
            "Base price for strikethrough should be None when comparison prices setting is disabled."
        )
