# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    holiday_id = fields.Many2one("hr.leave", string='Time Off Request', copy=False)
    global_leave_id = fields.Many2one("resource.calendar.leaves", string="Global Time Off", ondelete='cascade')
    task_id = fields.Many2one(domain="[('company_id', '=', company_id), ('project_id.allow_timesheets', '=', True),"
        "('project_id', '=?', project_id), ('is_timeoff_task', '=', False)]")

    def _get_redirect_action(self):
        leave_form_view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
        action_data = {
           'name': _('Time Off'),
           'type': 'ir.actions.act_window',
           'res_model': 'hr.leave',
           'views': [(self.env.ref('hr_holidays.hr_leave_view_tree_my').id, 'list'), (leave_form_view_id, 'form')],
           'domain': [('id', 'in', self.holiday_id.ids)],
        }
        if len(self.holiday_id) == 1:
            action_data['views'] = [(leave_form_view_id, 'form')]
            action_data['res_id'] = self.holiday_id.id
        return action_data

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_leave(self):
        if any(line.holiday_id for line in self):
            if not self.env.user.has_group('hr_holidays.group_hr_holidays_user') and self.env.user not in self.holiday_id.sudo().user_id:
                raise UserError(_('You cannot delete timesheets that are linked to time off requests. Please cancel your time off request from the Time Off application instead.'))
            warning_msg = _('You cannot delete timesheets linked to time off. Please, cancel the time off instead.')
            action = self._get_redirect_action()
            raise RedirectWarning(warning_msg, action, _('View Time Off'))

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
