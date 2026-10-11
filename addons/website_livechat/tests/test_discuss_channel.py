# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from freezegun import freeze_time

from odoo import Command, fields

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


class TestDiscussChannel(TestLivechatCommon):
    @freeze_time("2026-07-06 06:07:00")
    def test_store_recent_channels(self):
        now = fields.Datetime.now()
        (
            ongoing_older_interest,
            ongoing_same_interest_older_id,
            ongoing_same_interest_newer_id,
            closed_newer_interest,
            closed_older_interest,
            partner_source,
        ) = self.env["discuss.channel"].create([
            {
                "name": "Partner Conversation",
                "channel_type": "livechat",
                "last_interest_dt": last_interest_dt,
                "livechat_end_dt": livechat_end_dt,
                "livechat_channel_member_history_ids": [
                    Command.create({"livechat_member_type": "visitor", "partner_id": self.partner_employee.id}),
                ],
            }
            for last_interest_dt, livechat_end_dt in [
                (now - timedelta(hours=2), False),
                (now - timedelta(hours=1), False),
                (now - timedelta(hours=1), False),
                (now, now),
                (now - timedelta(hours=3), now),
                (now, False),
            ]
        ])
        guest_channels = self.env["discuss.channel"].create([
            {
                "name": f"Guest Conversation {index}",
                "channel_type": "livechat",
                "livechat_channel_member_history_ids": [
                    Command.create({"guest_id": self.guest.id, "livechat_member_type": "visitor"}),
                ],
            }
            for index in range(5)
        ])
        guest_source = self.env["discuss.channel"].create({
            "name": "Guest Source",
            "channel_type": "livechat",
            "livechat_channel_member_history_ids": [
                Command.create({"guest_id": self.guest.id, "livechat_member_type": "visitor"}),
            ],
            "livechat_visitor_id": self.visitor.id,
        })
        website_visitor_recent = self.env["discuss.channel"].create({
            "name": "Website Visitor Recent",
            "channel_type": "livechat",
            "livechat_visitor_id": self.visitor.id,
        })
        sources = partner_source | guest_source
        data = Store().add(sources, "_store_livechat_extra_fields")._build_result()
        stored_channels = {channel["id"]: channel for channel in data["discuss.channel"]}
        self.assertEqual(
            stored_channels[partner_source.id]["recent_channel_ids"],
            [
                ongoing_same_interest_newer_id.id,
                ongoing_same_interest_older_id.id,
                ongoing_older_interest.id,
                closed_newer_interest.id,
                closed_older_interest.id,
            ],
        )
        self.assertEqual(stored_channels[partner_source.id]["recent_channels_count"], 5)
        self.assertCountEqual(
            stored_channels[guest_source.id]["recent_channel_ids"],
            (guest_channels[-4:] | website_visitor_recent).ids,
        )
        self.assertEqual(stored_channels[guest_source.id]["recent_channels_count"], 6)
