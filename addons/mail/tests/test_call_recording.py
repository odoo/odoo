# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.mail.tests.common import MailCommon


@tagged("call_recordings")
class TestCallRecording(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create({
            "name": "Recorded call",
            "channel_type": "group",
        })

    def _create_call(self):
        return self.env["discuss.call.history"].create({
            "channel_id": self.channel.id,
            "start_dt": fields.Datetime.now(),
        })

    def _create_artifact(self, call=None, *, started_by=None, mimetype=None):
        call = call or self._create_call()
        artifact = self.env["mail.call.artifact"].create({
            "discuss_call_history_id": call.id,
            "recording_started_by_id": started_by.id if started_by else False,
            "start_ms": 0,
            "end_ms": 1_000,
        })
        if mimetype:
            self.env["ir.attachment"].create({
                "name": "recording.webm",
                "res_model": artifact._name,
                "res_id": artifact.id,
                "mimetype": mimetype,
                "raw": b"recording",
            })
            artifact.invalidate_recordset(["media_id"])
        return artifact

    def test_recording_available_email(self):
        artifact = self._create_artifact(
            started_by=self.partner_employee,
            mimetype="video/webm",
        )

        with self.mock_mail_gateway():
            artifact._send_recording_available_email()

        mail = self.assertMailMailWRecord(
            artifact,
            self.partner_employee,
            "outgoing",
        )
        recording_link = html.fromstring(mail.body_html).xpath(
            '//a[normalize-space(text())="View recording"]'
        )
        self.assertEqual(len(recording_link), 1)
        self.assertEqual(
            recording_link[0].get("href"),
            f"{artifact.get_base_url()}/odoo/discuss.call.history/{artifact.discuss_call_history_id.id}",
        )

    def test_recording_email_requires_starter_and_media(self):
        without_starter = self._create_artifact(mimetype="audio/webm")
        without_media = self._create_artifact(started_by=self.partner_employee)

        with self.mock_mail_gateway():
            (without_starter | without_media)._send_recording_available_email()

        self.assertFalse(self._new_mails)

    def test_active_recording_count_and_action(self):
        first_call = self._create_call()
        recordings_domain = [
            ("channel_id", "=", self.channel.id),
            ("artifact_ids", "!=", False),
        ]
        self.assertFalse(first_call.end_dt)
        self.assertEqual(self.channel.recording_count, 0)
        self.assertFalse(self.channel.action_view_recordings())

        self._create_artifact(first_call, mimetype="video/webm")
        self.channel.invalidate_recordset(["recording_count"])

        self.assertTrue(first_call.has_recording)
        self.assertFalse(first_call.has_audio)
        self.assertTrue(first_call.has_video)
        self.assertEqual(self.channel.recording_count, 1)
        action = self.channel.action_view_recordings()
        self.assertEqual(action["domain"], recordings_domain)
        self.assertEqual(action["res_id"], first_call.id)
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual([view_type for _, view_type in action["views"]], ["form"])

        second_call = self._create_call()
        self._create_artifact(second_call, mimetype="audio/webm")
        self.channel.invalidate_recordset(["recording_count"])

        self.assertTrue(second_call.has_audio)
        self.assertEqual(self.channel.recording_count, 2)
        action = self.channel.action_view_recordings()
        self.assertFalse(action["res_id"])
        self.assertEqual(action["domain"], recordings_domain)
        self.assertEqual(action["view_mode"], "list,form")
