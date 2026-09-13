from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    pos_session_id = fields.Many2one(
        comodel_name="pos.session",
        string="Session",
        index="btree_not_null",
        copy=False,
    )
