from unittest.mock import patch

from odoo.addons.website.models.website_technical_page import WebsiteTechnicalPage
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

    def test_load_website_escaping_title(self):
        patched_route = [
            ("H'\\e\"l/l\\'\\\"o", "/w'\\o\"r/l\\'\\\"d"),
        ]
        with patch.object(WebsiteTechnicalPage, 'get_static_routes', return_value=patched_route):
            page = self.env["website.technical.page"].search([])
            self.assertEqual(page.name, patched_route[0][0])
            self.assertEqual(page.website_url, patched_route[0][1])
