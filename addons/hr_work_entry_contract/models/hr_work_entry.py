# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from collections import defaultdict
from itertools import chain

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    contract_id = fields.Many2one('hr.contract', string="Contract", required=True)
    employee_id = fields.Many2one(domain=[('contract_ids.state', 'in', ('open', 'pending'))])
    work_entry_source = fields.Selection(related='contract_id.work_entry_source')

    def init(self):
        # FROM 7s by query to 2ms (with 2.6 millions entries)
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_work_entry_contract_date_start_stop_idx
            ON hr_work_entry(contract_id, date_start, date_stop)
            WHERE state in ('draft', 'validated');
        """)

    def _init_column(self, column_name):
        if column_name != 'contract_id':
            super()._init_column(column_name)
        else:
            self.env.cr.execute("""
                UPDATE hr_work_entry AS _hwe
                SET contract_id = result.contract_id
                FROM (
                    SELECT
                        hc.id AS contract_id,
                        array_agg(hwe.id) AS entry_ids
                    FROM
                        hr_work_entry AS hwe
                    LEFT JOIN
                        hr_contract AS hc
                    ON
                        hwe.employee_id=hc.employee_id AND
                        hc.state in ('open', 'close') AND
                        hwe.date_start >= hc.date_start AND
                        hwe.date_stop < COALESCE(hc.date_end + integer '1', '9999-12-31 23:59:59')
                    WHERE
                        hwe.contract_id IS NULL
                    GROUP BY
                        hwe.employee_id, hc.id
                ) AS result
                WHERE _hwe.id = ANY(result.entry_ids)
            """)

    def _get_duration_is_valid(self):
        return self.work_entry_type_id and self.work_entry_type_id.is_leave

    @api.onchange('employee_id', 'date_start', 'date_stop')
    def _onchange_contract_id(self):
        vals = {
            'employee_id': self.employee_id.id,
            'date_start': self.date_start,
            'date_stop': self.date_stop,
        }
        try:
            res = self._set_current_contract(vals)
        except ValidationError:
            return
        if res.get('contract_id'):
            self.contract_id = res.get('contract_id')

    @api.depends('date_start', 'duration')
    def _compute_date_stop(self):
        for work_entry in self:
            if work_entry._get_duration_is_valid():
                calendar = work_entry.contract_id.resource_calendar_id
                if not calendar:
                    continue
                work_entry.date_stop = calendar.plan_hours(work_entry.duration, work_entry.date_start, compute_leaves=True)
                continue
            super(HrWorkEntry, work_entry)._compute_date_stop()

    def _is_duration_computed_from_calendar(self):
        self.ensure_one()
        return self._get_duration_is_valid()

    def _get_duration_batch(self):
        super_work_entries = self.env['hr.work.entry']
        result = {}
        # {(date_start, date_stop): {calendar: employees}}
        mapped_periods = defaultdict(lambda: defaultdict(lambda: self.env['hr.employee']))
        for work_entry in self:
            if not work_entry.date_start or not work_entry.date_stop or not work_entry._is_duration_computed_from_calendar() or not work_entry.employee_id:
                super_work_entries |= work_entry
                continue
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            calendar = work_entry.contract_id.resource_calendar_id
            if not calendar:
                result[work_entry.id] = 0.0
                continue
            employee = work_entry.contract_id.employee_id
            mapped_periods[(date_start, date_stop)][calendar] |= employee

        # {(date_start, date_stop): {calendar: {'hours': foo}}}
        mapped_contract_data = defaultdict(lambda: defaultdict(lambda: {'hours': 0.0}))
        for (date_start, date_stop), employees_by_calendar in mapped_periods.items():
            for calendar, employees in employees_by_calendar.items():
                mapped_contract_data[(date_start, date_stop)][calendar] = employees._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar)
        result = super(HrWorkEntry, super_work_entries)._get_duration_batch()
        for work_entry in self - super_work_entries:
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            calendar = work_entry.contract_id.resource_calendar_id
            employee = work_entry.contract_id.employee_id
            result[work_entry.id] = mapped_contract_data[(date_start, date_stop)][calendar][employee.id]['hours'] if calendar else 0.0
        return result

    @api.model
    def _set_current_contract(self, vals):
        if not vals.get('contract_id') and vals.get('date_start') and vals.get('date_stop') and vals.get('employee_id'):
            contract_start = fields.Datetime.to_datetime(vals.get('date_start')).date()
            contract_end = fields.Datetime.to_datetime(vals.get('date_stop')).date()
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            contracts = employee._get_contracts(contract_start, contract_end, states=['open', 'pending', 'close'])
            if not contracts:
                raise ValidationError(_(
                    "%(employee)s does not have a contract from %(date_start)s to %(date_end)s.",
                    employee=employee.name,
                    date_start=contract_start,
                    date_end=contract_end,
                ))
            elif len(contracts) > 1:
                raise ValidationError(_("%(employee)s has multiple contracts from %(date_start)s to %(date_end)s. A work entry cannot overlap multiple contracts.",
                                        employee=employee.name, date_start=contract_start, date_end=contract_end))
            return dict(vals, contract_id=contracts[0].id)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._set_current_contract(vals) for vals in vals_list]
        work_entries = super().create(vals_list)
        return work_entries

    def _check_if_error(self):
        res = super()._check_if_error()
        outside_calendar = self._mark_leaves_outside_schedule()
        return res or outside_calendar

    def _get_leaves_entries_outside_schedule(self):
        return self.filtered(lambda w: w.work_entry_type_id.is_leave and w.state not in ('validated', 'cancelled'))

    def _mark_leaves_outside_schedule(self):
        """
        Check leave work entries in `self` which are completely outside
        the contract's theoretical calendar schedule. Mark them as conflicting.
        :return: leave work entries completely outside the contract's calendar
        """
        work_entries = self._get_leaves_entries_outside_schedule()
        entries_by_calendar = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in work_entries:
            calendar = work_entry.contract_id.resource_calendar_id
            entries_by_calendar[calendar] |= work_entry

        outside_entries = self.env['hr.work.entry']
        for calendar, entries in entries_by_calendar.items():
            datetime_start = min(entries.mapped('date_start'))
            datetime_stop = max(entries.mapped('date_stop'))

            calendar_intervals = calendar._attendance_intervals_batch(pytz.utc.localize(datetime_start), pytz.utc.localize(datetime_stop))[False]
            entries_intervals = entries._to_intervals()
            overlapping_entries = self._from_intervals(entries_intervals & calendar_intervals)
            outside_entries |= entries - overlapping_entries
        outside_entries.write({'state': 'conflict'})
        return bool(outside_entries)

    def _to_intervals(self):
        return WorkIntervals((w.date_start.replace(tzinfo=pytz.utc), w.date_stop.replace(tzinfo=pytz.utc), w) for w in self)

    @api.model
    def _from_intervals(self, intervals):
        return self.browse(chain.from_iterable(recs.ids for start, end, recs in intervals))


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    is_leave = fields.Boolean(
        default=False, string="Time Off", help="Allow the work entry type to be linked with time off types.")
