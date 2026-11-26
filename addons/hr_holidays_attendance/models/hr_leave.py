# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    attendance_id = fields.Many2one(
        'hr.attendance', string="Attendance", index='btree_not_null', readonly=True,
        help="Validated attendance this time off is generated from: its copy for the attendance "
             "based employees with a flexible schedule, or a time rule output for the others.")

    def _compute_date_from_to(self):
        """The time off of attendances keep the dates they are created with, seconds included."""
        attendance_leaves = self.filtered('attendance_id')
        super(HrLeave, self - attendance_leaves)._compute_date_from_to()
        for leave in attendance_leaves:
            leave.date_from = leave._origin.date_from
            leave.date_to = leave._origin.date_to

    def _get_generated_leave_domain(self):
        """Also the working time leaves of attendances."""
        return super()._get_generated_leave_domain() | Domain('attendance_id', '!=', False)

    def _get_source_extra_fields_domain(self):
        """The leaves covering the difference between the attendances and a fixed schedule are
        not time rule sources: only those of flexible schedules are split."""
        return super()._get_source_extra_fields_domain() + [
            '|', ('attendance_id', '=', False), ('resource_calendar_id.calendar_type', '=', 'undefined'),
        ]

    def _get_time_rule_output_vals(self, rule, df, dt, pp):
        """The outputs of the working time of an attendance belong to the attendance."""
        return {**super()._get_time_rule_output_vals(rule, df, dt, pp), 'attendance_id': self.attendance_id.id}

    def _get_time_rule_remainder_vals(self, df, dt):
        """The remainders of the working time of an attendance belong to the attendance."""
        return {**super()._get_time_rule_remainder_vals(df, dt), 'attendance_id': self.attendance_id.id}

    def _get_durations(self, check_work_entry_type=True, resource_calendar=None, additional_domain=None):
        """The time rule outputs of an attendance last the hours of the attendance they cover,
        whatever the schedule."""
        outputs = self.filtered(lambda leave: leave.attendance_id and leave.time_rule_id and leave.date_from and leave.date_to)
        result = super(HrLeave, self - outputs)._get_durations(check_work_entry_type, resource_calendar, additional_domain)
        for leave in outputs:
            hours = (leave.date_to - leave.date_from).total_seconds() / 3600
            calendar = resource_calendar or leave.resource_calendar_id
            result[leave.id] = (hours / (calendar.hours_per_day or HOURS_PER_DAY), hours)
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        """The working time of attendances and its time rule outputs follow the attendance,
        whatever the user rights."""
        return super(HrLeave, self.filtered(
            lambda leave: not leave.attendance_id and not leave.source_leave_id.attendance_id,
        ))._unlink_if_correct_states()

    def _compute_display_name(self):
        """Name the time off produced by a time rule ``<type> <duration>``, e.g.
        ``Overtime 1h30``."""
        super()._compute_display_name()
        for leave in self.filtered('time_rule_id'):
            if not (leave.date_from and leave.date_to):
                continue
            total_seconds = (leave.date_to - leave.date_from).total_seconds()
            h, rem = divmod(int(total_seconds), 3600)
            m = rem // 60
            duration = f'{h}h{m:02d}' if m else f'{h}h'
            leave.display_name = f'{leave.work_entry_type_id.name} {duration}'.strip()
