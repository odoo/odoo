from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self

from odoo import api, fields, models
from odoo.models import ValuesType
from odoo.tools.date_utils import localized

if TYPE_CHECKING:
    from .resource_calendar import ResourceCalendar


class MixinResource(models.AbstractModel):
    """One record of the host model is one resource.

    `_resource_type` says what kind of slot the host is. `_resource_owns` says
    whether the host owns its resource: an owner creates it, copies it and
    carries its identity; a host that does not own references a resource
    somebody else answers for, gets a bare one only when given none, and takes
    a fresh one when copied.
    """

    _name = "mixin.resource"
    _description = "Resource Mixin"
    _resource_type = "user"
    _resource_owns = True

    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        index="unique",
        required=True,
        ondelete="restrict",
        bypass_search_access=True,
    )
    tz = fields.Selection(
        related="resource_id.tz",
        string="Timezone",
        readonly=False,
        help="The time zone where this resource works. Its working schedule is read in this zone: an 08:00-17:00 schedule means 08:00-17:00 here, whatever zone the schedule names. For an employee deployed away from the corporate office, set the zone of the place of work.",
    )
    company_id = fields.Many2one(  # noqa: E8529  multi-company key of hr.employee and resource.asset: UNIQUE (user_id, company_id) and two more on hr_employee, and the raw SQL that joins either table
        comodel_name="res.company",
        related="resource_id.company_id",
        string="Company",
        precompute=True,
        default=lambda self: self.env.company,
        store=True,
        index=True,
        readonly=False,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        related="resource_id.calendar_id",
        string="Working Hours",
        readonly=False,
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        # The slot is created and written as the system: whoever may create
        # the owner may give it its resource.
        Resource = self.env["resource.resource"].sudo()
        resources_vals_list = []
        for vals in vals_list:
            if not vals.get("resource_id"):
                resources_vals_list.append(  # noqa: PERF401 — vals.pop() side effect
                    self._prepare_resource_values(vals, vals.pop("tz", False))
                )
        if resources_vals_list:
            resources = Resource.create(resources_vals_list)
            resources_iter = iter(resources.ids)
            for vals in vals_list:
                if not vals.get("resource_id"):
                    vals["resource_id"] = next(resources_iter)

        attached = [
            vals
            for vals in vals_list
            if vals.get("resource_id")
            and not ("company_id" in vals and "resource_calendar_id" in vals)
        ]
        if attached:
            resources_by_id = {
                resource.id: resource
                for resource in Resource.browse(
                    [vals["resource_id"] for vals in attached]
                ).exists()
            }
            for vals in attached:
                resource = resources_by_id.get(vals["resource_id"])
                if not resource:
                    continue
                vals.setdefault("company_id", resource.company_id.id)
                vals.setdefault("resource_calendar_id", resource.calendar_id.id)
        return super(MixinResource, self.with_context(check_idempotence=True)).create(
            vals_list
        )

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        default = dict(default or {})
        vals_list = super().copy_data(default=default)

        resource_default = {}
        if "company_id" in default:
            resource_default["company_id"] = default["company_id"]
        if "resource_calendar_id" in default:
            resource_default["calendar_id"] = default["resource_calendar_id"]
        if not self._resource_owns:
            for vals in vals_list:
                vals.pop("resource_id", None)
            return vals_list
        resources = [record.resource_id for record in self]
        resources_to_copy = self.env["resource.resource"].concat(*resources)
        new_resources = resources_to_copy.copy(resource_default)
        for resource, vals in zip(new_resources, vals_list, strict=True):
            vals["resource_id"] = resource.id
            vals["company_id"] = resource.company_id.id
            vals["resource_calendar_id"] = resource.calendar_id.id
            if self._rec_name in default:
                resource.name = default[self._rec_name]
        return vals_list

    def _adjust_to_calendar(self, start: datetime, end: datetime) -> dict:
        resource_results = self.resource_id._adjust_to_calendar(start, end)
        return {record: resource_results[record.resource_id] for record in self}

    @staticmethod
    def _fan_out_per_record(
        result_per_resource: dict[int, dict[str, float]],
        records_per_resource: dict[int, list[int]],
    ) -> dict[int, dict[str, float]]:
        return {
            record_id: result_per_resource[resource_id]
            for resource_id, record_ids in records_per_resource.items()
            for record_id in record_ids
            if resource_id in result_per_resource
        }

    def _get_calendars(
        self, date_from: datetime | None = None
    ) -> dict[int, ResourceCalendar]:
        return {record.id: record.resource_calendar_id for record in self}

    def _get_leave_days_data_batch(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        calendar: ResourceCalendar | None = None,
        domain: list | None = None,
    ) -> dict[int, dict[str, float]]:
        records_per_resource = self._records_per_resource()
        result = {}

        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        mapped_resources = defaultdict(lambda: self.env["resource.resource"])
        for record in self:
            mapped_resources[calendar or record.resource_calendar_id] |= (
                record.resource_id
            )

        for calendar, calendar_resources in mapped_resources.items():  # noqa: PLR1704  the parameter's value is consumed above; the loop reuses the name on purpose
            if not calendar:
                days = (to_datetime.date() - from_datetime.date()).days + 1
                hours = (to_datetime - from_datetime).total_seconds() / 3600
                for calendar_resource in calendar_resources:
                    result[calendar_resource.id] = {"days": days, "hours": hours}
                continue

            attendances = calendar._attendance_intervals_batch(
                from_datetime, to_datetime, calendar_resources
            )
            leaves = calendar._leave_intervals_batch(
                from_datetime, to_datetime, calendar_resources, domain
            )

            for calendar_resource in calendar_resources:
                result[calendar_resource.id] = (
                    calendar._get_attendance_intervals_days_data(
                        attendances[calendar_resource.id] & leaves[calendar_resource.id]
                    )
                )

        return self._fan_out_per_record(result, records_per_resource)

    def _get_work_days_data_batch(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        compute_leaves: bool = True,
        calendar: ResourceCalendar | None = None,
        domain: list | None = None,
    ) -> dict[int, dict[str, float]]:
        records_per_resource = self._records_per_resource()
        result = {}

        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        if calendar:
            mapped_resources = {calendar: self.resource_id}
        else:
            calendar_by_resource = self._get_calendars(from_datetime)
            mapped_resources = defaultdict(lambda: self.env["resource.resource"])
            for record in self:
                mapped_resources[calendar_by_resource[record.id]] |= record.resource_id

        for calendar, calendar_resources in mapped_resources.items():  # noqa: PLR1704  the parameter's value is consumed above; the loop reuses the name on purpose
            if not calendar:
                for calendar_resource in calendar_resources:
                    result[calendar_resource.id] = {"days": 0, "hours": 0}
                continue

            if compute_leaves:
                intervals = calendar._work_intervals_batch(
                    from_datetime, to_datetime, calendar_resources, domain
                )
            else:
                intervals = calendar._attendance_intervals_batch(
                    from_datetime, to_datetime, calendar_resources
                )

            for calendar_resource in calendar_resources:
                result[calendar_resource.id] = (
                    calendar._get_attendance_intervals_days_data(
                        intervals[calendar_resource.id]
                    )
                )

        return self._fan_out_per_record(result, records_per_resource)

    def _list_work_time_per_day(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        calendar: ResourceCalendar | None = None,
        domain: list | None = None,
    ) -> dict[int, list[tuple]]:
        result = {}
        records_by_calendar = defaultdict(lambda: self.env[self._name])
        for record in self:
            records_by_calendar[
                calendar
                or record.resource_calendar_id
                or record.company_id.resource_calendar_id
            ] += record

        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=UTC)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=UTC)
        compute_leaves = self.env.context.get("compute_leaves", True)

        for calendar, records in records_by_calendar.items():  # noqa: PLR1704  the parameter's value is consumed above; the loop reuses the name on purpose
            if not calendar:
                for record in records:
                    result[record.id] = []
                continue
            resources = records.resource_id
            all_intervals = calendar._work_intervals_batch(
                from_datetime,
                to_datetime,
                resources,
                domain,
                compute_leaves=compute_leaves,
            )
            for record in records:
                intervals = all_intervals[record.resource_id.id]
                record_result = defaultdict(float)
                for start, stop, _meta in intervals:
                    record_result[start.date()] += (stop - start).total_seconds() / 3600
                result[record.id] = sorted(record_result.items())
        return result

    def list_leaves(
        self,
        from_datetime: datetime,
        to_datetime: datetime,
        calendar: ResourceCalendar | None = None,
        domain: list | None = None,
    ) -> list[tuple]:
        self.check_singleton()
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        if not calendar:
            return []

        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=UTC)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=UTC)

        attendances = calendar._attendance_intervals_batch(
            from_datetime, to_datetime, resource
        )[resource.id]
        leaves = calendar._leave_intervals_batch(
            from_datetime, to_datetime, resource, domain
        )[resource.id]
        result = []
        for start, stop, leave in leaves & attendances:
            hours = (stop - start).total_seconds() / 3600
            result.append((start.date(), hours, leave))
        return result

    def _prepare_resource_values(self, vals: ValuesType, tz: str | bool) -> ValuesType:
        resource_vals = {
            "name": vals.get(self._rec_name),
            "resource_type": self._resource_type,
        }
        if tz:
            resource_vals["tz"] = tz
        company_id = vals.get("company_id", self.env.company.id)
        if company_id:
            resource_vals["company_id"] = company_id
        calendar_id = vals.get("resource_calendar_id")
        if calendar_id:
            resource_vals["calendar_id"] = calendar_id
        return resource_vals

    def _records_per_resource(self) -> dict[int, list[int]]:
        grouped = defaultdict(list)
        for record in self:
            grouped[record.resource_id.id].append(record.id)
        return grouped
