# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrHeadcountLine(models.Model):
    _name = 'hr.headcount.line'
    _description = 'Headcount Line'

    headcount_id = fields.Many2one('hr.headcount', string='headcount_id', required=True, index=True, ondelete='cascade')
    working_rate_ids = fields.Many2many('hr.headcount.working.rate', required=True, string='Working Rate')
    version_id = fields.Many2one('hr.version', string='Employee Record', required=True, index=True, readonly=True)
    department_id = fields.Many2one(related='version_id.department_id', string='Department')
    job_id = fields.Many2one(related='version_id.job_id', string='Job Title')
    currency_id = fields.Many2one(related='version_id.currency_id', string='Currency')
    wage_on_payroll = fields.Monetary(string='Wage On Payroll', currency_field='currency_id', compute='_compute_wage_on_payroll',
        groups='hr.group_hr_manager')
    employee_id = fields.Many2one(related="version_id.employee_id", required=True, readonly=True)
    employee_type = fields.Many2one(related='version_id.employee_type_id', string='Employee Type')

    @api.depends('version_id')
    def _compute_wage_on_payroll(self):
        for line in self:
            line.wage_on_payroll = line.version_id._get_contract_wage()
