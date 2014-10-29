from openerp import models, fields, api

class account_common_journal_report(models.TransientModel):
    _name = 'account.common.journal.report'
    _description = 'Account Common Journal Report'
    _inherit = "account.common.report"

    amount_currency = fields.Boolean(string='With Currency', 
        help="Print Report with the currency column if the currency differs from the company currency.")

    @api.multi
    def _build_contexts(self, data):
        result = super(account_common_journal_report, self)._build_contexts(data)

        if data['form']['filter'] == 'filter_date':
            self._cr.execute('SELECT period_id FROM account_move_line WHERE date >= %s AND date <= %s', (data['form']['date_from'], data['form']['date_to']))
            result['periods'] = map(lambda x: x[0], self._cr.fetchall())
        elif data['form']['filter'] == 'filter_period':
            result['periods'] = self.env['account.period'].build_ctx_periods(data['form']['period_from'], data['form']['period_to'])
        return result

    @api.multi
    def pre_print_report(self, data):
        data['form'].update(self.read(self.ids, ['amount_currency'])[0])
        fy_ids = data['form']['fiscalyear_id'] and [data['form']['fiscalyear_id']] or self.env['account.fiscalyear'].search([('state', '=', 'draft')])
        period_list = data['form']['periods'] or self.env['account.period'].search([('fiscalyear_id', 'in', fy_ids)])
        data['form']['active_ids'] = self.env['account.journal.period'].search([('journal_id', 'in', data['form']['journal_ids']), ('period_id', 'in', period_list)])
        return data

