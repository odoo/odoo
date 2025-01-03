# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import (
    TestSaleProductAttributeValueCommon,
)
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductFilters(WebsiteSaleCommon, TestSaleProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSnippetFilter = cls.env['website.snippet.filter'].with_context({
            'limit': 16,
            'search_domain': [],
            'allowed_company_ids': cls.env.company.ids,
        })

        # Computer accessories
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': "Color",
            'value_ids': [
                Command.create({'name': name})
                for name in ("Black", "Grey", "White", "Beige", "Red", "Pink")
            ],
        })
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.computer_case.id,
            'attribute_id': cls.color_attribute.id,
            'value_ids': [Command.set(cls.color_attribute.value_ids.ids)],
        })
        cls.computer_case.website_published = True
        cls.black_case_M = cls.computer_case.product_variant_ids.filtered_domain([
            ('product_template_attribute_value_ids.name', 'in', "Black"),
            ('product_template_attribute_value_ids.name', 'in', "M"),
        ])
        cls.pink_case_M = cls.computer_case.product_variant_ids.filtered_domain([
            ('product_template_attribute_value_ids.name', 'in', "Pink"),
            ('product_template_attribute_value_ids.name', 'in', "M"),
        ])
        cls.pink_case_L = cls.computer_case.product_variant_ids.filtered_domain([
            ('product_template_attribute_value_ids.name', 'in', "Pink"),
            ('product_template_attribute_value_ids.name', 'in', "L"),
        ])
        cls.monitor = cls.env['product.template'].create({
            'name': "Super Computer Monitor",
            'list_price': 200,
            'website_published': True,
        })
        cls.accessories = cls.computer_case.product_variant_ids + cls.monitor.product_variant_id
        cls.computer.write({
            'company_id': False,
            'website_published': True,
            'accessory_product_ids': cls.accessories.ids,
        })

        # Computer alternatives
        cls.windows_pc = cls.product_a.with_env(cls.env).product_tmpl_id
        cls.windows_pc.write({
            'name': "Windows PC",
            'company_id': False,
            'alternative_product_ids': cls.computer.ids,
            'website_published': True,
        })
        cls.mac = cls.product_b.with_env(cls.env).product_tmpl_id
        cls.mac.write({
            'name': "Mac",
            'company_id': False,
            'alternative_product_ids': (cls.computer + cls.windows_pc).ids,
            'website_published': True,
        })

    def test_latest_sold_filter(self):
        """Check the latest sold filter after selling 1 computer and 3 different cases.

        When showing variants, the computer should be the most sold product.
        When hiding variants, the case should be the most sold product.
        """
        computer = self.computer.product_variant_id
        self.empty_cart.write({
            'website_id': self.website.id,
            'order_line': [
                Command.create({'product_id': product_id})
                for product_id in (computer + self.pink_case_M + self.pink_case_L).ids
            ],
        })
        self.empty_cart.action_confirm()

        self.cart.order_line.unlink()
        self.cart.write({
            'website_id': self.website.id,
            'order_line': [
                Command.create({'product_id': product_id})
                for product_id in (computer + self.black_case_M).ids
            ],
        })
        self.cart.action_confirm()

        dyn_filter = self.env.ref('website_sale.dynamic_filter_latest_sold_products')
        with MockRequest(self.env, website=self.website):
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=False,
            )._get_products('latest_sold')
            self.assertSetEqual(
                {p['product_id'] for p in with_variants},
                {computer.id, *(self.pink_case_L + self.pink_case_M + self.black_case_M).ids},
                '"Latest sold" filter should return 4 products without hiding variants',
            )
            self.assertEqual(
                with_variants[0]['product_id'],
                computer.id,
                "When showing variants, `computer` should be the most sold product",
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=True,
            )._get_products('latest_sold')
            self.assertSetEqual(
                {p['product_id'] for p in no_variants},
                {computer.id, self.computer_case.product_variant_id.id},
                '"Latest sold" filter should return 2 products when hiding variants',
            )
            self.assertEqual(
                no_variants[0]['product_id'],
                self.computer_case.product_variant_id.id,
                "When hiding variants, `computer_case` should be the most sold product",
            )

    def test_latest_viewed_filter(self):
        """Check the latest viewed filter after viewing 2 different cases and 1 computer.

        When showing variants, the filter should return 3 items.
        When hiding variants, the filter should return 2 items.
        """
        viewed_products = self.black_case_M + self.pink_case_L + self.computer.product_variant_id
        dyn_filter = self.env.ref('website_sale.dynamic_filter_latest_viewed_products')
        with MockRequest(self.env, website=self.website):
            visitor = self.env['website.visitor']._upsert_visitor(self.env.user.partner_id.id)
            self.env['website.track'].create([{
                'visitor_id': visitor[0],
                'product_id': product_id,
            } for product_id in viewed_products.ids])
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=False,
            )._get_products('latest_viewed')
            self.assertSetEqual(
                {p['product_id'] for p in with_variants},
                set(viewed_products.ids),
                'When showing variants, "Latest viewed" filter should return viewed variants',
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=True,
            )._get_products('latest_viewed')
            self.assertSetEqual(
                {p['product_id'] for p in no_variants},
                {self.computer_case.product_variant_id.id, self.computer.product_variant_id.id},
                'When hiding variants, "Latest viewed" filter should return 1 variant per template',
            )

    def test_recently_sold_with_filter(self):
        """Check the recently-sold-with filter after selling 1 computer, 1 monitor & 1 case.

        When showing variants, the filter should return the sold variants.
        When hiding variants, the filter should return the default variants.
        """
        computer = self.computer.product_variant_id
        monitor = self.monitor.product_variant_id
        self.empty_cart.write({
            'website_id': self.website.id,
            'order_line': [
                Command.create({'product_id': product_id})
                for product_id in (computer + monitor + self.pink_case_L).ids
            ],
        })
        self.empty_cart.action_confirm()

        dyn_filter = self.env.ref('website_sale.dynamic_filter_cross_selling_recently_sold_with')
        with MockRequest(self.env, website=self.website):
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=False,
            )._get_products('recently_sold_with', product_template_id=str(self.computer.id))
            self.assertSetEqual(
                {p['product_id'] for p in with_variants},
                {self.monitor.product_variant_id.id, self.pink_case_L.id},
                '"Recently sold with" filter should return sold variants when showing variants',
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=True,
            )._get_products('recently_sold_with', product_template_id=str(self.computer.id))
            self.assertSetEqual(
                {p['product_id'] for p in no_variants},
                {self.monitor.product_variant_id.id, self.computer_case.product_variant_id.id},
                '"Recently sold with" filter should return generic variants when hiding variants',
            )

    def test_accessories_filter(self):
        """Check the accessories filter on the computer product.

        When showing variants, the filter should return 16 (limit) accessory products.
        When hiding variants, the filter should return 2 products: monitor & case.
        """
        dyn_filter = self.env.ref('website_sale.dynamic_filter_cross_selling_accessories')
        with MockRequest(self.env, website=self.website):
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=False,
            )._get_products('accessories', product_template_id=str(self.computer.id))
            self.assertListEqual(
                [p['product_id'] for p in with_variants],
                self.computer_case.product_variant_ids.ids[:16],
                "Accessories filter should return 16 results when showing variants",
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=True,
            )._get_products('accessories', product_template_id=str(self.computer.id))
            self.assertListEqual(
                [p['product_id'] for p in no_variants],
                self.accessories.product_variant_id.ids,
                "Accessories filter should return 2 results when hiding variants",
            )

    def test_alternative_products_filter(self):
        """Check the alternative products filter on the Mac product.

        When showing variants, the filter should return 16 (limit) alternative products.
        When hiding variants, the filter should return 2 products: computer & Windows PC.
        """
        dyn_filter = self.env.ref('website_sale.dynamic_filter_cross_selling_alternative_products')
        with MockRequest(self.env, website=self.website):
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=False,
            )._get_products('alternative_products', product_template_id=str(self.mac.id))
            self.assertListEqual(
                [p['product_id'] for p in with_variants],
                self.mac.alternative_product_ids.product_variant_ids.ids[:16],
                "Alternative products filter should return 16 results when showing variants",
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter,
                hide_variants=True,
            )._get_products('alternative_products', product_template_id=str(self.mac.id))
            self.assertListEqual(
                [p['product_id'] for p in no_variants],
                [self.computer.product_variant_id.id, self.windows_pc.product_variant_id.id],
                "Alternative products filter should return 2 results when hiding variants",
            )
