# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Leave Request', copy=False)
    global_leave_id = fields.Many2one("resource.calendar.leaves", string="Global Time Off", ondelete='cascade')
    task_id = fields.Many2one(domain="[('allow_timesheets', '=', True),"
        "('project_id', '=?', project_id), ('is_timeoff_task', '=', False)]")

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_leave(self):
        if any(line.holiday_id for line in self):
            raise UserError(_('You cannot delete timesheets that are linked to time off requests. Please cancel your time off request from the Time Off application instead.'))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            task_ids = [vals['task_id'] for vals in vals_list if vals.get('task_id')]
            has_timeoff_task = self.env['project.task'].search_count([('id', 'in', task_ids), ('is_timeoff_task', '=', True)], limit=1) > 0
            if has_timeoff_task:
                raise UserError(_('You cannot create timesheets for a task that is linked to a time off type. Please use the Time Off application to request new time off instead.'))
        return super().create(vals_list)

    def _check_can_update_timesheet(self):
        return self.env.su or not self.filtered('holiday_id')

    def write(self, vals):
        if not self._check_can_update_timesheet():
            raise UserError(_('You cannot modify timesheets that are linked to time off requests. Please use the Time Off application to modify your time off requests instead.'))
        return super().write(vals)

    def _get_favorite_project_id_domain(self, employee_id=False):
        return expression.AND([
            super()._get_favorite_project_id_domain(employee_id),
            [('holiday_id', '=', False), ('global_leave_id', '=', False)],
        ])
