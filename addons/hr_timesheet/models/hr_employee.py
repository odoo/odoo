# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timesheet_cost = fields.Monetary('Cost', currency_field='currency_id',
    	groups="hr.group_hr_user", default=0.0)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    def name_get(self):
        res = super().name_get()
        if len(self.env.context.get('allowed_company_ids', [])) <= 1:
            return res
        name_mapping = dict(res)
        employee_read_group = self.env['hr.employee'].sudo()._read_group(
            [('user_id', 'in', self.user_id.ids)],
            ['user_id'],
            ['user_id'],
        )
        employees_count_per_user = {res['user_id'][0]: res['user_id_count'] for res in employee_read_group}
        for employee in self:
            if employees_count_per_user.get(employee.user_id.id, 0) > 1:
                name_mapping[employee.id] = f'{name_mapping[employee.id]} - {employee.company_id.name}'
        return list(name_mapping.items())
