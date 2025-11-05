# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import BadRequest, NotFound

from odoo.http import Response, request, route

from odoo.addons.mail.controllers.discuss.rtc import RtcController, _check_jwt


class CloudStorageRtcController(RtcController):
    def _get_recording_destination(
        self,
        call_history,
        start_ms,
        end_ms,
        mimetype="application/octet-stream",
        user_id=None,
    ):
        """Allocate a recording upload or raise BadRequest for an unsupported media type."""
        if not mimetype.startswith(("audio/", "video/")):
            raise BadRequest()
        start_ms, end_ms = self._get_recording_offsets(call_history, start_ms, end_ms)
        recording_started_by = call_history.env["res.users"].browse(user_id).exists()
        artifact = call_history.env["mail.call.artifact"].create(
            {
                "discuss_call_history_id": call_history.id,
                "recording_started_by_id": recording_started_by.id,
                "recording_upload_pending": True,
                "start_ms": start_ms,
                "end_ms": end_ms,
            },
        )
        attachment = call_history.env["ir.attachment"].create(
            {
                "name": f"call_history_{call_history.id}_recording_{artifact.id}",
                "res_model": "mail.call.artifact",
                "res_id": artifact.id,
                "mimetype": mimetype,
            },
        )
        attachment._post_add_create(cloud_storage=True)
        # media_id is computed from attachments rather than an inverse relation.
        artifact.invalidate_recordset(["media_id"])
        artifact.modified(["media_id"])
        upload_info = attachment._generate_cloud_storage_upload_info()
        return {
            "destination": upload_info["url"],
            "method": upload_info["method"],
            "headers": upload_info.get("headers"),
            "response_status": upload_info["response_status"],
            "requires_completion": True,
        }

    @route(
        "/mail/rtc/recording/<int:call_history_id>/complete",
        type="http",
        auth="public",
        methods=["POST"],
        cors="*",
        csrf=False,
    )
    def complete_recording(self, call_history_id, start_ms, end_ms):
        """Publish an SFU-confirmed upload or raise NotFound for an unknown recording."""
        # sudo: discuss.call.history - the channel JWT authenticates the SFU callback below.
        call_history = self.env["discuss.call.history"].sudo().search(
            [("id", "=", call_history_id)],
        )
        _check_jwt(request, call_history.channel_id)
        start_ms, end_ms = self._get_recording_offsets(call_history, start_ms, end_ms)
        artifact = (
            call_history.env["mail.call.artifact"]
            .search(
                [
                    ("discuss_call_history_id", "=", call_history.id),
                    ("start_ms", "=", start_ms),
                    ("end_ms", "=", end_ms),
                ],
            )
            .filtered(
                lambda candidate: (
                    candidate.recording_upload_pending
                    or candidate._is_recording_media()
                ),
            )
        )
        if not artifact:
            raise NotFound()
        if artifact.recording_upload_pending:
            artifact.recording_upload_pending = False
            call_history._broadcast_recording_availability()
            artifact._send_recording_available_email()
        return Response(status=204)
