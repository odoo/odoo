# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.exceptions import UserError, ValidationError


@tagged("post_install", "-at_install")
class TestDiscussSubChannels(HttpCase):
    def test_01_gc_unpin_outdated_sub_channels(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent._create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        sub_channel._add_members(users=self.env.user)
        sub_channel.channel_pin(pinned=True)
        self_member = sub_channel.channel_member_ids.filtered(lambda m: m.is_self)
        self.assertTrue(self_member.is_pinned)
        # Last interrest of the member is older than 2 days, no activity on the
        # channel: should be unpinned.
        two_days_later_dt = datetime.now() + timedelta(days=3)
        with freeze_time(two_days_later_dt):
            self.env["discuss.channel.member"]._gc_unpin_outdated_sub_channels()
            self.assertFalse(self_member.is_pinned)
        # Last interrest of the member is older than 2 days, activity on the
        # channel: should be kept.
        sub_channel.channel_pin(pinned=True)
        with freeze_time(two_days_later_dt):
            sub_channel.message_post(body="Hey!")
            self.env["discuss.channel.member"]._gc_unpin_outdated_sub_channels()
            self.assertTrue(self_member.is_pinned)

    def test_02_sub_channel_members_sync_with_parent(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent.action_unfollow()
        self.assertFalse(any(m.is_self for m in parent.channel_member_ids))
        parent._create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        # Member created for sub channel (_create_sub_channel): should also be
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
        sub_channel._add_members(users=self.env.user)
        self.assertTrue(any(m.is_self for m in parent.channel_member_ids))
        self.assertTrue(any(m.is_self for m in sub_channel.channel_member_ids))

    def test_03_cannot_create_recursive_sub_channel(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent._create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        with self.assertRaises(ValidationError):
            sub_channel._create_sub_channel()

    def test_04_sub_channel_panel_search(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        self.authenticate("bob_user", "bob_user")
        channel = self.env["discuss.channel"]._create_channel(name="General", group_id=None)
        channel._add_members(users=bob_user)
        for i in range(100):
            channel._create_sub_channel(name=f"Sub Channel {i}")
        self.start_tour(
            f"/odoo/discuss?active_id=discuss.channel_{channel.id}",
            "test_discuss_sub_channel_search",
            login="bob_user",
        )

    def test_05_cannot_upate_first_message_nor_parent_channel(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent.message_post(body="Hello there!")
        parent._create_sub_channel(from_message_id=parent.message_ids[0].id)
        sub_channel = parent.sub_channel_ids[0]
        random_channel = self.env["discuss.channel"].create({"name": "Random"})
        parent.message_post(body="Random message")
        with self.assertRaises(UserError, msg="Cannot change initial message nor parent channel of: Hello there!."):
            sub_channel.parent_channel_id = random_channel
        with self.assertRaises(UserError, msg="Cannot change initial message nor parent channel of: Hello there!."):
            sub_channel.from_message_id = parent.message_ids[0]

    def test_06_initial_message_must_belong_to_parent_channel(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        random_channel = self.env["discuss.channel"].create({"name": "Random"})
        random_channel.message_post(body="Hello world!")
        with self.assertRaises(
            ValidationError,
            msg="Cannot create Hello world!: initial message should belong to parent channel.",
        ):
            parent._create_sub_channel(from_message_id=random_channel.message_ids[0].id)

    def test_07_unlink_sub_channel(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        baz_user = new_test_user(self.env, "baz_user", groups="base.group_user")
        parent_1 = self.env["discuss.channel"].with_user(bob_user).create({"name": "Parent 1"})
        parent_1_baz_member = parent_1._add_members(users=baz_user)
        parent_1_sub_channel_1 = parent_1._create_sub_channel(name="Parent 1 Sub 1")
        parent_1_sub_channel_1._add_members(users=baz_user)
        parent_1_sub_channel_2 = parent_1._create_sub_channel(name="Parent 1 Sub 2")
        parent_1_sub_channel_2._add_members(users=baz_user)
        parent_2 = self.env["discuss.channel"].with_user(baz_user).create({"name": "Parent 2"})
        parent_2_bob_member = parent_2._add_members(users=bob_user)
        parent_2_sub_channel = parent_2._create_sub_channel(name="Parent 2 Sub")
        parent_2_sub_channel._add_members(users=bob_user)
        parent_3 = self.env["discuss.channel"].with_user(bob_user).create({"name": "Parent 3"})
        guest = self.env["mail.guest"].create({"name": "Guest"})
        parent_3_guest_member = parent_3._add_members(guests=guest)
        parent_3_sub_channel = parent_3._create_sub_channel(name="Parent 3 Sub")
        parent_3_sub_channel._add_members(guests=guest)
        members_to_unlink = parent_1_baz_member + parent_2_bob_member + parent_3_guest_member
        members_to_unlink.sudo().unlink()
        self.assertNotIn(
            baz_user.partner_id,
            parent_1.channel_member_ids.partner_id
            | parent_1.sub_channel_ids.channel_member_ids.partner_id,
        )
        self.assertNotIn(
            bob_user.partner_id,
            parent_2.channel_member_ids.partner_id
            | parent_2.sub_channel_ids.channel_member_ids.partner_id,
        )
        self.assertNotIn(
            guest,
            parent_3.channel_member_ids.guest_id
            | parent_3.sub_channel_ids.channel_member_ids.guest_id,
        )
        self.assertIn(bob_user.partner_id, parent_1_sub_channel_1.channel_member_ids.partner_id)
        self.assertIn(bob_user.partner_id, parent_1_sub_channel_2.channel_member_ids.partner_id)
        self.assertIn(baz_user.partner_id, parent_2_sub_channel.channel_member_ids.partner_id)
        self.assertIn(bob_user.partner_id, parent_3_sub_channel.channel_member_ids.partner_id)

    def test_08_group_public_id_synced_with_parent(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent._create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        self.assertEqual(parent.group_public_id, self.env.ref("base.group_user"))
        self.assertEqual(sub_channel.group_public_id, parent.group_public_id)
        parent.group_public_id = self.env.ref("base.group_system")
        self.assertEqual(parent.group_public_id, self.env.ref("base.group_system"))
        self.assertEqual(sub_channel.group_public_id, parent.group_public_id)
        parent.group_public_id = None
        self.assertEqual(parent.group_public_id, self.env["res.groups"])
        self.assertEqual(sub_channel.group_public_id, parent.group_public_id)

    def test_09_cannot_change_group_public_id_of_sub_channel(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        parent._create_sub_channel()
        sub_channel = parent.sub_channel_ids[0]
        with self.assertRaises(UserError):
            sub_channel.group_public_id = self.env.ref("base.group_system")

    def test_10_sub_channel_message_author_member(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        parent = self.env["discuss.channel"].create({
            "name": "General",
            "channel_member_ids": [Command.create({"partner_id": bob_user.partner_id.id})],
        })
        message = parent.with_user(bob_user).message_post(body="Hello there!")
        sub_channel = parent._create_sub_channel(from_message_id=message.id)
        self.assertIn(bob_user.partner_id, sub_channel.channel_member_ids.partner_id)
        self.assertEqual(len(sub_channel.channel_member_ids), 2)

    def test_11_sub_channel_fallback_name_on_empty_message(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        message = parent.message_post(body="Hello there!", message_type="comment")
        parent._message_update_content(message, body="")
        sub_channel = parent._create_sub_channel(from_message_id=message.id)
        self.assertEqual(sub_channel.name, "This message has been removed")

    def test_12_unlink_children_members_only_once(self):
        parent = self.env["discuss.channel"].create({"name": "General"})
        child = parent._create_sub_channel()

        og_unlink = self.env.registry["discuss.channel.member"].unlink
        unlinked_member_ids = []
        expected_unlinked_member_ids = sorted((parent.self_member_id | child.self_member_id).ids)

        def _patched_unlink(records):
            unlinked_member_ids.extend(records.ids)
            og_unlink(records)

        with patch.object(self.env.registry["discuss.channel.member"], "unlink", _patched_unlink):
            (parent | child).channel_member_ids.unlink()
        self.assertEqual(expected_unlinked_member_ids, sorted(unlinked_member_ids))
