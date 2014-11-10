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

import time
import datetime
from dateutil.relativedelta import relativedelta

from openerp import tools
from openerp import models, fields, api

@api.model
def _code_get(self):
    acc_type_obj = self.env['account.account.type']
    account_type = acc_type_obj.search([])
    return [(r.code, r.name) for r in account_type]


class report_account_receivable(models.Model):
    _name = "report.account.receivable"
    _description = "Receivable accounts"
    _auto = False

    name = fields.Char(string='Week of Year', size=7, readonly=True)
    type = fields.Selection(_code_get, string='Account Type', required=True)
    balance = fields.Float(string='Balance', readonly=True)
    debit = fields.Float(string='Debit', readonly=True)
    credit = fields.Float(string='Credit', readonly=True)

    _order = 'name desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_receivable')
        cr.execute("""
            create or replace view report_account_receivable as (
                select
                    min(l.id) as id,
                    to_char(date,'YYYY:IW') as name,
                    sum(l.debit-l.credit) as balance,
                    sum(l.debit) as debit,
                    sum(l.credit) as credit,
                    a.type
                from
                    account_move_line l
                left join
                    account_account a on (l.account_id=a.id)
                where
                    l.state <> 'draft'
                group by
                    to_char(date,'YYYY:IW'), a.type
            )""")

                    #a.type in ('receivable','payable')
class temp_range(models.Model):
    _name = 'temp.range'
    _description = 'A Temporary table used for Dashboard view'
    
    name = fields.Char(string='Range')
    


