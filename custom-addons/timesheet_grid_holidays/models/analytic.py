# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError


class AnalyticLine(models.Model):
    _name = 'account.analytic.line'
    _inherit = ['account.analytic.line']

    def _should_not_display_timer(self):
        self.ensure_one()
        return super()._should_not_display_timer() or self.task_id.is_timeoff_task

    def action_merge_timesheets(self):
        if self.holiday_id:
            if not self.env.user.has_group('hr_holidays.group_hr_holidays_user') and self.env.user not in self.holiday_id.sudo().user_id:
                raise UserError(_('You cannot merge timesheets that are linked to time off requests. Please use the Time Off application to modify or cancel your time off requests instead.'))
            warning_msg = _('You cannot merge timesheets that are linked to time off requests. Please use the Time Off application to modify or cancel your time off requests instead.')
            action = self._get_redirect_action()
            raise RedirectWarning(warning_msg, action, _('View Time Off'))
        return super().action_merge_timesheets()

    @api.model
    def grid_update_cell(self, domain, measure_field_name, value):
        return super().grid_update_cell(
            expression.AND([domain, [('holiday_id', '=', False)]]),
            measure_field_name,
            value,
        )

    def action_timer_start(self):
        if self.task_id.is_timeoff_task:
            raise UserError(_('You cannot start a timer for a task that is linked to a time off request. To request additional time off, please use the Time Off application.'))
        return super().action_timer_start()
