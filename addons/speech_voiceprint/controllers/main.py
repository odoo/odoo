import base64

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from ..models.speech_voiceprint import MAX_ENROLL_BYTES


class VoiceprintController(http.Controller):
    def _employee(self):
        employee = request.env.user.employee_id
        if not employee:
            raise UserError(request.env._("Your user is not linked to an employee."))
        return employee

    def _print(self, employee):
        return (
            request.env["speech.voiceprint"]
            .sudo()
            .with_context(active_test=False)
            .search([("employee_id", "=", employee.id)], limit=1)
        )

    @http.route("/speech/voiceprint/status", type="jsonrpc", auth="user")
    def status(self):
        employee = self._employee()
        print_ = self._print(employee)
        return {
            "employee": employee.name,
            "enrolled": bool(print_),
            "active": bool(print_ and print_.active),
            "enrolled_at": (print_.enrolled_at and print_.enrolled_at.isoformat())
            or False,
            "sample_seconds": print_.sample_seconds or 0.0,
            "available": request.env["speech.voiceprint"]._embedder() is not None,
            "phrase": request.env["speech.voiceprint"]._enrolment_phrase(),
        }

    @http.route("/speech/voiceprint/enroll", type="jsonrpc", auth="user")
    def enroll(self, audio, consent=False):
        if not consent:
            raise UserError(request.env._("Consent is required to store a voiceprint."))
        employee = self._employee()
        if len(audio or "") > MAX_ENROLL_BYTES * 4 // 3 + 4:
            raise UserError(request.env._("The recording is too large."))
        try:
            audio_bytes = base64.b64decode(audio or "", validate=True)
        except (TypeError, ValueError) as error:
            raise UserError(
                request.env._("The recording is not valid base64.")
            ) from error
        print_ = request.env["speech.voiceprint"]._enroll(employee, audio_bytes)
        return {"ok": True, "sample_seconds": print_.sample_seconds}

    @http.route("/speech/voiceprint/revoke", type="jsonrpc", auth="user")
    def revoke(self):
        print_ = self._print(self._employee())
        if print_ and not print_.active:
            raise UserError(
                request.env._(
                    "Your voiceprint was deactivated; ask before deleting or "
                    "re-recording it."
                )
            )
        print_.unlink()
        return {"ok": True}
