# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from itertools import chain

import pytz
from dateutil.relativedelta import relativedelta
from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.intervals import Intervals


class HrWorkEntry(models.Model):
    _name = 'hr.work.entry'
    _description = 'HR Work Entry'
    _order = 'conflict desc,state,date_start'

    name = fields.Char(required=True, compute='_compute_name', store=True, readonly=False, precompute=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True)
    version_id = fields.Many2one('hr.version', string="Version", required=True)
    work_entry_source = fields.Selection(related='version_id.work_entry_source')
    date_start = fields.Datetime(required=True, string='From')
    date_stop = fields.Datetime(compute='_compute_date_stop', store=True, readonly=False, string='To')
    duration = fields.Float(compute='_compute_duration', store=True, string="Duration", readonly=False)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', index=True, default=lambda self: self.env['hr.work.entry.type'].search([], limit=1), domain="['|', ('country_id', '=', False), ('country_id', '=', country_id)]")
    code = fields.Char(related='work_entry_type_id.code')
    external_code = fields.Char(related='work_entry_type_id.external_code')
    color = fields.Integer(related='work_entry_type_id.color', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('conflict', 'Conflict'),
        ('cancelled', 'Cancelled')
    ], default='draft')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)
    conflict = fields.Boolean('Conflicts', compute='_compute_conflict', store=True)  # Used to show conflicting work entries first
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    country_id = fields.Many2one('res.country', related='employee_id.company_id.country_id')

    # There is no way for _error_checking() to detect conflicts in work
    # entries that have been introduced in concurrent transactions, because of the transaction
    # isolation.
    # So if 2 transactions create work entries in parallel it is possible to create a conflict
    # that will not be visible by either transaction. There is no way to detect conflicts
    # between different records in a safe manner unless a SQL constraint is used, e.g. via
    # an EXCLUSION constraint [1]. This (obscure) type of constraint allows comparing 2 rows
    # using special operator classes and it also supports partial WHERE clauses. Similarly to
    # CHECK constraints, it's backed by an index.
    # 1: https://www.postgresql.org/docs/9.6/sql-createtable.html#SQL-CREATETABLE-EXCLUDE
    _work_entry_has_end = models.Constraint(
        'CHECK (date_stop IS NOT NULL)',
        'Work entry must end. Please define an end date or a duration.',
    )
    _work_entry_start_before_end = models.Constraint(
        'CHECK (date_stop > date_start)',
        'Starting time should be before end time.',
    )
    _work_entries_no_validated_conflict = models.Constraint(
        """
            EXCLUDE USING GIST (
                tsrange(date_start, date_stop, '()') WITH &&,
                int4range(employee_id, employee_id, '[]') WITH =
            )
            WHERE (state = 'validated' AND active = TRUE)
        """,
        'Validated work entries cannot overlap',
    )
    _date_start_date_stop_index = models.Index("(date_start, date_stop)")
    # FROM 7s by query to 2ms (with 2.6 millions entries)
    _contract_date_start_stop_idx = models.Index("(version_id, date_start, date_stop) WHERE state IN ('draft', 'validated')")

    @api.depends('work_entry_type_id', 'employee_id')
    def _compute_name(self):
        for work_entry in self:
            if not work_entry.employee_id:
                work_entry.name = _('Undefined')
            else:
                work_entry.name = "%s: %s" % (work_entry.work_entry_type_id.name or _('Undefined Type'), work_entry.employee_id.name)

    @api.depends('state')
    def _compute_conflict(self):
        for rec in self:
            rec.conflict = rec.state == 'conflict'

    @api.depends('date_stop', 'date_start')
    def _compute_duration(self):
        durations = self._get_duration_batch()
        for work_entry in self:
            work_entry.duration = durations[work_entry.id]

    @api.depends('date_start', 'duration')
    def _compute_date_stop(self):
        for work_entry in self:
            if work_entry._get_duration_is_valid():
                calendar = work_entry.version_id.resource_calendar_id
                if not calendar:
                    continue
                work_entry.date_stop = calendar.plan_hours(work_entry.duration, work_entry.date_start, compute_leaves=True)
                continue
            if work_entry.date_start and work_entry.duration:
                work_entry.date_stop = work_entry.date_start + relativedelta(hours=work_entry.duration)

    @api.onchange('employee_id', 'date_start', 'date_stop')
    def _onchange_version_id(self):
        vals = {
            'employee_id': self.employee_id.id,
            'date_start': self.date_start,
            'date_stop': self.date_stop,
        }
        try:
            res = self._set_current_contract(vals)
        except ValidationError:
            return
        if version_id := res.get('version_id'):
            self.version_id = version_id

    def _get_duration_is_valid(self):
        return self.work_entry_type_id and self.work_entry_type_id.is_leave

    def _get_duration_batch(self):
        no_version_work_entries = self.env['hr.work.entry']
        result = {}
        # {(date_start, date_stop): {calendar: employees}}
        mapped_periods = defaultdict(lambda: defaultdict(lambda: self.env['hr.employee']))
        for work_entry in self:
            if not work_entry.date_start or not work_entry.date_stop or not work_entry._is_duration_computed_from_calendar() or not work_entry.employee_id:
                no_version_work_entries |= work_entry
                continue
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            calendar = work_entry.version_id.resource_calendar_id
            if not calendar:
                result[work_entry.id] = 0.0
                continue
            employee = work_entry.version_id.employee_id
            mapped_periods[date_start, date_stop][calendar] |= employee

        # {(date_start, date_stop): {calendar: {'hours': foo}}}
        mapped_contract_data = defaultdict(lambda: defaultdict(lambda: {'hours': 0.0}))
        for (date_start, date_stop), employees_by_calendar in mapped_periods.items():
            for calendar, employees in employees_by_calendar.items():
                mapped_contract_data[date_start, date_stop][calendar] = employees._get_work_days_data_batch(
                    date_start, date_stop, compute_leaves=False, calendar=calendar)

        cached_periods = defaultdict(float)
        for work_entry in no_version_work_entries:
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            if not date_start or not date_stop:
                result[work_entry.id] = 0.0
                continue
            if (date_start, date_stop) in cached_periods:
                result[work_entry.id] = cached_periods[date_start, date_stop]
            else:
                dt = date_stop - date_start
                duration = round(dt.total_seconds()) / 3600  # Number of hours
                cached_periods[date_start, date_stop] = duration
                result[work_entry.id] = duration

        for work_entry in self - no_version_work_entries:
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            calendar = work_entry.version_id.resource_calendar_id
            employee = work_entry.version_id.employee_id
            result[work_entry.id] = mapped_contract_data[date_start, date_stop][calendar][employee.id]['hours'] if calendar else 0.0
        return result

    def _is_duration_computed_from_calendar(self):
        self.ensure_one()
        return self._get_duration_is_valid()

    @api.model
    def _set_current_contract(self, vals):
        if not vals.get('version_id') and vals.get('date_start') and vals.get('date_stop') and vals.get('employee_id'):
            contract_start = fields.Datetime.to_datetime(vals.get('date_start')).date()
            contract_end = fields.Datetime.to_datetime(vals.get('date_stop')).date()
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            contracts = employee._get_versions_with_contract_overlap_with_period(contract_start, contract_end)
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
            return dict(vals, version_id=contracts[0].id)
        return vals

    def action_validate(self):
        """
        Try to validate work entries.
        If some errors are found, set `state` to conflict for conflicting work entries
        and validation fails.
        :return: True if validation succeeded
        """
        work_entries = self.filtered(lambda work_entry: work_entry.state != 'validated')
        if not work_entries._check_if_error():
            work_entries.write({'state': 'validated'})
            return True
        return False

    def _check_if_error(self):
        if not self:
            return False
        undefined_type = self.filtered(lambda b: not b.work_entry_type_id)
        undefined_type.write({'state': 'conflict'})
        conflict = self._mark_conflicting_work_entries(min(self.mapped('date_start')), max(self.mapped('date_stop')))
        outside_calendar = self._mark_leaves_outside_schedule()
        return undefined_type or conflict or outside_calendar

    def _mark_conflicting_work_entries(self, start, stop):
        """
        Set `state` to `conflict` for overlapping work entries
        between two dates.
        If `self.ids` is truthy then check conflicts with the corresponding work entries.
        Return True if overlapping work entries were detected.
        """
        # Use the postgresql range type `tsrange` which is a range of timestamp
        # It supports the intersection operator (&&) useful to detect overlap.
        # use '()' to exlude the lower and upper bounds of the range.
        # Filter on date_start and date_stop (both indexed) in the EXISTS clause to
        # limit the resulting set size and fasten the query.
        self.flush_model(['date_start', 'date_stop', 'employee_id', 'active'])
        query = """
            SELECT b1.id,
                   b2.id
              FROM hr_work_entry b1
              JOIN hr_work_entry b2
                ON b1.employee_id = b2.employee_id
               AND b1.id <> b2.id
             WHERE b1.date_start <= %(stop)s
               AND b1.date_stop >= %(start)s
               AND b1.active = TRUE
               AND b2.active = TRUE
               AND tsrange(b1.date_start, b1.date_stop, '()') && tsrange(b2.date_start, b2.date_stop, '()')
               AND {}
        """.format("b2.id IN %(ids)s" if self.ids else "b2.date_start <= %(stop)s AND b2.date_stop >= %(start)s")
        self.env.cr.execute(query, {"stop": stop, "start": start, "ids": tuple(self.ids)})
        conflicts = set(chain.from_iterable(self.env.cr.fetchall()))
        self.browse(conflicts).write({
            'state': 'conflict',
        })
        return bool(conflicts)

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
            calendar = work_entry.version_id.resource_calendar_id
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
        return Intervals(
            ((w.date_start.replace(tzinfo=pytz.utc), w.date_stop.replace(tzinfo=pytz.utc), w) for w in self),
            keep_distinct=True)

    @api.model
    def _from_intervals(self, intervals):
        return self.browse(chain.from_iterable(recs.ids for start, end, recs in intervals))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._set_current_contract(vals) for vals in vals_list]
        company_by_employee_id = {}
        for vals in vals_list:
            if vals.get('company_id'):
                continue
            if vals['employee_id'] not in company_by_employee_id:
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                company_by_employee_id[employee.id] = employee.company_id.id
            vals['company_id'] = company_by_employee_id[vals['employee_id']]
        work_entries = super().create(vals_list)
        work_entries._check_if_error()
        return work_entries

    def write(self, vals):
        skip_check = not bool({'date_start', 'date_stop', 'employee_id', 'work_entry_type_id', 'active'} & vals.keys())
        if 'state' in vals:
            if vals['state'] == 'draft':
                vals['active'] = True
            elif vals['state'] == 'cancelled':
                vals['active'] = False
                skip_check &= all(self.mapped(lambda w: w.state != 'conflict'))

        if 'active' in vals:
            vals['state'] = 'draft' if vals['active'] else 'cancelled'

        employee_ids = self.employee_id.ids
        if 'employee_id' in vals and vals['employee_id']:
            employee_ids += [vals['employee_id']]
        with self._error_checking(skip=skip_check, employee_ids=employee_ids):
            return super(HrWorkEntry, self).write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_validated_work_entries(self):
        if any(w.state == 'validated' for w in self):
            raise UserError(_("This work entry is validated. You can't delete it."))

    def unlink(self):
        employee_ids = self.employee_id.ids
        with self._error_checking(employee_ids=employee_ids):
            return super().unlink()

    def _reset_conflicting_state(self):
        self.filtered(lambda w: w.state == 'conflict').write({'state': 'draft'})

    @contextmanager
    def _error_checking(self, start=None, stop=None, skip=False, employee_ids=False):
        """
        Context manager used for conflicts checking.
        When exiting the context manager, conflicts are checked
        for all work entries within a date range. By default, the start and end dates are
        computed according to `self` (min and max respectively) but it can be overwritten by providing
        other values as parameter.
        :param start: datetime to overwrite the default behaviour
        :param stop: datetime to overwrite the default behaviour
        :param skip: If True, no error checking is done
        """
        try:
            skip = skip or self.env.context.get('hr_work_entry_no_check', False)
            start = start or min(self.mapped('date_start'), default=False)
            stop = stop or max(self.mapped('date_stop'), default=False)
            if not skip and start and stop:
                domain = [
                    ('date_start', '<', stop),
                    ('date_stop', '>', start),
                    ('state', 'not in', ('validated', 'cancelled')),
                ]
                if employee_ids:
                    domain = expression.AND([domain, [('employee_id', 'in', list(employee_ids))]])
                work_entries = self.sudo().with_context(hr_work_entry_no_check=True).search(domain)
                work_entries._reset_conflicting_state()
            yield
        except OperationalError:
            # the cursor is dead, do not attempt to use it or we will shadow the root exception
            # with a "psycopg2.InternalError: current transaction is aborted, ..."
            skip = True
            raise
        finally:
            if not skip and start and stop:
                # New work entries are handled in the create method,
                # no need to reload work entries.
                work_entries.exists()._check_if_error()
