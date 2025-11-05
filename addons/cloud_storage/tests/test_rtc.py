# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC

from odoo import fields
from odoo.tests.common import TransactionCase

from odoo.addons.cloud_storage.controllers.rtc import CloudStorageRtcController


class TestCloudStorageRtc(TransactionCase):
    def test_recording_artifact_creation(self):
        partner = self.env["res.partner"].create({
            "name": "Recording Starter",
            "email": "starter@example.com",
        })
        channel = self.env["discuss.channel"].create({
            "name": "Recorded Call",
            "channel_type": "channel",
        })
        call_start = fields.Datetime.now()
        call_history = self.env["discuss.call.history"].create({
            "channel_id": channel.id,
            "start_dt": call_start,
        })
        call_start_ms = int(call_start.replace(tzinfo=UTC).timestamp() * 1000)
        broadcast_call_ids = []
        emailed_artifact_ids = []

        def _generate_cloud_storage_url(attachment):
            return f"https://storage.example.com/{attachment.id}"

        def _generate_cloud_storage_upload_info(attachment):
            return {
                "url": attachment.url,
                "method": "PUT",
                "response_status": 201,
            }

        def _broadcast_recording_availability(histories):
            broadcast_call_ids.extend(histories.ids)

        def _send_recording_available_email(artifacts):
            emailed_artifact_ids.extend(artifacts.ids)

        self.patch(
            self.env.registry["ir.attachment"],
            "_generate_cloud_storage_url",
            _generate_cloud_storage_url,
        )
        self.patch(
            self.env.registry["ir.attachment"],
            "_generate_cloud_storage_upload_info",
            _generate_cloud_storage_upload_info,
        )
        self.patch(
            self.env.registry["discuss.call.history"],
            "_broadcast_recording_availability",
            _broadcast_recording_availability,
        )
        self.patch(
            self.env.registry["mail.call.artifact"],
            "_send_recording_available_email",
            _send_recording_available_email,
        )
        self.env["ir.config_parameter"].sudo().set_str("cloud_storage_provider", "dummy")

        upload_info = CloudStorageRtcController()._get_recording_destination(
            call_history,
            call_start_ms + 1_000,
            call_start_ms + 3_000,
            "audio/ogg",
            partner_id=partner.id,
        )

        call_history.invalidate_recordset(["artifact_ids"])
        artifact = call_history.artifact_ids
        self.assertEqual(len(artifact), 1)
        self.assertEqual(artifact.recording_started_by_id, partner)
        self.assertEqual((artifact.start_ms, artifact.end_ms), (1_000, 3_000))
        self.assertEqual(artifact.media_id.mimetype, "audio/ogg")
        self.assertEqual(broadcast_call_ids, call_history.ids)
        self.assertEqual(emailed_artifact_ids, artifact.ids)
        self.assertEqual(
            upload_info,
            {
                "destination": artifact.media_id.url,
                "method": "PUT",
                "headers": None,
                "response_status": 201,
            },
        )

        CloudStorageRtcController()._get_recording_destination(
            call_history,
            call_start_ms + 4_000,
            call_start_ms + 6_000,
            "audio/ogg",
            partner_id=self.env["res.partner"].search([], order="id desc", limit=1).id + 1_000,
        )
        call_history.invalidate_recordset(["artifact_ids"])
        self.assertFalse(call_history.artifact_ids.sorted("start_ms")[-1].recording_started_by_id)
