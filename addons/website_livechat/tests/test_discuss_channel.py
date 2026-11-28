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
        other_guest = self.env["mail.guest"].create({"name": "Other Guest"})
        no_visitor_channel = self.env["discuss.channel"].create({
            "name": "Other Conversation",
            "channel_type": "livechat",
            "livechat_channel_member_history_ids": [
                Command.create({"guest_id": other_guest.id, "livechat_member_type": "visitor"}),
            ],
        })
        data = Store().add(source | no_visitor_channel, "_store_livechat_extra_fields")._build_result()
        stored_channels = {channel["id"]: channel for channel in data["discuss.channel"]}
        self.assertEqual(stored_channels[source.id]["recent_channel_ids"], (guest_channel | visitor_channel).ids)
        self.assertFalse(stored_channels[source.id]["has_more_recent_channels"])
        # Without a website visitor, sessions are not matched on their absence of visitor.
        self.assertFalse(stored_channels[no_visitor_channel.id]["recent_channel_ids"])
        self.assertFalse(stored_channels[no_visitor_channel.id]["has_more_recent_channels"])
