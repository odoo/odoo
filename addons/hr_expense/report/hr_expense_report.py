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
from openerp.osv import fields, osv

from openerp.addons.decimal_precision import decimal_precision as dp


class hr_expense_report(osv.osv):
    _name = "hr.expense.report"
    _description = "Expenses Statistics"
    _auto = False
    _rec_name = 'date'
    _columns = {
        'date': fields.date('Date ', readonly=True),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'journal_id': fields.many2one('account.journal', 'Force Journal', readonly=True),
        'product_qty':fields.float('Product Quantity', readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee's Name", readonly=True),
        'date_confirm': fields.date('Confirmation Date', readonly=True),
        'date_valid': fields.date('Validation Date', readonly=True),
        'department_id':fields.many2one('hr.department','Department', readonly=True),
        'company_id':fields.many2one('res.company', 'Company', readonly=True),
        'user_id':fields.many2one('res.users', 'Validation User', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'price_total':fields.float('Total Price', readonly=True, digits_compute=dp.get_precision('Account')),
        'delay_valid':fields.float('Delay to Valid', readonly=True),
        'delay_confirm':fields.float('Delay to Confirm', readonly=True),
        'analytic_account': fields.many2one('account.analytic.account','Analytic account',readonly=True),
        'price_average':fields.float('Average Price', readonly=True, digits_compute=dp.get_precision('Account')),
        'nbr':fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'no_of_products':fields.integer('# of Products', readonly=True),
        'no_of_account':fields.integer('# of Accounts', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('confirm', 'Waiting confirmation'),
            ('accepted', 'Accepted'),
            ('done', 'Done'),
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
                     s.date as date,
                     s.create_date as create_date,
                     s.employee_id,
                     s.journal_id,
                     s.currency_id,
                     s.date_confirm as date_confirm,
                     s.date_valid as date_valid,
                     s.user_valid as user_id,
                     s.department_id,
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
                     s.date,
                     s.create_date,
                     s.date_confirm,
                     s.date_valid,
                     l.product_id,
                     l.analytic_account,
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
