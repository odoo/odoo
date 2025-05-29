from odoo.tests import tagged
from odoo.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsiteForumTechnicalPage(TestWebsiteTechnicalPage):

    def test_load_website_forum_technical_pages(self):
        self._validate_routes(["/forum"])
