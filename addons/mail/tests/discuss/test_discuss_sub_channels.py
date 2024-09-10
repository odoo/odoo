# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.exceptions import ValidationError


@tagged("post_install", "-at_install")
class TestDiscussSubChannels(HttpCase):
    def test_01_gc_unpin_outdated_sub_channels(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        now_dt = datetime.now().replace(microsecond=0)
        with freeze_time(now_dt):
            parent.create_sub_channel()
            recent_sub_channel = parent.sub_channel_ids[0]
            recent_sub_channel.add_members(partner_ids=[self.env.user.partner_id.id])
            recent_sub_channel.channel_pin(pinned=True)
        three_days_ago_dt = (datetime.now() - timedelta(days=3)).replace(microsecond=0)
        with freeze_time(three_days_ago_dt):
            parent.create_sub_channel()
            old_sub_channel = parent.sub_channel_ids[1]
            old_sub_channel.add_members(partner_ids=[self.env.user.partner_id.id])
            old_sub_channel.channel_pin(pinned=True)
        recent_sub_self_member = self.env["discuss.channel.member"].search(
            [("channel_id", "=", recent_sub_channel.id), ("is_self", "=", True)]
        )
        self.assertEqual(recent_sub_self_member.last_interest_dt, now_dt)
        old_sub_self_member = self.env["discuss.channel.member"].search(
            [("channel_id", "=", old_sub_channel.id), ("is_self", "=", True)]
        )
        self.assertEqual(old_sub_self_member.last_interest_dt, three_days_ago_dt)
        self.env["discuss.channel.member"]._gc_unpin_outdated_sub_channels()
        # Last interest of the member is smaller than 2 day: should be kept as
        # is.
        self.assertTrue(recent_sub_self_member.is_pinned)
        # Last interest of the member is bigger than 2 day: should be unpinned.
        self.assertFalse(old_sub_self_member.is_pinned)

    def test_02_group_public_id_sync_with_sub_channels(self):
        parent = self.env["discuss.channel"].create(
            {"name": "General", "group_public_id": self.env.ref("base.group_system").id}
        )
        parent.create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        self.assertEqual(sub_channel.group_public_id, self.env.ref("base.group_system"))
        parent.group_public_id = self.env.ref("base.group_user")
        self.assertEqual(sub_channel.group_public_id, self.env.ref("base.group_user"))

    def test_03_sub_channel_members_sync_with_parent(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent.action_unfollow()
        self.assertFalse(any(m.is_self for m in parent.channel_member_ids))
        parent.create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        # Member created for sub channel (create_sub_channel): should also be
        # created for the parent channel.
        self.assertTrue(any(m.is_self for m in parent.channel_member_ids))
        self.assertTrue(any(m.is_self for m in sub_channel.channel_member_ids))
        # Member removed from parent channel: should also be removed from the sub
        # channel.
        parent.action_unfollow()
        self.assertFalse(any(m.is_self for m in parent.channel_member_ids))
        self.assertFalse(any(m.is_self for m in sub_channel.channel_member_ids))
        # Member created for sub channel (add_members): should also be created
        # for parent.
        sub_channel.add_members(partner_ids=[self.env.user.partner_id.id])
        self.assertTrue(any(m.is_self for m in parent.channel_member_ids))
        self.assertTrue(any(m.is_self for m in sub_channel.channel_member_ids))

    def test_04_cannot_create_recursive_sub_channel(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent.create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        with self.assertRaises(ValidationError):
            sub_channel.create_sub_channel()

    def test_05_sub_channel_panel_search(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        self.authenticate("bob_user", "bob_user")
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.add_members(partner_ids=[bob_user.partner_id.id])
        for i in range(100):
            channel.create_sub_channel(name=f"Sub Channel {i}")
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{channel.id}",
            "test_discuss_sub_channel_search",
            login="bob_user",
        )

    def test_06_sub_channel_creation(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        self.authenticate("bob_user", "bob_user")
        channel = self.env["discuss.channel"].channel_create(name="General", group_id=None)
        channel.add_members(partner_ids=[bob_user.partner_id.id])
        self.make_jsonrpc_request(
            "/mail/message/post",
            {
                "post_data": {
                    "body": "Thanks! Could you please remind me where is Christine's office, if I may ask? I'm new here!",
                    "message_type": "comment",
                },
                "thread_id": channel.id,
                "thread_model": "discuss.channel",
            },
        )
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{channel.id}",
            "test_discuss_sub_channel_creation",
            login="bob_user",
        )
