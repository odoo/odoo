# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPortalDiscuss(HttpCaseWithUserPortal):
    def test_portal_discuss_navigation(self):
        """Portal navigation uses the home fallback or a valid originating portal page."""
        admin = self.env.ref("base.user_admin")
        channel = self.env["discuss.channel"].with_user(admin)._get_or_create_chat(self.partner_portal.ids)
        channel.with_user(admin).message_post(body="Hello")

        self.authenticate("portal", "portal")
        response = self.url_open(f"/my/conversations/{channel.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'portalDiscussNavigationUrl', response.content)
        self.assertIn(b'/my/home', response.content)

        response = self.url_open(
            "/my/conversations",
            headers={"Referer": f"{self.base_url()}/my/orders/42?view=details"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'portalDiscussHasOrigin', response.content)
        self.assertIn(b'/my/orders/42?view=details', response.content)

    def test_portal_discuss_navigation_is_not_shown_to_guests(self):
        self.env["ir.config_parameter"].set_bool("mail.chat_from_token", True)
        self.authenticate(None, None)
        response = self.url_open("/chat/portal-discuss-navigation-guest")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'portalDiscussNavigationUrl', response.content)
