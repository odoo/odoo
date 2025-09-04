from odoo import models, fields, api


class BankAccountAllocationLineWizard(models.TransientModel):
    _name = 'hr.bank.account.allocation.wizard.line'
    _description = 'Bank Account Allocation Line (Wizard)'
    _order = "sequence, id"

    wizard_id = fields.Many2one('hr.bank.account.allocation.wizard', required=True, ondelete="cascade")
    bank_account_id = fields.Many2one('res.partner.bank', required=True, readonly=True)

    acc_number = fields.Char(related='bank_account_id.acc_number', readonly=True)
    amount = fields.Float(string="Amount", readonly=False, digits=(16, 2))
    amount_type = fields.Selection(selection='_get_amount_type_selection_vals', readonly=False)
    symbol = fields.Char(compute="_compute_symbol", readonly=True)
    trusted = fields.Boolean(string="Trusted")
    sequence = fields.Integer(default=10)

    @api.depends('amount_type', 'bank_account_id.symbol')
    def _compute_symbol(self):
        for line in self:
            if line.amount_type == 'fixed':
                line.symbol = line.bank_account_id.currency_id.symbol \
                    or line.wizard_id.employee_id.company_id.currency_id.symbol
            else:
                line.symbol = '%'

    def _get_amount_type_selection_vals(self):
        return [('percentage', 'Percentage'), ('fixed', 'Fixed')]
