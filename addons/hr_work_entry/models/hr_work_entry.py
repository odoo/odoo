# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from itertools import chain

import pytz
from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools.intervals import Intervals


class HrWorkEntry(models.Model):
    _name = 'hr.work.entry'
    _description = 'HR Work Entry'
    _order = 'create_date'

    name = fields.Char()
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True)
    version_id = fields.Many2one('hr.version', string="Employee Record", required=True, index=True)
    work_entry_source = fields.Selection(related='version_id.work_entry_source')
    date = fields.Date(required=True)
    duration = fields.Float(string="Duration", default=8)
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        index=True,
        default=lambda self: self.env['hr.work.entry.type'].search([], limit=1),
        domain=lambda self: self._get_work_entry_type_domain())
    display_code = fields.Char(related='work_entry_type_id.display_code')
    code = fields.Char(related='work_entry_type_id.code')
    external_code = fields.Char(related='work_entry_type_id.external_code')
    color = fields.Integer(related='work_entry_type_id.color', readonly=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('conflict', 'In Conflict'),
        ('validated', 'In Payslip'),
        ('cancelled', 'Cancelled')
    ], default='draft')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True,
        default=lambda self: self.env.company)
    conflict = fields.Boolean('Conflicts', compute='_compute_conflict', store=True)  # Used to show conflicting work entries first
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    country_id = fields.Many2one('res.country', related='employee_id.company_id.country_id')
    amount_rate = fields.Float("Pay rate")

    # FROM 7s by query to 2ms (with 2.6 millions entries)
    _contract_date_start_stop_idx = models.Index("(version_id, date) WHERE state IN ('draft', 'validated')")

    @api.depends('display_code', 'duration')
    def _compute_display_name(self):
        for work_entry in self:
            duration = str(timedelta(hours=work_entry.duration)).split(":")
            work_entry.display_name = "%s - %sh%s" % (work_entry.work_entry_type_id.name, duration[0], duration[1])

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

    @api.onchange('employee_id', 'date')
    def _onchange_version_id(self):
        vals = {
            'employee_id': self.employee_id.id,
            'date': self.date,
        }
        try:
            res = self._set_current_contract(vals)
        except ValidationError:
            return
        if version_id := res.get('version_id'):
            self.version_id = version_id

    @api.model
    def _set_current_contract(self, vals):
        if not vals.get('version_id') and vals.get('date') and vals.get('employee_id'):
            contract_start = fields.Datetime.to_datetime(vals.get('date'))
            contract_end = contract_start
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            contracts = employee._get_versions_with_contract_overlap_with_period(contract_start, contract_end)
            if not contracts:
                raise ValidationError(_(
                    "%(employee)s does not have a contract on %(date)s.",
                    employee=employee.name,
                    date=contract_start,
                ))
            return dict(vals, version_id=contracts[0].id)
        return vals

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.company.resource_calendar_id._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=pytz.utc),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=pytz.utc),
            self.company_id,
        )

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

    def action_split(self, vals):
        self.ensure_one()
        if self.duration < 1:
            raise UserError(self.env._("You can't split a work entry with less than 1 hour."))
        split_duration = vals['duration']
        if self.duration <= split_duration:
            raise UserError(
                self.env._(
                    "Split work entry duration has to be less than the existing work entry duration."
                )
            )
        self.duration -= split_duration
        split_work_entry = self.copy()
        split_work_entry.write(vals)
        return split_work_entry.id

    def _check_if_error(self):
        if not self:
            return False
        undefined_type = self.filtered(lambda b: not b.work_entry_type_id)
        undefined_type.write({'state': 'conflict'})
        conflict = self._mark_conflicting_work_entries(min(self.mapped('date')), max(self.mapped('date')))
        outside_calendar = self._mark_leaves_outside_schedule()
        return undefined_type or conflict or outside_calendar

    def _mark_conflicting_work_entries(self, start, stop):
        """
        Set `state` to `conflict` for work entries where, for the same employee and day,
        the total duration exceeds 24 hours.
        Return True if such entries are found.
        """
        self.flush_model(['date', 'duration', 'employee_id', 'active'])
        query = """
            WITH excessive_days AS (
                SELECT employee_id, date
                FROM hr_work_entry
                WHERE active = TRUE
                  AND date BETWEEN %(start)s AND %(stop)s
                  {ids_filter}
                GROUP BY employee_id, date
                HAVING SUM(duration) > 1000
            )
            SELECT we.id
            FROM hr_work_entry we
            JOIN excessive_days ed
              ON we.employee_id = ed.employee_id
             AND we.date = ed.date
            WHERE we.active = TRUE
        """.format(
            ids_filter="AND id IN %(ids)s" if self.ids else ""
        )
        self.env.cr.execute(query, {
            "start": start,
            "stop": stop,
            "ids": tuple(self.ids) if self.ids else (),
        })
        conflict_ids = [row[0] for row in self.env.cr.fetchall()]
        self.browse(conflict_ids).write({'state': 'conflict'})
        return bool(conflict_ids)

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
            datetime_start = datetime.combine(min(entries.mapped('date')), time.min)
            datetime_stop = datetime.combine(max(entries.mapped('date')), time.max)

            if calendar:
                calendar_intervals = calendar._attendance_intervals_batch(pytz.utc.localize(datetime_start), pytz.utc.localize(datetime_stop))[False]
            else:
                calendar_intervals = Intervals([(pytz.utc.localize(datetime_start), pytz.utc.localize(datetime_stop), self.env['resource.calendar.attendance'])])
            entries_intervals = entries._to_intervals()
            overlapping_entries = self._from_intervals(entries_intervals & calendar_intervals)
            outside_entries |= entries - overlapping_entries
        outside_entries.write({'state': 'conflict'})
        return bool(outside_entries)

    def _to_intervals(self):
        return Intervals(
            ((datetime.combine(w.date, time.min).replace(tzinfo=pytz.utc), datetime.combine(w.date, time.max).replace(tzinfo=pytz.utc), w) for w in self),
            keep_distinct=True)

    @api.model
    def _from_intervals(self, intervals):
        return self.browse(chain.from_iterable(recs.ids for start, end, recs in intervals))

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._set_current_contract(vals) for vals in vals_list]
        company_by_employee_id = {}
        for vals in vals_list:
            if (
                not 'amount_rate' in vals
                and (work_entry_type_id := vals.get('work_entry_type_id'))
            ):
                work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
                vals['amount_rate'] = work_entry_type.amount_rate
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
            return super().write(vals)

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
            start = start or min(self.mapped('date'), default=False)
            stop = stop or max(self.mapped('date'), default=False)
            if not skip and start and stop:
                domain = (
                    Domain('date', '<=', stop)
                    & Domain('date', '>=', start)
                    & Domain('state', 'not in', ('validated', 'cancelled'))
                )
                if employee_ids:
                    domain &= Domain('employee_id', 'in', list(employee_ids))
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

    def _get_work_entry_type_domain(self):
        if len(self.env.companies.country_id.ids) > 1:
            return [('country_id', '=', False)]
        return ['|', ('country_id', '=', False), ('country_id', 'in', self.env.companies.country_id.ids)]
