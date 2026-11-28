# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if self.env.context.get('salary_simulation'):
            return employees

        # We need to create timesheet entries for the global time off that are already created
        # and are planned for after this employee creation date
        self.with_context(allowed_company_ids=employees.company_id.ids) \
            ._create_future_public_holidays_timesheets(employees)
        return employees

    def write(self, vals):
        if vals.get('active'):
            inactive_emp = self.filtered(lambda e: not e.active)
        result = super().write(vals)
        self_company = self.with_context(allowed_company_ids=self.company_id.ids)
        if 'active' in vals:
            if vals.get('active'):
                # Create future holiday timesheets
                inactive_emp = inactive_emp.with_env(self_company.env)
                inactive_emp._create_future_public_holidays_timesheets(inactive_emp)
            else:
                # Delete future holiday timesheets
                self_company._delete_future_public_holidays_timesheets()
        return result

    def _delete_future_public_holidays_timesheets(self):
        future_timesheets = self.env['account.analytic.line'].sudo().search([('global_leave_id', '!=', False), ('date', '>=', fields.Date.today()), ('employee_id', 'in', self.ids)])
        future_timesheets.write({'global_leave_id': False})
        future_timesheets.unlink()

    def _create_future_public_holidays_timesheets(self, employees):
        timesheets = self.env['account.analytic.line']
        today = fields.Datetime.today()
        for company, company_employees in employees.filtered('active').grouped('company_id').items():
            # The global time off already planned after today, of any working schedule of the employees
            calendars = company_employees.sudo().version_ids.resource_calendar_id | company_employees.resource_calendar_id
            global_leaves = self.env['resource.calendar.leaves'].search([
                ('resource_id', '=', False),
                ('date_from', '>=', today),
                '|',
                    ('calendar_id', 'in', calendars.ids),
                    '&', ('calendar_id', '=', False), ('company_id', '=', company.id),
            ])
            if global_leaves:
                timesheets |= global_leaves._generate_public_time_off_timesheets(company_employees)
        return timesheets
