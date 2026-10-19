# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestPortalDiscuss(HttpCaseWithUserPortal):
    def test_portal_user_can_open_chat_with_internal_user(self):
        """A portal user should be able to open a chat they share with an internal user
        from My Account > Discuss without hitting an access error."""
        admin = self.env.ref("base.user_admin")
        channel = self.env["discuss.channel"].with_user(admin)._get_or_create_chat(self.partner_portal.ids)
        channel.with_user(admin).message_post(body="Hello")

        self.authenticate("portal", "portal")
        response = self.url_open(f"/my/conversations/{channel.id}")
        self.assertEqual(response.status_code, 200)
