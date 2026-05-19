# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import float_round
from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string="Source Attendance",
        ondelete='cascade',
        index=True,
        copy=False,
        help="The attendance record that generated this leave.",
    )

    def _get_generated_leave_domain(self):
        return super()._get_generated_leave_domain() | Domain('attendance_id', '!=', False)

    def _compute_display_name(self):
        super()._compute_display_name()
        for leave in self.filtered('is_time_rule_output'):
            if not (leave.date_from and leave.date_to):
                continue
            total_seconds = (leave.date_to - leave.date_from).total_seconds()
            h, rem = divmod(int(total_seconds), 3600)
            m = rem // 60
            duration = f'{h}h{m:02d}' if m else f'{h}h'
            leave.display_name = f'{leave.work_entry_type_id.name} {duration}'.strip()

    def _get_durations(self, check_work_entry_type=True, resource_calendar=None, additional_domain=None):
        raw = self.filtered(lambda l: l.attendance_id and l.date_from and l.date_to)
        result = super(HrLeave, self - raw)._get_durations(
            check_work_entry_type=check_work_entry_type,
            resource_calendar=resource_calendar,
            additional_domain=additional_domain,
        )
        for leave in raw:
            hours = (leave.date_to - leave.date_from).total_seconds() / 3600
            calendar = resource_calendar or leave.resource_calendar_id
            hours_per_day = calendar.hours_per_day if calendar else HOURS_PER_DAY
            result[leave.id] = (hours / hours_per_day, hours)
        return result

    @api.depends('attendance_id', 'date_from', 'date_to')
    def _compute_request_hour_from_to(self):
        att_leaves = self.filtered('attendance_id')
        for leave in att_leaves:
            tz = ZoneInfo(leave.employee_id.tz or 'UTC')
            check_in = leave.date_from.replace(tzinfo=UTC).astimezone(tz)
            check_out = leave.date_to.replace(tzinfo=UTC).astimezone(tz)
            leave.request_hour_from = check_in.hour + check_in.minute / 60
            leave.request_hour_to = check_out.hour + check_out.minute / 60
        super(HrLeave, self - att_leaves)._compute_request_hour_from_to()

    @api.depends('attendance_id', 'attendance_id.check_in', 'attendance_id.check_out')
    def _compute_date_from_to(self):
        att_leaves = self.filtered(lambda l: l.attendance_id and not l.source_leave_id)
        for leave in att_leaves:
            if not leave.date_from or not leave.date_to:
                att = leave.attendance_id
                leave.date_from = att.check_in.replace(tzinfo=None) if att.check_in.tzinfo else att.check_in
                leave.date_to = att.check_out.replace(tzinfo=None) if att.check_out.tzinfo else att.check_out
        super(HrLeave, self - att_leaves)._compute_date_from_to()

    def _restore_source_leave_bounds(self, source_leaves, children):
        att_sources = source_leaves.filtered('attendance_id')
        auto_ctx = dict(
            skip_time_rules=True, leave_fast_create=True, leave_skip_date_check=True,
            leave_skip_state_check=True, tracking_disable=True, mail_activity_automation_skip=True,
        )
        writes = defaultdict(list)
        for source in att_sources:
            att = source.attendance_id
            new_df = att.check_in.replace(tzinfo=None) if att.check_in.tzinfo else att.check_in
            new_dt = att.check_out.replace(tzinfo=None) if att.check_out.tzinfo else att.check_out
            if new_df == source.date_from and new_dt == source.date_to:
                continue
            writes[(new_df, new_dt)].append(source.id)
        for (new_df, new_dt), ids in writes.items():
            self.env['hr.leave'].sudo().browse(ids).with_context(**auto_ctx).write({
                'date_from': new_df, 'date_to': new_dt,
                'request_date_from': new_df.date(), 'request_date_to': new_dt.date(),
            })
        super()._restore_source_leave_bounds(source_leaves - att_sources, children)

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
