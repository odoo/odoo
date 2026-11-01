from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_doubtful_debt_expense_account_id = fields.Many2one(
        related="company_id.od19_doubtful_debt_expense_account_id",
        readonly=False,
    )
    od19_doubtful_debt_allowance_account_id = fields.Many2one(
        related="company_id.od19_doubtful_debt_allowance_account_id",
        readonly=False,
    )
    od19_doubtful_debt_journal_id = fields.Many2one(
        related="company_id.od19_doubtful_debt_journal_id",
        readonly=False,
    )
