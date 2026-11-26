
from datetime import UTC

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError
from odoo.tools import SQL
from odoo.tools.intervals import Intervals


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    version_ids = fields.One2many('hr.version', 'resource_calendar_id', readonly=True, copy=False)
    employees_count = fields.Integer(string="Employees Count", compute="_compute_employees_count")
    material_resources_count = fields.Integer(string="Material Resources Count", compute="_compute_material_resources_count")

    def _access_domain(self, operation):
        """Grant read access to the working schedules of the resources of the employees having a version in the
        current companies.

        The resource of an employee moved to another company follows its current version, and so does its working
        schedule: without this, reading the employee from the companies of its other versions (e.g. its working
        hours) would fail (see ``resource.resource._access_domain``).
        """
        domain = super()._access_domain(operation)
        if operation != 'read' or domain.is_false() or domain.is_true():
            return domain
        versions = self.env['hr.version'].sudo()._search([('company_id', 'in', self.env.companies.ids)])
        resources = self.env['resource.resource'].sudo()._search([
            ('employee_id', 'any', Domain('id', 'in', versions.select(SQL('employee_id')))),
            ('calendar_id', '!=', False),
        ])
        return domain | Domain('id', 'in', resources.select(SQL('calendar_id')))

    @api.constrains('company_id')
    def _check_company_id(self):
        for res_calendar in self:
            if res_calendar.company_id:
                if any(res_calendar.company_id not in version.company_id.parent_ids for version in res_calendar.version_ids):
                    raise ValidationError(self.env._("The working schedule '%s' is linked to version(s) not compatible with its new company.") % res_calendar.name)

    def write(self, vals):
        """Refuse to modify a calendar used by versions of companies the user has not selected.

        :raise ValidationError: if a version using the calendar belongs to a
            company outside ``env.companies``
        """
        if self.sudo().version_ids.company_id - self.env.companies:
            raise ValidationError(self.env._("You can't change this working schedule, it's used by employees from other companies you don't have access to. Contact your admin or create a new working schedule."))
        return super().write(vals)

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Employees with a flexible calendar have no working hours: they are unavailable
        the whole period, except during their leaves counted as working time (e.g. a
        training). The other resources keep the ``resource`` behavior. """
        result = super()._unavailable_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
        flexible_employees = {
            resource
            for resources in (resources_per_tz or {}).values()
            for resource in resources
            # sudo: resource.resource - hr.employee is restricted to HR officers
            if resource.sudo().employee_id and resource._is_flexible()
        }
        if not flexible_employees:
            return result
        working_time_leaves = self._leave_intervals_batch(
            start_dt, end_dt, resources_per_tz, [('count_as', '=', 'working_time')])
        full_interval = Intervals([(start_dt.astimezone(UTC), end_dt.astimezone(UTC), self.env['resource.calendar'])])
        for resource in flexible_employees:
            result[resource.id] = full_interval - Intervals([
                (start.astimezone(UTC), stop.astimezone(UTC), self.env['resource.calendar.attendance'])
                for start, stop, _leave in working_time_leaves[resource.id]
            ])
        return result

    def _compute_employees_count(self):
        employees_per_calendar = dict(self.env['hr.version']._read_group(
            domain=[
                ('company_id', 'child_of', self.mapped('company_id').ids),
                ('resource_calendar_id', 'in', self.ids),
            ],
            groupby=['resource_calendar_id'],
            aggregates=['employee_id:count_distinct'],
        ))
        for calendar in self:
            calendar.employees_count = employees_per_calendar.get(calendar, 0)

    def _compute_material_resources_count(self):
        materials_per_calendar = dict(self.env['resource.resource']._read_group(
            domain=[
                ('resource_type', '=', 'material'),
                ('calendar_id', 'in', self.ids),
            ],
            groupby=['calendar_id'],
            aggregates=['__count'],
        ))
        for calendar in self:
            calendar.material_resources_count = materials_per_calendar.get(calendar, 0)

    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """Move the leaves of these calendars starting from ``from_date`` to ``other_calendar``.

        :param other_calendar: the target calendar
        :type other_calendar: resource.calendar
        :param resources: only move the leaves of these resources (all leaves if empty/``None``)
        :type resources: resource.resource or None
        :param from_date: only move leaves with ``date_from >= from_date``;
            today 00:00 (naive UTC) by default
        :type from_date: datetime.datetime or None
        """
        from_date = from_date or fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = Domain.AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })

    def action_duplicate_and_apply_to_employee(self):
        """
        Duplicates the current calendar and automatically assigns the new duplicate
        to the employee passed via context from the employee form view navigation.
        """
        self.ensure_one()
        employee_id = self.env.context.get('employee_id')
        employee = self.env['hr.employee'].browse(employee_id).exists() if employee_id else False

        if not employee:
            return False

        new_calendar = self.copy()
        new_calendar.write({
            'name': self.env._("%(calendar_name)s (%(employee_name)s)",
                calendar_name=self.name,
                employee_name=employee.name,
        )})

        employee.sudo().write({'resource_calendar_id': new_calendar.id})

        return {
            'name': self.env._('Working Schedule'),
            'type': 'ir.actions.act_window',
            'res_model': 'resource.calendar',
            'view_mode': 'form',
            'res_id': new_calendar.id,
            'target': 'current',
        }

    def action_view_employees(self):
        self.ensure_one()
        return {
            'name': self.env._('Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('version_ids', 'any', [('resource_calendar_id', '=', self.id)])],
            'context': {'default_resource_calendar_id': self.id},
            'target': 'current',
        }
