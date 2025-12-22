# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.tests import tagged


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
