# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDiscussMentionSuggestions(HttpCase):
    def test_mention_suggestions_group_restricted_channel(self):
        user_admin = self.env.ref("base.user_admin")
        user_group = self.env.ref("base.group_user")
        rd_group = self.env["res.groups"].create({"name": "R&D Group"})
        new_test_user(self.env, login="dev", name="Dev User", group_ids=[user_group.id, rd_group.id])
        # have a user that is not channel member and not in group -> should not be suggested as mention
        new_test_user(self.env, login="sales", name="Sales User", groups="base.group_user")
        consultant_user = new_test_user(self.env, login="consultant", name="Consultant User", groups="base.group_user")
        rd_channel = self.env['discuss.channel'].with_user(user_admin).create({
            "name": "R&D Channel",
            "channel_type": "channel",
            "group_public_id": rd_group.id,
            "channel_member_ids": [
                Command.create({"partner_id": consultant_user.partner_id.id}),
                Command.create({"partner_id": user_admin.partner_id.id}),
            ],
        })
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{rd_channel.id}",
            "discuss_mention_suggestions_group_restricted_channel.js",
            login="admin",
        )
