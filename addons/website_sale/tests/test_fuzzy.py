# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.http_routing.tests.common import MockRequest as HttpRoutingMockRequest
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest


@tagged("-at_install", "post_install")
class TestFuzzy(ProductVariantsCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'website.group_website_designer',  # read website to run _search_with_fuzzy
    )

    _test_user_name = 'Test Product Manager'

    def test_shop_and_search_bar_use_same_search_fields(self):
        website = self.env.ref("base.default_website")
        product_tmpl = self.env['product.template']
        expected_fields = [
            'name', 'variants_default_code',
            'description_ecommerce', 'attribute_line_ids.value_ids.name',
            'product_tag_ids.name', 'public_categ_ids.name', 'description_sale',
        ]
        options = {
            'displayImage': False, 'displayDescription': True, 'displayExtraLink': False,
            'displayDetail': False, 'display_currency': website.currency_id, 'allowFuzzy': False,
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

        visible_tag = self.env['product.tag'].create({
            'name': 'unique_term',
            'visible_to_customers': True,
        })
        product_by_tag = product_tmpl.create({
            'name': 'Product searched by tag',
            'is_published': True,
            'product_tag_ids': [Command.link(visible_tag.id)],
        })
        searched_products |= product_by_tag
        self.assertEqual(searched_products.filtered_domain(shop_domain), searched_products)

        for field in ('description', 'website_description'):
            product = product_tmpl.create({
                'name': f'Product not searched by {field}',
                field: 'unique_term',
                'is_published': True,
            })
            self.assertFalse(product.filtered_domain(shop_domain), f'Should not search in {field}')

        hidden_tag = self.env['product.tag'].create({
            'name': 'hidden_unique_term',
            'visible_to_customers': False,
        })
        product_by_hidden_tag = product_tmpl.create({
            'name': 'Product not searched by hidden tag',
            'is_published': True,
            'product_tag_ids': [Command.link(hidden_tag.id)],
        })
        with MockRequest(self.env, website=website):
            hidden_tag_domain = WebsiteSale()._get_shop_domain('hidden_unique_term', None, {})
        self.assertFalse(product_by_hidden_tag.filtered_domain(hidden_tag_domain))

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
        company_2 = self.env["res.company"].sudo().create({"name": "test"})
        website = self.env.ref("base.default_website")
        self.product_template_sofa.sudo().company_id = company_2  # FIXME: remove the sudo()
        self.env.user.sudo().company_id = company_2

        options = {"display_currency": False, "allowFuzzy": True}
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertNotIn(self.product_template_sofa, results[0]["results"])

        self.env.user.sudo().company_ids += website.company_id
        self.product_template_sofa.sudo().company_id = website.company_id  # FIXME: remove the sudo()
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertIn(self.product_template_sofa, results[0]["results"])

        self.product_template_sofa.sudo().company_id = False  # FIXME: remove the sudo()
        _, results, _ = website._search_with_fuzzy(
            "product_template", "Sofa", 0, 5, "name asc", options
        )
        self.assertIn(self.product_template_sofa, results[0]["results"])

    def test_search_product_tags(self):
        """ Tests that when searching a product by its tags, we only fetch the tags visible to customers"""
        website = self.env.ref("base.default_website")
        tag1, tag2 = self.env['product.tag'].create([
            {'name': 'Some tag1'},
            {'name': 'Some tag2', 'visible_to_customers': False},
        ])
        self.product_template_sofa.product_tag_ids = tag1 + tag2
        options = {'display_currency': self.env.ref('base.EUR'), 'allowFuzzy': False}
        result_count, _, _ = website._search_with_fuzzy('product_template', 'Some tag1', 0, 5, 'name asc', options)
        self.assertEqual(result_count, 1)
        result_count, _, _ = website._search_with_fuzzy('product_template', 'Some tag2', 0, 5, 'name asc', options)
        self.assertEqual(result_count, 0)

        result_count, results, _ = website.with_context(website_id=website.id)._search_with_fuzzy('product_template', 'Some tag', 0, 5, 'name asc', options)
        self.assertEqual(result_count, 1)
        # Needed because `_get_additionnal_combination_info` uses request.pricelist & request.fiscal_position
        with HttpRoutingMockRequest(self.env, website=website) as request:
            request.pricelist = self.env['product.pricelist'].create({
                'name': 'Some pricelist',
            })
            request.fiscal_position = self.env['account.fiscal.position'].sudo().create({
                'name': 'Some fiscal postion'
            })
            results = website._search_render_results(results, 5)
            badges = results[0]['results_data'][0]['badges']
            badge_names = [badge['name'] for badge in badges]
            self.assertIn('Some tag1', badge_names)
            self.assertNotIn('Some tag2', badge_names)
