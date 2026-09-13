from odoo import fields, models


class HrApplicantRefuseReason(models.Model):
    _name = "hr.applicant.refuse.reason"
    _description = "Refuse Reason of Applicant"
    _order = "sequence"

    sequence = fields.Integer(
        default=10,
        copy=False,
    )
    name = fields.Char(
        string="Description",
        translate=True,
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain="[('model', '=', 'hr.applicant')]",
    )
    active = fields.Boolean(default=True)
