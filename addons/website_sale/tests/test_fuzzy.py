# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('-at_install', 'post_install')
class TestFuzzy(ProductVariantsCommon):
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
        self.assertIsNone(fuzzy_term, "Should have no suggestion")

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

    def test_search_description_ecommerce(self):
        """
        Products must appear in website search results when the search keyword
        exists only in the description_ecommerce field.

        Regression test for GitHub issue #267505.
        """
        website = self.env.ref('website.default_website')

        # Create a product with keyword only in description_ecommerce
        product = self.env['product.template'].create({
            'name': 'Regression Test Product 267505',
            'description_sale': False,
            'description_ecommerce': '<p>aperolspecialkeyword267505</p>',
            'is_published': True,
            'website_id': website.id,
        })
        self.cr.flush()  # flush to DB so search index picks it up, same pattern as existing tests

        options = {
            'displayDescription': True,
            'displayDetail': True,
            'display_currency': True,
            'displayExtraDetail': True,
            'displayExtraLink': True,
            'displayImage': True,
            'allowFuzzy': False,  # exact search — we want to confirm ilike match, not fuzzy
        }

        results_count, results, _ = website._search_with_fuzzy(
            'products_only', 'aperolspecialkeyword267505', 5, 'name asc', options
        )

        result_records = results[0]['results'] if results else []
        self.assertIn(
            product,
            result_records,
            "Product must appear in search results when keyword is in description_ecommerce"
        )
        self.assertGreaterEqual(results_count, 1, "Search must return at least one result")
