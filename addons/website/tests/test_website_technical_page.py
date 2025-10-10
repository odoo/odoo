from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteTechnicalPage(TransactionCase):

    def _validate_routes(self, expected_routes):
        TechnicalPage = self.env["website.technical.page"]
        routes = TechnicalPage.search([]).mapped("website_url")
        filtered_routes = [url for url in routes if url in expected_routes]
        self.assertEqual(sorted(filtered_routes), sorted(expected_routes), "Some routes are missing from technical page records")

    def test_load_website_technical_pages(self):
        self._validate_routes([
            "/my/home",
            "/web/signup",
            "/web/login",
            "/web/reset_password",
            "/website/info",
        ])
