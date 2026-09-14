from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    pos_session_id = fields.Many2one(
        comodel_name="pos.session",
        string="Session",
        index="btree_not_null",
        copy=False,
    )
    pos_cash_move_type = fields.Selection(
        selection=[
            ("manual", "Cash In/Out"),
            ("payment", "POS Payment Settlement"),
            ("difference", "Cash Counting Difference"),
        ],
        string="POS Cash Movement Type",
        copy=False,
        help="Distinguishes cash movements from accounting entries created at closing.",
    )
