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

import tools
from osv import fields,osv
from decimal_precision import decimal_precision as dp


class hr_expense_report(osv.osv):
    _name = "hr.expense.report"
    _description = "Expenses Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date ', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'day': fields.char('Day', size=128, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month',readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Force Journal', readonly=True),
        'product_qty':fields.float('Qty', readonly=True),
        'invoiced':fields.integer('# of Invoiced Lines', readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee's Name", readonly=True),
        'date_confirm': fields.date('Confirmation Date', readonly=True),
        'date_valid': fields.date('Validation Date', readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'department_id':fields.many2one('hr.department','Department', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Validation User', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'price_total':fields.float('Total Price', readonly=True, digits_compute=dp.get_precision('Account')),
        'delay_valid':fields.float('Delay to Valid', readonly=True),
        'delay_confirm':fields.float('Delay to Confirm', readonly=True),
        'analytic_account': fields.many2one('account.analytic.account','Analytic account',readonly=True),
        'price_average':fields.float('Average Price', readonly=True, digits_compute=dp.get_precision('Account')),
        'nbr':fields.integer('# of Lines', readonly=True),
        'no_of_products':fields.integer('# of Products', readonly=True),
        'no_of_account':fields.integer('# of Accounts', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirm', 'Waiting confirmation'),
            ('accepted', 'Accepted'),
            ('invoiced', 'Invoiced'),
            ('paid', 'Reimbursed'),
            ('cancelled', 'Cancelled')],
            'Status', readonly=True),
    }
    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_expense_report')
        cr.execute("""
            create or replace view hr_expense_report as (
                 select
                     min(l.id) as id,
                     date_trunc('day',s.date) as date,
                     s.employee_id,
                     s.journal_id,
                     s.currency_id,
                     to_date(to_char(s.date_confirm, 'dd-MM-YYYY'),'dd-MM-YYYY') as date_confirm,
                     to_date(to_char(s.date_valid, 'dd-MM-YYYY'),'dd-MM-YYYY') as date_valid,
                     s.invoice_id,
                     count(s.invoice_id) as invoiced,
                     s.user_valid as user_id,
                     s.department_id,
                     to_char(date_trunc('day',s.create_date), 'YYYY') as year,
                     to_char(date_trunc('day',s.create_date), 'MM') as month,
                     to_char(date_trunc('day',s.create_date), 'YYYY-MM-DD') as day,
                     avg(extract('epoch' from age(s.date_valid,s.date)))/(3600*24) as  delay_valid,
                     avg(extract('epoch' from age(s.date_valid,s.date_confirm)))/(3600*24) as  delay_confirm,
                     l.product_id as product_id,
                     l.analytic_account as analytic_account,
                     sum(l.unit_quantity * u.factor) as product_qty,
                     s.company_id as company_id,
                     sum(l.unit_quantity*l.unit_amount) as price_total,
                     (sum(l.unit_quantity*l.unit_amount)/sum(case when l.unit_quantity=0 or u.factor=0 then 1 else l.unit_quantity * u.factor end))::decimal(16,2) as price_average,
                     count(*) as nbr,
                     (select unit_quantity from hr_expense_line where id=l.id and product_id is not null) as no_of_products,
                     (select analytic_account from hr_expense_line where id=l.id and analytic_account is not null) as no_of_account,
                     s.state
                 from hr_expense_line l
                 left join hr_expense_expense s on (s.id=l.expense_id)
                 left join product_uom u on (u.id=l.uom_id)
                 group by
                     date_trunc('day',s.date),
                     to_char(date_trunc('day',s.create_date), 'YYYY'),
                     to_char(date_trunc('day',s.create_date), 'MM'),
                     to_char(date_trunc('day',s.create_date), 'YYYY-MM-DD'),
                     to_date(to_char(s.date_confirm, 'dd-MM-YYYY'),'dd-MM-YYYY'),
                     to_date(to_char(s.date_valid, 'dd-MM-YYYY'),'dd-MM-YYYY'),
                     l.product_id,
                     l.analytic_account,
                     s.invoice_id,
                     s.currency_id,
                     s.user_valid,
                     s.department_id,
                     l.uom_id,
                     l.id,
                     s.state,
                     s.journal_id,
                     s.company_id,
                     s.employee_id
            )
        """)

hr_expense_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
