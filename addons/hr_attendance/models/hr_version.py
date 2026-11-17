# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain

# the fields of a version that change the hours expected from its employee
_EXPECTED_HOURS_FIELDS = frozenset({'resource_calendar_id', 'date_version'})


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = 'hr.version'

    attendance_based = fields.Boolean(
        string="Attendance Based",
        help="When enabled, payslips are computed from badge records rather than "
             "the employee's work schedule. Time off is always accounted for.",
        groups="hr.group_hr_user",
        default=lambda self: self.env.company.sudo().attendance_based,
    )

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
        """Recompute the issues of the days of the attendances after a change of schedule. The days left without
        issue get reviewed, as after any change of their day, see ``hr.attendance._auto_review``."""
        if attendances:
            attendances.with_context(skip_time_rules=False)._recompute_same_day_issues()._auto_review()

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
    def _get_whitelist_fields_from_template(self):
        """Also copy ``attendance_based`` from contract templates."""
        return super()._get_whitelist_fields_from_template() + ['attendance_based']

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
