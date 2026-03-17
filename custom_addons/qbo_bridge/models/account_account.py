from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    qbo_bridge_rule_id = fields.Many2one(
        "qbo.account.bridge.rule",
        string="QBO bridge rule",
        copy=False,
        ondelete="set null",
    )
    qbo_source_name = fields.Char(
        string="QBO source name",
        copy=False,
    )
    qbo_source_account_number = fields.Char(
        string="QBO source account number",
        copy=False,
    )
    qbo_source_account_type = fields.Char(
        string="QBO source account type",
        copy=False,
    )
    qbo_source_account_subtype = fields.Char(
        string="QBO source detail type",
        copy=False,
    )
