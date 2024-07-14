# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    currency_id = fields.Many2one(
        "res.currency",
        string='Currency',
        related='company_id.currency_id')
    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="hr_payroll.group_hr_payroll_user")
    registration_number = fields.Char('Registration Number of the Employee', groups="hr.group_hr_user", copy=False)
    salary_attachment_ids = fields.Many2many(
        'hr.salary.attachment',
        string='Salary Attachments',
        groups="hr_payroll.group_hr_payroll_user")
    salary_attachment_count = fields.Integer(
        compute='_compute_salary_attachment_count', string="Salary Attachment Count",
        groups="hr_payroll.group_hr_payroll_user")
    mobile_invoice = fields.Binary(string="Mobile Subscription Invoice", groups="hr_contract.group_hr_contract_manager")
    sim_card = fields.Binary(string="SIM Card Copy", groups="hr_contract.group_hr_contract_manager")
    internet_invoice = fields.Binary(string="Internet Subscription Invoice", groups="hr_contract.group_hr_contract_manager")
    is_non_resident = fields.Boolean(string='Non-resident', help='If recipient lives in a foreign country', groups="hr.group_hr_user")

    _sql_constraints = [
        ('unique_registration_number', 'UNIQUE(registration_number, company_id)', 'No duplication of registration numbers is allowed')
    ]

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)

    def _compute_salary_attachment_count(self):
        for employee in self:
            employee.salary_attachment_count = len(employee.salary_attachment_ids)
