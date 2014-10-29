
import time
from lxml import etree

from openerp import models, api, _
from openerp.exceptions import Warning
from openerp.osv.orm import setup_modifiers

class account_common_report(models.TransientModel):
    _name = "account.common.report"
    _description = "Account Common Report"

    @api.multi
    def onchange_chart_id(self, chart_account_id=False):
        res = {}
        if chart_account_id:
            company_id = self.env['account.account'].browse(chart_account_id).company_id.id
            now = time.strftime('%Y-%m-%d')
            domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
            fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
            res['value'] = {'company_id': company_id, 'fiscalyear_id': fiscalyears and fiscalyears[0] or False}
        return res

    chart_account_id = fields.Many2one('account.account', string='Chart of Account', 
        help='Select Charts of Accounts', default=lambda self: self._get_account(),
        required=True, domain = [('parent_id','=',False), ('deprecated', '=', False)])
    company_id = fields.Many2one('res.company', related='chart_account_id.company_id',
        string='Company', readonly=True, default=lambda self: self.env['res.company']._company_default_get('account.common.report'))
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', 
        help='Keep empty for all open fiscal year', default=lambda self: self._get_fiscalyear())
    filter = fields.Selection([('filter_no', 'Do not apply filter'), ('filter_date', 'Filter by date'), ('filter_period', 'Filter by period')], 
        string='Filter by', required=True, default='filter_no')
    period_from = fields.Many2one('account.period', string='Start Period')
    period_to = fields.Many2one('account.period', string='End Period')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, 
        default=lambda self: self._get_all_journal())
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    target_move = fields.Selection([('posted', 'All Posted Entries'), ('all', 'All Entries'), ],
        string='Target Moves', required=True, default='posted')

    @api.multi
    @api.constrains('chart_account_id','fiscalyear_id','period_from','period_to')
    def _check_company_id(self):
        for wiz in self:
            company_id = wiz.company_id.id
            if wiz.fiscalyear_id and company_id != wiz.fiscalyear_id.company_id.id:
                raise Warning(_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))
            if wiz.period_from and company_id != wiz.period_from.company_id.id:
                raise Warning(_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))
            if wiz.period_to and company_id != wiz.period_to.company_id.id:
                raise Warning(_('The fiscalyear, periods or chart of account chosen have to belong to the same company.'))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(account_common_report, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        if self._context.get('active_model', False) == 'account.account':
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='chart_account_id']")
            for node in nodes:
                node.set('readonly', '1')
                node.set('help', 'If you print the report from Account list/form view it will not consider Charts of account')
                setup_modifiers(node, res['fields']['chart_account_id'])
            res['arch'] = etree.tostring(doc)
        return res

    @api.multi
    def onchange_filter(self, filter='filter_no', fiscalyear_id=False):
        res = {'value': {}}
        if filter == 'filter_no':
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False}
        if filter == 'filter_date':
            res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
        if filter == 'filter_period' and fiscalyear_id:
            start_period = end_period = False
            self._cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.special = false
                               ORDER BY p.date_start ASC, p.special ASC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               AND p.special = false
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
            periods =  [i[0] for i in self._cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
        return res

    @api.model
    def _get_account(self):
        accounts = self.env['account.account'].search([('parent_id', '=', False), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return accounts and accounts[0] or False

    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self._context.get('active_ids', [])
        if ids and self._context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env.user.company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    @api.model
    def _get_all_journal(self):
        return self.env['account.journal'].search([])

    @api.multi
    def _build_contexts(self, data):
        result = {}
        result['fiscalyear'] = 'fiscalyear_id' in data['form'] and data['form']['fiscalyear_id'] or False
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form']['journal_ids'] or False
        result['chart_account_id'] = 'chart_account_id' in data['form'] and data['form']['chart_account_id'] or False
        result['state'] = 'target_move' in data['form'] and data['form']['target_move'] or ''
        if data['form']['filter'] == 'filter_date':
            result['date_from'] = data['form']['date_from']
            result['date_to'] = data['form']['date_to']
        elif data['form']['filter'] == 'filter_period':
            if not data['form']['period_from'] or not data['form']['period_to']:
                raise Warning(_('Select a starting and an ending period.'))
            result['period_from'] = data['form']['period_from']
            result['period_to'] = data['form']['period_to']
        return result

    @api.multi
    def _print_report(self, data):
        raise Warning(_('Not implemented.'))

    @api.multi
    def check_report(self):
        data = {}
        data['ids'] = self._context.get('active_ids', [])
        data['model'] = self._context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from',  'date_to',  'fiscalyear_id', 'journal_ids', 'period_from', 'period_to',  'filter',  'chart_account_id', 'target_move'])[0]
        for field in ['fiscalyear_id', 'chart_account_id', 'period_from', 'period_to']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        used_context = self._build_contexts(data)
        data['form']['periods'] = used_context.get('periods', False) and used_context['periods'] or []
        data['form']['used_context'] = dict(used_context, lang=self._context.get('lang', 'en_US'))
        return self._print_report(data)

