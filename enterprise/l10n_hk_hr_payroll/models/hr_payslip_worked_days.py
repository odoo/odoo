# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    l10n_hk_leave_id = fields.Many2one('hr.leave', string='Leave', readonly=True)

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        hk_worked_days = self.filtered(lambda wd: wd.payslip_id.struct_id.country_id.code == "HK")

        for worked_days in hk_worked_days:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT' or not worked_days.is_paid or worked_days.is_credit_time:
                worked_days.amount = 0
                continue
            if worked_days.payslip_id.wage_type == "hourly":
                hourly_wage = worked_days.payslip_id.contract_id.hourly_wage
                if worked_days.work_entry_type_id.l10n_hk_use_713:
                    hourly_wage = max(hourly_wage, worked_days.payslip_id._get_moving_daily_wage() / worked_days.contract_id.resource_calendar_id.hours_per_day)
                rate = 0.8 if worked_days.work_entry_type_id.l10n_hk_non_full_pay else 1
                worked_days.amount = hourly_wage * worked_days.number_of_hours * rate
            else:
                payslip = worked_days.payslip_id
                if worked_days.l10n_hk_leave_id:
                    payslip = self.env['hr.payslip'].search([
                        ('employee_id', '=', worked_days.payslip_id.employee_id.id),
                        ('date_from', '<=', worked_days.l10n_hk_leave_id.date_from),
                        ('date_to', '>=', worked_days.l10n_hk_leave_id.date_from),
                        ('state', 'in', ['done', 'paid']),
                    ], limit=1) or worked_days.payslip_id
                sum_worked_days = worked_days.payslip_id.sum_worked_hours / worked_days.contract_id.resource_calendar_id.hours_per_day
                daily_wage = worked_days.contract_id.contract_wage / (sum_worked_days or 1)
                if worked_days.work_entry_type_id.l10n_hk_use_713:
                    daily_wage = max(daily_wage, payslip._get_moving_daily_wage())
                rate = 0.8 if worked_days.work_entry_type_id.l10n_hk_non_full_pay else 1
                number_of_days = worked_days.number_of_hours / worked_days.contract_id.resource_calendar_id.hours_per_day
                worked_days.amount = daily_wage * number_of_days * rate

        super(HrPayslipWorkedDays, self - hk_worked_days)._compute_amount()
