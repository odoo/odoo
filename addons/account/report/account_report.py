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
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pooler
import tools
from osv import fields,osv

def _code_get(self, cr, uid, context=None):
    acc_type_obj = self.pool.get('account.account.type')
    ids = acc_type_obj.search(cr, uid, [])
    res = acc_type_obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res]


class report_account_receivable(osv.osv):
    _name = "report.account.receivable"
    _description = "Receivable accounts"
    _auto = False
    _columns = {
        'name': fields.char('Week of Year', size=7, readonly=True),
        'type': fields.selection(_code_get, 'Account Type', required=True),
        'balance':fields.float('Balance', readonly=True),
        'debit':fields.float('Debit', readonly=True),
        'credit':fields.float('Credit', readonly=True),
    }
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
report_account_receivable()

                    #a.type in ('receivable','payable')
class temp_range(osv.osv):
    _name = 'temp.range'
    _description = 'A Temporary table used for Dashboard view'

    _columns = {
        'name': fields.char('Range',size=64)
    }

temp_range()

class report_aged_receivable(osv.osv):
    _name = "report.aged.receivable"
    _description = "Aged Receivable Till Today"
    _auto = False

    def __init__(self, pool, cr):
        super(report_aged_receivable, self).__init__(pool, cr)
        self.called = False

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ To call the init() method timely
        """
        if not self.called:
            self.init(cr, user)
        self.called = True # To make sure that init doesn't get called multiple times

        res = super(report_aged_receivable, self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        return res

    def _calc_bal(self, cr, uid, ids, name, args, context=None):
        res = {}
        for period in self.read(cr, uid, ids, ['name'], context=context):
            date1,date2 = period['name'].split(' to ')
            cr.execute("SELECT SUM(credit-debit) FROM account_move_line AS line, account_account as ac  \
                        WHERE (line.account_id=ac.id) AND ac.type='receivable' \
                            AND (COALESCE(line.date,date) BETWEEN %s AND  %s) \
                            AND (reconcile_id IS NULL) AND ac.active",(str(date2),str(date1),))
            amount = cr.fetchone()
            amount = amount[0] or 0.00
            res[period['id']] = amount

        return res

    _columns = {
        'name': fields.char('Month Range', size=7, readonly=True),
        'balance': fields.function(_calc_bal, string='Balance', readonly=True),
    }

    def init(self, cr, uid=1):
        """ This view will be used in dashboard
        The reason writing this code here is, we need to check date range from today to first date of fiscal year.
        """
        pool_obj_fy = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        today = time.strftime('%Y-%m-%d')
        fy_id = pool_obj_fy.find(cr, uid, exception=False)
        LIST_RANGES = []
        if fy_id:
            fy_start_date = pool_obj_fy.read(cr, uid, fy_id, ['date_start'])['date_start']
            fy_start_date = datetime.strptime(fy_start_date, '%Y-%m-%d')
            last_month_date = datetime.strptime(today, '%Y-%m-%d') - relativedelta(months=1)

            while (last_month_date > fy_start_date):
                LIST_RANGES.append(today + " to " + last_month_date.strftime('%Y-%m-%d'))
                today = (last_month_date- relativedelta(days=1)).strftime('%Y-%m-%d')
                last_month_date = datetime.strptime(today, '%Y-%m-%d') - relativedelta(months=1)

            LIST_RANGES.append(today +" to " + fy_start_date.strftime('%Y-%m-%d'))
            cr.execute('delete from temp_range')

            for range in LIST_RANGES:
                pooler.get_pool(cr.dbname).get('temp.range').create(cr, uid, {'name':range})

        cr.execute("""
            create or replace view report_aged_receivable as (
                select id,name from temp_range
            )""")

report_aged_receivable()

class report_invoice_created(osv.osv):
    _name = "report.invoice.created"
    _description = "Report of Invoices Created within Last 15 days"
    _auto = False
    _columns = {
        'name': fields.char('Description', size=64, readonly=True),
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True),
        'number': fields.char('Invoice Number', size=32, readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'amount_untaxed': fields.float('Untaxed', readonly=True),
        'amount_total': fields.float('Total', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'date_invoice': fields.date('Invoice Date', readonly=True),
        'date_due': fields.date('Due Date', readonly=True),
        'residual': fields.float('Residual', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Cancelled')
        ],'State', readonly=True),
        'origin': fields.char('Source Document', size=64, readonly=True, help="Reference of the document that generated this invoice report."),
        'create_date': fields.datetime('Create Date', readonly=True)
    }
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
report_invoice_created()

class report_account_type_sales(osv.osv):
    _name = "report.account_type.sales"
    _description = "Report of the Sales by Account Type"
    _auto = False
    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True),
        'period_id': fields.many2one('account.period', 'Force Period', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'quantity': fields.float('Quantity', readonly=True),
        'user_type': fields.many2one('account.account.type', 'Account Type', readonly=True),
        'amount_total': fields.float('Total', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
    }
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
report_account_type_sales()


class report_account_sales(osv.osv):
    _name = "report.account.sales"
    _description = "Report of the Sales by Account"
    _auto = False
    _columns = {
        'name': fields.char('Year', size=64, required=False, readonly=True, select=True),
        'period_id': fields.many2one('account.period', 'Force Period', readonly=True),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'quantity': fields.float('Quantity', readonly=True),
        'account_id': fields.many2one('account.account', 'Account', readonly=True),
        'amount_total': fields.float('Total', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
    }
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
report_account_sales()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
