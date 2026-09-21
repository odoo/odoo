from __future__ import annotations

from odoo import http
from odoo.exceptions import UserError
from odoo.http import Response, request
from odoo.tools import replace_exceptions


class SpeechController(http.Controller):
    """Serve what a recording says, to whoever may already hear it.

    Access is delegated to `ir.binary._get_record`, the same resolver
    `/web/content` uses, so a caption track is readable exactly when the audio
    it captions is: the record rule, the access token and the public-content
    hook all answer once, for both, and a subtitle cannot become a way to read
    a recording one cannot fetch.
    """

    def _speech_attachment(self, attachment_id: int, access_token: str | None):
        with replace_exceptions(UserError, by=request.prepare_not_found_error()):
            return request.env["ir.binary"]._get_record(
                None, "ir.attachment", attachment_id, access_token, field_name="raw"
            )

    def _speech_text_response(self, body: str, mimetype: str) -> Response:
        if not body:
            raise request.prepare_not_found_error()
        return request.prepare_response(
            body.encode(),
            headers=[
                ("Content-Type", f"{mimetype}; charset=utf-8"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )

    @http.route(
        "/speech/attachment/<int:attachment_id>/subtitles.vtt",
        methods=["GET"],
        type="http",
        auth="public",
        readonly=True,
    )
    def subtitles(
        self, attachment_id: int, access_token: str | None = None
    ) -> Response:
        attachment = self._speech_attachment(attachment_id, access_token)
        return self._speech_text_response(
            attachment.sudo()._transcript_vtt(), "text/vtt"
        )

    @http.route(
        "/speech/attachment/<int:attachment_id>/transcript.txt",
        methods=["GET"],
        type="http",
        auth="public",
        readonly=True,
    )
    def transcript(
        self, attachment_id: int, access_token: str | None = None
    ) -> Response:
        attachment = self._speech_attachment(attachment_id, access_token)
        return self._speech_text_response(
            attachment.sudo().transcript_text, "text/plain"
        )
