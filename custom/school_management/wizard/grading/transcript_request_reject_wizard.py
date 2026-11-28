from odoo import _, fields, models
from odoo.exceptions import UserError


class UniversityTranscriptRequestRejectWizard(models.TransientModel):
    _name = "university.transcript.request.reject.wizard"
    _description = "Reject Transcript Request Wizard"

    request_id = fields.Many2one(
        "university.transcript.request",
        string="Transcript Request",
        required=True,
    )
    reject_reason = fields.Text(
        string="Rejection Reason",
        required=True,
        help="Specify the academic, disciplinary, or administrative reason for rejecting this request.",
    )

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.reject_reason or not self.reject_reason.strip():
            raise UserError(_("A rejection reason is mandatory."))
        return self.request_id.action_reject(reason=self.reject_reason.strip())
