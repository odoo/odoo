# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class HrLeave(models.Model):
    _inherit = 'hr.leave'


    l10n_ch_pay_interruption = fields.Boolean("Pay Interruption")
    l10n_ch_lpp_interruption = fields.Boolean("LPP Contributions Interruption")
    l10n_ch_continued_pay_percentage = fields.Float("Continued Pay %", default=1)
    l10n_ch_disability_percentage = fields.Float("Disability %", default=1)
    l10n_ch_swissdec_work_interruption = fields.Boolean(compute="_compute_l10n_ch_swissdec_work_interruption")
    l10n_ch_swissdec_payroll_impact = fields.Boolean(related='holiday_status_id.l10n_ch_swissdec_payroll_impact')

    @api.constrains('request_date_from', 'request_date_to', 'holiday_status_id')
    def _check_work_interruption(self):
        work_interruption = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt', raise_if_not_found=False)
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id == work_interruption:
                if leave.request_date_from.day != 1 or leave.request_date_to.day != (datetime.date(leave.request_date_to.year, leave.request_date_to.month, 1) + relativedelta(months=1, days=-1)).day:
                    raise ValidationError(_("Work interruptions must Start on the first of the month and end on the last of the month."))

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_payslip_generated(self):
        """
        Swiss Override, we never want to let a payroll impacting leave be placed on validated payslips even for a super user or time off officer
        """
        payroll_impacting_leave_types = self.env['hr.payslip']._get_payroll_impacting_swissdec()

        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
            ('state', 'in', ['done', 'paid']),
        ])

        payroll_impacting_leaves = self.filtered(
            lambda leave: leave.holiday_status_id.id in payroll_impacting_leave_types.ids and (
            leave.l10n_ch_swissdec_work_interruption or
            leave.l10n_ch_swissdec_payroll_impact and (
                leave.l10n_ch_continued_pay_percentage < 1 or
                leave.l10n_ch_disability_percentage < 1)
            )
        )

        for leave in payroll_impacting_leaves:
            if any(
                p.employee_id == leave.employee_id and
                p.date_from <= leave.date_to.date() and
                p.date_to >= leave.date_from.date() and
                p.is_regular
                for p in all_payslips
            ):
                raise ValidationError(_("The selected period is covered by a validated payslip. You can't create a time off for that period."))

    @api.depends('holiday_status_id')
    def _compute_l10n_ch_swissdec_work_interruption(self):
        work_interruption_leave = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt', raise_if_not_found=False)
        for leave in self:
            leave.l10n_ch_swissdec_work_interruption = leave.holiday_status_id == work_interruption_leave
