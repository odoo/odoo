from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tagged("post_install", "-at_install")
class TestDonationSnippets(HttpCaseWithUserPortal):
    def test_01_donation(self):
        self.start_tour(
            self.env["website"].get_client_action_url("/", True),
            "donation_snippet_edition",
            login="admin",
        )
        self.start_tour("/", "donation_snippet_use")
        self.start_tour(
            self.env["website"].get_client_action_url("/", True),
            "donation_snippet_edition_2",
            login="admin",
        )
        self.start_tour("/", "donation_snippet_use_2")

    def test_02_donation_on_cart_page(self):
        self.start_tour(
            self.env["website"].get_client_action_url("/shop/cart", True),
            "donation_snippet_edition_cart",
            login="admin",
        )
        self.start_tour("/shop/cart", "donation_snippet_use_cart")
