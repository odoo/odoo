# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, models, fields

from odoo.addons.hr.models.hr_version import format_date_abbr


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = 'hr.version'

    @api.model
    def _domain_current_countries(self):
        return ['|',
            ('country_id', '=', False),
            ('country_id', 'in', self.env.companies.country_id.ids),
        ]

    def _default_ruleset_id(self):
        country_ruleset = self.env['hr.attendance.overtime.ruleset'].sudo().search([
            ('country_id', 'in', self.env.companies.country_id.ids),
        ], limit=1).sudo(False)
        if country_ruleset:
            return country_ruleset
        return self.env.ref('hr_attendance.hr_attendance_default_ruleset', raise_if_not_found=False)

    ruleset_id = fields.Many2one(
         "hr.attendance.overtime.ruleset",
         domain=_domain_current_countries,
         groups="hr.group_hr_manager",
         tracking=True,
         index='btree_not_null',
         default=_default_ruleset_id,
    )

    def write(self, vals):
        """Track field changes and log them to the employees"""
        tracked_field_names = {fname for fname in self._track_get_fields() if fname in vals}
        if tracked_field_names:
            for version in self:
                employee = version.employee_id
                if not employee:
                    continue
                employee._track_record(
                    version, tracked_field_names,
                )
                version_sudo = employee.version_id.sudo()
                start = format_date_abbr(self.env, version_sudo.date_start) if version_sudo.date_start else False
                end = format_date_abbr(self.env, version_sudo.date_end) if version_sudo.date_end else False
                if start and end:
                    msg = self.env._("Modified from %(start)s to %(end)s") % {'start': start, 'end': end}
                elif start:
                    msg = self.env._("Modified from %s") % (start)
                else:
                    msg = self.env._("Modified")
                employee._track_set_log_message_for_target(Markup("<b>%s</b>") % msg, version)
        return super().write(vals)

    @api.model
    def _get_versions_by_employee_and_date(self, employee_dates):
        # for `employee_dates` a dict[employee] -> dates
        # Generate a 2 level dict[employee][date] -> version
        employees = self.env['hr.employee'].union(employee_dates.keys())
        all_dates = [date for dates in employee_dates.values() for date in dates]
        if not all_dates:
            return {}
        date_to = max(all_dates)
        all_versions = self.env['hr.version'].search([
            ('employee_id', 'in', employees.ids),
            ('date_version', '<=', date_to),
            # note: no check on date_from because we don't store the version date end
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
