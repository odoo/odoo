from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class WebsiteSaleShopPriceListCompareListPriceDispayTests(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ProductTemplate = cls.env['product.template']
        Pricelist = cls.env['product.pricelist']
        PricelistItem = cls.env['product.pricelist.item']

        cls.test_product_default = ProductTemplate.create({
            'name': 'test_product_default',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000
        })
        cls.test_product_with_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_compare_list_price',
            'type': 'consu',
            'website_published': True,
            'list_price': 2000,
            'compare_list_price': 2500
        })
        cls.test_product_with_pricelist = ProductTemplate.create({
            'name': 'test_product_with_pricelist',
            'website_published': True,
            'type': 'consu',
            'list_price': 2000
        })
        cls.test_product_with_pricelist_and_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_pricelist_and_compare_list_price',
            'website_published': True,
            'type': 'consu',
            'list_price': 4000,
            'compare_list_price': 4500

        })

        # Two pricelists
        website = cls.env['website'].get_current_website()

        cls.pricelist_with_discount = Pricelist.create({
            'name': 'pricelist_with_discount',
            'website_id': website.id,
            'selectable': True,
            'discount_policy': 'with_discount',
        })
        cls.pricelist_without_discount = cls.pricelist = Pricelist.create({
            'name': 'pricelist_without_discount',
            'website_id': website.id,
            'selectable': True,
            'discount_policy': 'without_discount',

        })

        # Pricelist items
        PricelistItem.create({
            'pricelist_id': cls.pricelist_with_discount.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.test_product_with_pricelist.id,
            'compute_price': 'fixed',
            'fixed_price': 1500,
        })

        PricelistItem.create({
            'pricelist_id': cls.pricelist_without_discount.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.test_product_with_pricelist.id,
            'compute_price': 'fixed',
            'fixed_price': 1500,
        })

        PricelistItem.create({
            'pricelist_id': cls.pricelist_without_discount.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.test_product_with_pricelist_and_compare_list_price.id,
            'compute_price': 'fixed',
            'fixed_price': 3500,
        })

        PricelistItem.create({
            'pricelist_id': cls.pricelist_with_discount.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.test_product_with_pricelist_and_compare_list_price.id,
            'compute_price': 'fixed',
            'fixed_price': 3500,
        })

    def test_compare_list_price_price_list_display(self):
        self.start_tour("/", 'compare_list_price_price_list_display')
