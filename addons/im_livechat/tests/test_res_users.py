# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


class TestLiveChatResUsersSessionLogin(TestImLivechatCommon):
    def test_join_livechat_sessions_from_guest_keeps_chat_window_open(self):
        portal_user = new_test_user(
            self.env, login="portal_user", groups="base.group_portal",
        )
        guest = self.env["mail.guest"].create({"name": "Visitor"})
        channel_id = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": self.livechat_channel.id},
            cookies={guest._cookie_name: guest._format_auth_cookie()},
        )["channel_id"]
        channel = self.env["discuss.channel"].browse(channel_id)
        guest_member = channel.channel_member_ids.filtered(lambda m: m.guest_id == guest)
        with self.assertBus(
            [
                BusResult(channel),
                BusResult(portal_user, "discuss.channel/joined"),
                BusResult(channel),
                BusResult((channel, "internal_users")),
                BusResult(
                    channel,
                    "mail.record/insert",
                    {
                        "discuss.channel": [{"id": channel.id, "member_count": 2}],
                        "discuss.channel.member": [{"_DELETE": True, "id": guest_member.id}],
                    },
                ),
                BusResult(channel, "discuss.channel/new_message"),
            ],
        ):
            portal_user.with_context(guest=guest)._join_livechat_sessions_from_guest(guest)
        visitor_member = channel.channel_member_ids.filtered(
            lambda m: m.livechat_member_type == "visitor",
        )
        self.assertEqual(visitor_member.partner_id, portal_user.partner_id)


class TestLiveChatResUsers(TransactionCase):

    def test_livechat_create_res_users(self):
        access_user = new_test_user(
            self.env,
            login="admin_access",
            name="admin_access",
            groups="base.group_erp_manager,base.group_partner_manager",
        )
        access_user.with_user(access_user.id).create({
            "login": "test_can_be_created",
            "name": "test_can_be_created",
            "livechat_username": False,
            "livechat_lang_ids": [],
        })

    def test_livechat_expertise_ids_write_keeps_previous_tags(self):
        user = new_test_user(self.env, login="livechat_operator")
        expertise_1, expertise_2 = self.env["im_livechat.expertise"].create([
            {"name": "Expertise 1"},
            {"name": "Expertise 2"},
        ])

        user.with_user(user).write({"livechat_expertise_ids": [Command.link(expertise_1.id)]})
        self.env.invalidate_all()
        self.assertEqual(user.livechat_expertise_ids, expertise_1)

        user.with_user(user).write({"livechat_expertise_ids": [Command.link(expertise_2.id)]})
        self.env.invalidate_all()
        self.assertEqual(user.livechat_expertise_ids, expertise_1 + expertise_2)
