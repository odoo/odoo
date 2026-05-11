# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime

from odoo.tests import common, tagged

from odoo.addons.website.helpers.jsonld_builder import JsonLd


@tagged('post_install', '-at_install')
class TestJsonLd(common.BaseCase):

    def test_set_rejects_nested_jsonld_values(self):
        offer = JsonLd('Offer', {'price': 10})

        with self.assertRaises(TypeError):
            JsonLd('Product').set({'offers': offer})

        with self.assertRaises(TypeError):
            JsonLd('Product').set({'offers': [offer]})

    def test_add_nested_appends_and_rejects_invalid_existing_list(self):
        product = JsonLd('Product', {'name': 'Widget'})
        offer_1 = JsonLd('Offer', {'price': 10})
        offer_2 = JsonLd('Offer', {'price': 20})

        product.add_nested({'offers': offer_1})
        self.assertIs(product.values['offers'], offer_1)

        product.add_nested({'offers': offer_2})
        self.assertEqual(len(product.values['offers']), 2)
        self.assertTrue(all(isinstance(v, JsonLd) for v in product.values['offers']))

        product.set({'tags': ['a', 'b']})
        with self.assertRaises(TypeError):
            product.add_nested({'tags': offer_1})

        with self.assertRaises(TypeError):
            product.add_nested({'offers': False})

    def test_render_preserves_false_and_skips_none(self):
        data = JsonLd('Thing').set({'name': 'Item', 'isFamilyFriendly': False, 'description': None})._to_jsonld_dict()
        self.assertEqual(data['isFamilyFriendly'], False)
        self.assertNotIn('description', data)

    def test_render_unwraps_single_list_item(self):
        product = JsonLd('Product', {'name': 'Widget'})
        product.add_nested({'offers': JsonLd('Offer', {'price': 10, 'priceCurrency': 'USD'})})
        rendered = product._to_jsonld_dict()
        self.assertIsInstance(rendered['offers'], dict)
        self.assertEqual(rendered['offers']['@type'], 'Offer')

    def test_render_structured_data(self):
        org = JsonLd('Organization', {'name': 'Org'})
        website = JsonLd('WebSite', {'name': 'Site'})
        self.assertFalse(JsonLd.render_structured_data([]))

        with self.assertRaises(TypeError):
            JsonLd.render_structured_data([org, 'bad'])

        payload = JsonLd.render_structured_data([org, website])
        # convert back to dict to check the content, as render_structured_data_list returns a json string
        decoded = json.loads(payload)
        self.assertEqual(len(decoded), 2)
        self.assertEqual(decoded[0]['@type'], 'Organization')
        self.assertEqual(decoded[1]['@type'], 'WebSite')

    def test_render_json_prevents_ascii_escaping(self):
        data = JsonLd('Thing').set({'name': 'Café'})
        data = JsonLd.render_structured_data([data])
        self.assertIn('Café', data)

    def test_datetime_normalization(self):
        naive = datetime(2025, 1, 15, 10, 30)
        self.assertEqual(JsonLd.to_iso_datetime(naive), '2025-01-15T10:30:00+00:00')
