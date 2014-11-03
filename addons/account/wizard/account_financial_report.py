# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class accounting_report(models.TransientModel):
    _name = "accounting.report"
    _inherit = "account.common.report"
    _description = "Accounting Report"

    enable_filter = fields.Boolean(string='Enable Comparison')
    account_report_id = fields.Many2one('account.financial.report', string='Account Reports', required=True, default=lambda self: self._get_account_report())
    label_filter = fields.Char(string='Column Label',
        help="This label will be displayed on report to show the balance computed for the given comparison filter.")
    fiscalyear_id_cmp = fields.Many2one('account.fiscalyear', string='Fiscal Year', help='Keep empty for all open fiscal year')
    filter_cmp = fields.Selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], string='Filter by',
        default='filter_no', required=True)
    period_from_cmp = fields.Many2one('account.period', string='Start Period')
    period_to_cmp = fields.Many2one('account.period', string='End Period')
    date_from_cmp = fields.Date(string='Start Date')
    date_to_cmp = fields.Date(string='End Date')
    debit_credit = fields.Boolean(string='Display Debit/Credit Columns',
        help="This option allows you to get more details about the way your balances are computed. Because it is space consuming, we do not allow to use it while doing a comparison.")

    @api.model
    def _get_account_report(self):
        # TODO deprecate this it doesnt work in web
        report = False
        if context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(context.get('active_id')).name
            report = self.env['account.financial.report'].search([('name', 'ilike', menu)], limit=1)
        return report

    @api.multi
    def _build_comparison_context(self, data):
        result = {}
        result['fiscalyear'] = 'fiscalyear_id_cmp' in data['form'] and data['form']['fiscalyear_id_cmp'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter_cmp'] == 'filter_date':
            result['date_from'] = data['form']['date_from_cmp']
            result['date_to'] = data['form']['date_to_cmp']
        elif data['form']['filter_cmp'] == 'filter_period':
            if not data['form']['period_from_cmp'] or not data['form']['period_to_cmp']:
                raise Warning(_('Select a starting and an ending period'))
            result['period_from'] = data['form']['period_from_cmp']
            result['period_to'] = data['form']['period_to_cmp']
        return result

    @api.multi
    def check_report(self):
        res = super(accounting_report, self).check_report()
        data = {}
        data['form'] = self.read(['account_report_id', 'date_from_cmp',  'date_to_cmp',  'fiscalyear_id_cmp', 'journal_ids', 'period_from_cmp', 'period_to_cmp',  'filter_cmp',  'chart_account_id', 'target_move'])[0]
        for field in ['fiscalyear_id_cmp', 'chart_account_id', 'period_from_cmp', 'period_to_cmp', 'account_report_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        comparison_context = self._build_comparison_context(data)
        res['data']['form']['comparison_context'] = comparison_context
        return res

    @api.multi
    def _print_report(self, data):
        data['form'].update(self.read(['date_from_cmp',  'debit_credit', 'date_to_cmp',  'fiscalyear_id_cmp', 'period_from_cmp', 'period_to_cmp',  'filter_cmp', 'account_report_id', 'enable_filter', 'label_filter','target_move'])[0])
        return self.env['report'].get_action([], 'account.report_financial', data=data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
