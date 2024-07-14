# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        if self.env.context.get('salary_simulation'):
            return super().compute_sheet()
        if self.filtered(lambda p: p.is_regular):
            employees = self.mapped('employee_id')
            leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '!=', 'refuse'),
            ])
            leaves_to_defer = leaves.filtered(lambda l: l.payslip_state == 'blocked')
            if leaves_to_defer:
                raise ValidationError(_(
                    'There is some remaining time off to defer for these employees: \n\n %s',
                    ', '.join(e.display_name for e in leaves_to_defer.mapped('employee_id'))))
            dates = self.mapped('date_to')
            max_date = datetime.combine(max(dates), datetime.max.time())
            leaves_to_green = leaves.filtered(lambda l: l.payslip_state != 'blocked' and l.date_to <= max_date)
            leaves_to_green.write({'payslip_state': 'done'})
        return super().compute_sheet()

    @api.model
    def _get_dashboard_warnings(self):
        res = super()._get_dashboard_warnings()
        leaves_to_defer = self.env['hr.leave'].search_count([
            ('payslip_state', '=', 'blocked'),
            ('state', '=', 'validate'),
            ('employee_company_id', 'in', self.env.companies.ids),
        ])
        if leaves_to_defer:
            res.append({
                'string': _('Time Off To Defer'),
                'count': leaves_to_defer,
                'action': 'hr_payroll_holidays.hr_leave_action_open_to_defer',
            })
        leaves_no_document = self.env['hr.leave'].search([
            ('state', 'not in', ['refuse', 'validate']),
            ('leave_type_support_document', '=', True),
            ('attachment_ids', '=', False),
            ('employee_company_id', 'in', self.env.companies.ids),
        ])
        if leaves_no_document:
            no_document_str = _('Time Off Without Joined Document')
            res.append({
                'string': no_document_str,
                'count': len(leaves_no_document),
                'action': self._dashboard_default_action(no_document_str, 'hr.leave', leaves_no_document.ids)
            })
        leaves_no_allocation_ids = []
        employees = self.env['hr.employee'].search([('company_id', 'in', self.env.companies.ids)])
        consumed_leaves = employees._get_consumed_leaves(leave_types=self.env['hr.leave.type'].search([
            ('requires_allocation', '=', 'yes'),
            ('allows_negative', '=', False),
        ]))[1]
        for employee in consumed_leaves:
            to_recheck_leaves_per_leave_type = consumed_leaves[employee]
            for holiday_status_id in to_recheck_leaves_per_leave_type:
                for end_dates in to_recheck_leaves_per_leave_type[holiday_status_id]['excess_days']:
                    leave_id = to_recheck_leaves_per_leave_type[holiday_status_id]['excess_days'][end_dates]['leave_id']
                    leaves_no_allocation_ids.append(leave_id)
        if leaves_no_allocation_ids:
            no_allocation_str = _('Time Off Not Related To An Allocation')
            res.append({
                'string': no_allocation_str,
                'count': len(leaves_no_allocation_ids),
                'action': self._dashboard_default_action(no_allocation_str, 'hr.leave', leaves_no_allocation_ids, additional_context={
                    'search_default_group_employee': True,
                })
            })
        return res
