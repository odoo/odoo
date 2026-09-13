from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRequestSourceIp(TransactionCase):
    def _source_ip_for(self, remote_addr):
        with patch.object(
            type(self.env["ir.http"]),
            "_get_request_remote_addr",
            return_value=remote_addr,
        ):
            return self.env["credential.credential"]._get_request_source_ip()

    def test_an_address_from_the_request_is_recorded(self):
        self.assertEqual(self._source_ip_for("203.0.113.9"), "203.0.113.9")
        self.assertEqual(self._source_ip_for("2001:db8::1"), "2001:db8::1")

    def test_no_request_records_no_address(self):
        self.assertIs(self._source_ip_for(None), False)

    def test_a_malformed_address_is_recorded_as_invalid(self):
        with self.assertLogs(
            "odoo.addons.credential.models.credential_credential", "WARNING"
        ):
            self.assertEqual(self._source_ip_for("not-an-ip"), "invalid")

    def test_outside_a_request_the_base_helper_has_no_address(self):
        self.assertIsNone(self.env["ir.http"]._get_request_remote_addr())
