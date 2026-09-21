from odoo import fields, models


class AccountReportAnnotation(models.Model):
    _name = "account.report.annotation"
    _description = "Account Report Annotation"

    # This field is a OneToOne to a mail.message.
    message_id = fields.Many2one(
        comodel_name="mail.message",
        required=True,
    )
    date = fields.Date(
        required=True,
        help="Date considered as annotated by the annotation.",
    )
