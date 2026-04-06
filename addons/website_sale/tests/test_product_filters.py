# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time
from lxml import html
from odoo import Command, fields
from odoo.tests import HttpCase, tagged
from odoo.tools import SQL

from odoo.addons.product.tests.test_product_attribute_value_config import (
    TestProductAttributeValueCommon,
)
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleProductFilters(WebsiteSaleCommon, TestProductAttributeValueCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSnippetFilter = cls.env["website.snippet.filter"].with_context({
            "limit": 16,
            "search_domain": [],
            "allowed_company_ids": cls.env.company.ids,
        })

        # Computer accessories
        cls.color_attribute = cls.env["product.attribute"].create({
            "name": "Color",
            "value_ids": [
                Command.create({"name": name})
                for name in ("Black", "Grey", "White", "Beige", "Red", "Pink")
            ],
        })
        cls.env["product.template.attribute.line"].create({
            "product_tmpl_id": cls.computer_case.id,
            "attribute_id": cls.color_attribute.id,
            "value_ids": [Command.set(cls.color_attribute.value_ids.ids)],
        })
        cls.computer_case.website_published = True
        cls.black_case_M = cls.computer_case.product_variant_ids.filtered_domain([
            ("product_template_attribute_value_ids.name", "in", "Black"),
            ("product_template_attribute_value_ids.name", "in", "M"),
        ])
        cls.pink_case_M = cls.computer_case.product_variant_ids.filtered_domain([
            ("product_template_attribute_value_ids.name", "in", "Pink"),
            ("product_template_attribute_value_ids.name", "in", "M"),
        ])
        cls.pink_case_L = cls.computer_case.product_variant_ids.filtered_domain([
            ("product_template_attribute_value_ids.name", "in", "Pink"),
            ("product_template_attribute_value_ids.name", "in", "L"),
        ])
        cls.monitor = cls.env["product.template"].create({
            "name": "Super Computer Monitor",
            "list_price": 200,
            "website_published": True,
        })
        cls.accessories = cls.computer_case.product_variant_ids + cls.monitor.product_variant_id
        cls.computer.write({
            "company_id": False,
            "website_published": True,
            "accessory_product_ids": cls.accessories.ids,
        })

        # Computer alternatives
        cls.windows_pc = cls._create_product(
            name="Windows PC",
            lst_price=1000.0,
            standard_price=800.0,
            alternative_product_ids=[Command.set(cls.computer.ids)],
        ).product_tmpl_id
        cls.mac = cls._create_product(
            name="Mac",
            uom_id=cls.uom_dozen.id,
            lst_price=200.0,
            standard_price=160.0,
            alternative_product_ids=[
                Command.link(cls.computer.id),
                Command.link(cls.windows_pc.id),
            ],
        ).product_tmpl_id

        # More generic products to get the number of product templates to 17
        generics = cls.env["product.template"].create([
            {"name": f"Generic product {i}", "company_id": False, "website_published": True}
            for i in range(1, 13)
        ])

        cls.product_tmpls = (
            cls.computer_case + cls.monitor + cls.computer + cls.windows_pc + cls.mac + generics
        )

        # Archive all products not relevant to the test suite, bypassing ORM constraints
        cls.env.invalidate_all()
        cls.env.cr.execute(
            SQL("; ").join(
                SQL(
                    "UPDATE %s SET active = false WHERE id NOT IN %s",
                    SQL.identifier(recs._table),
                    recs._ids,
                )
                for recs in (cls.product_tmpls.product_variant_ids, cls.product_tmpls)
            )
        )

    def assert_snippet_filters_route_public_access(self, filter, products, **kwargs):
        """Assert the access as a public user to the data returned by the route /website/snippet/filters

        The route must allow the public user to see the expected products
        while ensuring he cannot extract data with a dichotomic search using the `search_domain`
        e.g. the search of products is done with the (public) user access rights.
        """

        result = self.url_open("/website/snippet/filters", json={"params": {
            "filter_id": filter.id,
            "template_key": "website_sale.dynamic_filter_template_product_product_products_item",
            "limit": 16,
            "search_domain": [],
            **kwargs,
        }}).json()["result"]
        self.assertEqual(len(result), len(products))
        for product, html_description in zip(products, result):
            tree = html.fromstring(html_description)
            self.assertEqual(' '.join(tree.xpath('//h6')[0].text_content().split()), product.display_name)
            self.assertEqual(
                tree.xpath('//*[@name="product_price"]/span')[0].text,
                self.env['ir.qweb.field.float'].value_to_html(product.lst_price, {'precision': 2})
            )

        # A visitor / public user must not be able to guess the cost price of sold products through the search domain
        with self.assertLogs("odoo.http", "WARNING") as logs:
            result = self.url_open("/website/snippet/filters", json={"params": {
                "filter_id": filter.id,
                "template_key": "website_sale.dynamic_filter_template_product_product_products_item",
                "limit": 16,
                "search_domain": [("standard_price", "=", 42)],
                **kwargs,
            }}).json()
            self.assertIn('You do not have enough rights to access the field "standard_price"', logs.output[0])
            self.assertTrue(result.get('error'))

    def test_latest_sold_filter_returns_latest_sold_product(self):
        base_time = fields.Datetime.now()
        computer = self.computer.product_variant_id
        so_computer = self._create_so(
            date_order=base_time,
            state="sale",
            order_line=[Command.create({"product_id": computer.id})],
        )
        # Create a second sale order that is the most recent.
        self._create_so(
            date_order=fields.Datetime.add(so_computer.date_order, hours=1),
            state="sale",
            order_line=[Command.create({"product_id": self.pink_case_M.id})],
        )
        dyn_filter = self.env.ref("website_sale.dynamic_filter_latest_sold_products")
        with self.mock_request():
            products = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, website_id=self.website.id
            )._get_products("latest_sold")
        self.assertEqual(products[0]["product_id"], self.pink_case_M.id)

        self.assert_snippet_filters_route_public_access(dyn_filter, self.pink_case_M + computer)

    def test_latest_sold_filter_returns_all_variants_by_default(self):
        self._create_so(
            state="sale",
            order_line=[
                Command.create({"product_id": self.pink_case_M.id}),
                Command.create({"product_id": self.pink_case_L.id}),
            ],
        )
        dyn_filter = self.env.ref("website_sale.dynamic_filter_latest_sold_products")
        with self.mock_request():
            products = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, website_id=self.website.id, limit=2
            )._get_products("latest_sold")
        product_ids = {p["product_id"] for p in products}
        self.assertSetEqual(product_ids, {self.pink_case_M.id, self.pink_case_L.id})

        self.assert_snippet_filters_route_public_access(dyn_filter, self.pink_case_M + self.pink_case_L)

    def test_latest_sold_filter_hides_variants_if_context(self):
        self._create_so(
            state="sale",
            order_line=[
                Command.create({"product_id": self.pink_case_M.id}),
                Command.create({"product_id": self.pink_case_L.id}),
            ],
        )
        dyn_filter = self.env.ref("website_sale.dynamic_filter_latest_sold_products")
        with self.mock_request():
            products = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=True, website_id=self.website.id
            )._get_products("latest_sold")
        product_ids = {p["product_id"] for p in products}
        self.assertSetEqual(product_ids, {self.computer_case.product_variant_id.id})

        self.assert_snippet_filters_route_public_access(dyn_filter, self.pink_case_M + self.pink_case_L)

    def test_latest_sold_filter_returns_only_sellable_products(self):
        not_sellable_product = self.env["product.product"].create({
            "name": "Not sellable product",
            "sale_ok": False,
        })
        self._create_so(
            state="sale",
            order_line=[
                Command.create({"product_id": self.pink_case_M.id}),
                Command.create({"product_id": not_sellable_product.id}),
            ],
        )
        dyn_filter = self.env.ref("website_sale.dynamic_filter_latest_sold_products")
        with self.mock_request():
            products = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, website_id=self.website.id
            )._get_products("latest_sold")
        self.assertTrue(all(p["_record"].sale_ok for p in products))

        self.assert_snippet_filters_route_public_access(dyn_filter, self.pink_case_M)

    def test_latest_viewed_filter(self):
        """Check the latest viewed filter after viewing 2 different cases and 1 computer.

        When showing variants, the filter should return 3 items.
        When hiding variants, the filter should return 2 items.
        """
        viewed_products = self.black_case_M + self.pink_case_L + self.computer.product_variant_id
        dyn_filter = self.env.ref("website_sale.dynamic_filter_latest_viewed_products")
        with self.mock_request(user=self.env.user):
            visitor = self.env["website.visitor"]._upsert_visitor(self.env.user.partner_id.id)
            self.env["website.track"].create([
                {"visitor_id": visitor[0], "product_id": product_id}
                for product_id in viewed_products.ids
            ])
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=False
            )._get_products("latest_viewed")
            self.assertSetEqual(
                {p["product_id"] for p in with_variants},
                set(viewed_products.ids),
                'When showing variants, "Latest viewed" filter should return viewed variants',
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=True
            )._get_products("latest_viewed")
            self.assertSetEqual(
                {p["product_id"] for p in no_variants},
                {self.computer_case.product_variant_id.id, self.computer.product_variant_id.id},
                'When hiding variants, "Latest viewed" filter should return 1 variant per template',
            )

        now = datetime.now()
        for i, product in enumerate(viewed_products):
            with freeze_time(now - timedelta(seconds=i)):
                self.url_open("/shop/products/recently_viewed_update", json={"params": {"product_id": product.id}})

        self.assert_snippet_filters_route_public_access(dyn_filter, viewed_products)

    def test_recently_sold_with_filter(self):
        """Check the recently-sold-with filter after selling 1 computer, 1 monitor & 1 case.

        When showing variants, the filter should return the sold variants.
        When hiding variants, the filter should return the default variants.
        """
        computer = self.computer.product_variant_id
        monitor = self.monitor.product_variant_id
        self._create_so(
            order_line=[
                Command.create({"product_id": product_id})
                for product_id in (computer + monitor + self.pink_case_L).ids
            ]
        ).action_confirm()

        dyn_filter = self.env.ref("website_sale.dynamic_filter_cross_selling_recently_sold_with")
        with self.mock_request():
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=False, website_id=self.website.id
            )._get_products("recently_sold_with", product_template_id=str(self.computer.id))
            self.assertSetEqual(
                {p["product_id"] for p in with_variants},
                {self.monitor.product_variant_id.id, self.pink_case_L.id},
                '"Recently sold with" filter should return sold variants when showing variants',
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=True, website_id=self.website.id
            )._get_products("recently_sold_with", product_template_id=str(self.computer.id))
            self.assertSetEqual(
                {p["product_id"] for p in no_variants},
                {self.monitor.product_variant_id.id, self.computer_case.product_variant_id.id},
                '"Recently sold with" filter should return generic variants when hiding variants',
            )

        self.assert_snippet_filters_route_public_access(
            dyn_filter,
            self.pink_case_L + monitor,
            productTemplateId=str(self.computer.id)
        )

    def test_accessories_filter(self):
        """Check the accessories filter on the computer product.

        When showing variants, the filter should return 16 (limit) accessory products.
        When hiding variants, the filter should return 2 products: monitor & case.
        """
        dyn_filter = self.env.ref("website_sale.dynamic_filter_cross_selling_accessories")
        with self.mock_request():
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=False
            )._get_products("accessories", product_template_id=str(self.computer.id))
            self.assertListEqual(
                [p["product_id"] for p in with_variants],
                self.computer_case.product_variant_ids.ids[:16],
                "Accessories filter should return 16 results when showing variants",
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=True
            )._get_products("accessories", product_template_id=str(self.computer.id))
            self.assertListEqual(
                [p["product_id"] for p in no_variants],
                self.accessories.product_variant_id.ids,
                "Accessories filter should return 2 results when hiding variants",
            )

        self.assert_snippet_filters_route_public_access(
            dyn_filter,
            self.computer_case.product_variant_ids[:16],
            productTemplateId=str(self.computer.id)
        )

    def test_alternative_products_filter(self):
        """Check the alternative products filter on the Mac product.

        When showing variants, the filter should return 16 (limit) alternative products.
        When hiding variants, the filter should return 2 products: computer & Windows PC.
        """
        dyn_filter = self.env.ref("website_sale.dynamic_filter_cross_selling_alternative_products")
        with self.mock_request():
            with_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=False
            )._get_products("alternative_products", product_template_id=str(self.mac.id))
            self.assertListEqual(
                [p["product_id"] for p in with_variants],
                self.mac.alternative_product_ids.product_variant_ids.ids[:16],
                "Alternative products filter should return 16 results when showing variants",
            )

            no_variants = self.WebsiteSnippetFilter.with_context(
                dynamic_filter=dyn_filter, hide_variants=True
            )._get_products("alternative_products", product_template_id=str(self.mac.id))
            self.assertListEqual(
                [p["product_id"] for p in no_variants],
                [self.computer.product_variant_id.id, self.windows_pc.product_variant_id.id],
                "Alternative products filter should return 2 results when hiding variants",
            )

        self.assert_snippet_filters_route_public_access(
            dyn_filter,
            self.mac.alternative_product_ids.product_variant_ids[:16],
            productTemplateId=str(self.mac.id)
        )

    def test_newest_products_filter(self):
        """Check the newest products filter.

        When showing variants, the filter should return 16 variants with repeating templates.
        When hiding variants, the filter should return 16 templates, all unique.

        This filter is unique in that it's defined in `data/data.xml`, and hence can't be called
        via the `_get_products` method.
        """
        # Ensure we're working with a known set of products
        self.env["product.template"].search([("id", "not in", self.product_tmpls.ids)]).write({
            "sale_ok": False
        })

        dyn_filter = self.env.ref("website_sale.dynamic_filter_newest_products")
        with self.mock_request():
            with_variants = dyn_filter._prepare_values(search_domain=[])
            self.assertEqual(
                len(with_variants),
                16,
                "When displaying newest variants, 16 records should be shown",
            )
            self.assertLess(
                len({p["product_template_id"] for p in with_variants}),
                16,
                "When displaying newest variants, some product templates should be repeating",
            )

            no_variants = dyn_filter._prepare_values(search_domain=["hide_variants"])
            self.assertEqual(len(no_variants), 16)
            self.assertEqual(
                len({p["product_template_id"] for p in no_variants}),
                16,
                "When displaying newest product templates, 16 unique templates should be shown",
            )

        products = self.computer_case.product_variant_ids[:16]
        now = datetime.now()
        for i, product in enumerate(products):
            self.env.cr.execute(
                "UPDATE product_product SET create_date = %s WHERE id = %s",
                (fields.Datetime.to_string(now + timedelta(seconds=i)), product.id)
            )
        self.assert_snippet_filters_route_public_access(dyn_filter, products.sorted(reverse=True))

    def test_shop_attribute_filters_remain_when_changing_page(self):
        self.env["product.attribute"].search([]).write({"visibility": "hidden"})
        self.color_attribute.visibility = "visible"
        self.size_attribute.visibility = "visible"
        self.env["website"].get_current_website().shop_ppg = 1
        computer_case_copy = self.computer_case.copy()
        computer_case_copy.website_published = True
        self.start_tour("/shop", "shop_attribute_filters_remain_when_changing_page")

    def test_product_public_category_model_access(self):
        """Ensure that access to models not linked to a dynamic snippet filter is denied."""

        product_public_category_filter = self.env.ref('website_sale.dynamic_filter_category_list')
        result = self.url_open("/website/snippet/filters", json={"params": {
            "template_key": "website_sale.dynamic_filter_template_product_public_category_default",
            "filter_id": product_public_category_filter.id,
            "res_model": "product.template",
            "search_domain": [],
            "res_id": self.computer.id,
            "limit": 1,
        }}).json().get('result', [])
        self.assertEqual(len(result), 0)

    def test_newest_products_filter_unpublished_access(self):
        """Ensure unpublished products cannot be fetched using a mono-record snippet configuration"""

        product_filter = self.env.ref('website_sale.dynamic_filter_newest_products')
        # Unpublish products. The product dynamic snippet should be empty.
        products = self.env['product.product'].search([])
        products.write({'website_published': False})
        result = self.url_open("/website/snippet/filters", json={"params": {
            "template_key": "website_sale.dynamic_filter_template_product_product_products_item",
            "filter_id": product_filter.id,
            "res_model": "product.product",
            "search_domain": [],
            "res_id": self.computer.product_variant_id.id,
            "limit": 1,
        }}).json().get('result', [])
        self.assertEqual(len(result), 0)
