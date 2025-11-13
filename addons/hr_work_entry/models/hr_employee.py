# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.tools import SQL


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_work_entries = fields.Boolean(compute='_compute_has_work_entries', groups="base.group_system,hr.group_hr_user")

    def _compute_has_work_entries(self):
        if self.ids:
            result = dict(self.env.execute_query(SQL(
                """ SELECT id, EXISTS(SELECT 1 FROM hr_work_entry WHERE employee_id = e.id LIMIT 1)
                      FROM hr_employee e
                     WHERE id in %s """,
                tuple(self.ids),
            )))
        else:
            result = {}

        for employee in self:
            employee.has_work_entries = result.get(employee._origin.id, False)

    def action_open_work_entries(self, initial_date=False):
        self.ensure_one()
        ctx = {'default_employee_id': self.id}
        if initial_date:
            ctx['initial_date'] = initial_date
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s work entries', self.display_name),
            'view_mode': 'calendar,list,form',
            'res_model': 'hr.work.entry',
            'path': 'work-entries',
            'context': ctx,
            'domain': [('employee_id', '=', self.id)],
        }
