# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.intervals import Intervals

# the fields of a version that change the hours expected from its employee
_EXPECTED_HOURS_FIELDS = frozenset({'resource_calendar_id', 'date_version'})


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = 'hr.version'

    work_entry_source = fields.Selection(
        selection_add=[('attendance', 'Attendances')])

    def has_static_work_entries(self):
        """Attendance based versions with a flexible schedule have no static work entries:
        their worked time comes from the working time leaves of their attendances. With another
        schedule, the schedule gives the worked time and the leaves only the difference.

        :rtype: bool
        """
        return (self.work_entry_source != 'attendance' or not self._is_flexible()) and super().has_static_work_entries()

    def _get_attendance_intervals(self, start_dt, end_dt):
        """Attendance based versions with a flexible schedule have no expected schedule: only
        their leaves give entries."""
        based = self.filtered(lambda v: not v.has_static_work_entries())
        result = super(HrVersion, self - based)._get_attendance_intervals(start_dt, end_dt)
        for version in based:
            result[version.employee_id.resource_id.id] = Intervals()
        return result

    def _get_attendance_manager_domain(self):
        return "[('share', '=', False), ('company_ids', 'in', company_id), ('role', 'in', ['regular_user', 'group_system']), ('all_group_ids', 'in', %s)]" % self.env.ref('hr_attendance.group_hr_attendance_own').id

    attendance_manager_id = fields.Many2one(
        'res.users', store=True, readonly=False, index='btree_not_null',
        string="Attendance Approver",
        compute='_compute_attendance_manager',
        ui_domain=_get_attendance_manager_domain,
        groups="hr_attendance.group_hr_attendance_own,hr_attendance.group_hr_attendance_officer,hr.group_hr_user",
        help="The user set in Attendance will access the attendance of the employee through the dedicated app and will be able to edit them.")

    @api.depends('parent_id')
    def _compute_attendance_manager(self):
        for version in self:
            previous_manager = version._origin.parent_id.user_id
            new_manager = version.parent_id.user_id
            if new_manager and version.attendance_manager_id and version.attendance_manager_id == previous_manager:
                version.attendance_manager_id = new_manager
            elif not version.attendance_manager_id:
                version.attendance_manager_id = False

    @api.model_create_multi
    def create(self, vals_list):
        versions = super().create(vals_list)
        self._recompute_attendance_issues(versions._get_attendances_with_expected_hours())
        return versions

    def write(self, vals):
        if not _EXPECTED_HOURS_FIELDS & vals.keys():
            return super().write(vals)
        attendances_before = self._get_attendances_with_expected_hours()
        res = super().write(vals)
        self._recompute_attendance_issues(attendances_before | self._get_attendances_with_expected_hours())
        return res

    @api.model
    def _recompute_attendance_issues(self, attendances):
        """Recompute the expected hours and the issues of the days of the attendances after a change of schedule. The
        days left without issue get reviewed, as after any change of their day, see ``hr.attendance._auto_review``."""
        if attendances:
            had_issue = attendances.with_context(skip_time_rules=False)._recompute_same_day_issues()
            attendances._search_same_day_attendances()._recompute_expected_hours()
            had_issue._auto_review()

    def _get_attendances_with_expected_hours(self):
        """Return the attendances whose issues depend on the schedule of these versions: the attendances of their
        employees from the start of the versions, widened by a day as the attendances are compared per local day.

        :rtype: hr.attendance
        """
        versions = self.filtered(lambda version: version.employee_id and version.date_version)
        if not versions:
            return self.env['hr.attendance']
        attendances = self.env['hr.attendance'].sudo()
        return attendances.search(
            Domain.OR(
                Domain('employee_id', '=', version.employee_id.id)
                & Domain('check_in', '>', version.date_version - timedelta(days=1))
                for version in versions
            )
            & attendances._get_worked_time_domain()
        )

    @api.model
    def _get_versions_by_employee_and_date(self, employee_dates):
        """Return the active version of each employee on each date.

        :param dict employee_dates: ``{employee: iterable of dates}``
        :return: ``{employee: {date: version}}``; a date before the first version of the
            employee gets the first version, an employee without version an empty dict
        :rtype: dict
        """
        # for `employee_dates` a dict[employee] -> dates
        # Generate a 2 level dict[employee][date] -> version
        employees = self.env['hr.employee'].union(employee_dates.keys())
        all_dates = [date for dates in employee_dates.values() for date in dates]
        if not all_dates:
            return {}
        date_to = max(all_dates)
        all_versions = self.env['hr.version'].search([
            ('employee_id', 'in', employees.ids),
            ('active', '=', True),
            ('date_version', '<=', date_to),
        ])
        versions_by_employee = all_versions.grouped('employee_id')
        version_by_employee_and_date = {employee: {} for employee in employees}

        for employee, dates in employee_dates.items():
            if not (versions := versions_by_employee.get(employee)):
                continue
            version_index = 0
            for date in sorted(dates):
                if version_index + 1 < len(versions) and date >= versions[version_index + 1].date_version:
                    version_index += 1
                version_by_employee_and_date[employee][date] = versions[version_index]
        return version_by_employee_and_date
