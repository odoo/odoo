# Part of Odoo. See LICENSE file for full copyright and licensing details.

from requests.exceptions import HTTPError

from odoo import Command, http
from odoo.tests.common import tagged, HttpCase
from odoo.tools import file_open, mute_logger


@tagged("post_install", "-at_install")
class TestToggleUpload(HttpCase):
    def test_upload_allowed(self):
        self.authenticate(None, None)
        channel = self.env["discuss.channel"].create({"name": "General", "group_public_id": None})
        guest = self.env["mail.guest"].create({"name": "Guest"})
        channel.write({"channel_member_ids": [Command.create({"guest_id": guest.id})]})
        with file_open("addons/web/__init__.py") as file:
            response = self.url_open(
                "/mail/attachment/upload",
                {
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": channel.id,
                    "thread_model": "discuss.channel",
                },
                files={"ufile": file},
                cookies={guest._cookie_name: guest._format_auth_cookie()}
            )
        self.assertEqual(response.status_code, 200)
