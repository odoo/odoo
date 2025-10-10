# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class HrVersion(models.Model):
    _name = 'hr.version'
    _inherit = 'hr.version'

    @api.model
    def _domain_current_countries(self):
        return ['|',
            ('country_id', '=', False),
            ('country_id', 'in', self.env.companies.country_id.ids),
        ]

    ruleset_id = fields.Many2one(
         "hr.attendance.overtime.ruleset",
         domain=_domain_current_countries,
         groups="hr.group_hr_manager",
         tracking=True,
         compute="_compute_ruleset",
         store=True,
         readonly=False,
    )

    @api.depends('country_id', 'employee_id')
    def _compute_ruleset(self):
        default_ruleset_country = {}
        for version in self:
            if not version.employee_id:
                version.ruleset_id = False
                continue

            ruleset = version.ruleset_id
            version_country = version.employee_id.company_id.country_id
            if not ruleset or (ruleset.country_id != version_country
                and (not version.employee_id.company_id.country_id or ruleset.country_id)):
                default_ruleset = default_ruleset_country.get(version_country.id)
                if default_ruleset is None:
                    if version_country:
                        default_ruleset = default_ruleset_country[version_country.id] = \
                            self.env['hr.attendance.overtime.ruleset'].search([('country_id', '=', version_country.id)], limit=1)
                    if default_ruleset is None:
                        default_ruleset = default_ruleset_country[version_country.id if version_country else False] = \
                            self.env['hr.attendance.overtime.ruleset'].search([('country_id', '=', False)], limit=1)

                version.ruleset_id = default_ruleset

    @api.model
    def _get_versions_by_employee_and_date(self, employee_dates):
        # for `employee_dates` a dict[employee] -> dates
        # Generate a 2 level dict[employee][date] -> version
        employees = self.env['hr.employee'].union(*employee_dates.keys())
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
