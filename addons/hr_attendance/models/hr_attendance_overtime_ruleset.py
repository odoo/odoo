# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields


#TODO move HrVersion + Select Employees wizard or widget
class HrVersion(models.Model):
    _name='hr.version'
    _inherit='hr.version'

    ruleset_id = fields.Many2one("hr.attendance.overtime.ruleset")

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
            ('employee_id', 'in', employees.id),
            ('date_version', '<=', date_to),
            # note: no check on date_from because we don't store the version date end
        ])
        versions_by_employee = all_versions.grouped('employee_id')
        version_by_employee_and_date = {employee: {} for employee in employees}

        for employee, dates in employee_dates.items():
            if not (versions := versions_by_employee[employee]):
                continue
            version_index = 0
            for date in sorted(dates):
                if version_index + 1 < len(versions) and date >= versions[version_index+1].date_version:
                    version_index += 1
                version_by_employee_and_date[employee][date] = versions[version_index]
        return version_by_employee_and_date


class HrAttendanceOvertimeRuleset(models.Model):
    _name = 'hr.attendance.overtime.ruleset'
    _description = "Overtime Ruleset"

    name = fields.Char()
    description = fields.Html()
    rule_ids = fields.One2many('hr.attendance.overtime.rule', 'ruleset_id')
    version_ids = fields.One2many('hr.version', 'ruleset_id')
    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.company.country_id,
        #groups='base.group_multi_company',
    )
    combine_overtime_rates = fields.Selection([
            ('max', "Max"),
            ('sum', "Sum"),
        ],
        required=True,
        default='max',
        string="Rate Combination Mode",
        help="Controls how the rates from the different rules that apply are combined",
    )
