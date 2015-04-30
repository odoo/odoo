# -*- coding: utf-8 -*-

from openerp import tools
from openerp import fields, models

import openerp.addons.decimal_precision as dp


class HrExpenseReport(models.Model):
    _name = "hr.expense.report"
    _description = "Expenses Statistics"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Force Journal', readonly=True)
    product_qty = fields.Float(string='Product Quantity', readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee's Name", readonly=True)
    date_confirm = fields.Date(string='Confirmation Date', readonly=True)
    date_valid = fields.Date(string='Validation Date', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', string='Validation User', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    price_total = fields.Float(string='Total Price', readonly=True, digits=dp.get_precision('Account'))
    delay_valid = fields.Float(string='Delay to Valid', readonly=True)
    delay_confirm = fields.Float(string='Delay to Confirm', readonly=True)
    analytic_account = fields.Many2one('account.analytic.account', string='Analytic account', readonly=True)
    price_average = fields.Float(string='Average Price', readonly=True, digits=dp.get_precision('Account'))
    nbr_lines = fields.Integer(string='# of Lines', readonly=True)
    no_of_products = fields.Integer(string='# of Products', readonly=True)
    no_of_account = fields.Integer(string='# of Accounts', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Waiting confirmation'),
        ('accepted', 'Accepted'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')], readonly=True)


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
                     l.analytic_account_id as analytic_account,
                     sum(l.unit_quantity * u.factor) as product_qty,
                     s.company_id as company_id,
                     sum(l.unit_quantity*l.unit_amount) as price_total,
                     (sum(l.unit_quantity*l.unit_amount)/sum(case when l.unit_quantity=0 or u.factor=0 then 1 else l.unit_quantity * u.factor end))::decimal(16,2) as price_average,
                     count(*) as nbr_lines,
                     (select unit_quantity from hr_expense where id=l.id and product_id is not null) as no_of_products,
                     (select analytic_account_id from hr_expense where id=l.id and analytic_account_id is not null) as no_of_account,
                     s.state
                 from hr_expense l
                 left join hr_expense_sheet s on (s.id=l.expense_id)
                 left join product_uom u on (u.id=l.uom_id)
                 group by
                     s.date,
                     s.create_date,
                     s.date_confirm,
                     s.date_valid,
                     l.product_id,
                     l.analytic_account_id,
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
