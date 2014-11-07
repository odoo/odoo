# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import models, fields, api, _

class account_entries_report(models.Model):
    _name = "account.entries.report"
    _description = "Journal Items Analysis"
    _auto = False
    _rec_name = 'date'
    
    date = fields.Date(string='Effective Date', readonly=True)  # TDE FIXME master: rename into date_effective
    date_created = fields.Date(string='Date Created', readonly=True)
    date_maturity = fields.Date(string='Date Maturity', readonly=True)
    ref = fields.Char(string='Reference', readonly=True)
    nbr = fields.Integer(string='# of Items', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)
    balance = fields.Float(string='Balance', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    amount_currency = fields.Float(string='Amount Currency', digits=dp.get_precision('Account'), readonly=True)
    period_id = fields.Many2one('account.period', string='Period', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True, domain=[('deprecated', '=', False)])
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', readonly=True)
    move_state = fields.Selection([('draft','Unposted'), ('posted','Posted')], string='Status', readonly=True)
    move_line_state = fields.Selection([('draft','Unbalanced'), ('valid','Valid')], string='State of Move Line', readonly=True)
    reconcile_id = fields.Many2one('account.move.reconcile', string='Reconciliation number', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', readonly=True)
    quantity = fields.Float(string='Products Quantity', digits=(16,2), readonly=True)  # TDE FIXME master: rename into product_quantity
    user_type = fields.Many2one('account.account.type', string='Account Type', readonly=True)
    type = fields.Selection([
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('cash', 'Cash'),
        ('view', 'View'),
        ('consolidation', 'Consolidation'),
        ('other', 'Regular'),
        ('closed', 'Closed'),
    ], string='Internal Type', readonly=True, help="This type is used to differentiate types with "\
        "special effects in Odoo: view can not have entries, consolidation are accounts that "\
        "can have children accounts for multi-company consolidations, payable/receivable are for "\
        "partners accounts (for debit/credit computations), closed for depreciated accounts.")
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    

    _order = 'date desc'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        fiscalyear_obj = self.env['account.fiscalyear']
        period_obj = self.env['account.period']
        for arg in args:
            if arg[0] == 'period_id' and arg[2] == 'current_period':
                current_period = period_obj.find()[0]
                args.append(['period_id','in',[current_period]])
                break
            elif arg[0] == 'period_id' and arg[2] == 'current_year':
                current_year = fiscalyear_obj.find()
                ids = fiscalyear_obj.read([current_year], ['period_ids'])[0]['period_ids']
                args.append(['period_id','in',ids])
        for a in [['period_id','in','current_year'], ['period_id','in','current_period']]:
            if a in args:
                args.remove(a)
        return super(account_entries_report, self).with_context(context).search(args=args, offset=offset, limit=limit, order=order, count=count)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        fiscalyear_obj = self.env['account.fiscalyear']
        period_obj = self.env['account.period']
        if self._context.get('period', False) == 'current_period':
            current_period = period_obj.find()[0]
            domain.append(['period_id','in',[current_period]])
        elif self._context.get('year', False) == 'current_year':
            current_year = fiscalyear_obj.find()
            ids = fiscalyear_obj.read([current_year], ['period_ids'])[0]['period_ids']
            domain.append(['period_id','in',ids])
        else:
            domain = domain
        return super(account_entries_report, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'account_entries_report')
        cr.execute("""
            create or replace view account_entries_report as (
            select
                l.id as id,
                am.date as date,
                l.date_maturity as date_maturity,
                l.date_created as date_created,
                am.ref as ref,
                am.state as move_state,
                l.state as move_line_state,
                l.reconcile_id as reconcile_id,
                l.partner_id as partner_id,
                l.product_id as product_id,
                l.product_uom_id as product_uom_id,
                am.company_id as company_id,
                am.journal_id as journal_id,
                p.fiscalyear_id as fiscalyear_id,
                am.period_id as period_id,
                l.account_id as account_id,
                l.analytic_account_id as analytic_account_id,
                a.type as type,
                a.user_type as user_type,
                1 as nbr,
                l.quantity as quantity,
                l.currency_id as currency_id,
                l.amount_currency as amount_currency,
                l.debit as debit,
                l.credit as credit,
                l.debit-l.credit as balance
            from
                account_move_line l
                left join account_account a on (l.account_id = a.id)
                left join account_move am on (am.id=l.move_id)
                left join account_period p on (am.period_id=p.id)
                where l.state != 'draft'
            )
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
