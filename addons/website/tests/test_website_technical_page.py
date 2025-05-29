from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteTechnicalPage(TransactionCase):

    def _validate_routes(self, expected_routes):
        TechnicalPage = self.env["website.technical.page"]
        TechnicalPage.get_static_routes()
        routes = TechnicalPage.search([('website_url', 'in', expected_routes)]).mapped("website_url")

        for route in expected_routes:
            self.assertIn(route, routes, f"Route '{route}' is missing from technical page records.")

    def test_load_website_technical_pages(self):
        self._validate_routes([
            "/my/home",
            "/web/signup",
            "/web/login",
            "/web/reset_password",
            "/website/info",
        ])
