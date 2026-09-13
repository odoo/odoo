from odoo import fields, models

STATUS_SELECTION = [
    ("todo", "To Review"),
    ("reviewed", "Reviewed"),
    ("supervised", "Supervised"),
    ("anomaly", "Anomaly"),
]


class AccountAuditAccountStatus(models.Model):
    _name = "account.audit.account.status"
    _description = "Account Audit Account Status"

    audit_id = fields.Many2one(
        comodel_name="account.return",
        required=True,
        ondelete="cascade",
        index="btree",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        required=True,
        ondelete="cascade",
        index="btree",
    )
    status = fields.Selection(
        selection=STATUS_SELECTION,
    )
