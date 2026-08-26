# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest


@tagged('-at_install', 'post_install')
class TestFuzzy(ProductVariantsCommon):
    def test_shop_and_search_bar_use_same_search_fields(self):
        website = self.env.ref('website.default_website')
        product_tmpl = self.env['product.template']
        expected_fields = [
            'name', 'variants_default_code', 'description_sale', 'description_ecommerce',
        ]
        options = {
            'displayImage': False, 'displayDescription': True, 'displayExtraLink': False,
            'displayDetail': False, 'allowFuzzy': False,
        }

        search_detail = product_tmpl._search_get_detail(website, 'name asc', options)
        self.assertEqual(search_detail['search_fields'], expected_fields)

        with MockRequest(self.env, website=website):
            shop_domain = WebsiteSale()._get_shop_domain('unique_term', None, {})

        searched_products = product_tmpl
        for field in ('name', 'description_sale', 'description_ecommerce'):
            product = product_tmpl.create({
                'name': f'Product searched by {field}',
                field: 'unique_term',
                'is_published': True,
            })
            searched_products |= product

        product_by_reference = product_tmpl.create({
            'name': 'Product searched by reference',
            'is_published': True,
        })
        product_by_reference.product_variant_id.default_code = 'unique_term'
        searched_products |= product_by_reference
        self.assertEqual(searched_products.filtered_domain(shop_domain), searched_products)

        for field in ('description', 'website_description'):
            product = product_tmpl.create({
                'name': f'Product not searched by {field}',
                field: 'unique_term',
                'is_published': True,
            })
            self.assertFalse(product.filtered_domain(shop_domain), f'Should not search in {field}')

    def test_variant_default_code(self):
        website = self.env.ref('website.default_website')

        line = self.product_template_sofa.attribute_line_ids
        value_red = line.product_template_value_ids[0]
        value_blue = line.product_template_value_ids[1]
        value_green = line.product_template_value_ids[2]
        product_red = self.product_template_sofa._get_variant_for_combination(value_red)
        product_blue = self.product_template_sofa._get_variant_for_combination(value_blue)
        product_green = self.product_template_sofa._get_variant_for_combination(value_green)
        product_red.default_code = 'RED_12345'
        product_blue.default_code = 'BLUE_ABCDE'
        product_green.default_code = 'GREEN_98765'
        self.cr.flush()

        options = {
            'displayDescription': True, 'displayDetail': True, 'display_currency': True,
            'displayExtraDetail': True, 'displayExtraLink': True,
            'displayImage': True, 'allowFuzzy': True
        }
        results_count, _, fuzzy_term = website._search_with_fuzzy('products_only', 'RED234', 5, 'name asc', options)
        self.assertEqual(1, results_count, "Should have found red")
        self.assertEqual('red_12345', fuzzy_term, "Should suggest red")
        results_count, _, fuzzy_term = website._search_with_fuzzy('products_only', 'GROEN98765', 5, 'name asc', options)
        self.assertEqual(1, results_count, "Should have found green")
        self.assertEqual('green_98765', fuzzy_term, "Should suggest green")
        results_count, _, fuzzy_term = website._search_with_fuzzy('products_only', 'BLUABCE', 5, 'name asc', options)
        self.assertEqual(1, results_count, "Should have found blue")
        self.assertEqual('blue_abcde', fuzzy_term, "Should suggest blue")
        results_count, _, fuzzy_term = website._search_with_fuzzy('products_only', 'SQWBRNZ', 5, 'name asc', options)
        self.assertEqual(0, results_count, "Should have found none")
        self.assertFalse(fuzzy_term, "Should have no suggestion")

    def test_search_products_accessibility_multi_company(self):
        company_2 = self.env['res.company'].create({'name': 'test'})
        website = self.env.ref('website.default_website')
        self.product_template_sofa.company_id = company_2
        self.env.user.company_ids = company_2
        options = {
            'displayImage': False, 'displayDescription': False, 'displayExtraLink': False,
            'displayDetail': False, 'allowFuzzy': True
        }
        _, results, _ = website._search_with_fuzzy('products_only', 'Sofa', 5, 'name asc', options)
        self.assertNotIn(self.product_template_sofa, results[0]['results'])

        self.env.user.company_ids += website.company_id
        self.product_template_sofa.company_id = website.company_id
        _, results, _ = website._search_with_fuzzy('products_only', 'Sofa', 5, 'name asc', options)
        self.assertIn(self.product_template_sofa, results[0]['results'])

        self.product_template_sofa.company_id = False
        _, results, _ = website._search_with_fuzzy('products_only', 'Sofa', 5, 'name asc', options)
        self.assertIn(self.product_template_sofa, results[0]['results'])


@tagged('post_install', '-at_install')
class TestWebsiteSaleFuzzy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.registry.has_trigram:
            cls.env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cls.env.registry.has_trigram = True
        cls.website = cls.env.ref('website.default_website')
        cls.public_user = cls.website.user_id
        cls.valid_product = cls.env['product.template'].create({
            'name': 'FuzzyProductUnique',
            'sale_ok': True,
            'is_published': True,
        })
        # More than the 1000 pre-ranking candidate limit: if eligibility were
        # applied after ranking, these closer matches would fill the limit and
        # hide the valid product.
        cls.decoy_products = cls.env['product.template'].create([{
            'name': f'FuzzyProdcutUnique-{index:04d}',
            'sale_ok': False,
            'is_published': True,
        } for index in range(1001)])
        cls.env.flush_all()
        cls.search_options = {
            'allowFuzzy': True,
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
        }

    def _search(self, term):
        website = self.website.with_user(self.public_user).with_context(
            website_id=self.website.id,
        )
        with MockRequest(website.env, website=website):
            return website._search_with_fuzzy(
                'products_only', term, limit=None, order='name asc',
                options=self.search_options,
            )

    def test_fuzzy_candidates_filtered_before_ranking(self):
        count, details, fuzzy_term = self._search('FuzzyProdcutUnique')

        self.assertEqual(fuzzy_term, 'fuzzyproductunique')
        self.assertEqual(count, 1)
        self.assertEqual(details[0]['results'].ids, self.valid_product.ids)

        count, details, fuzzy_term = self._search('FuzzyProductUnique')

        self.assertFalse(fuzzy_term)
        self.assertEqual(count, 1)
        self.assertEqual(details[0]['results'].ids, self.valid_product.ids)
