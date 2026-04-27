# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class Project(models.Model):
    _name = 'project.project'
    _inherit = ["project.project", "timesheet.grid.mixin"]

    def check_can_start_timer(self):
        self.ensure_one()
        if self.sudo().company_id.timesheet_encode_uom_id == self.env.ref('uom.product_uom_day'):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('You cannot start the timer for a project in a company encoding its timesheets in days.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }
        return True

    def write(self, values):
        result = super(Project, self).write(values)
        if 'allow_timesheets' in values and not values['allow_timesheets']:
            self.env['timer.timer'].search([
                ('res_model', '=', "project.task"),
                ('res_id', 'in', self.with_context(active_test=False).task_ids.ids)
            ]).unlink()
        return result

    def get_allocated_hours_field(self):
        return 'allocated_hours'

    def get_worked_hours_fields(self):
        return ['total_timesheet_time']
