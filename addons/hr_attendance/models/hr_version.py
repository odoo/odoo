# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.fields import Domain


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

    has_ruleset_id = fields.Boolean(compute="_compute_has_ruleset_id", groups="hr.group_hr_user")

    @api.depends("ruleset_id")
    def _compute_has_ruleset_id(self):
        for version in self:
            version.has_ruleset_id = version.ruleset_id

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

    def action_open_version_selector(self):
        action = self.env['ir.actions.act_window']._for_xml_id('hr_attendance.hr_version_list_view_add')
        ruleset_id = self.env.context.get('default_ruleset_id', False)
        action['domain'] = Domain.AND([[("ruleset_id", "!=", ruleset_id)], self.env["hr.version"]._get_current_versions_domain()])
        action['context'] = {'default_ruleset_id': ruleset_id}
        return action

    def action_unassign_ruleset(self):
        self.ruleset_id = False

    def action_assign_ruleset(self):
        ruleset_id = self.env.context.get('default_ruleset_id', False)
        if not ruleset_id:
            return

        self.ruleset_id = ruleset_id
