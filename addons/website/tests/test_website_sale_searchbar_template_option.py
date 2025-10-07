from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleSearchbarTemplateOptions(HttpCase):
    def test_website_searchbar_template_option(self):
        self.start_tour(
            self.env["website"].get_client_action_url("/"),
            "website_searchbar_template_option",
            login="admin",
        )
