# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import HttpCase, tagged, users


@tagged("discuss_messaging_menu")
class TestDiscussMessagingMenu(MailCommon, HttpCase):

    @users("employee")
    def test_messaging_menu_initialize_counters_channel(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        group = self.env["discuss.channel"].with_user(self.user_admin)._create_group(
            users_to=self.env.user,
        )
        group.message_post(body="Hey", message_type="comment")
        data = self.make_jsonrpc_request(
            "/mail/store",
            {"fetch_params": [[
                "/mail/messaging_menu/initialize_counters",
                {"filter_id_by_tab_id_by_record_type": {
                    "discuss.channel": {"chat": "chat_unread"},
                }},
            ]]},
        )
        counter_ids_by_tab = {
            tab["id"]: tab["init_counter_ids"] for tab in data["MessagingMenuTab"]
        }
        self.assertEqual(counter_ids_by_tab["chat"], group.ids)

    @users("employee")
    def test_messaging_menu_channel_tab(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        Channel = self.env["discuss.channel"].with_user(self.user_admin)
        pinned, needaction, other = Channel.create(
            [{"name": name, "channel_type": "channel"} for name in ("pinned", "needaction", "other")],
        )
        pinned._add_members(users=self.env.user)
        pinned.message_post(body="Hey", message_type="comment")
        self.env["mail.message"].sudo().create({
            "model": "discuss.channel",
            "res_id": needaction.id,
            "body": "Hey",
            "message_type": "comment",
            "notification_ids": [
                (0, 0, {"res_partner_id": self.env.user.partner_id.id, "notification_type": "inbox"}),
            ],
        })
        fetch_params = [
            ["/mail/messaging_menu/discuss.channel/load_more", {"tab_id": "channel", "limit": 30}],
            [
                "/mail/messaging_menu/initialize_counters",
                {"filter_id_by_tab_id_by_record_type": {"discuss.channel": {"channel": None}}},
            ],
        ]
        tab_channels = pinned | needaction
        data = self.make_jsonrpc_request("/mail/store", {"fetch_params": fetch_params})
        # only the channels of this test: the employee is also in the general channel
        test_ids = set((tab_channels | other).ids)
        loaded_ids = {channel["id"] for channel in data["discuss.channel"]}
        self.assertEqual(loaded_ids & test_ids, set(tab_channels.ids))
        counter_ids_by_tab = {
            tab["id"]: tab["init_counter_ids"] for tab in data["MessagingMenuTab"]
        }
        self.assertEqual(set(counter_ids_by_tab["channel"]) & test_ids, set(tab_channels.ids))
