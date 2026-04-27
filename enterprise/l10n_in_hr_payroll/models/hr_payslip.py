# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import api, models, _
from odoo.tools import format_date, date_utils


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_l10n_in_company_working_time(self, return_hours=False):
        self.ensure_one()
        slip_date_time = datetime.combine(self.date_from, time(12, 0, 0))
        company_work_data = self.company_id.resource_calendar_id.get_work_duration_data(
            date_utils.start_of(slip_date_time, 'month'),
            date_utils.end_of(slip_date_time, 'month'))
        if return_hours:
            return company_work_data['hours']
        return company_work_data['days']

    @api.depends('employee_id', 'struct_id', 'date_from')
    def _compute_name(self):
        super()._compute_name()
        for slip in self.filtered(lambda s: s.country_code == 'IN'):
            lang = slip.employee_id.lang or self.env.user.lang
            payslip_name = slip.struct_id.payslip_name or _('Salary Slip')
            date = format_date(self.env, slip.date_from, date_format="MMMM y", lang_code=lang)
            if slip.number:
                slip.name = '%(payslip_name)s - %(slip_ref)s - %(dates)s' % {
                    'slip_ref': slip.number,
                    'payslip_name': payslip_name,
                    'dates': date
                }
            else:
                slip.name = '%(payslip_name)s - %(dates)s' % {
                    'payslip_name': payslip_name,
                    'dates': date
                }

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_in_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/res_partner_data.xml',
                'data/salary_rules/hr_salary_rule_ind_emp_data.xml',
                'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
                'data/salary_rules/hr_salary_rule_worker_data.xml',
            ])]

    def _get_base_local_dict(self):
        return {**super()._get_base_local_dict(), '_': lambda *a, **kw: self.env._(*a, **kw)}  # pylint: disable=E8502

    def _get_employee_timeoff_data(self):
        return self.env['hr.leave.type'].with_company(self.company_id).with_context(employee_id=self.employee_id.id).get_allocation_data_request()

    def get_month(self):
        from_date = min(self.mapped('date_from'))
        to_date = max(self.mapped('date_to'))
        return {
            'from_name': format_date(self.env, from_date, date_format='long'),
            'to_name': format_date(self.env, to_date, date_format='long')
        }

    def action_payslip_payment_report(self, export_format='advice'):
        action = super().action_payslip_payment_report()
        if self.company_id.country_code != 'IN':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
