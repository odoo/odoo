from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCase


@tagged("-at_install", "post_install")
class TestStoreReset(HttpCase):
    def test_store_reset_in_discuss(self):
        channel = self.env["discuss.channel"].create({"name": "MyChannel"})
        channel._add_members(users=self.env.ref("base.user_admin"))
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{channel.id}",
            "discuss.store_reset_in_discuss",
            login="admin",
        )

    def test_store_reset_with_chat_windows(self):
        channel = self.env["discuss.channel"].create({"name": "MyChannel"})
        channel._add_members(users=self.env.ref("base.user_admin"))
        self.start_tour("/odoo/apps", "discuss.store_reset_with_chat_windows", login="admin")

    def test_store_reset_in_public_page(self):
        channel = self.env["discuss.channel"].create({"name": "MyChannel"})
        channel._add_members(users=self.env.ref("base.user_admin"))
        self.start_tour(channel.invitation_url, "discuss.store_reset_in_discuss", login="admin")

    def test_store_reset_in_public_page_as_guest(self):
        channel = self.env["discuss.channel"].create({"name": "MyChannel", "group_public_id": None})
        guest = self.env["mail.guest"].create({"name": "Guest"})
        channel._add_members(guests=guest)
        self.start_tour(
            channel.invitation_url,
            "discuss.store_reset_in_discuss",
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )
