from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWebsiteTechnicalPage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.TechnicalPage = cls.env["website.technical.page"]
        cls.TechnicalPage.load_technical_pages()
        cls.created_routes = cls.TechnicalPage.search([]).mapped("website_url")

    def test_load_website_technical_pages(cls):
        expected_routes = [
            "/my",
            "/my/home",
            "/web/signup",
            "/web/login",
            "/web/reset_password",
            "/website/info",
        ]
        for route in expected_routes:
            cls.assertIn(route, cls.created_routes, f"Route '{route}' is missing from technical page records.")
