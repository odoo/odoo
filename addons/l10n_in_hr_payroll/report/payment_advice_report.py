# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists


class PaymentAdviceReport(models.Model):
    _name = "payment.advice.report"
    _description = "Payment Advice Analysis"
    _auto = False

    name = fields.Char(readonly=True)
    date = fields.Date(readonly=True)
    year = fields.Char(readonly=True)
    month = fields.Selection([('01', 'January'), ('02', 'February'), ('03', 'March'), ('04', 'April'),
        ('05', 'May'), ('06', 'June'), ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')], readonly=True)
    day = fields.Char(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
    ], string='Status', index=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    nbr = fields.Integer(string='# Payment Lines', readonly=True)
    number = fields.Char(readonly=True)
    bysal = fields.Float(string='By Salary', readonly=True)
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    cheque_nos = fields.Char(string='Cheque Numbers', readonly=True)
    neft = fields.Boolean(string='NEFT Transaction', readonly=True)
    ifsc_code = fields.Char(string='IFSC Code', readonly=True)
    employee_bank_no = fields.Char(string='Employee Bank Account', required=True)

    @api.model_cr
    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            create or replace view payment_advice_report as (
                select
                    min(l.id) as id,
                    sum(l.bysal) as bysal,
                    p.name,
                    p.state,
                    p.date,
                    p.number,
                    p.company_id,
                    p.bank_id,
                    p.chaque_nos as cheque_nos,
                    p.neft,
                    l.employee_id,
                    l.ifsc_code,
                    l.name as employee_bank_no,
                    to_char(p.date, 'YYYY') as year,
                    to_char(p.date, 'MM') as month,
                    to_char(p.date, 'YYYY-MM-DD') as day,
                    1 as nbr
                from
                    hr_payroll_advice as p
                    left join hr_payroll_advice_line as l on (p.id=l.advice_id)
                where
                    l.employee_id IS NOT NULL
                group by
                    p.number,p.name,p.date,p.state,p.company_id,p.bank_id,p.chaque_nos,p.neft,
                    l.employee_id,l.advice_id,l.bysal,l.ifsc_code, l.name
            )
        """)
