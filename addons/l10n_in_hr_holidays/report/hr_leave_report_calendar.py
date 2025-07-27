# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import ValidationError


class HrLeaveReportCalendar(models.Model):
    _inherit = 'hr.leave.report.calendar'
    before_linked_sandwich_leave_id = fields.Many2one(related='leave_id.before_linked_sandwich_leave_id')
    after_linked_sandwich_leave_id = fields.Many2one(related='leave_id.after_linked_sandwich_leave_id')

    def action_warning_refuse(self):
        current_user = self.env.user
        if current_user.has_group('hr_holidays.group_hr_holidays_user'):
            # If the user is a leave manager, refuse the leave
            return self.leave_id.action_warning_refuse()
        if self.leave_manager_id == current_user and self.sudo().holiday_status_id.leave_validation_type in ('manager', 'both'):
            # If the user is the employee's time off approver, refuse the leave
            return self.sudo().leave_id.sudo(False).action_warning_refuse()
        # If the user is not a leave manager, raise an error
        raise ValidationError(self.env._("You are not allowed to refuse this leave request."))
