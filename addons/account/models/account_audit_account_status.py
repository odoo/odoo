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
        index="btree",
        required=True,
        ondelete="cascade",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        index="btree",
        required=True,
        ondelete="cascade",
    )
    status = fields.Selection(selection=STATUS_SELECTION)
