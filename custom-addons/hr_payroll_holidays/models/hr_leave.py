# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    payslip_state = fields.Selection([
        ('normal', 'To compute in next payslip'),
        ('done', 'Computed in current payslip'),
        ('blocked', 'To defer to next payslip')], string='Payslip State',
        copy=False, default='normal', required=True, tracking=True)

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_payslip_generated(self):
        if self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser():
            return

        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
            ('state', 'in', ['done', 'paid']),
        ])

        for leave in self:
            if any(
                p.employee_id == leave.employee_id and
                p.date_from <= leave.date_to.date() and
                p.date_to >= leave.date_from.date() and
                p.is_regular
                for p in all_payslips
            ):
                raise ValidationError(_("The selected period is covered by a validated payslip. You can't create a time off for that period."))

    def action_validate(self):
        # Get employees payslips
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('state', 'in', ['done', 'paid', 'verify']),
        ]).filtered(lambda p: p.is_regular)
        done_payslips = all_payslips.filtered(lambda p: p.state in ['done', 'paid'])
        waiting_payslips = all_payslips - done_payslips
        # Mark Leaves to Defer
        for leave in self:
            if any(
                payslip.employee_id == leave.employee_id \
                and (payslip.date_from <= leave.date_to.date() \
                and payslip.date_to >= leave.date_from.date()) for payslip in done_payslips) \
                    and not any(payslip.employee_id == leave.employee_id \
                and (payslip.date_from <= leave.date_to.date() \
                and payslip.date_to >= leave.date_from.date()) for payslip in waiting_payslips):
                leave.payslip_state = 'blocked'
        res = super().action_validate()
        self.sudo()._recompute_payslips()
        return res

    def action_refuse(self):
        res = super().action_refuse()
        self.sudo()._recompute_payslips()
        return res

    def _action_user_cancel(self, reason):
        res = super()._action_user_cancel(reason)
        self.sudo()._recompute_payslips()
        return res

    def _recompute_payslips(self):
        # Recompute draft/waiting payslips
        all_payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.mapped('employee_id').ids),
            ('state', 'in', ['draft', 'verify']),
        ]).filtered(lambda p: p.is_regular)
        draft_payslips = self.env['hr.payslip']
        waiting_payslips = self.env['hr.payslip']
        for leave in self:
            for payslip in all_payslips:
                if payslip.employee_id == leave.employee_id and (payslip.date_from <= leave.date_to.date() and payslip.date_to >= leave.date_from.date()):
                    if payslip.state == 'draft':
                        draft_payslips |= payslip
                    elif payslip.state == 'verify':
                        waiting_payslips |= payslip
        if draft_payslips:
            draft_payslips._compute_worked_days_line_ids()
        if waiting_payslips:
            waiting_payslips.action_refresh_from_work_entries()

    def _cancel_work_entry_conflict(self):
        leaves_to_defer = self.filtered(lambda l: l.payslip_state == 'blocked')
        for leave in leaves_to_defer:
            leave.activity_schedule(
                'hr_payroll_holidays.mail_activity_data_hr_leave_to_defer',
                summary=_('Validated Time Off to Defer'),
                note=_('Please create manually the work entry for %s',
                        leave.employee_id._get_html_link()),
                user_id=leave.employee_id.company_id.deferred_time_off_manager.id or self.env.ref('base.user_admin').id)
        return super(HrLeave, self - leaves_to_defer)._cancel_work_entry_conflict()

    def activity_feedback(self, act_type_xmlids, user_id=None, feedback=None):
        if 'hr_payroll_holidays.mail_activity_data_hr_leave_to_defer' in act_type_xmlids:
            self.write({'payslip_state': 'done'})
        return super().activity_feedback(act_type_xmlids, user_id=user_id, feedback=feedback)

    def action_report_to_next_month(self):
        for leave in self:
            if not leave.employee_id or leave.payslip_state != 'blocked':
                raise UserError(_('Only an employee time off to defer can be reported to next month'))
            if (leave.date_to.year - leave.date_from.year) * 12 + leave.date_to.month - leave.date_from.month > 1:
                raise UserError(_('The time off %s can not be reported because it is defined over more than 2 months', leave.display_name))
            leave_work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('company_id', '=', self.env.company.id),
                ('date_start', '>=', leave.date_from),
                ('date_stop', '<=', leave.date_to),
            ])
            next_month_work_entries = self.env['hr.work.entry'].search([
                ('employee_id', '=', leave.employee_id.id),
                ('company_id', '=', self.env.company.id),
                ('state', '=', 'draft'),
                ('date_start', '>=', Datetime.to_datetime(leave.date_from + relativedelta(day=1, months=1))),
                ('date_stop', '<=', datetime.combine(Datetime.to_datetime(leave.date_to + relativedelta(day=31, months=1)), datetime.max.time()))
            ])
            if not next_month_work_entries:
                raise UserError(_('The next month work entries are not generated yet or are validated already for time off %s', leave.display_name))
            if not leave_work_entries:
                raise UserError(_('There is no work entries linked to this time off to report'))
            for work_entry in leave_work_entries:
                found = False
                for next_work_entry in next_month_work_entries:
                    if next_work_entry.work_entry_type_id.code != "WORK100":
                        continue
                    if not float_compare(next_work_entry.duration, work_entry.duration, 2):
                        next_work_entry.work_entry_type_id = leave.holiday_status_id.work_entry_type_id
                        found = True
                        break
                if not found:
                    raise UserError(_('Not enough attendance work entries to report the time off %s. Please make the operation manually', leave.display_name))
        # Should change payslip_state to 'done' at the same time
        self.activity_feedback(['hr_payroll_holidays.mail_activity_data_hr_leave_to_defer'])

    def _check_uncovered_by_validated_payslip(self):
        payslips = self.env['hr.payslip'].sudo().search([
            ('employee_id', 'in', self.employee_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
            ('state', 'in', ['done', 'paid']),
        ])

        for leave in self:
            if any(
                    p.employee_id == leave.employee_id and
                    p.date_from <= leave.date_to.date() and
                    p.date_to >= leave.date_from.date() and
                    p.is_regular
                    for p in payslips
            ):
                raise UserError(_("The pay of the month is already validated with this day included. If you need to adapt, please refer to HR."))

    def write(self, vals):
        if vals.get('active') and self._check_uncovered_by_validated_payslip():
            self._check_uncovered_by_validated_payslip()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_payslip(self):
        self._check_uncovered_by_validated_payslip()
