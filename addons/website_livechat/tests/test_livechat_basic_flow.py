# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo import fields, tests, _
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.website_livechat.tests.common import TestLivechatCommon
from odoo.tests.common import new_test_user


@tests.tagged('post_install', '-at_install')
class TestLivechatBasicFlowHttpCase(HttpCaseWithUserDemo, TestLivechatCommon):
    def test_channel_created_on_user_interaction(self):
        self.start_tour('/', 'im_livechat_request_chat', login=None)
        channel = self.env["discuss.channel"].search(
            [["livechat_end_dt", "=", False], ["livechat_visitor_id", "=", self.visitor.id]]
        )
        self.assertFalse(channel, 'Channel should not be created until user sends a message')
        self.start_tour('/', 'im_livechat_request_chat_and_send_message', login=None)
        channel = self.env["discuss.channel"].search(
            [["livechat_end_dt", "=", False], ["livechat_visitor_id", "=", self.visitor.id]]
        )
        self.assertTrue(channel, 'Channel should be created after sending the first message')

    def test_visitor_banner_history(self):
        # create visitor history
        self.env['website.track'].create([{
            'page_id': self.env.ref('website.homepage_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime,
        }, {
            'page_id': self.env.ref('website.contactus_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime - datetime.timedelta(minutes=10),
        }, {
            'page_id': self.env.ref('website.homepage_page').id,
            'visitor_id': self.visitor.id,
            'visit_datetime': self.base_datetime - datetime.timedelta(minutes=20),
        }])

        handmade_history = [
            (
                self.env.ref("website.homepage_page").name,
                (self.base_datetime - datetime.timedelta(minutes=20)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
            (
                self.env.ref("website.contactus_page").name,
                (self.base_datetime - datetime.timedelta(minutes=10)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            ),
            (
                self.env.ref("website.homepage_page").name,
                self.base_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        ]

        history = self.visitor._get_visitor_history()

        self.assertEqual(history, handmade_history)

    def test_livechat_username(self):
        # Open a new live chat
        res = self.url_open(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)
        channel_1 = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "=", self.visitor.id), ("livechat_end_dt", "=", False)],
            limit=1,
        )

        # Check Channel naming
        self.assertEqual(channel_1.name, "%s %s" % (f'Visitor #{channel_1.livechat_visitor_id.id}', self.operator.livechat_username))
        channel_1.unlink()

        # Remove livechat_username
        self.operator.livechat_username = False

        # This fixes an issue in the controller, possibly related to the testing
        # environment.  The business code unexpectedly uses two cache objects
        # (env.cache), which triggers cache misses: a field is computed with its
        # value stored into one cache and retrieved from another cache :-/
        self.operator.name

        # Open a new live chat
        res = self.url_open(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)
        channel_2 = self.env['discuss.channel'].search([('livechat_visitor_id', '=', self.visitor.id), ('livechat_end_dt', '=', False)], limit=1)

        # Check Channel naming
        self.assertEqual(channel_2.name, "%s %s" % (f'Visitor #{channel_2.livechat_visitor_id.id}', self.operator.name))

    def test_basic_flow_with_rating(self):
        channel = self._common_basic_flow()

        self._send_rating(channel, self.visitor, 5, "This deboulonnage was fine but not topitop.")

        channel._close_livechat_session()

        self.assertEqual(len(channel.message_ids), 4)
        self.assertEqual(channel.message_ids[0].author_id, self.env.ref('base.partner_root'), "Odoobot must be the sender of the 'left the conversation' message.")
        self.assertIn(f"Visitor #{channel.livechat_visitor_id.id}", channel.message_ids[0].body)
        self.assertTrue(channel.livechat_end_dt, "The livechat session must be inactive as the visitor sent his feedback.")

    def test_basic_flow_without_rating(self):
        channel = self._common_basic_flow()

        # left the conversation
        channel._close_livechat_session()
        self.assertEqual(len(channel.message_ids), 3)
        self.assertEqual(channel.message_ids[0].author_id, self.env.ref('base.partner_root'), "Odoobot must be the author the message.")
        self.assertIn(f"Visitor #{channel.livechat_visitor_id.id}", channel.message_ids[0].body)
        self.assertTrue(channel.livechat_end_dt, "The livechat session must be inactive since visitor left the conversation.")

    def test_visitor_info_access_rights(self):
        channel = self._common_basic_flow()
        self.authenticate(self.operator.login, 'ideboulonate')

        # Retrieve channels information, visitor info should be there
        init_messaging = self.make_jsonrpc_request(
            f"{self.livechat_base_url}/mail/data", {"fetch_params": ["channels_as_member"]}
        )
        livechat_info = next(c for c in init_messaging["discuss.channel"] if c["id"] == channel.id)
        self.assertIn("livechat_visitor_id", livechat_info)

        # Remove access to visitors and try again, visitors info shouldn't be included
        self.operator.group_ids -= self.group_livechat_user
        init_messaging = self.make_jsonrpc_request(
            f"{self.livechat_base_url}/mail/data", {"fetch_params": ["channels_as_member"]}
        )
        livechat_info = next(c for c in init_messaging["discuss.channel"] if c["id"] == channel.id)
        self.assertNotIn("livechat_visitor_id", livechat_info)

    def _common_basic_flow(self):
        # Open a new live chat
        res = self.url_open(url=self.open_chat_url, json=self.open_chat_params)
        self.assertEqual(res.status_code, 200)

        channel = self.env["discuss.channel"].search(
            [("livechat_visitor_id", "=", self.visitor.id), ("livechat_end_dt", "=", False)],
            limit=1,
        )

        # Check Channel and Visitor naming
        self.assertEqual(self.visitor.display_name, "%s #%s" % (_("Website Visitor"), self.visitor.id))
        self.assertEqual(channel.name, "%s %s" % (f'Visitor #{channel.livechat_visitor_id.id}', self.operator.livechat_username))

        # Post Message from visitor
        self._send_message(channel, self.visitor.display_name, "Message from Visitor")

        self.assertEqual(len(channel.message_ids), 1)
        self.assertEqual(channel.message_ids[0].author_id.id, False, "The author of the message is not a partner.")
        self.assertEqual(channel.message_ids[0].email_from, self.visitor.display_name, "The sender's email should be the visitor's email.")
        self.assertEqual(channel.message_ids[0].body, "<p>Message from Visitor</p>")
        self.assertFalse(channel.livechat_end_dt, "The livechat session must be active as the visitor did not left the conversation yet.")

        # Post message from operator
        self._send_message(channel, self.operator.email, "Message from Operator", author_id=self.operator.partner_id.id)

        self.assertEqual(len(channel.message_ids), 2)
        self.assertEqual(channel.message_ids[0].author_id, self.operator.partner_id, "The author of the message should be the operator.")
        self.assertEqual(channel.message_ids[0].email_from, self.operator.email, "The sender's email should be the operator's email.")
        self.assertEqual(channel.message_ids[0].body, "<p>Message from Operator</p>")
        self.assertFalse(
            channel.livechat_end_dt,
            "The livechat session must be active as the visitor did not left the conversation yet.",
        )

        return channel

    def test_livechat_as_portal_user(self):
        new_test_user(self.env, login="portal_user", groups="base.group_portal")
        self.start_tour("/my", "website_livechat_as_portal_tour", login="portal_user")

    def test_user_known_after_reload(self):
        self.start_tour('/', 'website_livechat_user_known_after_reload')

    def test_no_new_session_with_hide_button_rule(self):
        self.livechat_channel.rule_ids = self.env["im_livechat.channel.rule"].create(
            [
                {
                    "channel_id": self.livechat_channel.id,
                    "regex_url": "/livechat_url",
                    "sequence": 1,
                },
                {
                    "channel_id": self.livechat_channel.id,
                    "action": "hide_button",
                    "regex_url": "/",
                    "sequence": 2,
                },
            ]
        )
        self.start_tour("/livechat_url", "website_livechat_no_session_with_hide_rule")

    def test_channel_visitor_data(self):
        self.maxDiff = None
        channel = self._common_basic_flow()
        self._reset_bus()
        guest = self.env["mail.guest"].search([], order="id desc", limit=1)
        operator_member = channel.channel_member_ids.filtered(lambda m: m.partner_id == self.operator.partner_id)
        guest_member = channel.channel_member_ids.filtered(lambda m: m.guest_id == guest)
        self.assertEqual(
            Store().add(channel).get_result(),
            {
                "discuss.channel": self._filter_channels_fields(
                    {
                        "ai_agent_id": False,
                        "channel_type": "livechat",
                        "country_id": False,
                        "create_uid": self.user_public.id,
                        "default_display_mode": False,
                        "description": False,
                        "fetchChannelInfoState": "fetched",
                        "id": channel.id,
                        "invited_member_ids": [("ADD", [])],
                        "is_editable": True,
                        "last_interest_dt": fields.Datetime.to_string(channel.last_interest_dt),
                        "livechat_channel_id": self.livechat_channel.id,
                        "livechat_conversation_tag_ids": [],
                        "livechat_end_dt": False,
                        "livechat_lang_id": False,
                        "livechat_note": False,
                        "livechat_status": "in_progress",
                        "livechat_outcome": "no_failure",
                        "livechat_expertise_ids": [],
                        "livechat_operator_id": self.operator.partner_id.id,
                        "livechat_visitor_id": self.visitor.id,
                        "member_count": 2,
                        "message_needaction_counter": 0,
                        "message_needaction_counter_bus_id": 0,
                        "name": f"Visitor #{self.visitor.id} El Deboulonnator",
                        "requested_by_operator": False,
                        "rtc_session_ids": [("ADD", [])],
                        "uuid": channel.uuid,
                    }
                ),
                "discuss.channel.member": [
                    {
                        "create_date": fields.Datetime.to_string(operator_member.create_date),
                        "fetched_message_id": False,
                        "id": operator_member.id,
                        "livechat_member_type": "agent",
                        "last_seen_dt": False,
                        "partner_id": self.operator.partner_id.id,
                        "seen_message_id": False,
                        "channel_id": {"id": channel.id, "model": "discuss.channel"},
                    },
                    {
                        "create_date": fields.Datetime.to_string(guest_member.create_date),
                        "fetched_message_id": False,
                        "id": guest_member.id,
                        "livechat_member_type": "visitor",
                        "last_seen_dt": False,
                        "guest_id": guest.id,
                        "seen_message_id": False,
                        "channel_id": {"id": channel.id, "model": "discuss.channel"},
                    },
                ],
                "im_livechat.channel": [
                    {"id": self.livechat_channel.id, "name": "The basic channel"}
                ],
                "mail.guest": [
                    {
                        "avatar_128_access_token": guest._get_avatar_128_access_token(),
                        "country_id": False,
                        "id": guest.id,
                        "im_status": "offline",
                        "im_status_access_token": guest._get_im_status_access_token(),
                        "name": f"Visitor #{self.visitor.id}",
                        "offline_since": False,
                        "write_date": fields.Datetime.to_string(guest.write_date),
                    }
                ],
                "res.country": [
                    {"code": "BE", "id": self.env["ir.model.data"]._xmlid_to_res_id("base.be")}
                ],
                "res.lang": [{"id": self.env.ref("base.lang_en").id, "name": "English (US)"}],
                "res.partner": self._filter_partners_fields(
                    {
                        "active": True,
                        "avatar_128_access_token": self.operator.partner_id._get_avatar_128_access_token(),
                        "country_id": False,
                        "id": self.operator.partner_id.id,
                        "im_status": "online",
                        "im_status_access_token": self.operator.partner_id._get_im_status_access_token(),
                        "is_public": False,
                        "mention_token": self.operator.partner_id._get_mention_token(),
                        "user_livechat_username": "El Deboulonnator",
                        "write_date": fields.Datetime.to_string(
                            self.operator.partner_id.write_date
                        ),
                    }
                ),
                "website": [
                    {"id": self.env.ref("website.default_website").id, "name": "My Website"}
                ],
                "website.visitor": [
                    {
                        "country_id": self.env["ir.model.data"]._xmlid_to_res_id("base.be"),
                        "display_name": f"Website Visitor #{self.visitor.id}",
                        "page_visit_history": [],
                        "id": self.visitor.id,
                        "lang_id": self.env.ref("base.lang_en").id,
                        "partner_id": False,
                        "website_id": self.env.ref("website.default_website").id,
                    }
                ],
            },
        )

    def test_channel_to_store_after_operator_left(self):
        channel = self._common_basic_flow()
        guest = self.env["mail.guest"].search([], order="id desc", limit=1)
        guest_member = channel.channel_member_ids.filtered(lambda m: m.guest_id == guest)
        agent_left_dt = fields.Datetime.now()
        with freeze_time(agent_left_dt):
            channel.with_user(self.operator).action_unfollow()
        self._reset_bus()
        self.assertFalse(
            channel.channel_member_ids.filtered(lambda m: m.partner_id == self.operator.partner_id)
        )
        data = Store().add(
                channel.with_user(self.user_public).with_context(guest=guest),
            ).get_result()
        self.assertEqual(
            data["discuss.channel"],
            self._filter_channels_fields(
                {
                    "ai_agent_id": False,
                    "channel_type": "livechat",
                    "country_id": False,
                    "create_uid": self.user_public.id,
                    "default_display_mode": False,
                    "fetchChannelInfoState": "fetched",
                    "id": channel.id,
                    "invited_member_ids": [("ADD", [])],
                    "is_editable": False,
                    "last_interest_dt": fields.Datetime.to_string(channel.last_interest_dt),
                    "livechat_end_dt": fields.Datetime.to_string(agent_left_dt),
                    "livechat_lang_id": False,
                    "livechat_operator_id": self.operator.partner_id.id,
                    "member_count": 1,
                    "message_needaction_counter": 0,
                    "message_needaction_counter_bus_id": 0,
                    "name": f"Visitor #{self.visitor.id} El Deboulonnator",
                    "requested_by_operator": False,
                    "rtc_session_ids": [("ADD", [])],
                    "uuid": channel.uuid,
                },
            )
        )
        self.assertEqual(
            data["discuss.channel.member"],
            [
                {
                    "channel_id": {"id": channel.id, "model": "discuss.channel"},
                    "create_date": fields.Datetime.to_string(guest_member.create_date),
                    "custom_channel_name": False,
                    "custom_notifications": False,
                    "fetched_message_id": False,
                    "guest_id": guest.id,
                    "id": guest_member.id,
                    "last_interest_dt": fields.Datetime.to_string(guest_member.last_interest_dt),
                    "last_seen_dt": False,
                    "livechat_member_type": "visitor",
                    "message_unread_counter": 2,
                    "message_unread_counter_bus_id": self.env["bus.bus"].sudo()._bus_last_id(),
                    "mute_until_dt": False,
                    "new_message_separator": 0,
                    "rtc_inviting_session_id": False,
                    "seen_message_id": False,
                    "unpin_dt": False,
                }
            ],
        )

    def test_livechat_not_available_with_hide_button_rule(self):
        self.env["im_livechat.channel.rule"].create([
            {
                "channel_id": self.livechat_channel.id,
                "regex_url": "/show",
                "action": "display_button",
            },
            {
                "channel_id": self.livechat_channel.id,
                "action": "hide_button",
                "regex_url": "/hide",
            },
        ])
        result = self.make_jsonrpc_request(
            "/mail/action",
            {"fetch_params": [["init_livechat", self.livechat_channel.id]]},
            headers={"Referer": "/show"},
        )
        self.assertEqual(result["Store"]["livechat_available"], True)
        result = self.make_jsonrpc_request(
            "/mail/action",
            {"fetch_params": [["init_livechat", self.livechat_channel.id]]},
            headers={"Referer": "/hide"},
        )
        self.assertEqual(result["Store"]["livechat_available"], False)

    def test_livechat_visitor_to_store(self):
        """Test livechat_visitor_id is sent with livechat channels data even when there is no
        visitor."""
        self.target_visitor = None
        channel_data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
        )
        channel_info = next(
            c
            for c in channel_data["store_data"]["discuss.channel"]
            if c["id"] == channel_data["channel_id"]
        )
        self.assertEqual(channel_info["livechat_visitor_id"], False)


@tests.tagged('post_install', '-at_install')
class TestLivechatBasicFlowHttpCaseMobile(HttpCaseWithUserDemo, TestLivechatCommon):
    browser_size = '375x667'
    touch_enabled = True

    def test_mobile_user_interaction(self):
        self.start_tour('/', 'im_livechat_request_chat_and_send_message', login=None)
