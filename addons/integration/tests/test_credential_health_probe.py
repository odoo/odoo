from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.integration.tests.common import APITransportTestCase
from odoo.addons.integration.tools.api_client import OutboundAPIClient


@tagged("post_install", "-at_install", "integration")
class TestCredentialHealthProbe(APITransportTestCase):
    def _probe(self, answered):
        self.credential_bearer.sudo().auto_validate_health = True
        with patch.object(OutboundAPIClient, "probe_health", return_value=answered):
            return self.env["credential.credential"]._cron_probe_credentials()

    def test_the_cron_probes_an_endpoint_bound_credential(self):
        result = self._probe(True)

        self.assertGreaterEqual(result["healthy"], 1)
        credential = self.credential_bearer.sudo()
        self.assertEqual(credential.health_status, "healthy")
        self.assertEqual(credential.total_health_checks, 1)
        self.assertEqual(credential.failed_health_checks, 0)
        self.assertTrue(credential.last_validated)

    def test_a_failed_probe_is_recorded_as_an_error(self):
        result = self._probe(False)

        self.assertGreaterEqual(result["errors"], 1)
        credential = self.credential_bearer.sudo()
        self.assertEqual(credential.health_status, "error")
        self.assertEqual(credential.failed_health_checks, 1)

    def test_the_form_button_answers_with_a_notification(self):
        with patch.object(OutboundAPIClient, "probe_health", return_value=True):
            action = self.credential_bearer.action_probe_health()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["params"]["type"], "success")
