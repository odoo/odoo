from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class UniversityTranscriptRequestOverrideWizard(models.TransientModel):
    _name = "university.transcript.request.override.wizard"
    _description = "Admin Override Transcript Request Wizard"

    request_id = fields.Many2one(
        "university.transcript.request",
        string="Transcript Request",
        required=True,
    )
    reason = fields.Text(
        string="Reason",
        required=True,
        help="Specify the administrative reason for overriding the active hold(s). Minimum 10 characters.",
    )

    @api.constrains("reason")
    def _check_reason_length(self):
        for rec in self:
            if not rec.reason or len(rec.reason.strip()) < 10:
                raise ValidationError(_("The override reason must be at least 10 characters long."))

    def action_confirm_override(self):
        self.ensure_one()
        if not self.reason or len(self.reason.strip()) < 10:
            raise ValidationError(_("The override reason must be at least 10 characters long."))
        return self.request_id.action_confirm_override(self.reason.strip())
