# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestSubChannels(MailCommon):
    def test_gc_sub_empty_channels(self):
        owner = self.env["discuss.channel"].create({"name": "General"})
        owner.create_sub_channel()
        owner.create_sub_channel()
        empty_sub_channel = owner.sub_channel_ids[0]
        non_empty_sub_channel = owner.sub_channel_ids[1]
        non_empty_sub_channel.message_post(body="Hello world!")
        one_day_later_dt = datetime.now() + timedelta(days=1)
        with freeze_time(one_day_later_dt):
            self.env["discuss.channel"]._gc_empty_sub_channels()
            # Containing some messages: should be kept.
            self.assertIn(non_empty_sub_channel, owner.sub_channel_ids)
            # Empty: should be garbage collected.
            self.assertNotIn(empty_sub_channel, owner.sub_channel_ids)

    def test_gc_unpin_outdated_sub_channels(self):
        owner = self.env["discuss.channel"].create({"name": "General"})
        now_dt = datetime.now().replace(microsecond=0)
        with freeze_time(now_dt):
            owner.create_sub_channel()
            recent_sub_channel = owner.sub_channel_ids[0]
            recent_sub_channel.add_members(partner_ids=[self.env.user.partner_id.id])
            recent_sub_channel.channel_pin(pinned=True)
        three_days_ago_dt = (datetime.now() - timedelta(days=3)).replace(microsecond=0)
        with freeze_time(three_days_ago_dt):
            owner.create_sub_channel()
            old_sub_channel = owner.sub_channel_ids[1]
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
