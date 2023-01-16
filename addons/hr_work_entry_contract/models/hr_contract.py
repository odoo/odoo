# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date
from odoo import fields, models, _
from odoo.addons.resource.models.resource import datetime_to_string, string_to_datetime, Intervals
from odoo.osv import expression
from odoo.exceptions import UserError

import pytz

class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    date_generated_from = fields.Datetime(string='Generated From', readonly=True, required=True,
        default=lambda self: datetime.now().replace(hour=0, minute=0, second=0), copy=False)
    date_generated_to = fields.Datetime(string='Generated To', readonly=True, required=True,
        default=lambda self: datetime.now().replace(hour=0, minute=0, second=0), copy=False)

    def _get_default_work_entry_type(self):
        return self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)

    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        return self._get_leave_work_entry_type(leave)

    def _get_leave_work_entry_type(self, leave):
        return leave.work_entry_type_id

    # Is used to add more values, for example leave_id (in hr_work_entry_holidays)
    def _get_more_vals_leave_interval(self, interval, leaves):
        return []

    def _get_bypassing_work_entry_type_codes(self):
        return []

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_contract_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1] and leave[2]:
                interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                return self._get_leave_work_entry_type_dates(leave[2], interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry_contract.work_entry_type_leave')

    def _get_leave_domain(self, start_dt, end_dt):
        self.ensure_one()
        return [
            ('time_type', '=', 'leave'),
            ('calendar_id', 'in', [False, self.resource_calendar_id.id]),
            ('resource_id', 'in', [False, self.employee_id.resource_id.id]),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            ('company_id', 'in', [False, self.company_id.id]),
        ]

    def _get_contract_work_entries_values(self, date_start, date_stop):
        contract_vals = []
        bypassing_work_entry_type_codes = self._get_bypassing_work_entry_type_codes()
        for contract in self:
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            tz = pytz.timezone(calendar.tz)
            start_dt = pytz.utc.localize(date_start) if not date_start.tzinfo else date_start
            end_dt = pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop

            attendances = calendar._attendance_intervals_batch(
                start_dt, end_dt, resources=resource, tz=tz
            )[resource.id]

            # Other calendars: In case the employee has declared time off in another calendar
            # Example: Take a time off, then a credit time.
            # YTI TODO: This mimics the behavior of _leave_intervals_batch, while waiting to be cleaned
            # in master.
            resources_list = [self.env['resource.resource'], resource]
            resource_ids = [False, resource.id]
            leave_domain = contract._get_leave_domain(start_dt, end_dt)
            result = defaultdict(lambda: [])
            tz_dates = {}
            for leave in self.env['resource.calendar.leaves'].sudo().search(leave_domain):
                for resource in resources_list:
                    if leave.resource_id.id not in [False, resource.id]:
                        continue
                    tz = tz if tz else pytz.timezone((resource or contract).tz)
                    if (tz, start_dt) in tz_dates:
                        start = tz_dates[(tz, start_dt)]
                    else:
                        start = start_dt.astimezone(tz)
                        tz_dates[(tz, start_dt)] = start
                    if (tz, end_dt) in tz_dates:
                        end = tz_dates[(tz, end_dt)]
                    else:
                        end = end_dt.astimezone(tz)
                        tz_dates[(tz, end_dt)] = end
                    dt0 = string_to_datetime(leave.date_from).astimezone(tz)
                    dt1 = string_to_datetime(leave.date_to).astimezone(tz)
                    result[resource.id].append((max(start, dt0), min(end, dt1), leave))
            mapped_leaves = {r.id: Intervals(result[r.id]) for r in resources_list}
            leaves = mapped_leaves[resource.id]

            real_attendances = attendances - leaves
            real_leaves = attendances - real_attendances

            # A leave period can be linked to several resource.calendar.leave
            split_leaves = []
            for leave_interval in leaves:
                if leave_interval[2] and len(leave_interval[2]) > 1:
                    split_leaves += [(leave_interval[0], leave_interval[1], l) for l in leave_interval[2]]
                else:
                    split_leaves += [(leave_interval[0], leave_interval[1], leave_interval[2])]
            leaves = split_leaves

            # Attendances
            default_work_entry_type = contract._get_default_work_entry_type()
            for interval in real_attendances:
                work_entry_type_id = interval[2].mapped('work_entry_type_id')[:1] or default_work_entry_type
                # All benefits generated here are using datetimes converted from the employee's timezone
                contract_vals += [{
                    'name': "%s: %s" % (work_entry_type_id.name, employee.name),
                    'date_start': interval[0].astimezone(pytz.utc).replace(tzinfo=None),
                    'date_stop': interval[1].astimezone(pytz.utc).replace(tzinfo=None),
                    'work_entry_type_id': work_entry_type_id.id,
                    'employee_id': employee.id,
                    'contract_id': contract.id,
                    'company_id': contract.company_id.id,
                    'state': 'draft',
                }]

            for interval in real_leaves:
                # Could happen when a leave is configured on the interface on a day for which the
                # employee is not supposed to work, i.e. no attendance_ids on the calendar.
                # In that case, do try to generate an empty work entry, as this would raise a
                # sql constraint error
                if interval[0] == interval[1]:  # if start == stop
                    continue
                leave_entry_type = contract._get_interval_leave_work_entry_type(interval, leaves, bypassing_work_entry_type_codes)
                interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                contract_vals += [dict([
                    ('name', "%s%s" % (leave_entry_type.name + ": " if leave_entry_type else "", employee.name)),
                    ('date_start', interval_start),
                    ('date_stop', interval_stop),
                    ('work_entry_type_id', leave_entry_type.id),
                    ('employee_id', employee.id),
                    ('company_id', contract.company_id.id),
                    ('state', 'draft'),
                    ('contract_id', contract.id),
                ] + contract._get_more_vals_leave_interval(interval, leaves))]
        return contract_vals

    def _get_work_entries_values(self, date_start, date_stop):
        """
        Generate a work_entries list between date_start and date_stop for one contract.
        :return: list of dictionnary.
        """
        contract_vals = self._get_contract_work_entries_values(date_start, date_stop)

        for contract in self:
            # If we generate work_entries which exceeds date_start or date_stop, we change boundaries on contract
            if contract_vals:
                #Handle empty work entries for certain contracts, could happen on an attendance based contract
                #NOTE: this does not handle date_stop or date_start not being present in vals
                dates_stop = [x['date_stop'] for x in contract_vals if x['contract_id'] == contract.id]
                if dates_stop:
                    date_stop_max = max(dates_stop)
                    if date_stop_max > contract.date_generated_to:
                        contract.date_generated_to = date_stop_max

                dates_start = [x['date_start'] for x in contract_vals if x['contract_id'] == contract.id]
                if dates_start:
                    date_start_min = min(dates_start)
                    if date_start_min < contract.date_generated_from:
                        contract.date_generated_from = date_start_min

        return contract_vals

    def _generate_work_entries(self, date_start, date_stop, force=False):
        canceled_contracts = self.filtered(lambda c: c.state == 'cancel')
        if canceled_contracts:
            raise UserError(
                _("Sorry, generating work entries from cancelled contracts is not allowed.") + '\n%s' % (
                    ', '.join(canceled_contracts.mapped('name'))))
        vals_list = []
        date_start = fields.Datetime.to_datetime(date_start)
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())

        intervals_to_generate = defaultdict(lambda: self.env['hr.contract'])
        for contract in self:
            contract_start = fields.Datetime.to_datetime(contract.date_start)
            contract_stop = datetime.combine(fields.Datetime.to_datetime(contract.date_end or datetime.max.date()),
                                             datetime.max.time())
            date_start_work_entries = max(date_start, contract_start)
            date_stop_work_entries = min(date_stop, contract_stop)
            if force:
                intervals_to_generate[(date_start_work_entries, date_stop_work_entries)] |= contract
                continue

            # In case the date_generated_from == date_generated_to, move it to the date_start to
            # avoid trying to generate several months/years of history for old contracts for which
            # we've never generated the work entries.
            if contract.date_generated_from == contract.date_generated_to:
                contract.write({
                    'date_generated_from': date_start,
                    'date_generated_to': date_start,
                })
            # For each contract, we found each interval we must generate
            last_generated_from = min(contract.date_generated_from, contract_stop)
            if last_generated_from > date_start_work_entries:
                contract.date_generated_from = date_start_work_entries
                intervals_to_generate[(date_start_work_entries, last_generated_from)] |= contract

            last_generated_to = max(contract.date_generated_to, contract_start)
            if last_generated_to < date_stop_work_entries:
                contract.date_generated_to = date_stop_work_entries
                intervals_to_generate[(last_generated_to, date_stop_work_entries)] |= contract

        for interval, contracts in intervals_to_generate.items():
            date_from, date_to = interval
            vals_list.extend(contracts._get_work_entries_values(date_from, date_to))

        if not vals_list:
            return self.env['hr.work.entry']

        return self.env['hr.work.entry'].create(vals_list)

    def _remove_work_entries(self):
        ''' Remove all work_entries that are outside contract period (function used after writing new start or/and end date) '''
        all_we_to_unlink = self.env['hr.work.entry']
        for contract in self:
            date_start = fields.Datetime.to_datetime(contract.date_start)
            if contract.date_generated_from < date_start:
                we_to_remove = self.env['hr.work.entry'].search([('date_stop', '<=', date_start), ('contract_id', '=', contract.id)])
                if we_to_remove:
                    contract.date_generated_from = date_start
                    all_we_to_unlink |= we_to_remove
            if not contract.date_end:
                continue
            date_end = datetime.combine(contract.date_end, datetime.max.time())
            if contract.date_generated_to > date_end:
                we_to_remove = self.env['hr.work.entry'].search([('date_start', '>=', date_end), ('contract_id', '=', contract.id)])
                if we_to_remove:
                    contract.date_generated_to = date_end
                    all_we_to_unlink |= we_to_remove
        all_we_to_unlink.unlink()

    def _cancel_work_entries(self):
        if not self:
            return
        domain = [('state', '!=', 'validated')]
        for contract in self:
            date_start = fields.Datetime.to_datetime(contract.date_start)
            contract_domain = [
                ('contract_id', '=', contract.id),
                ('date_start', '>=', date_start),
            ]
            if contract.date_end:
                date_end = datetime.combine(contract.date_end, datetime.max.time())
                contract_domain += [('date_stop', '<=', date_end)]
            domain = expression.AND([domain, contract_domain])
        work_entries = self.env['hr.work.entry'].search(domain)
        if work_entries:
            work_entries.unlink()

    def write(self, vals):
        result = super(HrContract, self).write(vals)
        if vals.get('date_end') or vals.get('date_start'):
            self.sudo()._remove_work_entries()
        if vals.get('state') in ['draft', 'cancel']:
            self._cancel_work_entries()
        dependendant_fields = self._get_fields_that_recompute_we()
        if any(key in dependendant_fields for key in vals.keys()):
            for contract in self:
                date_from = max(self.date_start, self.date_generated_from.date())
                date_to = min(self.date_end or date.max, self.date_generated_to.date())
                if date_from != date_to:
                    contract._recompute_work_entries(date_from, date_to)

    def _recompute_work_entries(self, date_from, date_to):
        self.ensure_one()
        wizard = self.env['hr.work.entry.regeneration.wizard'].create({
            'employee_id': self.employee_id.id,
            'date_from': date_from,
            'date_to': date_to,
        })
        wizard.with_context(work_entry_skip_validation=True).regenerate_work_entries()

    def _get_fields_that_recompute_we(self):
        # Returns the fields that should recompute the work entries
        return ['resource_calendar_id']
