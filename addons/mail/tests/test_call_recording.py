# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo import fields
from odoo.tools import format_datetime

from odoo.addons.mail.tests.common import MailCommon


class TestCallRecording(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"].create(
            {
                "name": "Recorded call",
                "channel_type": "group",
            },
        )

    def _create_call(self):
        return self.env["discuss.call.history"].create(
            {
                "channel_id": self.channel.id,
                "start_dt": fields.Datetime.now(),
            },
        )

    def _create_artifact(self, call=None, *, started_by=None, mimetype=None):
        call = call or self._create_call()
        artifact = self.env["mail.call.artifact"].create(
            {
                "discuss_call_history_id": call.id,
                "recording_started_by_id": started_by.id if started_by else False,
                "start_ms": 0,
                "end_ms": 1_000,
            },
        )
        if mimetype:
            self.env["ir.attachment"].create(
                {
                    "name": "recording.webm",
                    "res_model": artifact._name,
                    "res_id": artifact.id,
                    "mimetype": mimetype,
                    "raw": b"recording",
                },
            )
            artifact.invalidate_recordset(["media_id"])
        return artifact

    def test_display_name_distinguishes_calls(self):
        call = self._create_call().with_context(lang="en_US", tz="UTC")
        call.start_dt = "2026-09-09 09:00:00"
        first_name = call.display_name
        self.assertEqual(
            first_name,
            f"{self.channel.display_name} - {format_datetime(call.env, call.start_dt, tz='UTC')}",
        )
        self.assertNotEqual(
            first_name,
            call.with_context(tz="Europe/Brussels").display_name,
        )
        call.start_dt = "2026-09-09 10:00:00"
        self.assertNotEqual(first_name, call.display_name)
        self.channel.name = "Renamed channel"
        self.assertTrue(call.display_name.startswith("Renamed channel - "))

    def test_recording_available_emails_use_starter_company(self):
        first_artifact = self._create_artifact(
            started_by=self.user_employee_c2,
            mimetype="video/webm",
        )
        second_artifact = self._create_artifact(
            started_by=self.user_employee_c3,
            mimetype="audio/webm",
        )
        artifacts = first_artifact | second_artifact
        self.company_3.email = False
        with self.mock_mail_gateway():
            artifacts.with_user(self.user_public).sudo().with_context(
                allowed_company_ids=[],
            )._send_recording_available_email()
        self.assertEqual(len(self._new_mails), 2)
        for artifact in artifacts:
            starter = artifact.recording_started_by_id
            mail = self.assertMailMailWRecord(artifact, starter.partner_id, "outgoing")
            self.assertEqual(
                mail.email_from,
                starter.company_id.email_formatted or starter.email_formatted,
            )
            body = html.fromstring(mail.body_html)
            self.assertIn(starter.company_id.name, body.xpath("//b/text()"))
            recording_link = body.xpath('//a[normalize-space(text())="View recording"]')
            self.assertEqual(len(recording_link), 1)
            self.assertEqual(
                recording_link[0].get("href"),
                f"{artifact.get_base_url()}/odoo/discuss.call.history/{artifact.discuss_call_history_id.id}",
            )

    def test_recording_email_requires_starter_and_media(self):
        without_starter = self._create_artifact(mimetype="audio/webm")
        without_media = self._create_artifact(started_by=self.user_employee)
        with self.mock_mail_gateway():
            (without_starter | without_media)._send_recording_available_email()
        self.assertFalse(self._new_mails)
        self.assertFalse(without_media.discuss_call_history_id.has_recording)

    def test_non_media_artifact_is_not_a_recording(self):
        artifact = self._create_artifact(mimetype="text/plain")
        self.assertFalse(artifact.discuss_call_history_id.has_recording)
        self.assertFalse(artifact.discuss_call_history_id.has_audio)
        self.assertFalse(artifact.discuss_call_history_id.has_video)

    def test_active_recording_action(self):
        self.assertIsNone(self.channel._get_recording_address())
        first_call = self._create_call()
        self.assertEqual(
            self.channel._get_recording_address(),
            f"{self.channel.get_base_url()}/mail/rtc/recording/{first_call.id}",
        )
        recordings_domain = [
            ("channel_id", "=", self.channel.id),
            ("artifact_ids", "any", [("recording_upload_pending", "=", False)]),
        ]
        self.assertFalse(first_call.end_dt)
        self.assertFalse(first_call.has_recording)
        action = self.channel.action_view_recordings()
        self.assertEqual(action["domain"], recordings_domain)
        self.assertFalse(action["res_id"])
        self.assertEqual(action["view_mode"], "list,form")
        self._create_artifact(first_call, mimetype="video/webm")
        self.assertTrue(first_call.has_recording)
        self.assertFalse(first_call.has_audio)
        self.assertTrue(first_call.has_video)
        action = self.channel.action_view_recordings()
        self.assertEqual(action["domain"], recordings_domain)
        self.assertEqual(action["res_id"], first_call.id)
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual([view_type for _, view_type in action["views"]], ["form"])
        second_call = self._create_call()
        self._create_artifact(second_call, mimetype="audio/webm")
        self.assertTrue(second_call.has_audio)
        self.assertTrue(second_call.has_recording)
        action = self.channel.action_view_recordings()
        self.assertFalse(action["res_id"])
        self.assertEqual(action["domain"], recordings_domain)
        self.assertEqual(action["view_mode"], "list,form")

    def test_upload_pending_recording_is_not_available(self):
        artifact = self._create_artifact(
            started_by=self.user_employee,
            mimetype="video/webm",
        )
        artifact.recording_upload_pending = True
        self.assertFalse(artifact._is_recording_available())
        self.assertFalse(artifact.discuss_call_history_id.has_recording)
        self.assertFalse(artifact.discuss_call_history_id.has_video)
        action = self.channel.action_view_recordings()
        self.assertFalse(action["res_id"])
        self.assertEqual(action["view_mode"], "list,form")
        self.assertFalse(self.env["discuss.call.history"].search(action["domain"]))
        with self.mock_mail_gateway():
            artifact._send_recording_available_email()
        self.assertFalse(self._new_mails)
