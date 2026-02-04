import logging
from urllib.parse import urlencode

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
class TestUrllib(TransactionCase):
    def test_urlencode_monkeypatch(self):
        """Try to use `urlencode` incorrectly, and check that warnings are emitted."""
        self.assertEqual(urlencode({"a": "b", "foo": "bar"}), "a=b&foo=bar")
        self.assertEqual(urlencode({"a": ["b", "c"]}, doseq=True), "a=b&a=c")

        with self.assertWarns(UserWarning):
            self.assertEqual(urlencode({"a": ["b"]}), "a=%5B%27b%27%5D")

        with self.assertWarns(UserWarning):
            self.assertEqual(urlencode({"a": None}), "a=None")

        with self.assertWarns(UserWarning):
            self.assertEqual(urlencode({"a": [None]}, doseq=True), "a=None")
