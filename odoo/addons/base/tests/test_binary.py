# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.binary import BinaryBytes


@tagged('at_install', '-post_install')
class TestBinaryValue(TransactionCase):
    def test_binary_bytes(self):
        data = b'test'
        val = BinaryBytes(data)
        self.assertIsInstance(val, BinaryBytes)
        self.assertIs(val.content, data)

        self.assertEqual(val.size, len(data))
        self.assertTrue(val.mimetype, "determine a mimetype")
        self.assertEqual(val.decode(), 'test')
        self.assertEqual(val.to_base64(), b64encode(data).decode())

        self.assertFalse(BinaryBytes(b''))

    def test_binary_open(self):
        with self.subTest("Can open multiple times (from_bytes)"):
            data = b'my data'
            val = BinaryBytes(data)
            for i in range(1, 3):
                with val.open() as f:
                    self.assertEqual(f.read(), data, f"Read {i}")
