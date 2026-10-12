from odoo.tests import tagged
from odoo.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsiteEventTechnicalPage(TestWebsiteTechnicalPage):

    def test_load_website_event_technical_pages(self):
        self._validate_routes(["/events"])
