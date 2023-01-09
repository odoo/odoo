# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import pytz

from datetime import date, datetime
from odoo import api, models


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    @api.constrains('date_start', 'date_end', 'state')
    def _check_contracts(self):
        self._get_leaves()._check_contracts()

    def _get_leaves(self):
        return self.env['hr.leave'].search([
            ('state', '!=', 'refuse'),
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('date_from', '<=', max([end or date.max for end in self.mapped('date_end')])),
            ('date_to', '>=', min(self.mapped('date_start'))),
        ])

    # override to add work_entry_type from leave
    def _get_leave_work_entry_type(self, leave):
        if leave.holiday_id:
            return leave.holiday_id.holiday_status_id.work_entry_type_id
        else:
            return leave.work_entry_type_id

    def _get_more_vals_leave_interval(self, interval, leaves):
        result = super()._get_more_vals_leave_interval(interval, leaves)
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1]:
                result.append(('leave_id', leave[2].holiday_id.id))
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_contract_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id.code in bypassing_codes:
            return interval[2].work_entry_type_id

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leaves if l[2] and interval_start >= l[2].date_from and interval_stop <= l[2].date_to]
        including_global_rcleaves = [l for l in including_rcleaves if not l.holiday_id]
        including_holiday_rcleaves = [l for l in including_rcleaves if l.holiday_id]
        rc_leave = False

        # Example: In CP200: Long term sick > Public Holidays (which is global)
        if bypassing_codes:
            bypassing_rc_leave = [l for l in including_holiday_rcleaves if l.holiday_id.holiday_status_id.work_entry_type_id.code in bypassing_codes]
        else:
            bypassing_rc_leave = []

        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
        elif including_holiday_rcleaves:
            rc_leave = including_holiday_rcleaves[0]
        if rc_leave:
            return self._get_leave_work_entry_type_dates(rc_leave, interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry_contract.work_entry_type_leave')

    def _get_leave_domain(self, start_dt, end_dt):
        # Complete override, compare over holiday_id.employee_id instead of calendar_id
        return [
            ('time_type', '=', 'leave'),
            '|', ('calendar_id', 'in', [False] + self.resource_calendar_id.ids),
                 ('holiday_id.employee_id', 'in', self.employee_id.ids), # see https://github.com/odoo/enterprise/pull/15091
            ('resource_id', 'in', [False] + self.employee_id.resource_id.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            ('company_id', 'in', [False, self.company_id.id]),
        ]

    def write(self, vals):
        # Special case when setting a contract as running:
        # If there is already a validated time off over another contract
        # with a different schedule, split the time off, before the
        # _check_contracts raises an issue.
        if 'state' not in vals or vals['state'] != 'open':
            return super().write(vals)
        specific_contracts = self.env['hr.contract']
        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}
        for contract in self:
            leaves = contract._get_leaves()
            for leave in leaves:
                overlapping_contracts = leave._get_overlapping_contracts(contract_states=[('state', '!=', 'cancel')])
                if len(overlapping_contracts.resource_calendar_id) <= 1:
                    continue
                if leave.id not in leaves_state:
                    leaves_state[leave.id] = leave.state
                if leave.state != 'refuse':
                    leave.action_refuse()
                super(HrContract, contract).write(vals)
                specific_contracts += contract
                for overlapping_contract in overlapping_contracts:
                    # Exclude other draft contracts that are not set to running on this
                    # transaction
                    if overlapping_contract.state == 'draft' and overlapping_contract not in self:
                        continue
                    new_date_from = max(leave.date_from, datetime.combine(overlapping_contract.date_start, datetime.min.time()))
                    new_date_to = min(leave.date_to, datetime.combine(overlapping_contract.date_end or date.max, datetime.max.time()))
                    new_leave_vals = leave.copy_data({
                        'date_from': new_date_from,
                        'date_to': new_date_to,
                        'state': leaves_state[leave.id],
                    })[0]
                    new_leave = self.env['hr.leave'].new(new_leave_vals)
                    new_leave._compute_date_from_to()
                    new_leave._compute_number_of_days()
                    # Could happen for part-time contract, that time off is not necessary
                    # anymore.
                    if new_leave.date_from < new_leave.date_to:
                        all_new_leave_origin.append(leave)
                        all_new_leave_vals.append(new_leave._convert_to_write(new_leave._cache))
        if all_new_leave_vals:
            new_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True
            ).create(all_new_leave_vals)
            new_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()
            for index, new_leave in enumerate(new_leaves):
                subtype_note = self.env.ref('mail.mt_note')
                new_leave.message_post_with_view(
                    'mail.message_origin_link',
                    values={'self': new_leave, 'origin': all_new_leave_origin[index]},
                    subtype_id=subtype_note.id)
        return super(HrContract, self - specific_contracts).write(vals)
