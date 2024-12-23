# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from contextlib import contextmanager
from dateutil.relativedelta import relativedelta
import itertools
from psycopg2 import OperationalError
from odoo.exceptions import UserError

from odoo import api, fields, models, _
from odoo.osv import expression
from dateutil import parser


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
                duration = dt.days * 24 + dt.seconds / 3600  # Number of hours
                cached_periods[(date_start, date_stop)] = duration
                result[work_entry.id] = duration
        return result

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

    @api.model
    def calendar_panel_create(self, params, vals):
        start_dt = params["start"]
        end_dt = params.get("end", False) or start_dt

        start_dt = parser.isoparse(start_dt).replace(tzinfo=None)
        end_dt = parser.isoparse(end_dt).replace(tzinfo=None)

        wtype_id = vals.get("work_entry_type_id")
        employee_id = vals.get("employee_id")
        wtype_id = self.env['hr.work.entry.type'].browse(int(wtype_id or 1)) or 1

        if employee_id:
            emp = self.env['hr.employee'].browse(int(employee_id))
            current_contracts = emp._get_contracts(start_dt, end_dt, states=["open", "close"])
        else:
            current_contracts = self.env['hr.employee']._get_all_contracts(start_dt, end_dt, states=["open", "close"])

        vals = current_contracts.generate_work_entry_vals(start_dt.date(), end_dt.date(), force=True)

        for val in vals:
            val['work_entry_type_id'] = wtype_id.id
        return self.create(vals)

    @api.model
    def calendar_panel_replace(self, params, vals):
        start_dt = params["start"]
        end_dt = params.get("end", False) or start_dt

        start_dt = parser.isoparse(start_dt).replace(tzinfo=None)
        end_dt = parser.isoparse(end_dt).replace(tzinfo=None).replace(hour=23, minute=59, second=59)

        domain = [('date_start', '>', start_dt), ('date_stop', '<', end_dt)]

        if "employee_id" in vals:
            domain.append(('employee_id', '=', vals.get('employee_id')))

        wtype_id = vals.get("work_entry_type_id")
        wtype_id = self.env['hr.work.entry.type'].browse(int(wtype_id or 1)) or 1

        valid_work_entries = self.env['hr.work.entry'].search(domain)

        valid_work_entries.write({
            'work_entry_type_id': wtype_id
        })

        return valid_work_entries


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
    country_id = fields.Many2one('res.country', string="Country")
    country_code = fields.Char(related='country_id.code')

    @api.constrains('country_id')
    def _check_work_entry_type_country(self):
        if self.env.ref('hr_work_entry.work_entry_type_attendance') in self:
            raise UserError(_("You can't change the country of this specific work entry type."))
        elif not self.env.context.get('install_mode') and self.env['hr.work.entry'].sudo().search_count([('work_entry_type_id', 'in', self.ids)], limit=1):
            raise UserError(_("You can't change the Country of this work entry type cause it's currently used by the system. You need to delete related working entries first."))

    @api.constrains('code', 'country_id')
    def _check_code_unicity(self):
        similar_work_entry_types = self.search([
            ('code', 'in', self.mapped('code')),
            ('country_id', 'in', self.country_id.ids + [False]),
            ('id', 'not in', self.ids)
        ])
        for work_entry_type in self:
            if similar_work_entry_types.filtered_domain([
                ('code', '=', work_entry_type.code),
                ('country_id', 'in', self.country_id.ids + [False]),
            ]):
                raise UserError(_("The same code cannot be associated to multiple work entry types."))





class HrUserWorkEntryEmployee(models.Model):
    """ Personnal calendar filter """

    _description = 'Work Entries Employees'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)

    _user_id_employee_id_unique = models.Constraint(
        'UNIQUE(user_id,employee_id)',
        'You cannot have the same employee twice.',
    )
