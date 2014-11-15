# -*- coding: utf-8 -*-

from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api

class account_treasury_report(models.Model):
    _name = "account.treasury.report"
    _description = "Treasury Analysis"
    _auto = False

    @api.multi
    @api.depends('company_id', 'balance')
    def _compute_balances(self):
        all_treasury_lines = self.search([])
        all_companies = self.env['res.company'].search([])
        current_sum = dict((company, 0.0) for company in all_companies)
        res = dict((id, dict((fn, 0.0) for fn in field_names)) for id in all_treasury_lines)
        for record in self.all_treasury_lines:
            record.starting_balance = current_sum[record.company_id.id]
            current_sum[record.company_id.id] += record.balance
            record.ending_balance = current_sum[record.company_id.id]
        return res

    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscalyear', readonly=True)
    date = fields.Date(string='Account Date', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)
    balance = fields.Float(string='Balance', readonly=True)
    starting_balance = fields.Float(compute='_compute_balances', digits=dp.get_precision('Account'), string='Starting Balance')
    ending_balance = fields.Float(compute='_compute_balances', digits=dp.get_precision('Account'), string='Ending Balance')
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    _order = 'date asc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_treasury_report')
        cr.execute("""
            create or replace view account_treasury_report as (
            select
                l.date as date,
                fs.id as fiscalyear_id,
                sum(l.debit) as debit,
                sum(l.credit) as credit,
                sum(l.debit-l.credit) as balance,
                l.date as date,
                am.company_id as company_id
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_move am on (am.id=l.move_id)
                left join account_fiscalyear fs on (l.date >= fs.date_start and l.date <= fs.date_stop)
            where l.state != 'draft'
              and a.type = 'liquidity'
            group by fs.id, l.date, am.company_id
            )
        """)
