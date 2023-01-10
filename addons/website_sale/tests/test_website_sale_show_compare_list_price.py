from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class WebsiteSaleShopPriceListCompareListPriceDispayTests(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        ProductTemplate = cls.env['product.template']
        Pricelist = cls.env['product.pricelist']
        PricelistItem = cls.env['product.pricelist.item']

        # Cleanup existing pricelist.
        cls.env['website'].search([]).write({'sequence': 1000})
        website = cls.env['website'].create({
            'name': "Test website",
            'company_id': cls.env.company.id,
            'sequence': 1,
        })

        cls.test_product_default = ProductTemplate.create({
            'name': 'test_product_default',
            'type': 'consu',
            'website_published': True,
            'list_price': 1000,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_compare_list_price',
            'type': 'consu',
            'website_published': True,
            'list_price': 2000,
            'compare_list_price': 2500,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_pricelist = ProductTemplate.create({
            'name': 'test_product_with_pricelist',
            'website_published': True,
            'type': 'consu',
            'list_price': 2000,
            'company_id': cls.env.company.id,
        })
        cls.test_product_with_pricelist_and_compare_list_price = ProductTemplate.create({
            'name': 'test_product_with_pricelist_and_compare_list_price',
            'website_published': True,
            'type': 'consu',
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
            'discount_policy': 'with_discount',
        })
        cls.pricelist_without_discount = Pricelist.create({
            'name': 'pricelist_without_discount',
            'website_id': website.id,
            'company_id': cls.env.company.id,
            'selectable': True,
            'sequence': 3,
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
        self.start_tour("/", 'compare_list_price_price_list_display', login=self.env.user.login)
