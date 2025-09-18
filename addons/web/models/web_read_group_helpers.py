"""Temporal expansion, group filling, and field-type formatters for web_read_group.

Extracted from ``web_read_group.py`` to keep the core API and the
formatting / expansion logic in separate files.
"""

import datetime
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from typing import Any

import babel
import babel.dates
import pytz

from odoo import api, models
from odoo.fields import Date, Domain
from odoo.models import (
    READ_GROUP_DISPLAY_FORMAT,
    READ_GROUP_NUMBER_GRANULARITY,
    READ_GROUP_TIME_GRANULARITY,
)
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    date_utils,
    get_lang,
    unique,
)


def AND(domains: Iterable) -> list:
    """Flatten a list of domains with ``&`` operator."""
    return list(Domain.AND(domains))


def OR(domains: Iterable) -> list:
    """Flatten a list of domains with ``|`` operator."""
    return list(Domain.OR(domains))


class Base(models.AbstractModel):
    _inherit = "base"

    def _web_read_group_field_expand(self, groupby: Sequence[str]) -> Any:
        """Return the field that should be expanded, if any."""
        if (
            len(groupby) == 1
            and self.env.context.get("read_group_expand")
            and "." not in groupby[0]
            and (field := self._fields[groupby[0].split(":")[0]])
            and field.group_expand
        ):
            return field
        return None

    def _web_read_group_expand(
        self,
        domain: Any,
        groups: list[tuple],
        groupby_spec: str,
        aggregates: tuple[str, ...],
        order: str,
    ) -> list[tuple]:
        """Expand the result of _read_group to show empty groups.

        Used by the webclient for some view types (e.g. empty columns for
        kanban view).  See ``Field.group_expand`` attribute.
        """
        field_name = groupby_spec.split(".")[0].split(":")[0]
        field = self._fields[field_name]

        # determine all groups that should be returned
        values = [group_value for group_value, *__ in groups if group_value]

        # field.group_expand is a callable or the name of a method, that returns
        # the groups that we want to display for this field, in the form of a
        # recordset or a list of values (depending on the type of the field).
        # This is useful to implement kanban views for instance, where some
        # columns should be displayed even if they don't contain any record.
        if field.relational:
            # groups is a recordset; determine order on groups's model
            values = self.env[field.comodel_name].browse(value.id for value in values)
            expand_values = field.determine_group_expand(self, values, domain)
            all_record_ids = tuple(unique(expand_values._ids + values._ids))
        else:
            # groups is a list of values
            expand_values = field.determine_group_expand(self, values, domain)

        if (groupby_spec + " desc") in order.lower():
            expand_values = reversed(expand_values)

        empty_aggregates = tuple(
            self._read_group_empty_value(spec) for spec in aggregates
        )
        result = dict.fromkeys(expand_values, empty_aggregates)
        result.update(
            {group_value: aggregate_values for group_value, *aggregate_values in groups}
        )

        if field.relational:
            return [
                (value.with_prefetch(all_record_ids), *aggregate_values)
                for value, aggregate_values in result.items()
            ]
        return [
            (value, *aggregate_values) for value, aggregate_values in result.items()
        ]

    @api.model
    def _web_read_group_fill_temporal(
        self,
        groups: list[tuple],
        groupby: list[str],
        aggregates: Sequence[str],
        fill_from: str | bool = False,
        fill_to: str | bool = False,
        min_groups: int | bool = False,
    ) -> list[tuple]:
        """Fill date/datetime 'holes' in a grouped result for the first groupby.

        We are in a use case where data are grouped by a date field (typically
        months but it could be any other interval) and displayed in a chart.

        Assume we group records by month, and we only have data for June,
        September and December. By default, plotting the result gives something
        like::

                                                ___
                                      ___      |   |
                                     |   | ___ |   |
                                     |___||___||___|
                                      Jun  Sep  Dec

        The problem is that December data immediately follow September data,
        which is misleading for the user. Adding explicit zeroes for missing
        data gives something like::

                                                           ___
                             ___                          |   |
                            |   |           ___           |   |
                            |___| ___  ___ |___| ___  ___ |___|
                             Jun  Jul  Aug  Sep  Oct  Nov  Dec

        To customize this output, the context key "fill_temporal" can be used
        under its dictionary format, which has 3 attributes : fill_from,
        fill_to, min_groups (see params of this function)

        Fill between bounds:
        Using either `fill_from` and/or `fill_to` attributes, we can further
        specify that at least a certain date range should be returned as
        contiguous groups. Any group outside those bounds will not be removed,
        but the filling will only occur between the specified bounds. When not
        specified, existing groups will be used as bounds, if applicable.
        By specifying such bounds, we can get empty groups before/after any
        group with data.

        If we want to fill groups only between August (fill_from)
        and October (fill_to)::

                                                     ___
                                 ___                |   |
                                |   |      ___      |   |
                                |___| ___ |___| ___ |___|
                                 Jun  Aug  Sep  Oct  Dec

        We still get June and December. To filter them out, we should match
        `fill_from` and `fill_to` with the domain e.g. ``['&',
        ('date_field', '>=', 'YYYY-08-01'), ('date_field', '<', 'YYYY-11-01')]``::

                                         ___
                                    ___ |___| ___
                                    Aug  Sep  Oct

        Minimal filling amount:
        Using `min_groups`, we can specify that we want at least that amount of
        contiguous groups. This amount is guaranteed to be provided from
        `fill_from` if specified, or from the lowest existing group otherwise.
        This amount is not restricted by `fill_to`. If there is an existing
        group before `fill_from`, `fill_from` is still used as the starting
        group for min_groups, because the filling does not apply on that
        existing group. If neither `fill_from` nor `fill_to` is specified, and
        there is no existing group, no group will be returned.

        If we set min_groups = 4::

                                         ___
                                    ___ |___| ___ ___
                                    Aug  Sep  Oct Nov

        :param list[tuple] groups: groups returned by _read_group
        :param list[str] groupby: list of fields being grouped on
        :param Sequence[str] aggregates: list of "<key_name>:<aggregate specification>"
        :param fill_from: (inclusive) string representation of a
            date/datetime, start bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :type fill_from: str | bool
        :param fill_to: (inclusive) string representation of a
            date/datetime, end bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :type fill_to: str | bool
        :param min_groups: minimal amount of required groups for the
            fill_temporal range (should be >= 1)
        :type min_groups: int | bool
        :rtype: list[tuple]
        :return: list
        """
        groupby_name = groupby[0]
        field_name = groupby_name.split(":")[0].split(".")[0]
        field = self._fields[field_name]
        if field.type not in ("date", "datetime") and not (
            field.type == "properties" and ":" in groupby_name
        ):
            return groups

        granularity = groupby_name.split(":")[1]
        days_offset = 0
        if granularity == "week":
            # _read_group week groups are dependent on the
            # locale, so filled groups should be too to avoid overlaps.
            first_week_day = int(get_lang(self.env).week_start) - 1
            days_offset = first_week_day and 7 - first_week_day
        tz = False
        if (
            field.type == "datetime"
            and self.env.context.get("tz") in pytz.all_timezones_set
        ):
            tz = pytz.timezone(self.env.context["tz"])

        # existing non null date(time)
        existing = sorted(
            group_value for group in groups if (group_value := group[0])
        ) or [None]
        # assumption: existing data is sorted by field 'groupby_name'
        existing_from, existing_to = existing[0], existing[-1]
        if fill_from:
            fill_from = Date.to_date(fill_from)
            fill_from = date_utils.start_of(
                fill_from, granularity
            ) - datetime.timedelta(days=days_offset)
            if tz:
                fill_from = tz.localize(fill_from)
        elif existing_from:
            fill_from = existing_from
        if fill_to:
            fill_to = Date.to_date(fill_to)
            fill_to = date_utils.start_of(fill_to, granularity) - datetime.timedelta(
                days=days_offset
            )
            if tz:
                fill_to = tz.localize(fill_to)
        elif existing_to:
            fill_to = existing_to

        if not fill_to and fill_from:
            fill_to = fill_from
        elif not fill_from and fill_to:
            fill_from = fill_to
        if not fill_from and not fill_to:
            return groups

        interval = READ_GROUP_TIME_GRANULARITY[granularity]
        if min_groups > 0:
            fill_to = max(fill_to, fill_from + (min_groups - 1) * interval)

        if fill_from > fill_to:
            return groups

        empty_item = tuple(
            self._read_group_empty_value(spec) for spec in groupby[1:] + aggregates
        )
        required_dates = list(date_utils.date_range(fill_from, fill_to, interval))

        if existing[0] is None:
            existing = list(required_dates)
        else:
            existing = sorted(set().union(existing, required_dates))

        groups_mapped = defaultdict(list)
        for group in groups:
            groups_mapped[group[0]].append(group)

        result = []
        for dt in existing:
            if dt in groups_mapped:
                result.extend(groups_mapped[dt])
            else:
                result.append((dt, *empty_item))

        if False in groups_mapped:
            result.extend(groups_mapped[False])

        return result

    def _web_read_group_groupby_formatter(
        self, groupby_spec: str, values: Any
    ) -> Callable:
        """Return a formatter that yields ``(value_label, domain)`` pairs.

        The returned callable is used by ``_web_read_group_format`` to convert
        raw ``_read_group`` values into webclient-friendly dicts.
        """
        field_path = groupby_spec.split(":")[0]
        field_name, _dot, remaining_path = field_path.partition(".")
        field = self._fields[field_name]

        if remaining_path and field.type == "many2one":
            model = self.env[field.comodel_name]
            sub_formatter = model._web_read_group_groupby_formatter(
                groupby_spec.split(".", 1)[1], values
            )

            def formatter_follow_many2one(value):
                value, domain = sub_formatter(value)
                if not value:
                    return value, [
                        "|",
                        (field_name, "not any", []),
                        (field_name, "any", domain),
                    ]
                return value, [(field_name, "any", domain)]

            return formatter_follow_many2one

        if field.type == "many2many":
            # Special case for many2many because (<many2many>, '=', False) domain bypass ir.rule.
            def formatter_many2many(value):
                if not value:
                    return False, [(field_name, "not any", [])]
                id_ = value.id
                return (id_, value.sudo().display_name), [(field_name, "=", id_)]

            return formatter_many2many

        if field.type == "many2one" or field_name == "id":

            def formatter_many2one(value):
                if not value:
                    return False, [(field_name, "=", False)]
                id_ = value.id
                return (id_, value.sudo().display_name), [(field_name, "=", id_)]

            return formatter_many2one

        if field.type in ("date", "datetime"):
            if ":" not in groupby_spec:
                raise ValueError(
                    f"Granularity is missing from date/datetime groupby: {groupby_spec!r}"
                )
            granularity = groupby_spec.split(":")[1]
            if granularity in READ_GROUP_TIME_GRANULARITY:
                locale = get_lang(self.env).code
                fmt = (
                    DEFAULT_SERVER_DATETIME_FORMAT
                    if field.type == "datetime"
                    else DEFAULT_SERVER_DATE_FORMAT
                )
                interval = READ_GROUP_TIME_GRANULARITY[granularity]

                def formatter_time_granularity(value):
                    if not value:
                        return value, [(field_name, "=", value)]
                    range_start = value
                    range_end = value + interval
                    if field.type == "datetime":
                        tzinfo = None
                        if self.env.context.get("tz") in pytz.all_timezones_set:
                            tzinfo = pytz.timezone(self.env.context["tz"])
                            range_start = tzinfo.localize(range_start).astimezone(
                                pytz.utc
                            )
                            # take into account possible hour change between start and end
                            range_end = tzinfo.localize(range_end).astimezone(pytz.utc)

                        label = babel.dates.format_datetime(
                            range_start,
                            format=READ_GROUP_DISPLAY_FORMAT[granularity],
                            tzinfo=tzinfo,
                            locale=locale,
                        )
                    else:
                        label = babel.dates.format_date(
                            value,
                            format=READ_GROUP_DISPLAY_FORMAT[granularity],
                            locale=locale,
                        )

                    # special case weeks because babel is broken *and*
                    # ubuntu reverted a change so it's also inconsistent
                    if granularity == "week":
                        year, week = date_utils.weeknumber(
                            babel.Locale.parse(locale),
                            value,  # provide date or datetime without UTC conversion
                        )
                        label = f"W{week} {year:04}"

                    additional_domain = [
                        "&",
                        (field_name, ">=", range_start.strftime(fmt)),
                        (field_name, "<", range_end.strftime(fmt)),
                    ]
                    # TODO: date label should be created by the webclient.
                    return (range_start.strftime(fmt), label), additional_domain

                return formatter_time_granularity

            if granularity in READ_GROUP_NUMBER_GRANULARITY:

                def formatter_date_number_granularity(value):
                    if value is None:
                        return None, [(field_name, "=", value)]
                    return value, [(f"{field_name}.{granularity}", "=", value)]

                return formatter_date_number_granularity

            raise ValueError(f"{granularity!r} isn't a valid granularity")

        if field.type == "properties":
            return self._web_read_group_groupby_properties_formatter(
                groupby_spec, values
            )

        return lambda value: (value, [(field_name, "=", value)])

    def _web_read_group_groupby_properties_formatter(
        self,
        groupby_spec: str,
        values: Any,
    ) -> Callable:
        """Return a formatter for property-type group-by fields."""
        if "." not in groupby_spec:
            msg = "You must choose the property you want to group by."
            raise ValueError(msg)

        fullname, __, func = groupby_spec.partition(":")
        definition = self.get_property_definition(fullname)
        property_type = definition.get("type")
        if property_type == "selection":
            options = definition.get("selection") or []
            options = tuple(option[0] for option in options)

            def formatter_property_selection(value):
                if not value:
                    # can not do ('selection', '=', False) because we might have
                    # option in database that does not exist anymore
                    return value, [
                        "|",
                        (fullname, "=", False),
                        (fullname, "not in", options),
                    ]
                return value, [(fullname, "=", value)]

            return formatter_property_selection

        if property_type == "many2one":
            comodel = definition["comodel"]
            all_groups = tuple(value for value in values if value)

            def formatter_property_many2one(value):
                if not value:
                    # can not only do ('many2one', '=', False) because we might have
                    # record in database that does not exist anymore
                    return value, [
                        "|",
                        (fullname, "=", False),
                        (fullname, "not in", all_groups),
                    ]
                record = self.env[comodel].browse(value).with_prefetch(all_groups)
                return (value, record.display_name), [(fullname, "=", value)]

            return formatter_property_many2one

        if property_type == "many2many":
            comodel = definition["comodel"]
            all_groups = tuple(value for value in values if value)

            def formatter_property_many2many(value):
                if not value:
                    return value, (
                        OR(
                            [
                                [(fullname, "=", False)],
                                AND(
                                    [
                                        [(fullname, "not in", [group])]
                                        for group in all_groups
                                    ]
                                ),
                            ]
                        )
                        if all_groups
                        else []
                    )
                record = self.env[comodel].browse(value).with_prefetch(all_groups)
                return (value, record.display_name), [(fullname, "in", [value])]

            return formatter_property_many2many

        if property_type == "tags":
            tags = definition.get("tags") or []
            tags = {tag[0]: tuple(tag) for tag in tags}

            def formatter_property_tags(value):
                if not value:
                    return value, (
                        OR(
                            [
                                [(fullname, "=", False)],
                                AND([[(fullname, "not in", [tag])] for tag in tags]),
                            ]
                        )
                        if tags
                        else []
                    )

                # replace tag raw value with tuple of raw value, label and color
                return tags.get(value), [(fullname, "in", [value])]

            return formatter_property_tags

        if property_type in ("date", "datetime"):
            interval = READ_GROUP_TIME_GRANULARITY[func]
            # Date / Datetime are not JSONifiable, so they are stored as raw text
            fmt = (
                DEFAULT_SERVER_DATE_FORMAT
                if property_type == "date"
                else DEFAULT_SERVER_DATETIME_FORMAT
            )

            def formatter_property_datetime(value):
                if not value:
                    return False, [(fullname, "=", False)]

                if func == "week":
                    # the value is the first day of the week (based on locale)
                    start = value
                else:
                    start = date_utils.start_of(value, func)
                end = start + interval

                label = babel.dates.format_date(
                    value,
                    format=READ_GROUP_DISPLAY_FORMAT[func],
                    locale=get_lang(self.env).code,
                )
                return (value.strftime(fmt), label), [
                    (fullname, ">=", start.strftime(fmt)),
                    (fullname, "<", end.strftime(fmt)),
                ]

            return formatter_property_datetime

        return lambda value: (value, [(fullname, "=", value)])
