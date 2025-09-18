"""
Fill and expansion methods for read_group results.

Contains the _ReadGroupFillMixin with methods that fill empty groups,
expand group results, and fill temporal gaps in date-based groupings.
"""

import collections
import datetime
import typing

from odoo.libs.datetime.tz import all_timezones
from odoo.libs.datetime.tz import timezone as get_timezone
from odoo.tools import date_utils, get_lang

from .... import decorators as api
from ...._typing import DomainType, ModelType
from ....constants import READ_GROUP_TIME_GRANULARITY
from ....fields.temporal import Date, Datetime
from ....parsing import parse_read_group_spec


class _ReadGroupFillMixin:
    """Fill and expansion methods for read_group results.

    Provides methods to fill empty groups for all possible values,
    expand groups to include all target records, and fill temporal
    gaps in date-based groupings.
    """

    __slots__ = ()

    # Type hints for attributes provided by BaseModel (runtime)
    _fields: dict
    _name: str
    env: typing.Any

    @api.model
    def _read_group_expand_full(
        self, groups: ModelType, domain: DomainType
    ) -> ModelType:
        """Extend the group to include all target records by default."""
        return groups.search([])

    @api.model
    def _read_group_fill_results(
        self,
        domain,
        groupby,
        annoted_aggregates,
        read_group_result,
        read_group_order=None,
    ):
        """Helper method for filling in empty groups for all possible values of
        the field being grouped by"""
        field_name = groupby.split(".")[0].split(":")[0]
        field = self._fields[field_name]
        if not field or not field.group_expand:
            return read_group_result

        # field.group_expand is a callable or the name of a method, that returns
        # the groups that we want to display for this field, in the form of a
        # recordset or a list of values (depending on the type of the field).
        # This is useful to implement kanban views for instance, where some
        # columns should be displayed even if they don't contain any record.
        group_expand = field.group_expand
        if isinstance(group_expand, str):
            group_expand = getattr(self.env.registry[self._name], group_expand)
        assert callable(group_expand)

        # determine all groups that should be returned
        values = [line[groupby] for line in read_group_result if line[groupby]]

        if field.relational:
            # groups is a recordset; determine order on groups's model
            groups = self.env[field.comodel_name].browse(value.id for value in values)
            values = group_expand(self, groups, domain).sudo()
            if read_group_order == groupby + " desc":
                values = values.browse(reversed(values._ids))
            def value2key(value):
                return value and value.id

        else:
            # groups is a list of values
            values = group_expand(self, values, domain)
            if read_group_order == groupby + " desc":
                values.reverse()
            def value2key(value):
                return value

        # Merge the current results (list of dicts) with all groups. Determine
        # the global order of results groups, which is supposed to be in the
        # same order as read_group_result (in the case of a many2one field).

        read_group_result_as_dict = {}
        for line in read_group_result:
            read_group_result_as_dict[value2key(line[groupby])] = line

        empty_item = {
            name: self._read_group_empty_value(spec)
            for name, spec in annoted_aggregates.items()
        }

        result = {}
        # fill result with the values order
        for value in values:
            key = value2key(value)
            if key in read_group_result_as_dict:
                result[key] = read_group_result_as_dict.pop(key)
            else:
                result[key] = dict(empty_item, **{groupby: value})

        for line in read_group_result_as_dict.values():
            key = value2key(line[groupby])
            result[key] = line

        # add folding information if present
        if field.relational and groups._fold_name in groups._fields:
            fold = {
                group.id: group[groups._fold_name]
                for group in groups.browse(key for key in result if key)
            }
            for key, line in result.items():
                line["__fold"] = fold.get(key, False)

        return list(result.values())

    @api.model
    def _read_group_fill_temporal(
        self,
        data,
        groupby,
        annoted_aggregates,
        fill_from=False,
        fill_to=False,
        min_groups=False,
    ):
        """Helper method for filling date/datetime 'holes' in a result set.

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

        :param list data: the data containing groups
        :param list groupby: list of fields being grouped on
        :param list annoted_aggregates: dict of "<key_name>:<aggregate specification>"
        :param str fill_from: (inclusive) string representation of a
            date/datetime, start bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param str fill_to: (inclusive) string representation of a
            date/datetime, end bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param int min_groups: minimal amount of required groups for the
            fill_temporal range (should be >= 1)
        :rtype: list
        :return: list
        """
        # min_groups is actively used by web clients (fill_temporal context key)
        # and tested in test_web_fill_temporal — cannot be removed.
        first_group = groupby[0]
        field_name = first_group.split(":")[0].split(".")[0]
        field = self._fields[field_name]
        if field.type not in ("date", "datetime") and not (
            field.type == "properties" and ":" in first_group
        ):
            return data

        granularity = first_group.split(":")[1] if ":" in first_group else "month"
        days_offset = 0
        if granularity == "week":
            # _read_group_process_groupby week groups are dependent on the
            # locale, so filled groups should be too to avoid overlaps.
            first_week_day = int(get_lang(self.env).week_start) - 1
            days_offset = first_week_day and 7 - first_week_day
        interval = READ_GROUP_TIME_GRANULARITY[granularity]
        tz = None
        if field.type == "datetime" and self.env.context.get("tz") in all_timezones():
            tz = get_timezone(self.env.context["tz"])

        # The fill logic below computes the date range, generates missing
        # group entries, and merges them with existing data.

        # existing non null datetimes
        existing = [d[first_group] for d in data if d[first_group]] or [None]
        # assumption: existing data is sorted by field 'groupby_name'
        existing_from, existing_to = existing[0], existing[-1]
        if fill_from:
            fill_from = (
                Datetime.to_datetime(fill_from)
                if isinstance(fill_from, datetime.datetime)
                else Date.to_date(fill_from)
            )
            fill_from = date_utils.start_of(
                fill_from, granularity
            ) - datetime.timedelta(days=days_offset)
            if tz:
                fill_from = fill_from.replace(tzinfo=tz)
        elif existing_from:
            fill_from = existing_from
        if fill_to:
            fill_to = (
                Datetime.to_datetime(fill_to)
                if isinstance(fill_to, datetime.datetime)
                else Date.to_date(fill_to)
            )
            fill_to = date_utils.start_of(fill_to, granularity) - datetime.timedelta(
                days=days_offset
            )
            if tz:
                fill_to = fill_to.replace(tzinfo=tz)
        elif existing_to:
            fill_to = existing_to

        if not fill_to and fill_from:
            fill_to = fill_from
        if not fill_from and fill_to:
            fill_from = fill_to
        if not fill_from and not fill_to:
            return data

        if min_groups > 0:
            fill_to = max(fill_to, fill_from + (min_groups - 1) * interval)

        if fill_to < fill_from:
            return data

        required_dates = date_utils.date_range(fill_from, fill_to, interval)

        if existing[0] is None:
            existing = list(required_dates)
        else:
            existing = sorted(set().union(existing, required_dates))

        empty_item = {
            name: self._read_group_empty_value(spec)
            for name, spec in annoted_aggregates.items()
        }
        for group in groupby[1:]:
            empty_item[group] = self._read_group_empty_value(group)

        grouped_data = collections.defaultdict(list)
        for d in data:
            grouped_data[d[first_group]].append(d)

        result = []
        for dt in existing:
            result.extend(grouped_data[dt] or [dict(empty_item, **{first_group: dt})])

        if False in grouped_data:
            result.extend(grouped_data[False])

        return result
