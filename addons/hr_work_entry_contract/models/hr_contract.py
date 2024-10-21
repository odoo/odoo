# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from datetime import datetime, date, time
import pytz

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.addons.resource.models.utils import string_to_datetime, Intervals
from odoo.osv import expression
from odoo.tools import ormcache, format_list
from odoo.exceptions import UserError

from .hr_work_intervals import WorkIntervals


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    date_generated_from = fields.Datetime(string='Generated From', readonly=True, required=True,
        default=lambda self: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), copy=False)
    date_generated_to = fields.Datetime(string='Generated To', readonly=True, required=True,
        default=lambda self: datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), copy=False)
    last_generation_date = fields.Date(string='Last Generation Date', readonly=True)
    work_entry_source = fields.Selection([('calendar', 'Working Schedule')], required=True, default='calendar', help='''
        Defines the source for work entries generation

        Working Schedule: Work entries will be generated from the working hours below.
        Attendances: Work entries will be generated from the employee's attendances. (requires Attendance app)
        Planning: Work entries will be generated from the employee's planning. (requires Planning app)
    '''
    )
    work_entry_source_calendar_invalid = fields.Boolean(compute='_compute_work_entry_source_calendar_invalid')

    @api.depends('work_entry_source', 'resource_calendar_id')
    def _compute_work_entry_source_calendar_invalid(self):
        for contract in self:
            contract.work_entry_source_calendar_invalid = contract.work_entry_source == 'calendar' and not contract.resource_calendar_id

    @ormcache('self.structure_type_id')
    def _get_default_work_entry_type_id(self):
        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)
        return attendance.id if attendance else False

    def _get_leave_work_entry_type_dates(self, leave, date_from, date_to, employee):
        return self._get_leave_work_entry_type(leave)

    def _get_leave_work_entry_type(self, leave):
        return leave.work_entry_type_id

    # Is used to add more values, for example planning_slot_id
    def _get_more_vals_attendance_interval(self, interval):
        return []

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

    def _get_sub_leave_domain(self):
        return [('calendar_id', 'in', [False] + self.resource_calendar_id.ids)]

    def _get_leave_domain(self, start_dt, end_dt):
        domain = [
            ('resource_id', 'in', [False] + self.employee_id.resource_id.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
            ('company_id', 'in', [False, self.company_id.id]),
        ]
        return expression.AND([domain, self._get_sub_leave_domain()])

    def _get_resource_calendar_leaves(self, start_dt, end_dt):
        return self.env['resource.calendar.leaves'].search(self._get_leave_domain(start_dt, end_dt))

    def _get_attendance_intervals(self, start_dt, end_dt):
        # {resource: intervals}
        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        for contract in self:
            if contract.work_entry_source != 'calendar':
                continue
            employees_by_calendar[contract.resource_calendar_id] |= contract.employee_id
        result = dict()
        for calendar, employees in employees_by_calendar.items():
            result.update(calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources=employees.resource_id,
                tz=pytz.timezone(calendar.tz)
            ))
        return result

    def _get_lunch_intervals(self, start_dt, end_dt):
        # {resource: intervals}
        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        for contract in self:
            employees_by_calendar[contract.resource_calendar_id] |= contract.employee_id
        result = {}
        for calendar, employees in employees_by_calendar.items():
            result.update(calendar._attendance_intervals_batch(
                start_dt,
                end_dt,
                resources=employees.resource_id,
                tz=pytz.timezone(calendar.tz),
                lunch=True,
            ))
        return result

    def _get_interval_work_entry_type(self, interval):
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id[:1]:
            return interval[2].work_entry_type_id[:1]
        return self.env['hr.work.entry.type'].browse(self._get_default_work_entry_type_id())

    def _get_valid_leave_intervals(self, attendances, interval):
        self.ensure_one()
        return [interval]

    def _get_contract_work_entries_values(self, date_start, date_stop):
        start_dt = pytz.utc.localize(date_start) if not date_start.tzinfo else date_start
        end_dt = pytz.utc.localize(date_stop) if not date_stop.tzinfo else date_stop
        contract_vals = []
        bypassing_work_entry_type_codes = self._get_bypassing_work_entry_type_codes()

        attendances_by_resource = self._get_attendance_intervals(start_dt, end_dt)

        resource_calendar_leaves = self._get_resource_calendar_leaves(start_dt, end_dt)
        # {resource: resource_calendar_leaves}
        leaves_by_resource = defaultdict(lambda: self.env['resource.calendar.leaves'])
        for leave in resource_calendar_leaves:
            leaves_by_resource[leave.resource_id.id] |= leave

        tz_dates = {}
        for contract in self:
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            # if the contract is fully flexible, we refer to the employee's timezone
            tz = pytz.timezone(resource.tz) if contract._is_fully_flexible() else pytz.timezone(calendar.tz)
            attendances = attendances_by_resource[resource.id]

            # Other calendars: In case the employee has declared time off in another calendar
            # Example: Take a time off, then a credit time.
            resources_list = [self.env['resource.resource'], resource]
            result = defaultdict(lambda: [])
            for leave in itertools.chain(leaves_by_resource[False], leaves_by_resource[resource.id]):
                for resource in resources_list:
                    # Global time off is not for this calendar, can happen with multiple calendars in self
                    if resource and leave.calendar_id and leave.calendar_id != calendar and not leave.resource_id:
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
                    leave_start_dt = max(start, dt0)
                    leave_end_dt = min(end, dt1)
                    leave_interval = (leave_start_dt, leave_end_dt, leave)
                    leave_interval = contract._get_valid_leave_intervals(attendances, leave_interval)
                    if leave_interval:
                        result[resource.id] += leave_interval
            mapped_leaves = {r.id: WorkIntervals(result[r.id]) for r in resources_list}
            leaves = mapped_leaves[resource.id]

            real_attendances = attendances - leaves
            if contract.has_static_work_entries() or not leaves:
                # Empty leaves means empty real_leaves
                real_leaves = attendances - real_attendances
            else:
                # In the case of attendance based contracts use regular attendances to generate leave intervals
                static_attendances = calendar._attendance_intervals_batch(
                    start_dt, end_dt, resources=resource, tz=tz)[resource.id]
                real_leaves = static_attendances & leaves

            if not contract.has_static_work_entries():
                # An attendance based contract might have an invalid planning, by definition it may not happen with
                # static work entries.
                # Creating overlapping slots for example might lead to a single work entry.
                # In that case we still create both work entries to indicate a problem (conflicting W E).
                split_attendances = []
                for attendance in real_attendances:
                    if attendance[2] and len(attendance[2]) > 1:
                        split_attendances += [(attendance[0], attendance[1], a) for a in attendance[2]]
                    else:
                        split_attendances += [attendance]
                real_attendances = split_attendances

            # A leave period can be linked to several resource.calendar.leave
            split_leaves = []
            for leave_interval in leaves:
                if leave_interval[2] and len(leave_interval[2]) > 1:
                    split_leaves += [(leave_interval[0], leave_interval[1], l) for l in leave_interval[2]]
                else:
                    split_leaves += [(leave_interval[0], leave_interval[1], leave_interval[2])]
            leaves = split_leaves

            # Attendances
            for interval in real_attendances:
                work_entry_type = contract._get_interval_work_entry_type(interval)
                # All benefits generated here are using datetimes converted from the employee's timezone
                contract_vals += [dict([
                    ('name', "%s: %s" % (work_entry_type.name, employee.name)),
                    ('date_start', interval[0].astimezone(pytz.utc).replace(tzinfo=None)),
                    ('date_stop', interval[1].astimezone(pytz.utc).replace(tzinfo=None)),
                    ('work_entry_type_id', work_entry_type.id),
                    ('employee_id', employee.id),
                    ('contract_id', contract.id),
                    ('company_id', contract.company_id.id),
                    ('state', 'draft'),
                ] + contract._get_more_vals_attendance_interval(interval))]

            leaves_over_attendances = WorkIntervals(leaves) & real_leaves
            for interval in real_leaves:
                # Could happen when a leave is configured on the interface on a day for which the
                # employee is not supposed to work, i.e. no attendance_ids on the calendar.
                # In that case, do try to generate an empty work entry, as this would raise a
                # sql constraint error
                if interval[0] == interval[1]:  # if start == stop
                    continue
                leaves_over_interval = [l for l in leaves_over_attendances if l[0] >= interval[0] and l[1] <= interval[1]]
                for leave_interval in [(l[0], l[1], interval[2]) for l in leaves_over_interval]:
                    leave_entry_type = contract._get_interval_leave_work_entry_type(leave_interval, leaves, bypassing_work_entry_type_codes)
                    interval_leaves = [leave for leave in leaves if leave[2].work_entry_type_id.id == leave_entry_type.id]
                    interval_start = leave_interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                    interval_stop = leave_interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                    contract_vals += [dict([
                        ('name', "%s%s" % (leave_entry_type.name + ": " if leave_entry_type else "", employee.name)),
                        ('date_start', interval_start),
                        ('date_stop', interval_stop),
                        ('work_entry_type_id', leave_entry_type.id),
                        ('employee_id', employee.id),
                        ('company_id', contract.company_id.id),
                        ('state', 'draft'),
                        ('contract_id', contract.id),
                    ] + contract._get_more_vals_leave_interval(interval, interval_leaves))]
        return contract_vals

    def _get_work_entries_values(self, date_start, date_stop):
        """
        Generate a work_entries list between date_start and date_stop for one contract.
        :return: list of dictionnary.
        """
        if isinstance(date_start, datetime):
            contract_vals = self._get_contract_work_entries_values(date_start, date_stop)
        else:
            contract_vals = []
            contracts_by_tz = defaultdict(lambda: self.env['hr.contract'])
            for contract in self:
                contracts_by_tz[contract.resource_calendar_id.tz] += contract
            for contract_tz, contracts in contracts_by_tz.items():
                tz = pytz.timezone(contract_tz) if contract_tz else pytz.utc
                contract_vals += contracts._get_contract_work_entries_values(
                    tz.localize(date_start),
                    tz.localize(date_stop))

        # {contract_id: ([dates_start], [dates_stop])}
        mapped_contract_dates = defaultdict(lambda: ([], []))
        for x in contract_vals:
            mapped_contract_dates[x['contract_id']][0].append(x['date_start'])
            mapped_contract_dates[x['contract_id']][1].append(x['date_stop'])

        for contract in self:
            # If we generate work_entries which exceeds date_start or date_stop, we change boundaries on contract
            if contract_vals:
                #Handle empty work entries for certain contracts, could happen on an attendance based contract
                #NOTE: this does not handle date_stop or date_start not being present in vals
                dates_stop = mapped_contract_dates[contract.id][1]
                if dates_stop:
                    date_stop_max = max(dates_stop)
                    if date_stop_max > contract.date_generated_to:
                        contract.date_generated_to = date_stop_max

                dates_start = mapped_contract_dates[contract.id][0]
                if dates_start:
                    date_start_min = min(dates_start)
                    if date_start_min < contract.date_generated_from:
                        contract.date_generated_from = date_start_min

        return contract_vals

    def has_static_work_entries(self):
        # Static work entries as in the same are to be generated each month
        # Useful to differentiate attendance based contracts from regular ones
        self.ensure_one()
        return self.work_entry_source == 'calendar'

    def generate_work_entries(self, date_start, date_stop, force=False):
        # Generate work entries between 2 dates (datetime.date)
        # To correctly englobe the period, the start and end periods are converted
        # using the calendar timezone.
        assert not isinstance(date_start, datetime)
        assert not isinstance(date_stop, datetime)

        date_start = datetime.combine(fields.Datetime.to_datetime(date_start), datetime.min.time())
        date_stop = datetime.combine(fields.Datetime.to_datetime(date_stop), datetime.max.time())

        contracts_by_company_tz = defaultdict(lambda: self.env['hr.contract'])
        for contract in self:
            contracts_by_company_tz[(
                contract.company_id,
                (contract.resource_calendar_id or contract.employee_id.resource_calendar_id).tz
            )] += contract
        utc = pytz.timezone('UTC')
        new_work_entries = self.env['hr.work.entry']
        for (company, contract_tz), contracts in contracts_by_company_tz.items():
            tz = pytz.timezone(contract_tz) if contract_tz else pytz.utc
            date_start_tz = tz.localize(date_start).astimezone(utc).replace(tzinfo=None)
            date_stop_tz = tz.localize(date_stop).astimezone(utc).replace(tzinfo=None)
            new_work_entries += contracts.with_company(company).sudo()._generate_work_entries(
                date_start_tz, date_stop_tz, force=force)
        return new_work_entries

    def _generate_work_entries(self, date_start, date_stop, force=False):
        # Generate work entries between 2 dates (datetime.datetime)
        # This method considers that the dates are correctly localized
        # based on the target timezone
        assert isinstance(date_start, datetime)
        assert isinstance(date_stop, datetime)
        self = self.with_context(tracking_disable=True)
        canceled_contracts = self.filtered(lambda c: c.state == 'cancel')
        if canceled_contracts:
            raise UserError(
                _("Sorry, generating work entries from cancelled contracts is not allowed.")
                + "\n%s" % (format_list(self.env, canceled_contracts.mapped("name"))),
            )
        vals_list = []
        self.write({'last_generation_date': fields.Date.today()})

        intervals_to_generate = defaultdict(lambda: self.env['hr.contract'])
        # In case the date_generated_from == date_generated_to, move it to the date_start to
        # avoid trying to generate several months/years of history for old contracts for which
        # we've never generated the work entries.
        self.filtered(lambda c: c.date_generated_from == c.date_generated_to).write({
            'date_generated_from': date_start,
            'date_generated_to': date_start,
        })
        utc = pytz.timezone('UTC')
        for contract in self:
            contract_tz = (contract.resource_calendar_id or contract.employee_id.resource_calendar_id).tz
            tz = pytz.timezone(contract_tz) if contract_tz else pytz.utc
            contract_start = tz.localize(fields.Datetime.to_datetime(contract.date_start)).astimezone(utc).replace(tzinfo=None)
            contract_stop = datetime.combine(fields.Datetime.to_datetime(contract.date_end or datetime.max.date()),
                                             datetime.max.time())
            if contract.date_end:
                contract_stop = tz.localize(contract_stop).astimezone(utc).replace(tzinfo=None)
            if date_start > contract_stop or date_stop < contract_start:
                continue
            date_start_work_entries = max(date_start, contract_start)
            date_stop_work_entries = min(date_stop, contract_stop)
            if force:
                intervals_to_generate[(date_start_work_entries, date_stop_work_entries)] |= contract
                continue

            # For each contract, we found each interval we must generate
            # In some cases we do not want to set the generated dates beforehand, since attendance based work entries
            #  is more dynamic, we want to update the dates within the _get_work_entries_values function
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
        work_entries = self.env['hr.work.entry'].sudo().search(domain)
        if work_entries:
            work_entries.sudo().unlink()

    def write(self, vals):
        result = super(HrContract, self).write(vals)
        if vals.get('date_end') or vals.get('date_start'):
            self.sudo()._remove_work_entries()
        if vals.get('state') in ['draft', 'cancel']:
            self._cancel_work_entries()
        dependendant_fields = self._get_fields_that_recompute_we()
        salary_simulation = self.env.context.get('salary_simulation')
        if not salary_simulation and any(key in dependendant_fields for key in vals.keys()):
            for contract in self:
                date_from = max(contract.date_start, contract.date_generated_from.date())
                date_to = min(contract.date_end or date.max, contract.date_generated_to.date())
                if date_from != date_to and self.employee_id:
                    contract._recompute_work_entries(date_from, date_to)
        return result

    def _recompute_work_entries(self, date_from, date_to):
        self.ensure_one()
        if self.employee_id:
            wizard = self.env['hr.work.entry.regeneration.wizard'].create({
                'employee_ids': [(4, self.employee_id.id)],
                'date_from': date_from,
                'date_to': date_to,
            })
            wizard.with_context(work_entry_skip_validation=True).regenerate_work_entries()

    def _get_fields_that_recompute_we(self):
        # Returns the fields that should recompute the work entries
        return ['resource_calendar_id', 'work_entry_source']

    @api.model
    def _cron_generate_missing_work_entries(self):
        # retrieve contracts for the current month
        today = fields.Date.today()
        start = datetime.combine(today + relativedelta(day=1), time.min)
        stop = datetime.combine(today + relativedelta(months=1, day=31), time.max)
        all_contracts = self.env['hr.employee']._get_all_contracts(
            start, stop, states=['open', 'close'])
        # determine contracts to do (the ones whose generated dates have open periods this month)
        contracts_todo = all_contracts.filtered(lambda c:\
            (c.date_generated_from > start or c.date_generated_to < stop) and\
            (not c.last_generation_date or c.last_generation_date < today))
        if not contracts_todo:
            return
        countract_todo_count = len(contracts_todo)
        # Filter contracts by company, work entries generation is not supposed to be called on
        # contracts from differents companies, as we will retrieve the resource.calendar.leave
        # and we don't want to mix everything up. The other contracts will be treated when the
        # cron is re-triggered
        contracts_todo = contracts_todo.filtered(lambda c: c.company_id == contracts_todo[0].company_id)
        # generate a batch of work entries
        BATCH_SIZE = 100
        # Since attendance based are more volatile for their work entries generation
        # it can happen that the date_generated_from and date_generated_to fields are not
        # pushed to start and stop
        # It is more interesting for batching to process statically generated work entries first
        # since we get benefits from having multiple contracts on the same calendar
        contracts_todo = contracts_todo.sorted(key=lambda c: 1 if c.has_static_work_entries() else 100)
        contracts_todo = contracts_todo[:BATCH_SIZE].generate_work_entries(
            start.date(), stop.date(), False)
        # if necessary, retrigger the cron to generate more work entries
        if countract_todo_count > BATCH_SIZE:
            self.env.ref('hr_work_entry_contract.ir_cron_generate_missing_work_entries')._trigger()
