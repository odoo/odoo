from odoo.tests import tagged
from odoo.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsiteSaleTechnicalPage(TestWebsiteTechnicalPage):

    def test_load_website_sale_technical_pages(cls):
        expected_routes = [
            "/shop",
            "/shop/confirmation",
            "/shop/extra_info",
            "/shop/payment",
            "/shop/checkout"
        ]
        for route in expected_routes:
            cls.assertIn(route, cls.created_routes, f"Route '{route}' is missing from technical page records.")
