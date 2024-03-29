# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    has_work_entries = fields.Boolean(compute='_compute_has_work_entries')

    def _compute_has_work_entries(self):
        self.env.cr.execute("""
        SELECT id, EXISTS(SELECT 1 FROM hr_work_entry WHERE employee_id = e.id limit 1)
          FROM hr_employee e
         WHERE id in %s
        """, (tuple(self.ids), ))

        result = {eid[0]: eid[1] for eid in self.env.cr.fetchall()}

        for employee in self:
            employee.has_work_entries = result.get(employee.id, False)

    def action_open_work_entries(self, initial_date=False):
        self.ensure_one()
        ctx = {'default_employee_id': self.id}
        if initial_date:
            ctx['initial_date'] = initial_date
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s work entries', self.display_name),
            'view_mode': 'calendar,tree,form',
            'res_model': 'hr.work.entry',
            'context': ctx,
            'domain': [('employee_id', '=', self.id)],
        }
