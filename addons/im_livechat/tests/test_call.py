# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import new_test_user, tagged, HttpCase, JsonRpcException


@tagged("post_install", "-at_install")
class TestCall(HttpCase):
    def test_visitor_cannot_start_call(self):
        self.authenticate(None, None)
        operator = self.env["res.users"].create({"name": "Operator", "login": "operator"})
        self.env["mail.presence"]._update_presence(operator)
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [operator.id]}
        )
        for pseudo_user in [
            new_test_user(self.env, "portal_user", groups="base.group_portal"),
            self.env["mail.guest"].create({"name": "Guest"}),
        ]:
            user = pseudo_user if pseudo_user._name == "res.users" else self.env["res.users"]
            guest = pseudo_user if pseudo_user._name == "mail.guest" else self.env["mail.guest"]
            if user:
                self.authenticate(user.login, user.login)
            else:
                self.authenticate(None, None)
            if guest:
                self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
            data = self.make_jsonrpc_request(
                "/im_livechat/get_session",
                {
                    "anonymous_name": "Visitor",
                    "channel_id": livechat_channel.id,
                    "persisted": True,
                },
            )
            with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
                self.make_jsonrpc_request(
                    "/mail/rtc/channel/join_call",
                    {"channel_id": data["channel_id"]},
                )
