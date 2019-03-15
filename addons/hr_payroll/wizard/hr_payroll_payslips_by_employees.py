# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    def _get_available_contracts_domain(self):
        return [('contract_ids.state', 'in', ('open', 'pending', 'close')), ('company_id', '=', self.env.user.company_id.id)]

    def _get_employees(self):
        return self.env['hr.employee'].search(self._get_available_contracts_domain())

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                    domain=lambda self: self._get_available_contracts_domain(),
                                    default=lambda self: self._get_employees(), required=True)

    @api.multi
    def compute_sheet(self):
        self.ensure_one()
        if not self.env.context.get('active_id'):
            from_date = fields.Date.to_date(self.env.context.get('default_date_start'))
            end_date = fields.Date.to_date(self.env.context.get('default_date_end'))
            payslip_run = self.env['hr.payslip.run'].create({
                'name': from_date.strftime('%B %Y'),
                'date_start': from_date,
                'date_end': end_date,
            })
        else:
            payslip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))

        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))

        payslips = self.env['hr.payslip']
        Payslip = self.env['hr.payslip']
        for employee in self.employee_ids.filtered(lambda e: not e.has_non_validated_work_entries(payslip_run.date_start, payslip_run.date_end)):
            values = Payslip.default_get(Payslip.fields_get())
            values.update({
                'employee_id': employee.id,
                'credit_note': payslip_run.credit_note,
                'payslip_run_id': payslip_run.id,
                'date_from': payslip_run.date_start,
                'date_to': payslip_run.date_end,
            })
            for contract in employee._get_contracts(payslip_run.date_start, payslip_run.date_end, states=['open', 'pending', 'close']):
                values.update({
                    'contract_id': contract.id,
                    'struct_id': contract.structure_type_id.default_struct_id.id,
                })
                payslip = self.env['hr.payslip'].new(values)
                payslip.onchange_employee()
                payslip._onchange_struct_id()
                values = payslip._convert_to_write(payslip._cache)
                payslips += Payslip.create(values)
        payslips.compute_sheet()
        payslip_run.state = 'verify'

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run',
            'view_type': 'form',
            'views': [[False, 'form']],
            'res_id': payslip_run.id,
        }
