from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    balance_id = fields.Many2one('account.balance', string='Balance')

class AccountBalance(models.Model):
    _name = 'account.balance'
    _description = 'Account Balance'

    account_ids = fields.Many2many('account.account', string='Accounts')
    move_line_ids = fields.One2many('account.move.line', 'balance_id', string='Move Lines')
    balance = fields.Float(string='Balance', compute='_compute_balance')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, default=lambda self: self.env.company.currency_id)



    @api.onchange('account_ids')
    def _onchange_account_ids(self):
        # Clear existing move lines
        self.move_line_ids = [(5, 0, 0)]

        # Get move lines associated with selected accounts
        move_lines = self.env['account.move.line'].search([('account_id', 'in', self.account_ids.ids)])

        # Update move_line_ids with the relevant move lines
        self.move_line_ids = [(4, line.id) for line in move_lines]

    @api.depends('move_line_ids.balance')
    def _compute_balance(self):
        for record in self:
            balance_sum = sum(record.move_line_ids.mapped('balance'))
            record.balance = balance_sum

    # def action_calculate_balance(self):
    #     # Set self.balance to 10
    #     self.balance = 10.0


