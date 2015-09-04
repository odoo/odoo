# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, tools

import openerp.addons.decimal_precision as dp


class HrExpenseReport(models.Model):
    _name = "hr.expense.report"
    _description = "Expenses Statistics"
    _auto = False
    _rec_name = 'date'

    date = fields.Date(readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Force Journal', readonly=True)
    product_qty = fields.Float(string='Total Quantity', readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee's Name", readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    price_total = fields.Float(string='Total Price', readonly=True, digits=0)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Contract', readonly=True, oldname='analytic_account')
    price_average = fields.Float(string='Average Price', readonly=True, digits=0)
    nbr = fields.Integer(string='# of Expenses', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Waiting Payment'),
        ('done', 'Paid'),
        ('cancel', 'Refused')], readonly=True)

    _order = 'date desc'
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'hr_expense_report')
        cr.execute("""
            CREATE OR REPLACE VIEW hr_expense_report AS (
                SELECT
                    MIN(e.id) AS id,
                    e.date AS date,
                    e.create_date AS create_date,
                    e.employee_id,
                    e.journal_id,
                    e.currency_id,
                    e.department_id,
                    e.product_id AS product_id,
                    e.analytic_account_id AS analytic_account_id,
                    SUM(e.quantity * u.factor) AS product_qty,
                    e.company_id AS company_id,
                    SUM(e.quantity * e.unit_amount) AS price_total,
                    (SUM(e.quantity * e.unit_amount) / SUM(CASE WHEN e.quantity=0 OR u.factor=0 THEN 1 ELSE e.quantity * u.factor END))::DECIMAL(16,2) AS price_average,
                    COUNT(*) AS nbr,
                    e.state
                FROM hr_expense e
                LEFT JOIN product_uom u ON (u.id=e.product_uom_id)
                GROUP BY
                    e.date,
                    e.create_date,
                    e.product_id,
                    e.analytic_account_id,
                    e.currency_id,
                    e.department_id,
                    e.product_uom_id,
                    e.id,
                    e.state,
                    e.journal_id,
                    e.company_id,
                    e.employee_id
            )
        """)
