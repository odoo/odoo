# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import models, _


class HrEmployee(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_us_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
            ])]

    def _l10n_us_get_leave_lines(self):
        self.ensure_one()
        leaves_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('date_from', '<', self.date_to),
            '|',
            ('date_to', '=', False),
            ('date_to', '>', self.date_from),
        ])
        if not leaves_allocations:
            return []

        day_before_period = self.date_from + relativedelta(days=-1)
        before_period_durations_by_leave_type = self.env['hr.work.entry']._get_leaves_duration_between_two_dates(
            self.employee_id, min(leaves_allocations.mapped('date_from')), day_before_period)
        period_durations_by_leave_type = self.env['hr.work.entry']._get_leaves_duration_between_two_dates(
            self.employee_id, self.date_from, self.date_to)

        # Only get the leave types associated to valid allocations
        leave_types = leaves_allocations.holiday_status_id
        leave_lines = []
        for leave_type in leave_types.filtered(lambda h: h.l10n_us_show_on_payslip):
            related_allocations = leaves_allocations.filtered(lambda a: a.holiday_status_id == leave_type)

            allocated_before = related_allocations._l10n_us_get_total_allocated(day_before_period)
            allocated_now = related_allocations._l10n_us_get_total_allocated(self.date_to)

            total_used_before = before_period_durations_by_leave_type.get(leave_type, 0.0)
            used = period_durations_by_leave_type.get(leave_type, 0.0)

            gain = allocated_now - allocated_before
            balance = allocated_now - total_used_before - used

            leave_lines.append({
                'type': leave_type.name,
                'used': used,
                'accrual': gain,
                'balance': balance,
            })
        return leave_lines

    # FIXME: this should be removed in master (see https://www.odoo.com/odoo/1251/tasks/3844686)
    def _get_rule_name(self, localdict, rule, employee_lang):
        if self.country_code == 'US' and rule.code == 'GROSS':
            return _('Gross Pay')
        return super()._get_rule_name(localdict, rule, employee_lang)
