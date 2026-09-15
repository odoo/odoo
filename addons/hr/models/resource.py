from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models
from odoo.libs.datetime import localize_standard, timezone
from odoo.libs.intervals import Intervals

from ..tools import debug_log as dbg


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    user_id = fields.Many2one(copy=False)
    employee_id = fields.One2many(
        comodel_name="hr.employee",
        inverse_name="resource_id",
        context={"active_test": False},
        check_company=True,
    )
    job_title = fields.Char(
        compute="_compute_job_title",
        compute_sudo=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        compute_sudo=True,
    )
    work_location_id = fields.Many2one(related="employee_id.work_location_id")
    work_email = fields.Char(related="employee_id.work_email")
    show_hr_icon_display = fields.Boolean(related="employee_id.show_hr_icon_display")
    hr_icon_display = fields.Selection(related="employee_id.hr_icon_display")

    def get_avatar_card_data(self, field_names):
        stored = [fname for fname in field_names if fname != "work_phone"]
        data = super().get_avatar_card_data(stored)
        if "work_phone" in field_names:
            for resource, values in zip(self, data, strict=True):
                values["work_phone"] = resource.employee_id.phone_ids._primary().number
        return data

    @api.depends("employee_id")
    def _compute_job_title(self):
        for resource in self:
            resource.job_title = resource.employee_id.job_title

    @api.depends("employee_id")
    def _compute_department_id(self):
        for resource in self:
            resource.department_id = resource.employee_id.department_id

    @api.depends_context("uid")
    @api.depends("employee_id")
    def _compute_avatar_128(self):
        super()._compute_avatar_128()
        for resource in self:
            employee = resource.employee_id
            if employee:
                resource.avatar_128 = employee[0].avatar_128

    @dbg.timed
    def _get_resources_without_contract(self):
        employee_ids_with_active_contracts = {
            employee.id
            for [employee] in self.env["hr.version"]._read_group(
                domain=[
                    ("employee_id", "in", self.employee_id.ids),
                    ("contract_date_start", "!=", False),
                ],
                groupby=["employee_id"],
            )
        }
        without = self.filtered(
            lambda r: (
                not r.employee_id
                or r.employee_id.id not in employee_ids_with_active_contracts
            )
        )
        dbg.logic.debug(
            "_get_resources_without_contract on %s: %d employee(s) under contract, "
            "%s without",
            dbg.rec(self),
            len(employee_ids_with_active_contracts),
            dbg.rec(without),
        )
        return without

    @dbg.timed
    def _get_contracts_valid_periods(self, start, end):
        res = defaultdict(lambda: defaultdict(Intervals))
        timezones = {resource.tz for resource in self}
        date_start = min(start.astimezone(timezone(tz)).date() for tz in timezones)
        date_end = max(end.astimezone(timezone(tz)).date() for tz in timezones)
        contracts = self.employee_id._get_versions_with_contract_overlap_with_period(
            date_start, date_end
        )
        dbg.logic.debug(
            "_get_contracts_valid_periods on %s (%s..%s, %d tz): versions %s",
            dbg.rec(self),
            date_start,
            date_end,
            len(timezones),
            dbg.rec(contracts),
        )
        for contract in contracts:
            tz = timezone(contract.employee_id.tz)
            if contract.date_start > start.astimezone(tz).date():
                interval_start = localize_standard(
                    datetime.combine(contract.date_start, datetime.min.time()),
                    tz,
                )
            else:
                interval_start = start
            if contract.date_end and contract.date_end < end.astimezone(tz).date():
                interval_end = localize_standard(
                    datetime.combine(contract.date_end, datetime.max.time()),
                    tz,
                )
            else:
                interval_end = end
            if interval_start >= interval_end:
                continue
            res[contract.employee_id.resource_id.id][contract.resource_calendar_id] |= (
                Intervals(
                    [
                        (
                            interval_start,
                            interval_end,
                            self.env["resource.calendar.attendance"],
                        )
                    ]
                )
            )
        return res

    @dbg.timed
    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        assert start.tzinfo and end.tzinfo
        if not self:
            return super()._get_calendars_validity_within_period(
                start, end, default_company=default_company
            )
        calendars_within_period_per_resource = defaultdict(
            lambda: defaultdict(Intervals)
        )
        resource_without_contract = self._get_resources_without_contract()
        if resource_without_contract:
            calendars_within_period_per_resource.update(
                super(
                    ResourceResource, resource_without_contract
                )._get_calendars_validity_within_period(
                    start, end, default_company=default_company
                )
            )
        resource_with_contract = self - resource_without_contract
        dbg.logic.debug(
            "_get_calendars_validity_within_period on %s: %s from resource "
            "calendars, %s from contracts",
            dbg.rec(self),
            dbg.rec(resource_without_contract),
            dbg.rec(resource_with_contract),
        )
        if not resource_with_contract:
            return calendars_within_period_per_resource

        calendars_within_period_per_resource.update(
            resource_with_contract._get_contracts_valid_periods(start, end)
        )
        return calendars_within_period_per_resource

    @dbg.timed
    def _get_flexible_resources_calendars_validity_within_period(self, start, end):
        assert start.tzinfo and end.tzinfo
        resource_default_work_intervals = (
            self._get_flexible_resources_default_work_intervals(start, end)
        )

        calendars_within_period_per_resource = defaultdict(
            lambda: defaultdict(Intervals)
        )
        resource_without_contract = self.sudo()._get_resources_without_contract()
        for resource in resource_without_contract:
            calendar = False if resource._is_fully_flexible() else resource.calendar_id
            calendars_within_period_per_resource[resource.id][calendar] = (
                resource_default_work_intervals[resource.id]
            )

        resource_with_contract = self - resource_without_contract
        dbg.logic.debug(
            "_get_flexible_resources_calendars_validity_within_period on %s: %s "
            "default intervals, %s intersected with contracts",
            dbg.rec(self),
            dbg.rec(resource_without_contract),
            dbg.rec(resource_with_contract),
        )
        if resource_with_contract:
            resource_contracts_valid_periods = (
                resource_with_contract.sudo()._get_contracts_valid_periods(start, end)
            )
            for (
                resource_id,
                calendar_intervals,
            ) in resource_contracts_valid_periods.items():
                for calendar_id, intervals in calendar_intervals.items():
                    calendars_within_period_per_resource[resource_id][calendar_id] = (
                        intervals & resource_default_work_intervals[resource_id]
                    )

        return calendars_within_period_per_resource

    def _get_calendar_at(self, date_target, tz=False):
        result = super()._get_calendar_at(date_target, tz)
        resources_with_employee = self.filtered(lambda r: r.employee_id)
        if not resources_with_employee:
            return result
        zones = resources_with_employee.grouped(
            lambda resource: tz or timezone(resource.tz)
        )
        for zone, resources in zones.items():
            date_at = date_target.astimezone(zone)
            employee_calendars = resources.employee_id._get_calendars(date_at)
            dbg.logic.debug(
                "_get_calendar_at on %s at %s: %s take their employee's calendar",
                dbg.rec(self),
                date_at,
                dbg.rec(resources),
            )
            for resource in resources:
                result[resource] = employee_calendars[resource.employee_id.id]
        return result
