# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
import itertools
from psycopg2 import OperationalError

from odoo import api, fields, models, tools, _
from odoo.osv import expression


class HrWorkEntry(models.Model):
    _name = 'hr.work.entry'
    _description = 'HR Work Entry'
    _order = 'conflict desc,state,date_start'

    name = fields.Char(required=True, compute='_compute_name', store=True, readonly=False)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True)
    date_start = fields.Datetime(required=True, string='From')
    date_stop = fields.Datetime(compute='_compute_date_stop', store=True, readonly=False, string='To')
    duration = fields.Float(compute='_compute_duration', store=True, string="Duration", readonly=False)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', index=True, default=lambda self: self.env['hr.work.entry.type'].search([], limit=1))
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
    _sql_constraints = [
        ('_work_entry_has_end', 'check (date_stop IS NOT NULL)', 'Work entry must end. Please define an end date or a duration.'),
        ('_work_entry_start_before_end', 'check (date_stop > date_start)', 'Starting time should be before end time.'),
        (
            '_work_entries_no_validated_conflict',
            """
                EXCLUDE USING GIST (
                    tsrange(date_start, date_stop, '()') WITH &&,
                    int4range(employee_id, employee_id, '[]') WITH =
                )
                WHERE (state = 'validated' AND active = TRUE)
            """,
            'Validated work entries cannot overlap'
        ),
    ]

    def init(self):
        tools.create_index(self._cr, "hr_work_entry_date_start_date_stop_index", self._table, ["date_start", "date_stop"])

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
        for work_entry in self.filtered(lambda w: w.date_start and w.duration):
            work_entry.date_stop = work_entry.date_start + relativedelta(hours=work_entry.duration)

    def _get_duration_batch(self):
        result = {}
        cached_periods = defaultdict(float)
        for work_entry in self:
            date_start = work_entry.date_start
            date_stop = work_entry.date_stop
            if not date_start or not date_stop:
                result[work_entry.id] = 0.0
                continue
            if (date_start, date_stop) in cached_periods:
                result[work_entry.id] = cached_periods[(date_start, date_stop)]
            else:
                dt = date_stop - date_start
                duration = dt.days * 24 + round(dt.total_seconds()) / 3600  # Number of hours
                cached_periods[(date_start, date_stop)] = duration
                result[work_entry.id] = duration
        return result

    def action_validate(self):
        """
        Try to validate work entries.
        If some errors are found, set `state` to conflict for conflicting work entries
        and validation fails.
        :return: True if validation succeded
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
        return undefined_type or conflict

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
        conflicts = set(itertools.chain.from_iterable(self.env.cr.fetchall()))
        self.browse(conflicts).write({
            'state': 'conflict',
        })
        return bool(conflicts)

    @api.model_create_multi
    def create(self, vals_list):
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


class HrWorkEntryType(models.Model):
    _name = 'hr.work.entry.type'
    _description = 'HR Work Entry Type'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string="Payroll Code", required=True, help="Careful, the Code is used in many references, changing it could lead to unwanted changes.")
    external_code = fields.Char(help="Use this code to export your data to a third party")
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=25)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to false, it will allow you to hide the work entry type without removing it.")

    _sql_constraints = [
        ('unique_work_entry_code', 'UNIQUE(code)', 'The same code cannot be associated to multiple work entry types.'),
    ]


class Contacts(models.Model):
    """ Personnal calendar filter """

    _name = 'hr.user.work.entry.employee'
    _description = 'Work Entries Employees'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('user_id_employee_id_unique', 'UNIQUE(user_id,employee_id)', 'You cannot have the same employee twice.')
    ]
