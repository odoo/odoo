from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from odoo.fields import Domain
from odoo.libs.intervals import Intervals
from odoo.tools.date_utils import get_intervals_hours

if TYPE_CHECKING:
    from .resource_resource import ResourceResource

CUSTODY_SYNC = "custody_sync"
OPERATOR_ROLE = "operator"
MANAGER_ROLE = "manager"
EXCLUSIVE_CUSTODY_ROLES = (OPERATOR_ROLE, MANAGER_ROLE)
CUSTODY_ROLE_BY_FIELD = {"operator_id": OPERATOR_ROLE, "manager_id": MANAGER_ROLE}
DEFAULT_HANDOVER_DELAY = timedelta(days=7)

HOURS_PER_DAY = 8


def capacity_timeline(bookings, start, stop):
    if stop <= start:
        return
    changes = defaultdict(float, {start: 0.0, stop: 0.0})
    for booking_start, booking_stop, load in bookings:
        left, right = max(start, booking_start), min(stop, booking_stop)
        if left < right and load > 0:
            changes[left] += load
            changes[right] -= load
    previous, total = start, 0.0
    for instant, change in sorted(changes.items()):
        if previous < instant:
            yield previous, instant, total
        total += change
        previous = instant


def peak_capacity(bookings, start, stop):
    return max(
        (load for _, _, load in capacity_timeline(bookings, start, stop)), default=0.0
    )


def filter_domain_leaf(
    domain: Domain | list,
    field_check: Callable[[str], bool],
    field_name_mapping: dict[str, str] | None = None,
) -> Domain:
    field_name_mapping = field_name_mapping or {}

    def adapt_condition(condition, ignored):
        field_name = condition.field_expr
        if not field_check(field_name):
            return ignored
        field_name = field_name_mapping.get(field_name)
        if field_name is None:
            return condition
        return Domain(field_name, condition.operator, condition.value)

    def adapt_domain(domain: Domain, ignored) -> Domain:
        if hasattr(domain, "OPERATOR"):
            if domain.OPERATOR in ("&", "|"):
                domain = domain.apply(
                    adapt_domain(d, domain.ZERO) for d in domain.children
                )
            elif domain.OPERATOR == "!":
                domain = ~adapt_domain(~domain, ~ignored)
            else:
                msg = f"domain.OPERATOR = {domain.OPERATOR!r} unhandled"
                raise AssertionError(msg)
        else:
            domain = domain.map_conditions(
                lambda condition: adapt_condition(condition, ignored)
            )
        return ignored if domain.is_true() or domain.is_false() else domain

    domain = Domain(domain)
    if domain.is_false():
        return domain
    return adapt_domain(domain, ignored=Domain.TRUE)


@dataclass
class ResourceSchedule:
    intervals: defaultdict[int, Intervals] = field(
        default_factory=lambda: defaultdict(Intervals)
    )
    calendar_intervals: dict[int, Intervals] = field(default_factory=dict)
    hours_per_day: defaultdict[int, dict] = field(
        default_factory=lambda: defaultdict(dict)
    )
    hours_per_week: defaultdict[int, dict] = field(
        default_factory=lambda: defaultdict(dict)
    )
    flexible_ids: frozenset[int] = frozenset()

    def work_hours(
        self,
        resource: ResourceResource,
        intervals: Intervals | None = None,
        work_hours_per_day: dict[Any, float] | None = None,
    ) -> float:
        if intervals is None:
            intervals = self.intervals[resource.id]
        if resource.id in self.flexible_ids:
            return resource._get_flexible_resource_work_hours(
                intervals,
                self.hours_per_day[resource.id],
                self.hours_per_week[resource.id],
                work_hours_per_day,
            )
        hours = get_intervals_hours(intervals)
        if work_hours_per_day is not None:
            for start, stop, _meta in intervals:
                work_hours_per_day[start.date()] += (
                    stop - start
                ).total_seconds() / 3600
        return hours
