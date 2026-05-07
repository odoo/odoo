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
