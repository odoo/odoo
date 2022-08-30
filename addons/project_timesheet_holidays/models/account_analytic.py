# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Leave Request', copy=False)
    global_leave_id = fields.Many2one("resource.calendar.leaves", string="Global Time Off", ondelete='cascade')
    task_id = fields.Many2one(domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True),"
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

    def write(self, vals):
        if not self.env.su and self.filtered('holiday_id'):
            raise UserError(_('You cannot modify timesheets that are linked to time off requests. Please use the Time Off application to modify your time off requests instead.'))
        return super().write(vals)
