# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.discuss.rtc import RtcController


class CloudStorageRtcController(RtcController):
    def _get_recording_destination(
        self,
        call_history,
        start_ms,
        end_ms,
        mimetype="application/octet-stream",
        partner_id=None,
    ):
        super()._get_recording_destination(
            call_history,
            start_ms,
            end_ms,
            mimetype,
            partner_id,
        )
        start_ms, end_ms = self._get_recording_offsets(call_history, start_ms, end_ms)
        recording_started_by = call_history.env["res.partner"].browse(
            partner_id
        ).exists()
        artifact = call_history.env["mail.call.artifact"].create({
            "discuss_call_history_id": call_history.id,
            "recording_started_by_id": recording_started_by.id,
            "start_ms": start_ms,
            "end_ms": end_ms,
        })
        attachment = call_history.env["ir.attachment"].create({
            "name": f"media_{call_history.id}",
            "res_model": "mail.call.artifact",
            "res_id": artifact.id,
            "mimetype": mimetype,
        })
        attachment._post_add_create(cloud_storage=True)
        artifact.invalidate_recordset(["media_id"])
        call_history._broadcast_recording_availability()
        artifact._send_recording_available_email()
        upload_info = attachment._generate_cloud_storage_upload_info()
        return {
            "destination": upload_info["url"],
            "method": upload_info["method"],
            "headers": upload_info.get("headers"),
            "response_status": upload_info["response_status"],
        }
