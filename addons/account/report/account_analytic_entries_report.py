# -*- coding: utf-8 -*-

from openerp import tools
from openerp import models, fields

class analytic_entries_report(models.Model):
    _name = "analytic.entries.report"
    _description = "Analytic Entries Statistics"
    _auto = False

    date = fields.Date(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    name = fields.Char(string='Description', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    account_id = fields.Many2one('account.analytic.account', string='Analytic Account', required=False)
    general_account_id = fields.Many2one('account.account', string='Financial Account', required=True, domain=[('deprecated', '=', False)])
    journal_id = fields.Many2one('account.analytic.journal', string='Journal', required=True)
    move_id = fields.Many2one('account.move.line', string='Move', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True)
    amount = fields.Float(string='Amount', readonly=True)
    unit_amount = fields.Integer(string='Unit Amount', readonly=True)
    nbr_entries = fields.Integer(string='# Entries', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'analytic_entries_report')
        cr.execute("""
            create or replace view analytic_entries_report as (
                 select
                     min(a.id) as id,
                     count(distinct a.id) as nbr_entries,
                     a.date as date,
                     a.user_id as user_id,
                     a.name as name,
                     analytic.partner_id as partner_id,
                     a.company_id as company_id,
                     a.currency_id as currency_id,
                     a.account_id as account_id,
                     a.general_account_id as general_account_id,
                     a.journal_id as journal_id,
                     a.move_id as move_id,
                     a.product_id as product_id,
                     a.product_uom_id as product_uom_id,
                     sum(a.amount) as amount,
                     sum(a.unit_amount) as unit_amount
                 from
                     account_analytic_line a, account_analytic_account analytic
                 where analytic.id = a.account_id
                 group by
                     a.date, a.user_id,a.name,analytic.partner_id,a.company_id,a.currency_id,
                     a.account_id,a.general_account_id,a.journal_id,
                     a.move_id,a.product_id,a.product_uom_id
            )
        """)
