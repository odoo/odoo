from odoo.addons.account_batch_payment.models.sepa_mapping import sanitize_communication
from odoo.tests.common import TransactionCase


class TestSepaMapping(TransactionCase):
    def test_sepa_mapping(self):
        self.assertEqual(sanitize_communication("Hello/world", 5), "Hello")
        self.assertEqual(sanitize_communication("Hello / World"), "Hello / World")
        self.assertEqual(sanitize_communication("Hello // World"), "Hello / World")
        self.assertEqual(sanitize_communication("Hello //// W//orld"), "Hello / W/orld")
        self.assertEqual(sanitize_communication("/Hello / World/"), "Hello / World")
        self.assertEqual(sanitize_communication("Hello / World /"), "Hello / World ")
        self.assertEqual(sanitize_communication("\u1F9E/Hello"), "Hello")
        self.assertEqual(sanitize_communication("Hello/\u1F9E"), "Hello")
        self.assertEqual(sanitize_communication("Hello/\u1F9E/ World"), "Hello/ World")
        self.assertEqual(sanitize_communication("Net & Cost"), "Net + Cost")
