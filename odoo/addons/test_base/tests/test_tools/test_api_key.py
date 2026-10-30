from odoo.tests import BaseCase
from odoo.tools import api_key


class TestToolsApiKey(BaseCase):
    def test_new_api_key(self):
        key = api_key.new_api_key(readonly=False)
        token, suffix = key.split('_')
        self.assertEqual(len(bytes.fromhex(token)), 20, key)
        self.assertEqual(suffix, 'oak')
        self.assertTrue(api_key.is_api_key(key), key)
        self.assertTrue(api_key.is_readwrite_api_key(key), key)
        self.assertFalse(api_key.is_readonly_api_key(key), key)

    def test_new_ro_api_key(self):
        key = api_key.new_api_key(readonly=True)
        prefix, token, suffix = key.split('_')
        self.assertEqual(prefix, 'ro')
        self.assertEqual(len(bytes.fromhex(token)), 20, key)
        self.assertEqual(suffix, 'oak')
        self.assertTrue(api_key.is_api_key(key), key)
        self.assertFalse(api_key.is_readwrite_api_key(key), key)
        self.assertTrue(api_key.is_readonly_api_key(key), key)

    def test_api_key_unique(self):
        many_keys = [
            api_key.new_api_key(readonly=False) for _ in range(50)
        ] + [
            api_key.new_api_key(readonly=True) for _ in range(50)
        ]
        self.assertEqual(len(many_keys), len(set(many_keys)))

    def test_are_keys_api_keys(self):
        token = "a" * 40
        for key, is_key in [
            (token, True),
            (f'{token}_oak', True),
            (f'ro_{token}_oak', True),
            ('supersecretpassword', False),
        ]:
            with self.subTest(key=key):
                self.assertEqual(api_key.is_api_key(key), is_key)
