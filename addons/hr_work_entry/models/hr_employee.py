# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

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
