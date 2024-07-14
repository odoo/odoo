# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.tools import format_date, date_utils


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    advice_id = fields.Many2one('hr.payroll.advice', string='Bank Advice', copy=False)

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
                'data/salary_rules/hr_salary_rule_ind_emp_data.xml',
                'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
                'data/salary_rules/hr_salary_rule_worker_data.xml',
            ])]

    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        indian_companies = self.env.companies.filtered(lambda c: c.country_id.code == 'IN')
        if indian_companies:
            # Employees Without PAN Number
            Employee = self.env['hr.employee']
            employees_wo_pan = Employee.search([
                ('l10n_in_pan', '=', False),
                ('company_id', 'in', indian_companies.ids),
            ])
            if employees_wo_pan:
                no_pan_id_str = _('Employees Without PAN Number')
                res.append({
                    'string': no_pan_id_str,
                    'count': len(employees_wo_pan),
                    'action': self._dashboard_default_action(no_pan_id_str, 'hr.employee', employees_wo_pan.ids)
                })

            # Employees Without UAN Number
            employees_wo_uan = Employee.search([
                ('l10n_in_uan', '=', False),
                ('company_id', 'in', indian_companies.ids),
            ])
            if employees_wo_uan:
                no_uan_id_str = _('Employees Without UAN Number')
                res.append({
                    'string': no_uan_id_str,
                    'count': len(employees_wo_uan),
                    'action': self._dashboard_default_action(no_uan_id_str, 'hr.employee', employees_wo_uan.ids)
                })

            # Employees Without ESIC Number
            employees_wo_esic = Employee.search([
                ('l10n_in_esic_number', '=', False),
                ('company_id', 'in', indian_companies.ids),
            ])
            if employees_wo_esic:
                no_esic_id_str = _('Employees Without ESIC Number')
                res.append({
                    'string': no_esic_id_str,
                    'count': len(employees_wo_esic),
                    'action': self._dashboard_default_action(no_esic_id_str, 'hr.employee', employees_wo_esic.ids)
                })

            # Employees who are on the probation & their contracts expire within a week
            probation_contract_type = self.env.ref('l10n_in_hr_payroll.l10n_in_contract_type_probation', raise_if_not_found=False)
            if probation_contract_type:
                nearly_expired_contracts = self.env['hr.contract'].search([
                    ('contract_type_id', '=', probation_contract_type.id),
                    ('state', '=', 'open'), ('kanban_state', '!=', 'blocked'),
                    ('date_end', '<=', fields.Date.to_string(date.today() + relativedelta(days=7))),
                    ('date_end', '>=', fields.Date.to_string(date.today() + relativedelta(days=1))),
                ])
                if nearly_expired_contracts:
                    prob_end_str = _("Employees Probation ends within a week")
                    employee_ids = nearly_expired_contracts.employee_id.ids
                    res.append({
                        'string': prob_end_str,
                        'count': len(employee_ids),
                        'action': self._dashboard_default_action(prob_end_str, 'hr.employee', employee_ids)
                    })
        return res

    def _get_base_local_dict(self):
        return {**super()._get_base_local_dict(), '_': _}

    def _get_employee_timeoff_data(self):
        return self.env['hr.leave.type'].with_company(self.company_id).with_context(employee_id=self.employee_id.id).get_allocation_data_request()
