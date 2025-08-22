# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo, new_test_user


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo):

    def test_01_mail_tour(self):
        self.start_tour("/odoo", 'discuss_channel_tour', login="admin")

    def test_02_mail_create_channel_no_mail_tour(self):
        self.env['res.users'].create({
            'email': '', # User should be able to create a channel even if no email is defined
            'group_ids': [Command.set([self.ref('base.group_user')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })
        self.start_tour("/odoo", 'discuss_channel_tour', login='testuser')

    # basic rendering test of the configuration menu in Discuss
    def test_03_mail_discuss_configuration_tour(self):
        self.start_tour("/odoo", "discuss_configuration_tour", login="admin")

    def test_04_meeting_view_tour(self):
        bob = new_test_user(self.env, "bob", groups="base.group_user", email="bob@test.com")
        john = new_test_user(self.env, "john", groups="base.group_user", email="john@test.com")
        group_chat = (
            self.env["discuss.channel"]
            .with_user(bob)
            ._create_group(
                partners_to=john.partner_id.ids, default_display_mode="video_full_screen"
            )
        )
        self.authenticate("bob", "bob")
        self.make_jsonrpc_request("/mail/rtc/channel/join_call", {"channel_id": group_chat.id})
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{group_chat.id}&fullscreen=1",
            "discuss.meeting_view_tour",
            login="john",
        )
        self.start_tour(group_chat.invitation_url, "discuss.meeting_view_public_tour", login="john")
