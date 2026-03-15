from odoo.tests import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestKodooLegalPages(HttpCase):
    def test_privacy_policy_is_public(self):
        response = self.url_open("/privacy-policy", timeout=20)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Privacy Policy", response.text)
        self.assertIn("QuickBooks Online", response.text)
        self.assertIn("privacy@kodoo.online", response.text)

    def test_eula_is_public(self):
        response = self.url_open("/eula", timeout=20)

        self.assertEqual(response.status_code, 200)
        self.assertIn("End-User License Agreement", response.text)
        self.assertIn("kodoo.online", response.text)
        self.assertIn("legal@kodoo.online", response.text)

    def test_quickbooks_setup_hub_is_public(self):
        response = self.url_open("/quickbooks", timeout=20)

        self.assertEqual(response.status_code, 200)
        self.assertIn("QuickBooks App Setup Hub", response.text)
        self.assertIn("https://kodoo.online/quickbooks/launch", response.text)
        self.assertIn("https://kodoo.online/quickbooks/connect", response.text)

    def test_quickbooks_action_pages_are_public(self):
        connect_response = self.url_open("/quickbooks/connect", timeout=20)
        launch_response = self.url_open("/quickbooks/launch", timeout=20)
        disconnect_response = self.url_open("/quickbooks/disconnect", timeout=20)

        self.assertEqual(connect_response.status_code, 200)
        self.assertIn("Connect Or Reconnect QuickBooks", connect_response.text)

        self.assertEqual(launch_response.status_code, 200)
        self.assertIn("Launch Kodoo After Authentication", launch_response.text)

        self.assertEqual(disconnect_response.status_code, 200)
        self.assertIn("Disconnect QuickBooks From Kodoo", disconnect_response.text)
