from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        help="The employee who made the cash move.",
    )
