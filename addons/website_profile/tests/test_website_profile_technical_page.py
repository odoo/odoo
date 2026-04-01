from odoo.tests import tagged
from odoo.addons.website.tests.test_website_technical_page import TestWebsiteTechnicalPage


@tagged("post_install", "-at_install")
class TestWebsiteProfileTechnicalPage(TestWebsiteTechnicalPage):

    def test_load_website_profile_technical_pages(self):
        self._validate_routes(["/profile/users", "/profile/ranks_badges"])
