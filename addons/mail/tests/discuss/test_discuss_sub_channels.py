# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestDiscussSubThread(HttpCase):
    def test_01_leave_sub_channel_on_channel_unlink(self):
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.create_sub_channel()
        self.assertEqual(len(channel.sub_channel_ids), 1)
        channel.unlink()
        self.assertEqual(len(channel.sub_channel_ids), 0)

    def test_02_leave_sub_channel_on_channel_leave(self):
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.add_members(partner_ids=[self.env.user.partner_id.id])
        self.assertTrue(channel.is_member)
        sub_channel = self.env["discuss.channel"].browse(channel.create_sub_channel()["id"])
        self.assertEqual(len(channel.sub_channel_ids), 1)
        sub_channel.add_members(partner_ids=[self.env.user.partner_id.id])
        self.assertTrue(sub_channel.is_member)
        channel.action_unfollow()
        self.assertFalse(channel.is_member)
        self.assertFalse(sub_channel.is_member)

    def test_03_sub_channel_group_public_id_synced_with_owner(self):
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        sub_channel = self.env["discuss.channel"].browse(channel.create_sub_channel()["id"])
        self.assertEqual(channel.group_public_id, self.env["res.groups"])
        self.assertEqual(channel.group_public_id, sub_channel.group_public_id)
        channel.group_public_id = self.env.ref("base.group_system")
        self.assertEqual(channel.group_public_id, self.env.ref("base.group_system"))
        self.assertEqual(channel.group_public_id, sub_channel.group_public_id)

    def test_04_sub_channel_panel_search(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        self.authenticate("bob_user", "bob_user")
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.add_members(partner_ids=[bob_user.partner_id.id])
        for i in range(100):
            sub_channel = self.env["discuss.channel"].browse(channel.create_sub_channel()["id"])
            sub_channel.channel_rename(name="Sub Channel %s" % i)
        self.start_tour(f"/odoo/discuss?active_id=discuss.channel_{channel.id}", "test_discuss_sub_channel_search", login="bob_user", watch=True)

    def test_05_sub_channel_creation(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        self.authenticate("bob_user", "bob_user")
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.add_members(partner_ids=[bob_user.partner_id.id])
        self.make_jsonrpc_request("/mail/message/post", {
            "post_data": {
                "body": "Thanks! Could you please remind me where is Christine's office, if I may ask? I'm new here!",
                "message_type": "comment",
            },
            "thread_id": channel.id,
            "thread_model": "discuss.channel",
        })
        self.start_tour(f"/odoo/discuss?active_id=discuss.channel_{channel.id}", "test_discuss_sub_channel_creation", login="bob_user")

    def test_06_sub_channel_notification(self):
        pass
