from odoo import api, fields, models


class BankAccountAllocationLineWizard(models.TransientModel):
    _name = "hr.bank.account.allocation.wizard.line"
    _description = "Bank Account Allocation Line (Wizard)"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="hr.bank.account.allocation.wizard",
        required=True,
        ondelete="cascade",
    )
    bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        readonly=True,
        required=True,
    )

    acc_number = fields.Char(
        related="bank_account_id.acc_number",
        readonly=True,
    )
    amount = fields.Float(
        digits=(16, 2),
        readonly=False,
    )
    amount_type = fields.Selection(
        selection="_selection_amount_type",
        readonly=False,
    )
    symbol = fields.Char(
        compute="_compute_symbol",
        readonly=True,
    )
    trusted = fields.Boolean()
    sequence = fields.Integer(default=10)

    @api.depends("amount_type", "bank_account_id.symbol")
    def _compute_symbol(self):
        for line in self:
            if line.amount_type == "fixed":
                line.symbol = (
                    line.bank_account_id.currency_id.symbol
                    or line.wizard_id.employee_id.company_id.currency_id.symbol
                )
            else:
                line.symbol = "%"

    def _selection_amount_type(self):
        return [("percentage", "Percentage"), ("fixed", "Fixed")]
