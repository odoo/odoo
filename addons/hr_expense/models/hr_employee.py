# -*- coding: utf-8 -*-

from openerp import api, fields, models

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    expenses_amount = fields.Float(compute='_expenses_amount', string='Expenses', digits=0)

    @api.multi
    def _expenses_amount(self):
        sheet = self.env['hr.expense.sheet'].read_group([('employee_id', 'in', self.ids), ('state', '=', 'confirm')], ['employee_id', 'amount'], ['employee_id'])
        result = dict((data['employee_id'][0], data['amount']) for data in sheet)
        for employee in self:
            employee.expenses_amount = result.get(employee.id, 0)
