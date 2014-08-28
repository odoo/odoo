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

from openerp.osv import fields,osv
from openerp.tools.sql import drop_view_if_exists

class report_timesheet_line(osv.osv):
    _name = "report.timesheet.line"
    _description = "Timesheet Line"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'user_id': fields.many2one('res.users', 'User', readonly=True),
        'date': fields.date('Date', readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'quantity': fields.float('Time', readonly=True),
        'cost': fields.float('Cost', readonly=True),
        'product_id': fields.many2one('product.product', 'Product',readonly=True),
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'general_account_id': fields.many2one('account.account', 'Financial Account', readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoiced', readonly=True),
        'month': fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
    }
    _order = 'name desc,user_id desc'
    def init(self, cr):
        drop_view_if_exists(cr, 'report_timesheet_line')
        cr.execute("""
            create or replace view report_timesheet_line as (
                select
                    min(l.id) as id,
                    l.date as date,
                    to_char(l.date,'YYYY') as name,
                    to_char(l.date,'MM') as month,
                    l.user_id,
                    to_char(l.date, 'YYYY-MM-DD') as day,
                    l.invoice_id,
                    l.product_id,
                    l.account_id,
                    l.general_account_id,
                    sum(l.unit_amount) as quantity,
                    sum(l.amount) as cost
                from
                    account_analytic_line l
                where
                    l.user_id is not null
                group by
                    l.date,
                    l.user_id,
                    l.product_id,
                    l.account_id,
                    l.general_account_id,
                    l.invoice_id
            )
        """)




class report_timesheet_user(osv.osv):
    _name = "report_timesheet.user"
    _description = "Timesheet per day"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'quantity': fields.float('Time', readonly=True),
        'cost': fields.float('Cost', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                                  ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
    }
    _order = 'name desc,user_id desc'
    def init(self, cr):
        drop_view_if_exists(cr, 'report_timesheet_user')
        cr.execute("""
            create or replace view report_timesheet_user as (
                select
                    min(l.id) as id,
                    to_char(l.date,'YYYY') as name,
                    to_char(l.date,'MM') as month,
                    l.user_id,
                    sum(l.unit_amount) as quantity,
                    sum(l.amount) as cost
                from
                    account_analytic_line l
                where
                    user_id is not null
                group by l.date, to_char(l.date,'YYYY'),to_char(l.date,'MM'), l.user_id
            )
        """)

class report_timesheet_account(osv.osv):
    _name = "report_timesheet.account"
    _description = "Timesheet per account"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'quantity': fields.float('Time', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),

    }
    _order = 'name desc,account_id desc,user_id desc'
    def init(self, cr):
        drop_view_if_exists(cr, 'report_timesheet_account')
        cr.execute("""
            create or replace view report_timesheet_account as (
                select
                    min(id) as id,
                    to_char(create_date, 'YYYY') as name,
                    to_char(create_date,'MM') as month,
                    user_id,
                    account_id,
                    sum(unit_amount) as quantity
                from
                    account_analytic_line
                group by
                    to_char(create_date, 'YYYY'),to_char(create_date, 'MM'), user_id, account_id
            )
        """)


class report_timesheet_account_date(osv.osv):
    _name = "report_timesheet.account.date"
    _description = "Daily timesheet per account"
    _auto = False
    _columns = {
        'name': fields.char('Year', required=False, readonly=True),
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'quantity': fields.float('Time', readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'), ('05','May'), ('06','June'),
                          ('07','July'), ('08','August'), ('09','September'), ('10','October'), ('11','November'), ('12','December')],'Month', readonly=True),
    }
    _order = 'name desc,account_id desc,user_id desc'

    def init(self, cr):
        drop_view_if_exists(cr, 'report_timesheet_account_date')
        cr.execute("""
            create or replace view report_timesheet_account_date as (
                select
                    min(id) as id,
                    to_char(date,'YYYY') as name,
                    to_char(date,'MM') as month,
                    user_id,
                    account_id,
                    sum(unit_amount) as quantity
                from
                    account_analytic_line
                group by
                    to_char(date,'YYYY'),to_char(date,'MM'), user_id, account_id
            )
        """)


class report_timesheet_invoice(osv.osv):
    _name = "report_timesheet.invoice"
    _description = "Costs to invoice"
    _auto = False
    _columns = {
        'user_id':fields.many2one('res.users', 'User', readonly=True),
        'account_id':fields.many2one('account.analytic.account', 'Project', readonly=True),
        'manager_id':fields.many2one('res.users', 'Manager', readonly=True),
        'quantity': fields.float('Time', readonly=True),
        'amount_invoice': fields.float('To invoice', readonly=True)
    }
    _rec_name = 'user_id'
    _order = 'user_id desc'
    def init(self, cr):
        drop_view_if_exists(cr, 'report_timesheet_invoice')
        cr.execute("""
            create or replace view report_timesheet_invoice as (
                select
                    min(l.id) as id,
                    l.user_id as user_id,
                    l.account_id as account_id,
                    a.user_id as manager_id,
                    sum(l.unit_amount) as quantity,
                    sum(l.unit_amount * t.list_price) as amount_invoice
                from account_analytic_line l
                    left join hr_timesheet_invoice_factor f on (l.to_invoice=f.id)
                    left join account_analytic_account a on (l.account_id=a.id)
                    left join product_product p on (l.to_invoice=f.id)
                    left join product_template t on (l.to_invoice=f.id)
                where
                    l.to_invoice is not null and
                    l.invoice_id is null
                group by
                    l.user_id,
                    l.account_id,
                    a.user_id
            )
        """)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
