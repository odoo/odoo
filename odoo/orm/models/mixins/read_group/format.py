import datetime
import typing

import babel
import babel.dates

from odoo.libs.datetime import all_timezones, utc
from odoo.libs.datetime import timezone as get_timezone
from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    date_utils,
    get_lang,
    unique,
)

from .... import fields
from ...._recordset import is_recordset
from ....constants import (
    READ_GROUP_DISPLAY_FORMAT,
    READ_GROUP_NUMBER_GRANULARITY,
    READ_GROUP_TIME_GRANULARITY,
)
from ....domain import Domain
from ....parsing import parse_read_group_spec
from ._empty import _ReadGroupEmptyMixin

if typing.TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from odoo.libs.datetime import Granularity

    from ...base import BaseModel

_debug = DebugLog(__name__)


class _ReadGroupFormatMixin(_ReadGroupEmptyMixin):
    __slots__ = ()

    def _read_group_postprocess_groupby(
        self, groupby_spec: str, raw_values: Sequence
    ) -> Generator:
        empty_value = self._read_group_empty_value(groupby_spec)

        fname, chain_fnames, granularity = parse_read_group_spec(groupby_spec)
        field = self._fields[fname]

        if field.relational or fname == "id":
            if chain_fnames and field.relational:
                groupby_seq = (
                    f"{chain_fnames}:{granularity}" if granularity else chain_fnames
                )
                model = self.env[field.comodel_name]
                _debug.logic(
                    "read_group.postprocess.chained_groupby",
                    model=self._name,
                    groupby=groupby_spec,
                    comodel=model._name,
                    values=len(raw_values),
                )
                return model._read_group_postprocess_groupby(groupby_seq, raw_values)

            registry = self.env.registry
            Model = (
                registry[field.comodel_name]
                if field.relational
                else registry[self._name]
            )
            prefetch_ids = tuple(raw_value for raw_value in raw_values if raw_value)

            def recordset(value):
                return Model(self.env, (value,), prefetch_ids) if value else empty_value

            return (recordset(value) for value in raw_values)

        return ((value if value is not None else empty_value) for value in raw_values)

    def _read_group_postprocess_aggregate(
        self, aggregate_spec: str, raw_values: Sequence
    ) -> Generator:
        empty_value = self._read_group_empty_value(aggregate_spec)

        if aggregate_spec == "__count":
            return (
                (value if value is not None else empty_value) for value in raw_values
            )

        fname, __, func = parse_read_group_spec(aggregate_spec)
        field = self._fields.get(fname)
        if (
            field is not None
            and func is not None
            and self._aggregates_through_records(field, func)
        ):
            return self._read_group_fold_through_records(
                field, func, raw_values, empty_value
            )
        if func == "recordset":
            field = self._fields[fname]
            _debug.logic(
                "read_group.postprocess.recordset_aggregate",
                model=self._name,
                aggregate=aggregate_spec,
                comodel=field.comodel_name if field.relational else self._name,
                rows=len(raw_values),
            )
            registry = self.env.registry
            Model = (
                registry[field.comodel_name]
                if field.relational
                else registry[self._name]
            )
            prefetch_ids = tuple(
                unique(
                    id_
                    for array_values in raw_values
                    if array_values
                    for id_ in array_values
                    if id_
                )
            )

            def recordset(value):
                if not value:
                    return empty_value
                ids = tuple(unique(id_ for id_ in value if id_))
                return Model(self.env, ids, prefetch_ids)

            return (recordset(value) for value in raw_values)

        return ((value if value is not None else empty_value) for value in raw_values)

    def _read_group_fold_through_records(
        self, field, func: str, raw_values: Sequence, empty_value
    ) -> Generator:
        Model = self.env.registry[self._name]
        prefetch_ids = tuple(
            unique(id_ for ids in raw_values if ids for id_ in ids if id_)
        )
        all_records = Model(self.env, prefetch_ids, prefetch_ids)
        if func == "sum_currency":
            currency_field = self._fields[field.get_currency_field(self)]
            to_currency = self.env.company.currency_id
            today = fields.Date.context_today(typing.cast("BaseModel", self))

        def value_of(record):
            value = record[field.name]
            if field.is_boolean:
                return value
            return None if value is False else value

        def present(records):
            return [v for v in (value_of(r) for r in records) if v is not None]

        _debug.logic(
            "read_group.postprocess.through_records",
            model=self._name,
            field=field.name,
            func=func,
            records=len(prefetch_ids),
            groups=len(raw_values),
        )

        def fold(ids):
            if not ids:
                return empty_value
            records = Model(self.env, tuple(unique(i for i in ids if i)), prefetch_ids)
            if func == "sum_currency":
                total = 0.0
                for record in records:
                    amount = value_of(record)
                    if amount is None:
                        continue
                    currency = record[currency_field.name]
                    total += (
                        currency._convert(
                            from_amount=amount,
                            to_currency=to_currency,
                            company=self.env.company,
                            date=today,
                        )
                        if currency and currency != to_currency
                        else amount
                    )
                return total
            if func in ("array_agg", "array_agg_distinct"):
                values = [value_of(r) for r in records]
                if func == "array_agg_distinct":
                    distinct = set(values)
                    has_none = None in distinct
                    distinct.discard(None)
                    values = [*sorted(distinct), *([None] if has_none else [])]
                return values or empty_value
            values = present(records)
            if func == "count":
                return len(values)
            if func == "count_distinct":
                return len(set(values))
            if not values:
                return empty_value
            if func == "sum":
                return sum(values)
            if func == "avg":
                return sum(values) / len(values)
            if func == "min":
                return min(values)
            if func == "max":
                return max(values)
            if func == "bool_and":
                return all(values)
            if func == "bool_or":
                return any(values)
            raise ValueError(f"Aggregate method {func!r} cannot fold {field}")

        del all_records
        return (fold(ids) for ids in raw_values)

    def _read_group_temporal_range(
        self, value, field, interval, granularity: str, locale: str, fmt: str
    ) -> tuple[str, str, str]:
        range_start = value
        range_end = value + interval
        if field.is_datetime:
            assert isinstance(range_start, datetime.datetime)
            assert isinstance(range_end, datetime.datetime)
            tzinfo = None
            if self.env.context.get("tz") in all_timezones():
                tzinfo = get_timezone(self.env.context["tz"])
                range_start = range_start.replace(tzinfo=tzinfo).astimezone(utc)
                range_end = range_end.replace(tzinfo=tzinfo).astimezone(utc)

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
        if granularity == "week":
            year, week = date_utils.weeknumber(
                babel.Locale.parse(locale),
                value,
            )
            label = f"W{week} {year:04}"
        return label, range_start.strftime(fmt), range_end.strftime(fmt)

    def _read_group_format_result(
        self, rows_dict: list[dict], lazy_groupby: list[str]
    ) -> None:
        for group in lazy_groupby:
            field_name = group.split(":")[0].split(".")[0]
            field = self._fields[field_name]

            if field.is_temporal:
                granularity = group.split(":")[1] if ":" in group else "month"
                if granularity in READ_GROUP_TIME_GRANULARITY:
                    locale = get_lang(self.env).code
                    fmt = (
                        DEFAULT_SERVER_DATETIME_FORMAT
                        if field.is_datetime
                        else DEFAULT_SERVER_DATE_FORMAT
                    )
                    interval = READ_GROUP_TIME_GRANULARITY[granularity]
            elif field.is_properties:
                self._read_group_format_result_properties(rows_dict, group)
                continue

            for row in rows_dict:
                value = row[group]

                if is_recordset(value):
                    row[group] = (
                        (value.id, value.sudo().display_name) if value else False
                    )
                    value = value.id

                additional_domain: list
                if not value and field.is_many2many:
                    additional_domain = [(field_name, "not any", [])]
                else:
                    additional_domain = [(field_name, "=", value)]

                if field.is_temporal:
                    if value and isinstance(value, datetime.date):
                        label, range_start_str, range_end_str = (
                            self._read_group_temporal_range(
                                value, field, interval, granularity, locale, fmt
                            )
                        )
                        row[group] = label
                        row.setdefault("__range", {})[group] = {
                            "from": range_start_str,
                            "to": range_end_str,
                        }
                        additional_domain = [
                            "&",
                            (field_name, ">=", range_start_str),
                            (field_name, "<", range_end_str),
                        ]
                    elif (
                        value is not None
                        and granularity in READ_GROUP_NUMBER_GRANULARITY
                    ):
                        additional_domain = [
                            (f"{field_name}.{granularity}", "=", value)
                        ]
                    elif not value:
                        row.setdefault("__range", {})[group] = False

                row["__domain"] &= Domain(additional_domain)
        for row in rows_dict:
            row["__domain"] = list(row["__domain"])
        _debug.pipeline(
            "read_group.formatted",
            model=self._name,
            rows=len(rows_dict),
            groups=len(lazy_groupby),
        )

    def _format_properties_selection(
        self, rows_dict: list[dict], fullname: str, definition: dict
    ) -> None:
        options = definition.get("selection") or []
        options = tuple(option[0] for option in options)
        for row in rows_dict:
            if not row[fullname]:
                additional_domain = Domain(fullname, "=", False) | Domain(
                    fullname, "not in", options
                )
            else:
                additional_domain = Domain(fullname, "=", row[fullname])

            row["__domain"] &= additional_domain

    def _format_properties_many2one(
        self, rows_dict: list[dict], fullname: str, definition: dict
    ) -> None:
        comodel = self.env[definition.get("comodel")]
        prefetch_ids = all_groups = tuple(
            row[fullname] for row in rows_dict if row[fullname]
        )
        for row in rows_dict:
            if not row[fullname]:
                additional_domain = Domain(fullname, "=", False) | Domain(
                    fullname, "not in", all_groups
                )
            else:
                additional_domain = Domain(fullname, "=", row[fullname])
                record = comodel.browse(row[fullname]).with_prefetch(prefetch_ids)
                row[fullname] = (row[fullname], record.display_name)

            row["__domain"] &= additional_domain

    def _format_properties_many2many(
        self, rows_dict: list[dict], fullname: str, definition: dict
    ) -> None:
        comodel = self.env[definition.get("comodel")]
        prefetch_ids = all_groups = tuple(
            row[fullname] for row in rows_dict if row[fullname]
        )
        for row in rows_dict:
            if not row[fullname]:
                if all_groups:
                    additional_domain = Domain(fullname, "=", False) | Domain.AND(
                        [(fullname, "not in", group)] for group in all_groups
                    )
                else:
                    additional_domain = Domain.TRUE
            else:
                additional_domain = Domain(fullname, "in", row[fullname])
                record = comodel.browse(row[fullname]).with_prefetch(prefetch_ids)
                row[fullname] = (row[fullname], record.display_name)

            row["__domain"] &= additional_domain

    def _format_properties_tags(
        self, rows_dict: list[dict], fullname: str, definition: dict
    ) -> None:
        tags = definition.get("tags") or []
        tags = {tag[0]: tag for tag in tags}
        for row in rows_dict:
            if not row[fullname]:
                if tags:
                    additional_domain = Domain(fullname, "=", False) | Domain.AND(
                        [(fullname, "not in", tag)] for tag in tags
                    )
                else:
                    additional_domain = Domain.TRUE
            else:
                additional_domain = Domain(fullname, "in", row[fullname])
                row[fullname] = tags.get(row[fullname])

            row["__domain"] &= additional_domain

    def _format_properties_temporal(
        self,
        rows_dict: list[dict],
        fullname: str,
        group: str,
        property_type: str,
        func: str,
    ) -> None:
        for row in rows_dict:
            if not row[group]:
                row[group] = False
                row["__domain"] &= Domain(fullname, "=", False)
                row.setdefault("__range", {})[group] = False
                continue

            db_format = "%Y-%m-%d" if property_type == "date" else "%Y-%m-%d %H:%M:%S"

            if func == "week":
                start = row[group].strftime(db_format)
                end = (row[group] + datetime.timedelta(days=7)).strftime(db_format)
            else:
                granularity = typing.cast("Granularity", func)
                start = (date_utils.start_of(row[group], granularity)).strftime(
                    db_format
                )
                end = (
                    date_utils.end_of(row[group], granularity)
                    + datetime.timedelta(minutes=1)
                ).strftime(db_format)

            row["__domain"] &= Domain(fullname, ">=", start) & Domain(
                fullname, "<", end
            )
            row.setdefault("__range", {})[group] = {"from": start, "to": end}
            row[group] = babel.dates.format_date(
                row[group],
                format=READ_GROUP_DISPLAY_FORMAT[func],
                locale=get_lang(self.env).code,
            )

    def _read_group_format_result_properties(self, rows_dict, group):
        if "." not in group:
            msg = "You must choose the property you want to group by."
            raise ValueError(msg)
        fullname, __, func = group.partition(":")

        definition = self.get_property_definition(fullname)
        property_type = definition.get("type")

        _debug.logic(
            "read_group.format.property",
            model=self._name,
            groupby=group,
            property_type=property_type,
            rows=len(rows_dict),
        )
        if property_type == "selection":
            self._format_properties_selection(rows_dict, fullname, definition)
        elif property_type == "many2one":
            self._format_properties_many2one(rows_dict, fullname, definition)
        elif property_type == "many2many":
            self._format_properties_many2many(rows_dict, fullname, definition)
        elif property_type == "tags":
            self._format_properties_tags(rows_dict, fullname, definition)
        elif property_type in ("date", "datetime"):
            self._format_properties_temporal(
                rows_dict, fullname, group, property_type, func
            )
        else:
            for row in rows_dict:
                row["__domain"] &= Domain(fullname, "=", row[fullname])
