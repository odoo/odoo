from odoo import api, fields, models

class AccountBankStatementSplit(models.TransientModel):
    _name = 'account.bank.statement.split'
    _description = 'Split Bank Statement'

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        defaults = super().default_get(fields_list)

        st_line = self.env['account.bank.statement.line'].browse(self.env.context.get('active_id'))
        preceding_statement = self.env['account.bank.statement'].search(
            domain=['id', '!=', st_line.statement_id.id],
            order='date desc, id desc',
            limit=1
        )
        last_line = preceding_statement.line_ids.sorted()[:1]
        lines_in_between = self.env['account.bank.statement.line'].search([
            ('journal_id', '=', st_line.journal_id.id),
            '|', ('date', '<', st_line.date), '&', ('date', '=', st_line.date), ('id', '<', st_line.id),
            '|', ('statement_id', '=', st_line.statement_id.id), ('statement_id', '=', False),
            '|', ('date', '>', last_line.date), '&', ('date', '=', last_line.date), ('id', '>', last_line.id),
        ],
        )
        defaults['current_line'] = st_line.id
        defaults['last_line'] = last_line.id
        defaults['lines_in_between'] = lines_in_between.ids
        defaults['real_balance'] = preceding_statement.balance_end_real + \
                                       sum((lines_in_between + st_line).mapped('amount'))
        defaults['theoretical_balance'] = st_line.cumulated_balance

        return defaults

    real_balance = fields.Monetary(string='Real Balance', required=True)
    theoretical_balance = fields.Monetary(string='Theoretical Balance', required=True)
    preceding_statement = fields.Many2one('account.bank.statement', string='Preceding Statement')
    last_line = fields.Many2one('account.bank.statement.line', string='Last Line')
    lines_in_between = fields.Many2many('account.bank.statement.line', string='Lines in Between')
    current_line = fields.Many2one('account.bank.statement.line', string='Current Statement Line')
