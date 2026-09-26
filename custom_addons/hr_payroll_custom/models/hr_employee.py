from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    slip_ids = fields.One2many('custom.payroll.slip', 'employee_id', string='Payslips')
    slip_count = fields.Integer(string='Payslip Count', compute='_compute_slip_count')

    def _compute_slip_count(self):
        for rec in self:
            rec.slip_count = len(rec.slip_ids)

    def action_view_slips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslips',
            'res_model': 'custom.payroll.slip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
