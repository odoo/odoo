# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    '''
    Employee
    '''

    _inherit = 'hr.employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', 'Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslips', groups="base.group_hr_user")

    def _compute_payslip_count(self):
        payslip_data = self.env['hr.payslip'].read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        mapped_data = dict([(m['employee_id'][0], m['employee_id_count']) for m in payslip_data])
        for data in self:
            data.payslip_count = mapped_data.get(data.id, 0)
