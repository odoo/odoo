# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', string='Employees')

    @api.multi
    def compute_sheet(self):
        HrPayslip = self.env['hr.payslip']
        HrPayslipRun = self.env['hr.payslip.run']
        if self.env.context.get('active_id'):
            HrPayslipRun = HrPayslipRun.browse(self.env.context['active_id'])
        start_date = fields.Date.from_string(fields.Datetime.now()) + relativedelta(day=1)
        end_date = fields.Date.from_string(fields.Datetime.now()) + relativedelta(months=1, day=1, days=-1)
        from_date = HrPayslipRun.date_start or start_date
        to_date = HrPayslipRun.date_end or end_date
        credit_note = HrPayslipRun.credit_note or False
        if self.filtered(lambda x: not x.employee_ids):
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for emp in self.mapped('employee_ids'):
            res = {
                'employee_id': emp.id,
                'payslip_run_id': self.env.context.get('active_id'),
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': credit_note,
            }
            payslip = HrPayslip.create(res)
            payslip.onchange_employee_id_wrapper()
            HrPayslip |= payslip
        HrPayslip.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}