class report_aged_receivable(models.Model):
    _name = "report.aged.receivable"
    _description = "Aged Receivable Till Today"
    _auto = False

    def __init__(self, pool, cr):
        super(report_aged_receivable, self).__init__(pool, cr)
        self.called = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ To call the init() method timely
        """
        if not self.called:
            self._init(cr, user)
        self.called = True # To make sure that init doesn't get called multiple times

        res = super(report_aged_receivable, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        return res

    @api.multi
    def _calc_bal(self):
        res = {}
        for period in self.name:
            date1,date2 = period['name'].split(' to ')
            cr.execute("SELECT SUM(credit-debit) FROM account_move_line AS line, account_account as ac  \
                        WHERE (line.account_id=ac.id) AND ac.type='receivable' \
                            AND (COALESCE(line.date,date) BETWEEN %s AND  %s) \
                            AND (reconcile_id IS NULL) AND ac.active",(str(date2),str(date1),))
            amount = cr.fetchone()
            amount = amount[0] or 0.00
            res[period['id']] = amount

        return res

    name = fields.Char(string='Month Range', size=24, readonly=True)
    balance = fields.Float(string='Balance', compute='_calc_bal', readonly=True)
    
    @api.model
    def _init(self): 
        """ This view will be used in dashboard
        The reason writing this code here is, we need to check date range from today to first date of fiscal year.
        """
        pool_obj_fy = self.env['account.fiscalyear']
        current_date = datetime.date.today()
        fy_id = pool_obj_fy.find(exception=False)
        names = []

        def add(names, start_on, stop_on):
            names.append(start_on.strftime("%Y-%m-%d") + ' to ' + stop_on.strftime('%Y-%m-%d'))
            return names

        if fy_id:
            fiscal_year = pool_obj_fy.browse(fy_id)
            fy_start_date = datetime.datetime.strptime(fiscal_year.date_start, '%Y-%m-%d').date()
            last_month_date = current_date - relativedelta(months=1)

            while (last_month_date > fy_start_date):
                add(names, current_date, last_month_date)
                current_date = last_month_date - relativedelta(days=1)
                last_month_date = current_date - relativedelta(months=1)

                add(names, current_date, fy_start_date)
            cr.execute('delete from temp_range')

            for name in names:
                self.env['temp.range'].create({'name':name})

        cr.execute("""
            create or replace view report_aged_receivable as (
                select id,name from temp_range
            )""")


class report_invoice_created(models.Model):
    _name = "report.invoice.created"
    _description = "Report of Invoices Created within Last 15 days"
    _auto = False

    name = fields.Char(string='Description', readonly=True)
    type = fields.Selection([
        ('out_invoice','Customer Invoice'),
        ('in_invoice','Supplier Invoice'),
        ('out_refund','Customer Refund'),
        ('in_refund','Supplier Refund'),
        ],'Type', readonly=True)
    number = fields.Char(string='Invoice Number', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    amount_untaxed = fields.Float(string='Untaxed', readonly=True)
    amount_total = fields.Float(string='Total', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    date_invoice = fields.Date(string='Invoice Date', readonly=True)
    date_due = fields.Date(string='Due Date', readonly=True)
    residual = fields.Float(string='Residual', readonly=True)
    state = fields.Selection([
        ('draft','Draft'),
        ('proforma','Pro-forma'),
        ('proforma2','Pro-forma'),
        ('open','Open'),
        ('paid','Done'),
        ('cancel','Cancelled')
    ],'Status', readonly=True)
    origin = fields.Char(string='Source Document', readonly=True, help="Reference of the document that generated this invoice report.")
    create_date = fields.Datetime(string='Create Date', readonly=True)

    _order = 'create_date'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_invoice_created')
        cr.execute("""create or replace view report_invoice_created as (
            select
               inv.id as id, inv.name as name, inv.type as type,
               inv.number as number, inv.partner_id as partner_id,
               inv.amount_untaxed as amount_untaxed,
               inv.amount_total as amount_total, inv.currency_id as currency_id,
               inv.date_invoice as date_invoice, inv.date_due as date_due,
               inv.residual as residual, inv.state as state,
               inv.origin as origin, inv.create_date as create_date
            from
                account_invoice inv
            where
                (to_date(to_char(inv.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') <= CURRENT_DATE)
                AND
                (to_date(to_char(inv.create_date, 'YYYY-MM-dd'),'YYYY-MM-dd') > (CURRENT_DATE-15))
            )""")

class report_account_type_sales(models.Model):
    _name = "report.account_type.sales"
    _description = "Report of the Sales by Account Type"
    _auto = False

    name = fields.Char(string='Year', required=False, readonly=True)
    period_id = fields.Many2one('account.period', string='Force Period', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    user_type = fields.Many2one('account.account.type', string='Account Type', readonly=True)
    amount_total = fields.Float(string='Total', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    month = fields.Selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                              ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')], string='Month', readonly=True)

    _order = 'name desc,amount_total desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_type_sales')
        cr.execute("""create or replace view report_account_type_sales as (
            select
               min(inv_line.id) as id,
               to_char(inv.date_invoice, 'YYYY') as name,
               to_char(inv.date_invoice,'MM') as month,
               sum(inv_line.price_subtotal) as amount_total,
               inv.currency_id as currency_id,
               inv.period_id,
               inv_line.product_id,
               sum(inv_line.quantity) as quantity,
               account.user_type
            from
                account_invoice_line inv_line
            inner join account_invoice inv on inv.id = inv_line.invoice_id
            inner join account_account account on account.id = inv_line.account_id
            where
                inv.state in ('open','paid')
            group by
                to_char(inv.date_invoice, 'YYYY'),to_char(inv.date_invoice,'MM'),inv.currency_id, inv.period_id, inv_line.product_id, account.user_type
            )""")


class report_account_sales(models.Model):
    _name = "report.account.sales"
    _description = "Report of the Sales by Account"
    _auto = False

    name = fields.Char(string='Year', required=False, readonly=True, select=True)
    period_id = fields.Many2one('account.period', string='Force Period', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    quantity = fields.Float(string='Quantity', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True, domain=[('deprecated', '=', False)])
    amount_total = fields.Float(string='Total', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    month = fields.Selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                              ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')], string='Month', readonly=True)

    _order = 'name desc'

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_account_sales')
        cr.execute("""create or replace view report_account_sales as (
            select
               min(inv_line.id) as id,
               to_char(inv.date_invoice, 'YYYY') as name,
               to_char(inv.date_invoice,'MM') as month,
               sum(inv_line.price_subtotal) as amount_total,
               inv.currency_id as currency_id,
               inv.period_id,
               inv_line.product_id,
               sum(inv_line.quantity) as quantity,
               account.id as account_id
            from
                account_invoice_line inv_line
            inner join account_invoice inv on inv.id = inv_line.invoice_id
            inner join account_account account on account.id = inv_line.account_id
            where
                inv.state in ('open','paid')
            group by
                to_char(inv.date_invoice, 'YYYY'),to_char(inv.date_invoice,'MM'),inv.currency_id, inv.period_id, inv_line.product_id, account.id
            )""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
