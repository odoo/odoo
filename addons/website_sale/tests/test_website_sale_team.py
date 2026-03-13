from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class WebsiteSaleTeam(WebsiteSaleCommon):
    def test_website_sale_cart_confirmation_does_not_change_team(self):
        website_team = self.cart.team_id
        self.cart.action_confirm()
        self.assertEqual(self.cart.team_id, website_team)
