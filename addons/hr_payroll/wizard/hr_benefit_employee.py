# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.benefit.employees'
    _description = 'Generate benefits for all selected employees'

    def _get_domain(self):
        return [('contract_ids.state', 'in', ('open', 'pending')), ('company_id', '=', self.env.user.company_id.id)]

    employee_ids = fields.Many2many('hr.employee', string='Employees', domain=lambda self: self._get_domain())


    def generate_benefit(self):
        if not self.employee_ids:
            raise UserError(_("You must select employee(s) to generate benefits."))
        date_start = self.env.context.get('start_benefits')
        date_stop = self.env.context.get('stop_benefits')

        date_start = fields.Datetime.from_string(date_start)
        date_stop = fields.Datetime.from_string(date_stop)
        self.employee_ids.generate_benefit(date_start, date_stop)
