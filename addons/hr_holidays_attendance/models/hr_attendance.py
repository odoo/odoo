# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    leave_ids = fields.One2many('hr.leave', 'attendance_id')

    # The source leave
    work_time_leave_id = fields.Many2one(
        'hr.leave',
        compute='_compute_work_time_leave_id',
        string="Work-Time Leave",
        copy=False,
    )
    # Output leaves created by time rules for this attendance interval
    overtime_leave_ids = fields.Many2many(
        'hr.leave',
        compute='_compute_overtime_leave_ids',
        string="Overtime Leaves",
    )

    @api.depends('leave_ids', 'leave_ids.source_leave_id')
    def _compute_work_time_leave_id(self):
        for att in self:
            att.work_time_leave_id = att.leave_ids.filtered(lambda l: not l.source_leave_id)[:1]

    @api.depends('leave_ids', 'leave_ids.is_time_rule_output')
    def _compute_overtime_leave_ids(self):
        for att in self:
            att.overtime_leave_ids = att.leave_ids.filtered('is_time_rule_output')

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_attendance_check_in_check_out_employee_id
            ON hr_attendance (check_in, check_out, employee_id);
        """)

    # -------------------------------------------------------------------------
    # work-time leave sync
    # -------------------------------------------------------------------------

    def _sync_work_time_leave(self):
        """Create, update, or delete the work-time hr.leave linked to each attendance."""
        Leave = self.env['hr.leave'].sudo()
        auto_ctx = dict(
            leave_skip_date_check=True,
            leave_skip_state_check=True,
            leave_fast_create=True,
            tracking_disable=True,
            mail_activity_automation_skip=True,
        )
        for company, company_atts in self.grouped(lambda a: a.employee_id.company_id).items():
            work_entry_type = company.attendance_work_entry_type_id
            if not work_entry_type:
                continue

            to_create = []
            for att in company_atts:
                if not att.check_out:
                    att.work_time_leave_id.with_context(skip_time_rules=True).unlink()
                    continue

                tz = ZoneInfo(att.employee_id.tz or 'UTC')
                vals = {
                    'employee_id': att.employee_id.id,
                    'work_entry_type_id': work_entry_type.id,
                    'attendance_id': att.id,
                    'date_from': att.check_in,
                    'date_to': att.check_out,
                    'request_date_from': att.check_in.replace(tzinfo=UTC).astimezone(tz).date(),
                    'request_date_to': att.check_out.replace(tzinfo=UTC).astimezone(tz).date(),
                    'state': 'validate',
                }
                if att.work_time_leave_id:
                    att.work_time_leave_id.with_context(**auto_ctx).write(
                        {k: v for k, v in vals.items() if k != 'state'}
                    )
                else:
                    to_create.append(vals)

            if to_create:
                Leave.with_context(**auto_ctx).create(to_create)

    # -------------------------------------------------------------------------
    # create / write / unlink hooks
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._sync_work_time_leave()
        return res

    def write(self, vals):
        result = super().write(vals)
        if any(f in vals for f in ('employee_id', 'check_in', 'check_out')):
            self._sync_work_time_leave()
        return result

    def _get_employee_calendar(self):
        self.ensure_one()
        versions = self.employee_id.sudo()._get_versions_with_contract_overlap_with_period(
            self.check_in.date(), self.check_out.date()
        )
        if versions:
            return versions[0].resource_calendar_id
        return super()._get_employee_calendar()

    @api.ondelete(at_uninstall=False)
    def _unlink_leave_ids(self):
        self.leave_ids.with_context(skip_time_rules=True).unlink()
