# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists


class PayslipReport(models.Model):
    _name = "payslip.report"
    _description = "Payslip Analysis"
    _auto = False

    name = fields.Char(readonly=True)
    date_from = fields.Date(string='Date From', readonly=True)
    date_to = fields.Date(string='Date To', readonly=True)
    year = fields.Char(size=4, readonly=True)
    month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')], readonly=True)
    day = fields.Char(size=128, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Rejected'),
    ], string='Status', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    nbr = fields.Integer(string='# Payslip lines', readonly=True)
    number = fields.Char(readonly=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    paid = fields.Boolean(string='Made Payment Order ? ', readonly=True)
    total = fields.Float(readonly=True)
    category_id = fields.Many2one('hr.salary.rule.category', string='Category', readonly=True)

    @api.model_cr
    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            create or replace view payslip_report as (
                select
                    min(l.id) as id,
                    l.name,
                    p.struct_id,
                    p.state,
                    p.date_from,
                    p.date_to,
                    p.number,
                    p.company_id,
                    p.paid,
                    l.category_id,
                    l.employee_id,
                    sum(l.total) as total,
                    to_char(p.date_from, 'YYYY') as year,
                    to_char(p.date_from, 'MM') as month,
                    to_char(p.date_from, 'YYYY-MM-DD') as day,
                    to_char(p.date_to, 'YYYY') as to_year,
                    to_char(p.date_to, 'MM') as to_month,
                    to_char(p.date_to, 'YYYY-MM-DD') as to_day,
                    1 AS nbr
                from
                    hr_payslip as p
                    left join hr_payslip_line as l on (p.id=l.slip_id)
                where
                    l.employee_id IS NOT NULL
                group by
                    p.number,l.name,p.date_from,p.date_to,p.state,p.company_id,p.paid,
                    l.employee_id,p.struct_id,l.category_id
            )
        """)
