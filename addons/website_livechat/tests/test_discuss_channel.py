# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.mail.tools.discuss import Store
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


class TestDiscussChannel(TestLivechatCommon):
    def test_store_recent_channels_match_livechat_visitor(self):
        source = self.env["discuss.channel"].create({
            "name": "Source Conversation",
            "channel_type": "livechat",
            "livechat_visitor_id": self.visitor.id,
            "livechat_channel_member_history_ids": [
                Command.create({"guest_id": self.guest.id, "livechat_member_type": "visitor"}),
            ],
        })
        visitor_channel = self.env["discuss.channel"].create({
            "name": "Visitor Conversation",
            "channel_type": "livechat",
            "livechat_visitor_id": self.visitor.id,
        })
        guest_channel = self.env["discuss.channel"].create({
            "name": "Guest Conversation",
            "channel_type": "livechat",
            "livechat_channel_member_history_ids": [
                Command.create({"guest_id": self.guest.id, "livechat_member_type": "visitor"}),
            ],
        })
        data = Store().add(source, "_store_livechat_extra_fields")._build_result()
        stored_channels = {channel["id"]: channel for channel in data["discuss.channel"]}
        self.assertEqual(stored_channels[source.id]["recent_channel_ids"], (guest_channel | visitor_channel).ids)
        self.assertEqual(stored_channels[source.id]["recent_channels_count"], 2)
