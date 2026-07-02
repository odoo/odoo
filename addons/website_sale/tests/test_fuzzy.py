# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged("-at_install", "post_install")
class TestFuzzy(ProductVariantsCommon):
    _test_groups = None  # FIXME list needed groups

    def test_variant_default_code(self):
        website = self.env.ref("base.default_website")

        line = self.product_template_sofa.attribute_line_ids
        value_red = line.product_template_value_ids[0]
        value_blue = line.product_template_value_ids[1]
        value_green = line.product_template_value_ids[2]
        product_red = self.product_template_sofa._get_variant_for_combination(value_red)
        product_blue = self.product_template_sofa._get_variant_for_combination(value_blue)
        product_green = self.product_template_sofa._get_variant_for_combination(value_green)
        product_red.default_code = "RED_12345"
        product_blue.default_code = "BLUE_ABCDE"
        product_green.default_code = "GREEN_98765"
        self.cr.flush()

        options = {"display_currency": True, "allowFuzzy": True}
        results_count, _, fuzzy_term = website._search_with_fuzzy(
            "product_template", "RED234", 0, 5, "name asc", options
        )
        self.assertEqual(1, results_count, "Should have found red")
        self.assertEqual("red_12345", fuzzy_term, "Should suggest red")
        results_count, _, fuzzy_term = website._search_with_fuzzy(
            "product_template", "GROEN98765", 0, 5, "name asc", options
        )
        self.assertEqual(1, results_count, "Should have found green")
        self.assertEqual("green_98765", fuzzy_term, "Should suggest green")
        results_count, _, fuzzy_term = website._search_with_fuzzy(
            "product_template", "BLUABCE", 0, 5, "name asc", options
        )
        self.assertEqual(1, results_count, "Should have found blue")
        self.assertEqual("blue_abcde", fuzzy_term, "Should suggest blue")
        results_count, _, fuzzy_term = website._search_with_fuzzy(
            "product_template", "SQWBRNZ", 0, 5, "name asc", options
        )
        self.assertEqual(0, results_count, "Should have found none")
        self.assertIsNone(fuzzy_term, "Should have no suggestion")

    def test_search_products_accessibility_multi_company(self):
        company_2 = self.env["res.company"].create({"name": "test"})
        website = self.env.ref("base.default_website")
        self.product_template_sofa.company_id = company_2
        self.env.user.company_ids = company_2
        options = {"display_currency": False, "allowFuzzy": True}
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertNotIn(self.product_template_sofa, results[0]["results"])

        self.env.user.company_ids += website.company_id
        self.product_template_sofa.company_id = website.company_id
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertIn(self.product_template_sofa, results[0]["results"])

        self.product_template_sofa.company_id = False
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertIn(self.product_template_sofa, results[0]["results"])
