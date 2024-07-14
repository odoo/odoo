# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    wage_type = fields.Selection(related='contract_id.wage_type', readonly=True)
    payslips_count = fields.Integer("# Payslips", compute='_compute_payslips_count', groups="hr_payroll.group_hr_payroll_user")
    salary_attachment_count = fields.Char(compute='_compute_salary_attachment_count', groups="hr_payroll.group_hr_payroll_user")

    def _compute_payslips_count(self):
        for history in self:
            history.payslips_count = sum(contract.payslips_count for contract in history.contract_ids)

    @api.depends('employee_id.salary_attachment_count')
    def _compute_salary_attachment_count(self):
        for history in self:
            if history.employee_id.salary_attachment_count > 0:
                history.salary_attachment_count = str(history.employee_id.salary_attachment_count)
            else:
                history.salary_attachment_count = _('New')

    def action_open_payslips(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_payroll.action_view_hr_payslip_month_form")
        action.update({'domain': [('contract_id', 'in', self.contract_ids.ids)]})
        return action

    def action_open_salary_attachments(self):
        self.ensure_one()
        if self.employee_id.salary_attachment_count == 0:
            action = {
                'name': _('Salary Attachment'),
                'res_model': 'hr.salary.attachment',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_employee_id': self.employee_id.id,
                }
            }
        else:
            action = self.env['ir.actions.actions']._for_xml_id('hr_payroll.hr_salary_attachment_action')
            action.update({'context': {
                'search_default_employee_id': self.employee_id.id,
                'default_employee_id': self.employee_id.id,
            }})
        return action
