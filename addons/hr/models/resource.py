# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.tools.intervals import Intervals
from odoo.addons.mail.tools.discuss import Store


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many('hr.employee', 'resource_id', check_company=True, context={'active_test': False})
    tz = fields.Selection(compute='_compute_tz', inverse='_inverse_tz', store=True, readonly=False)

    job_title = fields.Char(compute='_compute_job_title', compute_sudo=True)
    department_id = fields.Many2one('hr.department', compute='_compute_department_id', compute_sudo=True)
    work_location_id = fields.Many2one(related='employee_id.work_location_id')
    work_email = fields.Char(related='employee_id.work_email')
    work_phone = fields.Char(related='employee_id.work_phone')
    show_hr_icon_display = fields.Boolean(related='employee_id.show_hr_icon_display')
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display')
    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
    calendar_id = fields.Many2one(compute='_compute_calendar_id', inverse='_inverse_calendar_id', store=True, readonly=False)

    @api.depends('employee_id.current_version_id.tz')
    def _compute_tz(self):
        for resource in self.filtered('employee_id.current_version_id'):
            resource.tz = resource.employee_id.current_version_id.tz

    @api.depends('employee_id.current_version_id.resource_calendar_id')
    def _compute_calendar_id(self):
        """Follow the calendar of the employee's current version (the resource keeps its
        calendar when it has no employee)."""
        for resource in self.filtered('employee_id.current_version_id'):
            resource.calendar_id = resource.employee_id.current_version_id.resource_calendar_id

    def _inverse_tz(self):
        for resource in self.filtered('employee_id'):
            resource.employee_id.current_version_id.tz = resource.tz

    @api.depends('employee_id')
    def _compute_job_title(self):
        for resource in self:
            resource.job_title = resource.employee_id.job_title

    @api.depends('employee_id')
    def _compute_department_id(self):
        for resource in self:
            resource.department_id = resource.employee_id.department_id

    @api.depends('employee_id')
    def _compute_avatar_128(self):
        for resource in self:
            employee = resource.employee_id
            if not employee:
                resource.avatar_128 = False
                continue
            resource.avatar_128 = employee[0].avatar_128

    def _inverse_calendar_id(self):
        """Propagate a calendar written on the resource to its employee (i.e. the employee's current version)."""
        for resource in self:
            if resource.calendar_id != resource.employee_id.resource_calendar_id:
                resource.employee_id.resource_calendar_id = resource.calendar_id

    def _get_resource_without_contract(self):
        """Return the resources that are not employees, or whose employee never had a contract.

        "Ever": any active version with a ``contract_date_start``, whatever the
        dates. Such resources keep the plain ``resource`` behavior (their own
        ``calendar_id`` over the whole period).

        :rtype: resource.resource
        """
        employee_ids_with_active_contracts = {
            employee.id for [employee] in
            self.env['hr.version']._read_group(
                domain=[
                    ('employee_id', 'in', self.employee_id.ids),
                    ('contract_date_start', '!=', False),
                ],
                groupby=['employee_id'],
            )
        }
        return self.filtered(
            lambda r: not r.employee_id
                   or not r.employee_id.id in employee_ids_with_active_contracts
        )

    def _get_contracts_valid_periods(self, start, end):
        """Return, per resource and calendar, the intervals within ``[start, end]`` covered by a version in contract.

        Each version in contract during the period
        (``hr.employee._get_versions_with_contract_overlap_with_period``)
        contributes the interval from its ``date_start`` 00:00 to its
        ``date_end`` 23:59:59 (in the employee's timezone), clipped to
        ``[start, end]``. Periods out of contract are absent.

        :param datetime.datetime start: timezone-aware start
        :param datetime.datetime end: timezone-aware end
        :return: ``{resource_id: {resource.calendar: Intervals}}`` (nested ``defaultdict``)
        :rtype: dict
        """
        res = defaultdict(lambda: defaultdict(Intervals))
        timezones = {resource.tz for resource in self}
        date_start = min(start.astimezone(ZoneInfo(tz)).date() for tz in timezones)
        date_end = max(end.astimezone(ZoneInfo(tz)).date() for tz in timezones)
        contracts = self.employee_id._get_versions_with_contract_overlap_with_period(date_start, date_end)
        for contract in contracts:
            tz = ZoneInfo(contract.employee_id.tz)
            res[contract.employee_id.resource_id.id][contract.resource_calendar_id] |= Intervals([(
                datetime.combine(contract.date_start, datetime.min.time(), tzinfo=tz) if contract.date_start > start.astimezone(tz).date() else start,
                datetime.combine(contract.date_end, datetime.max.time(), tzinfo=tz) if contract.date_end and contract.date_end < end.astimezone(tz).date() else end,
                self.env['resource.calendar.attendance']
            )])
        return res

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        """Return the calendars of each resource with their validity intervals, following the employees' contracts.

        Resources of employees who ever had a contract get one entry per
        calendar used by their versions in contract, valid only while in
        contract (:meth:`_get_contracts_valid_periods`): out of contract, they
        have no calendar, hence no work time. Other resources keep the
        ``resource`` behavior (own calendar, whole period).

        :param datetime.datetime start: timezone-aware start
        :param datetime.datetime end: timezone-aware end
        :param default_company: company whose calendar is used when ``self`` is empty
        :type default_company: res.company or None
        :return: ``{resource_id: {resource.calendar: Intervals}}``
        :rtype: dict
        """
        assert start.tzinfo and end.tzinfo
        if not self:
            return super()._get_calendars_validity_within_period(start, end, default_company=default_company)
        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        # Employees that have ever had an active contract
        resource_without_contract = self._get_resource_without_contract()
        if resource_without_contract:
            calendars_within_period_per_resource.update(
                super(ResourceResource, resource_without_contract)._get_calendars_validity_within_period(start, end, default_company=default_company)
            )
        resource_with_contract = self - resource_without_contract
        if not resource_with_contract:
            return calendars_within_period_per_resource

        calendars_within_period_per_resource.update(resource_with_contract._get_contracts_valid_periods(start, end))
        return calendars_within_period_per_resource

    def _get_flexible_resources_calendars_validity_within_period(self, start, end):
        """Same as :meth:`_get_calendars_validity_within_period` for flexible resources.

        The validity intervals are intersected with the resources' default
        work intervals (``_get_flexible_resources_default_work_intervals``).
        For resources without contract, fully flexible ones are keyed by
        ``False`` instead of a calendar.

        :param datetime.datetime start: timezone-aware start
        :param datetime.datetime end: timezone-aware end
        :return: ``{resource_id: {resource.calendar or False: Intervals}}``
        :rtype: dict
        """
        assert start.tzinfo and end.tzinfo
        resource_default_work_intervals = self._get_flexible_resources_default_work_intervals(start, end)

        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        # Employees that have ever had an active contract
        resource_without_contract = self.sudo()._get_resource_without_contract()
        for resource in resource_without_contract:
            calendar = False if resource._is_fully_flexible() else resource.calendar_id
            calendars_within_period_per_resource[resource.id][calendar] = resource_default_work_intervals[resource.id]

        resource_with_contract = self - resource_without_contract
        if resource_with_contract:
            resource_contracts_valid_periods = resource_with_contract.sudo()._get_contracts_valid_periods(start, end)
            # r: calendar: Intervals
            for resource_id, calendar_intervals in resource_contracts_valid_periods.items():
                for calendar_id, intervals in calendar_intervals.items():
                    calendars_within_period_per_resource[resource_id][calendar_id] = intervals & resource_default_work_intervals[resource_id]

        return calendars_within_period_per_resource

    def _get_calendar_data_at(self, date_target, tz=False):
        """Return the calendar, hours per week and hours per day of each resource on a given day.

        For employees, the calendar of the version in contract on the day
        (``date_target`` converted to ``tz``) is used, see
        ``hr.employee._get_calendars``; other resources use their own calendar.

        :param datetime.datetime date_target: timezone-aware datetime
        :param tz: timezone in which ``date_target``'s day is evaluated
        :type tz: zoneinfo.ZoneInfo
        :return: ``{resource: {'resource_calendar_id': resource.calendar,
            'hours_per_week': float, 'hours_per_day': float}}``
        :rtype: dict
        """
        result = super()._get_calendar_data_at(date_target)
        resources_with_employee = self.filtered('employee_id')
        # The hours per week and per day are those of the calendar (see _get_hours_per_week_batch
        # and _get_hours_per_day_batch): the version in effect is looked up once.
        employee_calendars = resources_with_employee.employee_id._get_calendars(date_target.astimezone(tz))
        for resource in resources_with_employee:
            calendar = employee_calendars[resource.employee_id.id]
            result[resource] = {
                'resource_calendar_id': calendar,
                'hours_per_week': calendar.sudo().hours_per_week,
                'hours_per_day': calendar.sudo().hours_per_day,
            }
        return result

    def _get_calendar_tz_periods(self, start, stop):
        """Follow the versions in contract of the employees: one period per version, with its
        working schedule and timezone. An employee without contract in the period has no period.
        Other resources keep their own calendar and timezone."""
        result = super()._get_calendar_tz_periods(start, stop)
        resources_with_employee = self.filtered('employee_id')
        version_periods = resources_with_employee.employee_id.sudo()._get_version_periods(
            start, stop, ['resource_calendar_id', 'tz'], check_contract=True)
        for resource in resources_with_employee:
            result[resource] = [
                (date_from, date_to, calendar, tz)
                for date_from, date_to, (calendar, tz) in version_periods.get(resource.employee_id[:1], [])
            ]
        return result

    def _store_avatar_card_fields(self, res: Store.FieldList):
        super()._store_avatar_card_fields(res)
        res.one("department_id", ["name"])
        # sudo: resource.resource - can access employee information of resource
        res.one("employee_id", "_store_avatar_card_fields", sudo=True)
