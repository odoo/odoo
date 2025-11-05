from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.addons.mail.tools.discuss import get_derived_sfu_key
from odoo.addons.mail.tools import jwt


# TODO will fail until merge of PR #233836
@tagged("mail_controller")
class TestDiscussController(HttpCase):
    def test_sfu_uploading_call_media_happy_path(self):
        channel = self.env["discuss.channel"].create({"name": "Test Channel"})
        call_history = self.env["discuss.call.history"].create({
            "channel_id": channel.id,
            "start_dt": fields.Datetime.now(),
        })
        derived_key = get_derived_sfu_key(self.env, channel.id)
        token = jwt.sign({"iss": "sfu"}, derived_key, ttl=3600, algorithm=jwt.Algorithm.HS256)
        file_content = b"fake_video_data"

        response = self.url_open(
            f"/mail/rtc/recording/{call_history.id}/upload?main_media=True",
            data=file_content,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "video/webm;codecs=opus"},
        )
        self.assertEqual(response.status_code, 200)
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", "discuss.call.history"),
            ("res_id", "=", call_history.id),
            ("mimetype", "=", "video/webm;codecs=opus"),
        ])
        self.assertTrue(attachment)
        self.assertEqual(attachment.raw, file_content)
        call_history.invalidate_recordset()
        self.assertEqual(call_history.media, attachment)

    def test_sfu_uploading_call_media_invalid_jwt(self):
        channel = self.env["discuss.channel"].create({"name": "Test Channel"})
        call_history = self.env["discuss.call.history"].create({
            "channel_id": channel.id,
            "start_dt": fields.Datetime.now(),
        })
        file_content = b"fake_video_data"

        response = self.url_open(
            f"/mail/rtc/recording/{call_history.id}/upload?main_media=True",
            data=file_content,
            headers={"Authorization": "Bearer wrong-token", "Content-Type": "video/webm;codecs=opus"},
        )
        self.assertEqual(response.status_code, 404)
