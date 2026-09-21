from __future__ import annotations

from odoo import http
from odoo.exceptions import AccessError, ValidationError
from odoo.http import BadRequest, Forbidden, Response, UnsupportedMediaType, request

from odoo.addons.mail.controllers.utils import get_self_member_or_404
from odoo.addons.mail.tools.discuss import add_guest_to_context
from odoo.addons.speech.tools.engines import SPOKEN_MIMETYPES

MAX_SEGMENT_MS = 4 * 60 * 60 * 1000


def _self_rtc_session(channel_id: int):
    member = get_self_member_or_404(channel_id)
    rtc_session = member.sudo().rtc_session_ids[:1]
    if not rtc_session:
        raise Forbidden
    return member.sudo().channel_id, rtc_session


class CallRecordingController(http.Controller):
    @http.route(
        "/discuss/call/recording/start",
        methods=["POST"],
        type="jsonrpc",
        auth="public",
    )
    @add_guest_to_context
    def start_recording(self, channel_id: int) -> dict:
        channel_sudo, rtc_session = _self_rtc_session(channel_id)
        if not channel_sudo._start_call_recording(rtc_session):
            return {"error": "already_being_recorded"}
        return {"recording": True}

    @http.route(
        "/discuss/call/recording/stop",
        methods=["POST"],
        type="jsonrpc",
        auth="public",
    )
    @add_guest_to_context
    def stop_recording(self, channel_id: int) -> dict:
        member_sudo = get_self_member_or_404(channel_id).sudo()
        if rtc_session := member_sudo.rtc_session_ids[:1]:
            member_sudo.channel_id._stop_call_recording(rtc_session)
        return {"recording": False}

    @http.route(
        "/discuss/call/upload_recording",
        methods=["POST"],
        type="http",
        auth="public",
        csrf=True,
    )
    @add_guest_to_context
    def upload_recording(
        self,
        channel_id: int,
        ufile: object,
        start_ms: str = "0",
        end_ms: str = "0",
        **_kwargs: object,
    ) -> Response:
        channel_sudo, rtc_session = _self_rtc_session(channel_id)
        if not ufile:
            raise BadRequest
        mimetype = (getattr(ufile, "content_type", "") or "").split(";")[0].strip()
        if mimetype not in SPOKEN_MIMETYPES:
            raise UnsupportedMediaType
        try:
            start, end = int(start_ms), int(end_ms)
        except (TypeError, ValueError) as error:
            raise BadRequest from error
        if not 0 <= start < end <= MAX_SEGMENT_MS:
            raise BadRequest

        attachment_sudo = (
            request.env["ir.attachment"]
            .sudo()
            ._create_from_request_file(file=ufile, mimetype=mimetype)
        )
        try:
            segment = channel_sudo._record_call_media(
                rtc_session, attachment_sudo, start, end
            )
        except AccessError:
            attachment_sudo.unlink()
            return request.prepare_json_response({"error": "not_recording"}, status=409)
        except ValidationError:
            attachment_sudo.unlink()
            return request.prepare_json_response(
                {"error": "already_being_recorded"}, status=409
            )
        attachment_sudo.write({"res_model": "media.segment", "res_id": segment.id})
        if attachment_sudo.can_transcribe:
            attachment_sudo._transcribe_later()
        return request.prepare_json_response(
            {"segment_id": segment.id, "attachment_id": attachment_sudo.id}
        )
