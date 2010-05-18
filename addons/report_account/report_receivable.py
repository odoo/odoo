# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import datetime
import mx.DateTime

import pooler
from osv import fields,osv


def _code_get(self, cr, uid, context={}):
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
        'name' : fields.char('Range',size=64)
    }
    
temp_range()    
    
class report_aged_receivable(osv.osv):
    _name = "report.aged.receivable"
    _description = "Aged Receivable Till Today"
    _auto = False
    
    def __init__(self, pool, cr):
        super(report_aged_receivable, self).__init__(pool, cr)
        self.called = False
        
    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False):
        """ To call the init() method timely
        """
        if not self.called:
            self.init(cr, user)
        self.called = True # To make sure that init doesn't get called multiple times
        
        res = super(report_aged_receivable, self).fields_view_get(cr, user, view_id, view_type, context, toolbar)
        return res
    
    def _calc_bal(self, cr, uid, ids, name, args, context):
        res = {}
        for period in self.read(cr,uid,ids,['name']):
           date1,date2 = period['name'].split(' to ')
           query = "SELECT SUM(credit-debit) FROM account_move_line AS line, account_account as ac  \
                        WHERE (line.account_id=ac.id) AND ac.type='receivable' \
                            AND (COALESCE(line.date,date) BETWEEN %s AND  %s) \
                            AND (reconcile_id IS NULL) AND ac.active"
           cr.execute(query, (date2, date1))
           amount = cr.fetchone()
           amount = amount[0] or 0.00
           res[period['id']] = amount
           
        return res
    
    _columns = {
        'name': fields.char('Month Range', size=7, readonly=True),
        'balance': fields.function(_calc_bal, method=True, string='Balance', readonly=True),
    }
    
    def init(self, cr, uid=1):
        """ This view will be used in dashboard
        """
#        ranges = _get_ranges(cr) # Gets the ranges for the x axis of the graph (name column values)
        pool_obj_fy = pooler.get_pool(cr.dbname).get('account.fiscalyear')
        today = mx.DateTime.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d') - mx.DateTime.RelativeDateTime(days=1)
        today = today.strftime('%Y-%m-%d')
        fy_id  = pool_obj_fy.find(cr,uid, exception=False)
        LIST_RANGES = []
        if fy_id:
            fy_start_date = pool_obj_fy.read(cr, uid, fy_id, ['date_start'])['date_start']
            fy_start_date = mx.DateTime.strptime(fy_start_date, '%Y-%m-%d')
            last_month_date = mx.DateTime.strptime(today, '%Y-%m-%d') - mx.DateTime.RelativeDateTime(months=1)

            while (last_month_date > fy_start_date):
                LIST_RANGES.append(today + " to " + last_month_date.strftime('%Y-%m-%d'))
                today = (last_month_date- 1).strftime('%Y-%m-%d')
                last_month_date = mx.DateTime.strptime(today, '%Y-%m-%d') - mx.DateTime.RelativeDateTime(months=1)
            
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
        'date_invoice': fields.date('Date Invoiced', readonly=True),
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
        'origin': fields.char('Origin', size=64, readonly=True),
        'create_date' : fields.datetime('Create Date', readonly=True)
    }
    _order = 'create_date'
    
    def init(self, cr):
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

