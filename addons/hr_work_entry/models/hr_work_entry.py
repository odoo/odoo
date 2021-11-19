# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
import itertools
from psycopg2 import OperationalError

from odoo import api, fields, models, tools


class HrWorkEntry(models.Model):
    _name = 'hr.work.entry'
    _description = 'HR Work Entry'
    _order = 'conflict desc,state,date_start'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one('hr.employee', required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", index=True)
    date_start = fields.Datetime(required=True, string='From')
    date_stop = fields.Datetime(compute='_compute_date_stop', store=True, readonly=False, string='To')
    duration = fields.Float(compute='_compute_duration', store=True, string="Period")
    work_entry_type_id = fields.Many2one('hr.work.entry.type', index=True)
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

    _sql_constraints = [
        ('_work_entry_has_end', 'check (date_stop IS NOT NULL)', 'Work entry must end. Please define an end date or a duration.'),
        ('_work_entry_start_before_end', 'check (date_stop > date_start)', 'Starting time should be before end time.')
    ]

    def init(self):
        tools.create_index(self._cr, "hr_work_entry_date_start_date_stop_index", self._table, ["date_start", "date_stop"])

    @api.depends('state')
    def _compute_conflict(self):
        for rec in self:
            rec.conflict = rec.state == 'conflict'

    @api.depends('date_stop', 'date_start')
    def _compute_duration(self):
        for work_entry in self:
            work_entry.duration = work_entry._get_duration(work_entry.date_start, work_entry.date_stop)

    @api.depends('date_start', 'duration')
    def _compute_date_stop(self):
        for work_entry in self.filtered(lambda w: w.date_start and w.duration):
            work_entry.date_stop = work_entry.date_start + relativedelta(hours=work_entry.duration)

    def _get_duration(self, date_start, date_stop):
        if not date_start or not date_stop:
            return 0
        dt = date_stop - date_start
        return dt.days * 24 + dt.seconds / 3600  # Number of hours

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
        self.flush(['date_start', 'date_stop', 'employee_id', 'active'])
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

        with self._error_checking(skip=skip_check):
            return super(HrWorkEntry, self).write(vals)

    def unlink(self):
        with self._error_checking():
            return super().unlink()

    def _reset_conflicting_state(self):
        self.filtered(lambda w: w.state == 'conflict').write({'state': 'draft'})

    @contextmanager
    def _error_checking(self, start=None, stop=None, skip=False):
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
                work_entries = self.sudo().with_context(hr_work_entry_no_check=True).search([
                    ('date_start', '<', stop),
                    ('date_stop', '>', start),
                    ('state', 'not in', ('validated', 'cancelled')),
                ])
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
    code = fields.Char(required=True)
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

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)

    _sql_constraints = [
        ('user_id_employee_id_unique', 'UNIQUE(user_id,employee_id)', 'You cannot have the same employee twice.')
    ]
