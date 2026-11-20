# Part of Odoo. See LICENSE file for full copyright and licensing details.


import pytz

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


def _get_version_tz(version):
    version_tz = (version.resource_calendar_id or version.employee_id.resource_calendar_id or version.employee_id).tz
    return pytz.timezone(version_tz) if version_tz else pytz.utc


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type', index='btree_not_null')


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _prepare_resource_leave_vals(self):
        vals = super(HrLeave, self)._prepare_resource_leave_vals()
        vals['work_entry_type_id'] = self.holiday_status_id.work_entry_type_id.id
        return vals

    def _split_leaves(self, split_date_from, split_date_to=False):
        split_source_dates = {
            leave.id: (leave.request_date_from, leave.request_date_to)
            for leave in self
        }
        new_leaves = super()._split_leaves(split_date_from, split_date_to)
        modified_leaves = self.filtered(
            lambda leave: split_source_dates[leave.id] != (leave.request_date_from, leave.request_date_to)
        )
        (modified_leaves | new_leaves).filtered(lambda leave: leave.state == 'validate')._cancel_work_entry_conflict()
        return new_leaves

    def _cancel_work_entry_conflict(self):
        """
        Creates a leave work entry for each hr.leave in self.
        Check overlapping work entries with self.
        Work entries completely included in a leave are archived.
        e.g.:
            |----- work entry ----|---- work entry ----|
                |------------------- hr.leave ---------------|
                                    ||
                                    vv
            |----* work entry ****|
                |************ work entry leave --------------|
        """
        if not self:
            return

        # 1. Create a work entry for each leave
        work_entries_vals_list = self._get_work_entries_values_of_days(self._get_work_entry_days())
        work_entries_vals_list = self.env['hr.version']._generate_work_entries_postprocess(work_entries_vals_list)
        new_leave_work_entries = self.env['hr.work.entry'].create(work_entries_vals_list)

        if new_leave_work_entries:
            # 2. Fetch overlapping work entries, grouped by employees
            start = min(self.mapped('date_from'), default=False)
            stop = max(self.mapped('date_to'), default=False)
            work_entry_groups = self.env['hr.work.entry']._read_group([
                ('date', '<=', stop),
                ('date', '>=', start),
                ('employee_id', 'in', self.employee_id.ids),
            ], ['employee_id'], ['id:recordset'])
            work_entries_by_employee = {
                employee.id: work_entries
                for employee, work_entries in work_entry_groups
            }

            # 3. Archive work entries included in leaves
            included = self.env['hr.work.entry']
            overlappping = self.env['hr.work.entry']
            for work_entries in work_entries_by_employee.values():
                # Work entries for this employee
                new_employee_work_entries = work_entries & new_leave_work_entries
                previous_employee_work_entries = work_entries - new_leave_work_entries

                # Build intervals from work entries
                leave_intervals = new_employee_work_entries._to_intervals()
                conflicts_intervals = previous_employee_work_entries._to_intervals()

                # Compute intervals completely outside any leave
                # Intervals are outside, but associated records are overlapping.
                outside_intervals = conflicts_intervals - leave_intervals

                overlappping |= self.env['hr.work.entry']._from_intervals(outside_intervals)
                included |= previous_employee_work_entries - overlappping
            overlappping.filtered(lambda entry: entry.state != 'validated').write({'leave_id': False})
            included.filtered(lambda entry: entry.state != 'validated').write({'active': False})

    def write(self, vals):
        if not self:
            return True
        skip_check = not bool({'employee_id', 'state', 'request_date_from', 'request_date_to'} & vals.keys())
        employee_ids = self.employee_id.ids
        if 'employee_id' in vals and vals['employee_id']:
            employee_ids += [vals['employee_id']]
        # We check a whole day before and after the interval of the earliest
        # request_date_from and latest request_date_end because date_{from,to}
        # can lie in this range due to time zone reasons.
        # (We can't use date_from and date_to as they are not yet computed at
        # this point.)
        start_dates = self.filtered('request_date_from').mapped('request_date_from') + [fields.Date.to_date(vals.get('request_date_from', False)) or datetime.max.date()]
        stop_dates = self.filtered('request_date_to').mapped('request_date_to') + [fields.Date.to_date(vals.get('request_date_to', False)) or datetime.min.date()]
        start = datetime.combine(min(start_dates) - relativedelta(days=1), time.min)
        stop = datetime.combine(max(stop_dates) + relativedelta(days=1), time.max)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, skip=skip_check, employee_ids=employee_ids):
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        employee_ids = {v['employee_id'] for v in vals_list if v.get('employee_id')}
        # We check a whole day before and after the interval of the earliest
        # request_date_from and latest request_date_end because date_{from,to}
        # can lie in this range due to time zone reasons.
        # (We can't use date_from and date_to as they are not yet computed at
        # this point.)
        start_dates = [fields.Date.to_date(v.get('request_date_from')) for v in vals_list if v.get('request_date_from')]
        stop_dates = [fields.Date.to_date(v.get('request_date_to')) for v in vals_list if v.get('request_date_to')]
        start = datetime.combine(min(start_dates, default=datetime.max.date()) - relativedelta(days=1), time.min)
        stop = datetime.combine(max(stop_dates, default=datetime.min.date()) + relativedelta(days=1), time.max)
        with self.env['hr.work.entry']._error_checking(start=start, stop=stop, employee_ids=employee_ids):
            return super().create(vals_list)

    def _get_leaves_on_public_holiday(self):
        return super()._get_leaves_on_public_holiday().filtered(
            lambda l: l.holiday_status_id.work_entry_type_id.code not in ['LEAVE110', 'LEAVE210', 'LEAVE280'])

    def _validate_leave_request(self):
        super()._validate_leave_request()
        self.sudo()._cancel_work_entry_conflict()  # delete preexisting conflicting work_entries
        return True

    def action_refuse(self):
        """
        Override to archive linked work entries and recreate attendance work entries
        where the refused leave was.
        """
        validated_leaves = self.filtered(lambda leave: leave.state == 'validate')
        res = super().action_refuse()
        validated_leaves._regen_work_entries()
        return res

    def _move_validate_leave_to_confirm(self):
        res = super()._move_validate_leave_to_confirm()
        self._regen_work_entries()
        return res

    def _action_user_cancel(self, reason=None):
        validated_leaves = self.filtered(lambda leave: leave.state == 'validate')
        res = super()._action_user_cancel(reason)
        validated_leaves.sudo()._regen_work_entries()
        return res

    def _regen_work_entries(self):
        """
        Called when the leave is refused or cancelled to regenerate the work entries properly for that period.
        """
        days = self._get_work_entry_days()
        work_entries = self.env['hr.work.entry'].sudo().search([
            ('version_id', 'in', [version.id for version in days]),
            ('date', 'in', list(set().union(*days.values()))),
        ]).filtered(lambda work_entry: work_entry.date in days[work_entry.version_id])
        validated = work_entries.filtered(lambda work_entry: work_entry.state == 'validated')
        (work_entries - validated).write({'active': False})
        for work_entry in validated:
            days[work_entry.version_id].discard(work_entry.date)
        vals_list = self._get_work_entries_values_of_days(days)
        vals_list = self.env['hr.version']._generate_work_entries_postprocess(vals_list)
        self.env['hr.work.entry'].create(vals_list)

    def _get_work_entry_days(self):
        """ Return the days covered by the leaves whose work entries were already generated, per version. """
        days = defaultdict(set)
        for leave in self:
            versions = leave.employee_id.sudo()._get_versions_with_contract_overlap_with_period(leave.date_from.date(), leave.date_to.date())
            for version in versions:
                # Generate only if it has already been generated
                if leave.date_to >= version.date_generated_from and leave.date_from <= version.date_generated_to:
                    tz = _get_version_tz(version)
                    version_start = version.date_start
                    version_stop = version.date_end or date.max
                    start = max(pytz.utc.localize(leave.date_from).astimezone(tz).date(), version_start)
                    stop = min(pytz.utc.localize(leave.date_to).astimezone(tz).date(), version_stop)
                    days[version] |= {start + timedelta(days=offset) for offset in range((stop - start).days + 1)}
        return days

    def _get_work_entries_values_of_days(self, days):
        """ Generate the work entries of each day once, by runs of consecutive days. """
        vals_list = []
        for version, version_days in days.items():
            tz = _get_version_tz(version)
            run_start = run_stop = None
            for day in sorted(version_days) + [None]:
                if run_stop and day == run_stop + timedelta(days=1):
                    run_stop = day
                    continue
                if run_start:
                    vals_list += version._get_work_entries_values(
                        tz.localize(datetime.combine(run_start, time.min)),
                        tz.localize(datetime.combine(run_stop, time.max)),
                    )
                run_start = run_stop = day
        return vals_list

    def _compute_can_cancel(self):
        super()._compute_can_cancel()

        cancellable_leaves = self.filtered('can_cancel')
        work_entries = self.env['hr.work.entry'].sudo().search([('state', '=', 'validated'), ('leave_id', 'in', cancellable_leaves.ids)])
        leave_ids = work_entries.mapped('leave_id').ids

        for leave in cancellable_leaves:
            leave.can_cancel = leave.id not in leave_ids
