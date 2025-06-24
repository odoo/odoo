from odoo import api, fields, models


class AccountFinancialSummaryWizard(models.TransientModel):
    _name = 'account.financial.summary.wizard'
    _description = 'Financial Summary Wizard'
    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True
    )
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('account.financial.summary.line', 'wizard_id')

    def action_generate(self):
        self.ensure_one()
        self.line_ids.unlink()
        query = """
            SELECT account_id, SUM(debit) AS debit, SUM(credit) AS credit
            FROM account_move_line
            WHERE company_id = %s AND date >= %s AND date <= %s AND parent_state = 'posted'
            GROUP BY account_id
        """
        params = (self.company_id.id, self.date_from, self.date_to)
        self.env.cr.execute(query, params)
        results = self.env.cr.fetchall()
        lines = []
        for account_id, debit, credit in results:
            lines.append((0, 0, {
                'account_id': account_id,
                'debit': debit,
                'credit': credit,
                'balance': debit - credit,
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'name': 'Financial Summary',
            'res_model': 'account.financial.summary.line',
            'view_mode': 'tree',
            'target': 'new',
            'domain': [('wizard_id', '=', self.id)],
        }


class AccountFinancialSummaryLine(models.TransientModel):
    _name = 'account.financial.summary.line'
    _description = 'Financial Summary Line'
    _order = 'account_id'

    wizard_id = fields.Many2one('account.financial.summary.wizard', ondelete='cascade')
    account_id = fields.Many2one('account.account', readonly=True)
    debit = fields.Monetary(currency_field='currency_id', readonly=True)
    credit = fields.Monetary(currency_field='currency_id', readonly=True)
    balance = fields.Monetary(currency_field='currency_id', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.company_id.currency_id',
        readonly=True
    )

