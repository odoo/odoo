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
