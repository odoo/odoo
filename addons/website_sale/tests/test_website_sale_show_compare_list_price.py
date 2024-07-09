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
                    'compute_price': 'fixed',
                    'fixed_price': 3500,
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
                    'compute_price': 'fixed',
                    'fixed_price': 1500,
                }),
                Command.create({
                    'applied_on': '1_product',
                    'product_tmpl_id': cls.test_product_with_pricelist_and_compare_list_price.id,
                    'compute_price': 'fixed',
                    'fixed_price': 3500,
                })
            ]
        })

    def test_compare_list_price_price_list_display(self):
        self.env.user.write({
            'groups_id': [Command.link(
                self.env.ref('website_sale.group_product_price_comparison').id
            )],
        })
        self.start_tour("/", 'compare_list_price_price_list_display', login=self.env.user.login)
