# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests.common import tagged, HttpCase
from odoo.tools import mute_logger, file_open


@tagged("post_install", "-at_install")
class TestUploadAttachment(HttpCase):
    def test_visitor_cannot_upload_on_closed_livechat(self):
        self.authenticate(None, None)
        operator = self.env["res.users"].create({"name": "Operator", "login": "operator"})
        self.env["mail.presence"]._update_presence(operator)
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Livechat Channel", "user_ids": [operator.id]}
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": livechat_channel.id,
                "persisted": True,
            },
        )
        self.make_jsonrpc_request(
            "/im_livechat/visitor_leave_session", {"channel_id": data["channel_id"]}
        )
        with mute_logger("odoo.http"), file_open("addons/web/__init__.py") as file:
            response = self.url_open(
                "/mail/attachment/upload",
                {
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": data["channel_id"],
                    "thread_model": "discuss.channel",
                },
                files={"ufile": file},
            )
            self.assertEqual(response.status_code, 403)
