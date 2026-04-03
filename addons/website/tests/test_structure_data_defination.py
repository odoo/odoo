# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime

from odoo.tests import common, tagged

from odoo.addons.website.tools.jsonld_builder import JsonLd, create_breadcrumbs


@tagged('post_install', '-at_install')
class TestJsonLd(common.BaseCase):

    def test_set_and_get_normalized_keys(self):
        product = JsonLd("Product").set(name="Widget", price_currency="USD", product_id="P-1")

        self.assertEqual(product.get("name"), "Widget")
        self.assertEqual(product.get("price_currency"), "USD")
        self.assertEqual(product.get("product_id"), "P-1")
        self.assertEqual(product.get("missing", "default"), "default")

    def test_set_rejects_nested_jsonld_values(self):
        offer = JsonLd("Offer", price=10)

        with self.assertRaises(TypeError):
            JsonLd("Product").set(offers=offer)

        with self.assertRaises(TypeError):
            JsonLd("Product").set(offers=[offer])

    def test_add_nested_appends_and_rejects_invalid_existing_list(self):
        product = JsonLd("Product", name="Widget")
        offer_1 = JsonLd("Offer", price=10)
        offer_2 = JsonLd("Offer", price=20)

        product.add_nested(offers=offer_1)
        self.assertIs(product.values["offers"], offer_1)

        product.add_nested(offers=offer_2)
        self.assertEqual(len(product.values["offers"]), 2)
        self.assertTrue(all(isinstance(v, JsonLd) for v in product.values["offers"]))

        product.set(tags=["a", "b"])
        with self.assertRaises(TypeError):
            product.add_nested(tags=offer_1)

        with self.assertRaises(TypeError):
            product.add_nested(offers=False)

    def test_add_nested_rejects_invalid_item_in_existing_list(self):
        product = JsonLd("Product", name="Widget")
        product.values["offers"] = [JsonLd("Offer", price=10), "invalid"]

        with self.assertRaises(TypeError):
            product.add_nested(offers=JsonLd("Offer", price=20))

    def test_render_preserves_false_and_skips_none(self):
        data = JsonLd("Thing").set(name="Item", is_family_friendly=False, description=None)._render()
        self.assertEqual(data["isFamilyFriendly"], False)
        self.assertNotIn("description", data)

    def test_render_unwraps_single_list_item(self):
        product = JsonLd("Product", name="Widget")
        product.add_nested(offers=JsonLd("Offer", price=10, price_currency="USD"))
        rendered = product._render()
        self.assertIsInstance(rendered["offers"], dict)
        self.assertEqual(rendered["offers"]["@type"], "Offer")

    def test_render_structured_data_list(self):
        org = JsonLd("Organization", name="Org")
        website = JsonLd("WebSite", name="Site")
        self.assertFalse(JsonLd.render_structured_data_list([]))

        with self.assertRaises(TypeError):
            JsonLd.render_structured_data_list([org, "bad"])

        payload = JsonLd.render_structured_data_list([org, website])
        # convert back to dict to check the content, as render_structured_data_list returns a json string
        decoded = json.loads(payload)
        self.assertEqual(len(decoded), 2)
        self.assertEqual(decoded[0]["@type"], "Organization")
        self.assertEqual(decoded[1]["@type"], "WebSite")

    def test_render_json_prevents_ascii_escaping(self):
        data = JsonLd("Thing").set(name="Café")
        data = data.render_json()
        self.assertIn("Café", data)

    def test_render_structured_data_list_all_none_returns_false(self):
        self.assertFalse(JsonLd.render_structured_data_list([None, None]))

    def test_create_id_reference(self):
        with self.assertRaises(ValueError):
            JsonLd.create_id_reference("Organization", "")

        ref = JsonLd.create_id_reference("Organization", "https://example.com/#org")
        rendered = ref._render()

        self.assertEqual(rendered["@type"], "Organization")
        self.assertEqual(rendered["@id"], "https://example.com/#org")

    def test_datetime_normalization(self):
        naive = datetime(2025, 1, 15, 10, 30)
        self.assertEqual(JsonLd.datetime(naive), "2025-01-15T10:30:00+00:00")


class TestCreateBreadcrumbs(common.BaseCase):

    def test_create_breadcrumbs_filters_none_and_sets_positions(self):
        breadcrumbs = create_breadcrumbs([
            ("Home", "https://example.com/"),
            None,
            ("Products", "https://example.com/products"),
        ])

        self.assertIsNotNone(breadcrumbs)
        rendered = breadcrumbs._render()
        elements = rendered["itemListElement"]

        self.assertEqual(rendered["@type"], "BreadcrumbList")
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0]["position"], 1)
        self.assertEqual(elements[0]["name"], "Home")
        self.assertEqual(elements[1]["position"], 2)
        self.assertEqual(elements[1]["name"], "Products")

    def test_create_breadcrumbs_empty_returns_none(self):
        self.assertIsNone(create_breadcrumbs([None]))
        self.assertIsNone(create_breadcrumbs([]))
