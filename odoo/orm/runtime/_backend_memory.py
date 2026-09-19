from __future__ import annotations

import functools
import logging
import operator as pyoperator
import re
import typing
import zoneinfo
from collections import defaultdict
from datetime import UTC, date, datetime
from datetime import timedelta as _timedelta
from decimal import Decimal
from itertools import product

from psycopg.errors import (
    ForeignKeyViolation,
    NotNullViolation,
    UniqueViolation,
)

from odoo.exceptions import LockError, UserError
from odoo.libs.accel import fast_clone
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, Query, get_lang, partition, unique
from odoo.tools.translate import _

from ..components.storage import NamedSequence
from ..domain import Domain
from ..fields.temporal import Date
from ..models.table_objects import Constraint
from ..parsing import parse_read_group_spec, regex_order_part_read_group
from ..primitives import MODULE_UNINSTALL_FLAG, NewId
from ._search_flush import flush_search_dependencies
from .backend import (
    ColumnStore,
    PostgresBackend,
    SequenceStore,
    _get_column_read_value,
    _unwrap_json,
)

if typing.TYPE_CHECKING:
    from ..components.storage import DictBackend
    from ..fields import Field
    from ..models.base import BaseModel
    from .environment import Environment

_logger = logging.getLogger("odoo.orm.backend")
_debug = DebugLog(__name__)


class InMemorySequenceStore:
    __slots__ = ("storage",)

    def __init__(self, storage: DictBackend):
        self.storage = storage

    def create(self, env, name: str, *, increment: int, start: int) -> None:
        self.storage._named_sequences[name] = NamedSequence(increment, max(start, 1))

    def drop(self, env, names: typing.Collection[str]) -> None:
        for name in names:
            self.storage._named_sequences.pop(name, None)

    def alter(
        self,
        env,
        name: str,
        *,
        increment: int | None = None,
        restart: int | None = None,
    ) -> None:
        sequence = self.storage._named_sequences.get(name)
        if sequence is None:
            return
        if increment is not None:
            sequence.increment = increment
        if restart is not None:
            sequence.last_value = max(restart, 1)
            sequence.is_called = False

    def next_values(self, env, name: str, count: int) -> list[int]:
        return self.storage._named_sequences[name].next_values(count)

    def peek(self, env, names: typing.Collection[str]) -> dict[str, int]:
        sequences = self.storage._named_sequences
        return {name: sequences[name].peek() for name in names if name in sequences}


def _load(value: typing.Any) -> typing.Any:
    # what the cursor's loaders answer for the stored value: a numeric as a
    # float (db.lifecycle registers the loader), a json object unwrapped
    if isinstance(value, Decimal):
        return float(value)
    return _unwrap_json(value)


class InMemoryColumnStore:
    __slots__ = ("storage",)

    def __init__(self, storage: DictBackend):
        self.storage = storage

    def read(
        self, model: BaseModel, column: str, ids: typing.Collection[int]
    ) -> dict[int, typing.Any]:
        rows = self.storage.get_rows(model._table, list(ids))
        return {id_: _load(row.get(column)) for id_, row in rows.items()}

    def write(
        self,
        model: BaseModel,
        column: str,
        rows: typing.Collection[tuple[int, typing.Any]],
    ) -> None:
        self.storage.update_rows(
            model._table, [(id_, {column: _unwrap_json(value)}) for id_, value in rows]
        )

    def fetch_and_add(
        self, model: BaseModel, column: str, record_id: int, delta: int
    ) -> int | None:
        row = self.storage.get_row(model._table, record_id)
        if row is None:
            # the SQL twin unpacks the RETURNING of an UPDATE that matched
            # nothing: an absent row is an error, never a fabricated 0
            raise ValueError(f"fetch_and_add: no row {record_id} in {model._table!r}")
        value = row.get(column)
        # NULL + delta is NULL on PostgreSQL, and the raw old value returns
        new = None if value is None else value + delta
        self.storage.update_rows(model._table, [(record_id, {column: new})])
        return value

    def try_write(
        self, model: BaseModel, column: str, record_id: int, value: typing.Any
    ) -> bool:
        # a value the table refuses under a unique constraint is an answer,
        # not an error: the caller picks the next candidate (mirrors the
        # UniqueViolation catch of the PostgreSQL twin)
        row = dict(self.storage.get_row(model._table, record_id) or {})
        row["id"] = record_id
        row[column] = value
        try:
            _check_table_constraints(self.storage, model, [row])
        except UniqueViolation:
            return False
        self.storage.update_rows(model._table, [(record_id, {column: value})])
        return True

    def merge_json(
        self,
        model: BaseModel,
        column: str,
        record_id: int,
        fallback: dict[str, typing.Any],
        value: dict[str, typing.Any],
    ) -> int:
        row = self.storage.get_row(model._table, record_id)
        if row is None:
            return 0
        stored = _unwrap_json(row.get(column)) or {}
        merged = {
            key: item
            for key, item in {
                **_unwrap_json(fallback),
                **stored,
                **_unwrap_json(value),
            }.items()
            if item is not None
        }
        self.storage.update_rows(model._table, [(record_id, {column: merged or None})])
        return 1

    def get_column_values(
        self, model: BaseModel, column: str
    ) -> list[tuple[int, typing.Any]]:
        storage = self.storage
        return [
            (row_id, _load(row[column]))
            for row_id in sorted(storage.get_table_ids(model._table))
            if (row := storage.get_row(model._table, row_id)) is not None
            and row.get(column) is not None
        ]


_UNIQUE_DEFINITION = re.compile(r"^\s*unique\s*\(([^)]*)\)\s*$", re.IGNORECASE)


def _check_table_constraints(storage, model: BaseModel, rows: list[dict]) -> None:
    # what the table refuses on PostgreSQL: a NULL in a NOT NULL column and a
    # duplicate under a unique constraint (NULLs distinct, as SQL treats them)
    registry = model.env.registry
    not_null = [
        field.name
        for field in model._fields.values()
        if field.name != "id" and field in registry.not_null_fields
    ]
    for row in rows:
        for name in not_null:
            if name in row and row[name] is None:
                raise NotNullViolation(
                    f'null value in column "{name}" of relation '
                    f'"{model._table}" violates not-null constraint'
                )
    uniques = [
        (obj.get_full_name(model), tuple(c.strip() for c in match[1].split(",")))
        for obj in model._table_objects.values()
        if isinstance(obj, Constraint)
        and (match := _UNIQUE_DEFINITION.match(obj.get_definition(registry)))
    ]
    if not uniques:
        return
    existing = [
        stored
        for row_id in storage.get_table_ids(model._table)
        if (stored := storage.get_row(model._table, row_id)) is not None
    ]
    for conname, columns in uniques:
        seen: set[tuple] = set()
        for row in rows:
            key = tuple(row.get(column) for column in columns)
            if any(value is None for value in key):
                continue
            if key in seen or any(
                stored.get("id") != row.get("id")
                and tuple(stored.get(column) for column in columns) == key
                for stored in existing
            ):
                raise UniqueViolation(
                    f'duplicate key value violates unique constraint "{conname}"'
                )
            seen.add(key)


@functools.cache
def _python_timezone_names() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones())


class _MultiValued(list):
    __slots__ = ()


# date_part() for the number granularities, a double precision as PostgreSQL
# answers it; its dow runs Sunday 0 .. Saturday 6 and its week is the ISO week
_DATE_PART = {
    "year_number": lambda d: float(d.year),
    "quarter_number": lambda d: float((d.month - 1) // 3 + 1),
    "month_number": lambda d: float(d.month),
    "iso_week_number": lambda d: float(d.isocalendar()[1]),
    "day_of_year": lambda d: float(d.timetuple().tm_yday),
    "day_of_month": lambda d: float(d.day),
    "day_of_week": lambda d: float((d.weekday() + 1) % 7),
    "hour_number": lambda d: float(d.hour),
    "minute_number": lambda d: float(d.minute),
    "second_number": lambda d: float(d.second),
}


_TRUNCATE_GRANULARITY = {
    "year": lambda d: d.replace(month=1, day=1),
    "quarter": lambda d: d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1),
    "month": lambda d: d.replace(day=1),
    "day": lambda d: d,
}


def _truncate(
    value: typing.Any,
    granularity: str,
    first_week_day: int = 0,
    tz: zoneinfo.ZoneInfo | None = None,
) -> typing.Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        if tz is not None:
            # timezone(tz, timezone('UTC', col)): the stored UTC instant as
            # the local wall-clock time, without an offset
            value = value.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        if granularity == "hour":
            return value.replace(minute=0, second=0, microsecond=0)
        if granularity in _DATE_PART:
            return _DATE_PART[granularity](value)
        value = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity in _DATE_PART:
        if granularity in ("hour_number", "minute_number", "second_number"):
            return 0.0
        return _DATE_PART[granularity](value)
    if granularity == "week":
        # the language's first week day, 0 Monday .. 6 Sunday, as the SQL
        # path shifts date_trunc('week') by it
        return value - _timedelta(days=(value.weekday() - first_week_day) % 7)
    try:
        return _TRUNCATE_GRANULARITY[granularity](value)
    except KeyError:
        raise NotImplementedError(
            f"InMemoryBackend.read_group_rows: granularity {granularity!r} is not "
            "supported in memory"
        ) from None


def _cache_snapshot(env: Environment) -> dict:
    core = env.core
    snapshot: dict = {}
    for field in list(core.iter_cached_fields()):
        data = core.get_field_data_or_none(field)
        if data is not None:
            snapshot[field, None] = set(data)
        for key, slot in core.iter_context_caches(field):
            snapshot[field, key] = set(slot)
    return snapshot


def _drop_cache_additions(env: Environment, snapshot: dict) -> None:
    core = env.core
    for field in list(core.iter_cached_fields()):
        data = core.get_field_data_or_none(field)
        if data is not None:
            for id_ in set(data) - snapshot.get((field, None), set()):
                del data[id_]
        for key, slot in list(core.iter_context_caches(field)):
            for id_ in set(slot) - snapshot.get((field, key), set()):
                del slot[id_]


class _InMemoryReadGroup:
    """read_group over the dict storage: one row per group, raw values shaped as
    the SQL rows are (a many2one is its id, a date is truncated, text NULLIF'd)."""

    def __init__(self, model, domain, groupby, aggregates, storage=None):
        self.model = model
        self.storage = storage
        # the compiled query carries a GROUP BY meant for SQL; the in-memory search
        # answers the domain itself
        self.records = model.browse(model._search(domain).get_result_ids())
        self.groupby_specs = list(groupby)
        self.aggregate_specs = list(aggregates)
        self.groupby = [self._groupby_reader(spec) for spec in groupby]
        self.aggregates = [self._aggregate_reader(spec) for spec in aggregates]
        self.order_specs: list[str] = []
        self.order_aggregates: list = []

    def _unsupported(self, what: str) -> typing.NoReturn:
        raise NotImplementedError(
            f"InMemoryBackend.read_group_rows on {self.model._name}: {what} is not "
            "supported in memory; use a DB-backed TransactionCase"
        )

    def _groupby_reader(self, spec: str, model: BaseModel | None = None):
        model = self.model if model is None else model
        fname, seq_fnames, granularity = parse_read_group_spec(spec)
        field = model._fields[fname]
        if field.is_properties:
            return self._property_reader(model, field, seq_fnames, granularity, spec)
        if field.is_many2many:
            return self._many2many_reader(model, field, spec)
        if seq_fnames:
            return self._many2one_path_reader(
                model, fname, field, seq_fnames, granularity, spec
            )

        first_week_day = 0
        tz = None
        if field.is_temporal and granularity == "week":
            first_week_day = int(get_lang(model.env).week_start) - 1
        if field.is_datetime and (tz_name := model.env.context.get("tz")):
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
            except zoneinfo.ZoneInfoNotFoundError, ValueError:
                # the SQL path groups in UTC when the server does not know the zone
                tz = None

        def read(record):
            value = record[fname]
            if field.is_many2one:
                return value.id or None
            if field.is_temporal:
                return _truncate(
                    value or None, granularity or "day", first_week_day, tz
                )
            if field.is_boolean:
                return bool(value)
            if field.is_text:
                return value or None
            return value if value is not False else None

        return read

    def _many2many_reader(self, model, field, spec):
        # the relation rows whose comodel side the user may see under the
        # field's domain, as the LEFT JOIN's IN (subselect) keeps
        if not field.store:
            raise ValueError(f"Group by non-stored many2many field: {spec!r}")
        comodel = model.env[field.comodel_name].with_context(**field.context)
        allowed = set(
            comodel._search(
                field.get_comodel_domain(model),
                bypass_access=field.bypass_search_access,
            ).get_result_ids()
        )

        def read(record):
            ids = [id_ for id_ in record[field.name]._ids if id_ in allowed]
            return _MultiValued(ids or [None])

        return read

    def _property_reader(self, model, field, property_name, granularity, spec):
        # the SQL path groups by the property's raw json value shaped by its
        # definition type; a collection property and html stay refused
        if not property_name:
            self._unsupported(f"groupby {spec!r}")
        definition = model.get_property_definition(f"{field.name}.{property_name}")
        property_type = definition.get("type")
        if property_type == "html":
            raise UserError(_("Grouping by HTML properties is not supported."))
        options = {option[0] for option in definition.get("selection") or ()}
        tags = {tag[0] for tag in definition.get("tags") or ()}
        comodel = None
        if property_type in ("many2one", "many2many") and definition.get("comodel"):
            comodel = (
                model.env[definition["comodel"]].sudo().with_context(active_test=False)
            )

        def is_id(raw):
            return isinstance(raw, int) and not isinstance(raw, bool)

        if property_type in ("tags", "many2many"):
            # the SQL path LEFT JOINs the json array's elements that the
            # definition (or the comodel's table) knows: one key per element,
            # a NULL row when none qualifies
            def read_collection(record):
                values = record[field.name]
                raw = (values._values or {}).get(property_name)
                if not isinstance(raw, list):
                    return None
                if property_type == "tags":
                    keys = [key for key in raw if key in tags]
                elif comodel is None:
                    keys = []
                else:
                    keys = [
                        key
                        for key in raw
                        if is_id(key) and comodel.browse(key).exists()
                    ]
                return _MultiValued(keys) if keys else None

            return read_collection

        first_week_day = 0
        if granularity == "week":
            first_week_day = int(get_lang(model.env).week_start) - 1

        def read(record):
            values = record[field.name]
            raw = (values._values or {}).get(property_name)
            if property_type == "selection":
                return raw if raw in options else None
            if property_type == "many2one":
                if not is_id(raw) or comodel is None:
                    return None
                return raw if comodel.browse(raw).exists() else None
            if property_type in ("date", "datetime"):
                if not isinstance(raw, str):
                    return None
                parsed = (
                    date.fromisoformat(raw[:10])
                    if property_type == "date"
                    else datetime.fromisoformat(raw)
                )
                return _truncate(parsed, granularity or "day", first_week_day)
            if property_type == "boolean":
                return bool(raw)
            if raw is None or raw is False:
                return None
            return raw

        return read

    def _many2one_path_reader(self, model, fname, field, seq_fnames, granularity, spec):
        # the SQL path LEFT JOINs the comodel under the user's record rules
        # and groups by the rest of the spec on the joined row
        if not field.is_many2one:
            raise ValueError(
                f"Only many2one path is accepted for the {spec!r} groupby spec"
            )
        env = model.env
        comodel = env[field.comodel_name]
        rules = None
        if not env.su:
            sec_domain = env.registry.access_policy.record_domain(
                env, comodel._name, "read"
            )
            if not sec_domain.is_true():
                rules = sec_domain
        rest = f"{seq_fnames}:{granularity}" if granularity else seq_fnames
        read_rest = self._groupby_reader(rest, comodel)

        def read(record):
            corecord = record[fname]
            if not corecord:
                return None
            if rules is not None and not (
                corecord.sudo().with_context(active_test=False).filtered_domain(rules)
            ):
                return None
            return read_rest(corecord)

        return read

    def _aggregate_reader(self, spec: str):
        if spec == "__count":
            return len
        fname, _property, func = parse_read_group_spec(spec)
        field = self.model._fields[fname]
        if not field.store and not self.model._aggregates_through_records(
            field, func or ""
        ):
            raise ValueError(f"Cannot convert {field} to SQL because it is not stored")

        storage = self.storage
        table = self.model._table

        def raw(record):
            value = record[fname]
            if field.relational:
                return value.id or None if field.is_many2one else list(value.ids)
            if field.is_boolean:
                return value
            if not value and storage is not None:
                # the cache reads a stored NULL as the type's falsy value
                # (0, 0.0, ""), which SQL aggregates would have skipped:
                # only the stored cell tells NULL apart from a real zero
                row = storage.get_row(table, record.id)
                if row is None or row.get(fname) is None:
                    return None
            return None if value is False else value

        def values(records):
            return [raw(record) for record in records]

        def present(records):
            return [v for v in values(records) if v is not None]

        def distinct_sorted(all_values):
            distinct = set(all_values)
            has_null = None in distinct
            distinct.discard(None)
            return [*sorted(distinct), *([None] if has_null else [])] or None

        if field.column_type and field.column_type[0] == "numeric":
            # a numeric column holds the decimal the float spells, and SUM
            # is exact: 0.1 + 0.2 answers 0.3, not the double's 0.30000000000000004
            def total(present_values):
                return float(sum(Decimal(repr(v)) for v in present_values))

            def mean(present_values):
                exact = sum(Decimal(repr(v)) for v in present_values)
                return float(exact / len(present_values))
        else:
            total = sum

            def mean(present_values):
                return sum(present_values) / len(present_values)

        readers = {
            "count": lambda records: len(present(records)),
            "count_distinct": lambda records: len(set(present(records))),
            "sum": lambda records: (
                total(present(records)) if present(records) else None
            ),
            "avg": lambda records: mean(present(records)) if present(records) else None,
            "max": lambda records: max(present(records), default=None),
            "min": lambda records: min(present(records), default=None),
            "bool_and": lambda records: (
                all(present(records)) if present(records) else None
            ),
            "bool_or": lambda records: (
                any(present(records)) if present(records) else None
            ),
            "array_agg": lambda records: values(records) or None,
            "array_agg_distinct": lambda records: distinct_sorted(values(records)),
            "recordset": lambda records: (
                [
                    id_
                    for record in records
                    for id_ in (record.ids if fname == "id" else record[fname].ids)
                ]
                or None
            ),
        }
        if func == "sum_currency":
            return self._sum_currency_reader(field, fname, raw)
        if func not in readers:
            self._unsupported(f"aggregate {spec!r}")
        return readers[func]

    def _sum_currency_reader(self, field, fname: str, raw):
        # the SQL path divides each value by the rate of its currency, 1.0
        # for a currency without one; the port picks the rate as its subquery does
        if not field.is_monetary:
            raise ValueError(
                f'Aggregator "sum_currency" only works on currency field for {fname!r}'
            )
        env = self.model.env
        currency_field_name = field.get_currency_field(self.model)
        rate_by_currency = env.registry.locale.currency_rates(
            env, env.company, Date.context_today(self.model)
        )

        def read(records):
            present = [
                (value, record[currency_field_name].id)
                for record in records
                if (value := raw(record)) is not None
            ]
            if not present:
                return None
            return sum(
                value / rate_by_currency.get(currency_id, 1.0)
                for value, currency_id in present
            )

        return read

    def rows(self, having, order, limit, offset) -> list[tuple]:
        self._select_order_aggregates(order)
        groups: dict[tuple, list] = {}
        for record in self.records:
            # a many2many term yields one key per related row, as the
            # relation LEFT JOIN yields one row per pair (or one NULL row)
            for key in product(
                *(
                    value if isinstance(value, _MultiValued) else (value,)
                    for value in (read(record) for read in self.groupby)
                )
            ):
                groups.setdefault(key, []).append(record)
        if not self.groupby:
            groups = {(): list(self.records)}
        rows = [
            (
                *key,
                *(
                    aggregate(self.model.browse(sorted(r.id for r in members)))
                    for aggregate in (*self.aggregates, *self.order_aggregates)
                ),
            )
            for key, members in groups.items()
        ]
        if having:
            keep = self._having_predicate(having)
            rows = [row for row in rows if keep(row) is True]
        self._sort(rows, order)
        if self.groupby:
            rows = rows[offset:]
            if limit is not None:
                rows = rows[:limit]
        if self.order_specs:
            width = len(self.groupby_specs) + len(self.aggregate_specs)
            rows = [row[:width] for row in rows]
        return rows

    def _select_order_aggregates(self, order: str | None) -> None:
        self.order_specs = []
        self.order_aggregates = []
        if not order:
            return
        for order_part in order.split(","):
            match = regex_order_part_read_group.fullmatch(order_part)
            if not match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = match["term"]
            if (
                term in self.groupby_specs
                or term in self.aggregate_specs
                or term in self.order_specs
            ):
                continue
            try:
                reader = self._aggregate_reader(term)
            except (ValueError, KeyError) as e:
                raise ValueError(
                    f"Order term {order_part!r} is not a valid aggregate nor valid groupby"
                ) from e
            self.order_specs.append(term)
            self.order_aggregates.append(reader)

    def _having_predicate(self, having: list):
        # the SQL path's polish-notation walk, with three-valued comparisons:
        # a NULL on either side answers None and the row is not kept
        specs = [*self.groupby_specs, *self.aggregate_specs]
        compare = {
            "=": pyoperator.eq,
            "!=": pyoperator.ne,
            "<": pyoperator.lt,
            "<=": pyoperator.le,
            ">": pyoperator.gt,
            ">=": pyoperator.ge,
        }

        def condition(item):
            left, op, right = item
            if left not in specs:
                raise ValueError(
                    f"Invalid having clause {item!r}: {left!r} is neither an "
                    "aggregate nor a groupby of this read_group"
                )
            index = specs.index(left)
            if op in ("in", "not in"):
                values = (
                    tuple(right) if isinstance(right, (list, set, frozenset)) else right
                )
                if isinstance(values, tuple) and not values:
                    return lambda row: op == "not in"
                return lambda row: (
                    None
                    if row[index] is None
                    else (row[index] in values) == (op == "in")
                )
            if op not in compare:
                raise ValueError(
                    f"Invalid having clause {item!r}: supported comparators are "
                    "('in', 'not in', '<', '>', '<=', '>=', '=', '!=')"
                )
            test = compare[op]
            return lambda row: (
                None if row[index] is None or right is None else test(row[index], right)
            )

        def negate(pred):
            return lambda row: None if (v := pred(row)) is None else not v

        def both(a, b):
            def pred(row):
                x, y = a(row), b(row)
                if x is False or y is False:
                    return False
                return None if x is None or y is None else True

            return pred

        def either(a, b):
            def pred(row):
                x, y = a(row), b(row)
                if x is True or y is True:
                    return True
                return None if x is None or y is None else False

            return pred

        stack: list = []
        try:
            for item in reversed(having):
                if item == "!":
                    stack.append(negate(stack.pop()))
                elif item == "&":
                    stack.append(both(stack.pop(), stack.pop()))
                elif item == "|":
                    stack.append(either(stack.pop(), stack.pop()))
                elif isinstance(item, (list, tuple)) and len(item) == 3:
                    stack.append(condition(item))
                else:
                    raise ValueError(
                        f"Invalid having clause {item!r}: it should be a domain-like clause"
                    )
            while len(stack) > 1:
                stack.append(both(stack.pop(), stack.pop()))
            [predicate] = stack
        except IndexError:
            raise ValueError(f"Invalid having clause {having!r}") from None
        return predicate

    def _sort(self, rows: list[tuple], order: str | None) -> None:
        # one stable pass per term, last term first, so the first term wins;
        # PostgreSQL puts NULLs last ascending and first descending
        for index, rank, desc, nulls_first in reversed(self._order_terms(rows, order)):
            # a NULL sorts first when its flag is the largest in the direction
            # of the pass: None-is-True ascending puts it last, descending first
            null_is_true = nulls_first == desc

            def key(row, index=index, rank=rank, null_is_true=null_is_true):
                value = row[index]
                if value is not None and rank is not None:
                    value = rank(value)
                if isinstance(value, list):
                    # PostgreSQL compares arrays element by element, a shorter
                    # prefix first and a NULL element after every value
                    value = tuple((item is None, item) for item in value)
                return (value is None if null_is_true else value is not None, value)

            rows.sort(key=key, reverse=desc)

    def _day_of_week_rank(self, spec: str):
        if parse_read_group_spec(spec)[2] != "day_of_week":
            return None
        # mod(7 - week_start + dow, 7): the language's first day sorts first
        week_start = int(get_lang(self.model.env).week_start)
        return lambda dow: (7 - week_start + dow) % 7

    def _order_terms(self, rows: list[tuple], order: str | None) -> list[tuple]:
        if not order:
            # SQL orders by the groupby terms as they are, ascending -- a
            # day_of_week term through the week-start shift, as its ORDER BY does
            return [
                (index, self._day_of_week_rank(spec), False, False)
                for index, spec in enumerate(self.groupby_specs)
            ]
        terms = []
        for order_part in order.split(","):
            match = regex_order_part_read_group.fullmatch(order_part)
            if not match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = match["term"]
            desc = (match["direction"] or "asc").lower() == "desc"
            nulls = (match["nulls"] or "").lower()
            nulls_first = nulls == "nulls first" if nulls else desc
            rank = None
            if term in self.groupby_specs:
                index = self.groupby_specs.index(term)
                fname, seq_fnames, _granularity = parse_read_group_spec(term)
                rank = self._day_of_week_rank(term)
                field = self.model._fields[fname]
                # a path spec groups by the comodel's field, which sorts as is
                if field.is_many2one and not seq_fnames:
                    comodel = self.model.env[field.comodel_name]
                    if comodel._order != "id":
                        ids = [row[index] for row in rows if row[index] is not None]
                        ordered = comodel.browse(ids).sorted(key=comodel._order)
                        positions = {
                            id_: position for position, id_ in enumerate(ordered._ids)
                        }
                        rank = positions.__getitem__
            elif term in self.aggregate_specs:
                index = len(self.groupby) + self.aggregate_specs.index(term)
            else:
                index = (
                    len(self.groupby)
                    + len(self.aggregate_specs)
                    + self.order_specs.index(term)
                )
            terms.append((index, rank, desc, nulls_first))
        return terms


def _order_within_grouping_set(
    order: str | None,
    present: typing.Sequence[str],
    aggregates: typing.Sequence[str],
    all_specs: typing.Sequence[str],
) -> str | None:
    # an order term on a groupby the set lacks sorts a NULL column: nothing
    if not order:
        return None
    kept = []
    for part in order.split(","):
        match = regex_order_part_read_group.fullmatch(part)
        if not match:
            raise ValueError(f"Invalid order {order!r} for _read_grouping_sets()")
        term = match["term"]
        if term in present or term in aggregates or term not in all_specs:
            kept.append(part.strip())
    return ", ".join(kept) or None


class _ForeignKeyPlan:
    __slots__ = ("backend", "m2m_rows", "nulls", "registry", "rows")

    def __init__(self, backend, registry) -> None:
        self.backend = backend
        self.registry = registry
        self.rows: dict[str, set[int]] = {}
        self.nulls: dict[str, list[tuple[int, dict]]] = {}
        self.m2m_rows: dict[str, set[int]] = {}

    def add_removal(self, model: BaseModel, ids: set[int]) -> None:
        storage = self.backend.storage
        seen = self.rows.setdefault(model._table, set())
        ids = ids.difference(seen)
        if not ids:
            return
        seen.update(ids)
        for field in model._fields.values():
            if field.is_many2many and field.store and field.relation and field.column1:
                self._add_relation_removal(field.relation, field.column1, ids)
        for field in self.registry.fields_by_comodel.get(model._name, ()):
            if not field.store:
                continue
            if field.is_many2many:
                if field.relation and field.column2:
                    self._add_relation_removal(field.relation, field.column2, ids)
                continue
            if not field.is_many2one or field.company_dependent:
                continue
            referrer = model.env[field.model_name]
            if referrer._abstract or not referrer._table:
                continue
            table = referrer._table
            hit = [
                row_id
                for row_id in storage.get_table_ids(table)
                if (row := storage.get_row(table, row_id))
                and row.get(field.name) in ids
                and row_id not in self.rows.get(table, ())
            ]
            if not hit:
                continue
            _debug.logic(
                "backend.memory.foreign_key",
                model=model._name,
                referrer=f"{field.model_name}.{field.name}",
                action=field.ondelete,
                rows=len(hit),
            )
            if field.ondelete == "cascade":
                self.add_removal(referrer, set(hit))
            elif field.ondelete == "restrict":
                raise ForeignKeyViolation(
                    f"update or delete on table {model._table!r} violates foreign "
                    f"key constraint on table {table!r}: key still referenced by "
                    f"{field.model_name}.{field.name}"
                )
            else:
                self.nulls.setdefault(table, []).extend(
                    (row_id, {field.name: None}) for row_id in hit
                )

    def _add_relation_removal(self, relation: str, column: str, ids: set[int]) -> None:
        self.m2m_rows.setdefault(relation, set()).update(
            row_id
            for row_id, row in self.backend._iter_m2m_rows(relation)
            if row.get(column) in ids
        )

    def apply(self, storage) -> None:
        for table, updates in self.nulls.items():
            storage.update_rows(table, updates)
        for relation, row_ids in self.m2m_rows.items():
            storage.remove_rows(relation, list(row_ids))
        for table, ids in self.rows.items():
            storage.remove_rows(table, list(ids))


class InMemoryBackend:
    __slots__ = ("columns", "sequences", "storage")

    def __init__(self, storage: DictBackend):
        self.storage = storage
        self.sequences: SequenceStore = InMemorySequenceStore(storage)
        self.columns: ColumnStore = InMemoryColumnStore(storage)

    def timezone_names(self, env) -> frozenset[str]:
        return _python_timezone_names()

    def create_rows(
        self,
        model: BaseModel,
        stored_list: list[dict[str, typing.Any]],
        columns: list[str],
        col_fields: list[Field],
    ) -> list[int]:
        row_dicts: list[dict[str, typing.Any]] = []
        new_ids: list[int] = []
        for stored in stored_list:
            new_id = self.storage.allocate_next_id(model._table)
            row_dict: dict[str, typing.Any] = {"id": new_id}
            for fname, field in zip(columns, col_fields, strict=True):
                if fname in stored:
                    row_dict[fname] = _unwrap_json(
                        # same flag as the PostgreSQL _prepare_insert_rows:
                        # an Html column is stored as handed in, not sanitized
                        field.convert_to_column_insert(
                            stored[fname], model, stored, validate=not field.is_html
                        )
                    )
            row_dicts.append(row_dict)
            new_ids.append(new_id)
        _check_table_constraints(self.storage, model, row_dicts)
        self.storage.put_rows(model._table, row_dicts)
        _debug.pipeline(
            "backend.memory.rows_created",
            model=model._name,
            rows=len(row_dicts),
            columns=len(columns),
        )
        return new_ids

    @staticmethod
    def _strip_company_fallbacks(model: BaseModel, field: Field, merged: dict) -> dict:
        kept = {}
        for key, item in merged.items():
            rec = model.with_company(int(key))
            fallback = field._to_json_value(
                field.convert_to_column(
                    field._get_company_dependent_fallback_raw(rec), rec
                )
            )
            if item != fallback:
                kept[key] = item
        return kept

    def update_rows(
        self, model: BaseModel, fnames: tuple[str, ...], rows: list[tuple]
    ) -> None:
        fields_map = model._fields
        updates = []
        for row in rows:
            id_ = row[0]
            values: dict[str, typing.Any] = {}
            for fname, value in zip(fnames, row[1:], strict=True):
                value = _unwrap_json(value)
                field = fields_map.get(fname)
                if (
                    value is not None
                    and field is not None
                    and (field.translate is True or field.company_dependent)
                    and isinstance(value, dict)
                ):
                    old_row = self.storage.get_row(model._table, id_)
                    old = old_row.get(fname) if old_row else None
                    if field.translate is True and not isinstance(old, dict):
                        old = {"en_US": next(iter(value.values()))}
                    if isinstance(old, dict):
                        value = {**old, **value}
                    if field.company_dependent and isinstance(value, dict):
                        # the SQL update stores only entries that differ from
                        # the field's fallback for their company (the
                        # jsonb_object_agg join in the PostgreSQL twin); the
                        # insert path already strips them
                        value = (
                            self._strip_company_fallbacks(model, field, value) or None
                        )
                values[fname] = value
            updates.append((id_, values))
        _check_table_constraints(
            self.storage,
            model,
            [
                {**(self.storage.get_row(model._table, id_) or {}), **values}
                for id_, values in updates
            ],
        )
        self.storage.update_rows(model._table, updates)

    def fetch(
        self,
        model: BaseModel,
        query: Query,
        column_fields: typing.Iterable[Field],
        other_fields: typing.Iterable[Field],
    ) -> BaseModel:
        column_fields = list(column_fields)
        result_ids = query._ids
        if result_ids is None:
            result_ids = tuple(self.storage.get_table_ids(model._table))
            _debug.logic(
                "backend.memory.fetch_whole_table",
                model=model._name,
                rows=len(result_ids),
            )
        elif column_fields:
            existing = self.storage.get_existing_ids(model._table, list(result_ids))
            result_ids = tuple(id_ for id_ in result_ids if id_ in existing)

        if not result_ids:
            _debug.logic("backend.memory.fetch_nothing", model=model._name)
            return model.browse()

        fetched = model.browse(result_ids)
        self._load_column_cache(model, result_ids, column_fields, fetched)

        if fetched:
            for field in other_fields:
                field.read(fetched)
        return fetched

    def _load_column_cache(
        self,
        model: BaseModel,
        record_ids: typing.Sequence[int],
        column_fields: list[Field],
        records: BaseModel,
    ) -> None:
        if not column_fields:
            return
        env = model.env
        _fdc = env._field_depends_context
        field_caches: dict = {}
        for field in column_fields:
            if field not in _fdc:
                field_caches[field] = env.core.get_field_data(field)
            else:
                try:
                    field_caches[field] = field._get_cache(env)
                except (KeyError, AttributeError, TypeError) as e:
                    _logger.debug(
                        "DictBackend cache load skipped %s.%s: %s",
                        model._name,
                        field.name,
                        e,
                    )
                    field_caches[field] = env.core.get_field_data(field)
        prefetch_langs = bool(env.context.get("prefetch_langs"))
        for field in column_fields:
            if field.is_stored_computed:
                # a stale PENDING marker would keep the row's value out
                field._clear_dead_pending(records)
        for record_id in record_ids:
            row = self.storage.get_row(model._table, record_id)
            if row is not None:
                for field in column_fields:
                    if field.translate and prefetch_langs:
                        # the whole translation object, spread over the
                        # language caches the way the SQL read is inserted
                        field._insert_cache(
                            model.browse((record_id,)),
                            [_unwrap_json(row.get(field.name))],
                        )
                        continue
                    value = _get_column_read_value(field, row.get(field.name), env)
                    if field.type == "json":
                        value = fast_clone(value)
                    elif not (field.is_binary and isinstance(value, str)):
                        # a pretty size enters the cache as the text SQL
                        # answers, not as the bytes a binary holds
                        value = field.convert_to_cache(value, records)
                    field_caches[field].setdefault(record_id, value)

    def search_raw(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
    ) -> Query | None:
        return None

    def search(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
        prof: typing.Any = None,
    ) -> Query:
        searched_fnames = flush_search_dependencies(model, domain, order)
        # a SQL search fills no field cache; the in-memory one evaluates the
        # domain and the order through the records, so what it loads to do
        # that is dropped again, and a test sees the cache PostgreSQL leaves
        cached_before = _cache_snapshot(model.env)
        all_ids = self.storage.get_table_ids(model._table)
        all_records = model.browse(all_ids)

        fields = model._fields
        self._load_column_cache(
            model,
            all_ids,
            [
                field
                for fname in searched_fnames.get(model._name, ())
                if (field := fields[fname]).column_type
            ],
            all_records,
        )

        if not domain.is_true():
            matching = all_records.filtered_domain(domain)
        else:
            matching = all_records

        if check_access:
            sec_domain = model.env.registry.access_policy.record_domain(
                model.env, model._name, "read"
            )
            if not sec_domain.is_true():
                _debug.logic(
                    "backend.memory.rules_applied", model=model._name, uid=model.env.uid
                )
                allowed = (
                    matching.sudo()
                    .with_context(active_test=False)
                    .filtered_domain(sec_domain)
                )
                matching = model.browse(allowed._ids)

        if order:
            matching = matching.sorted(key=order)

        ids = matching._ids
        if offset:
            ids = ids[offset:]
        if limit is not None and limit is not False:
            ids = ids[:limit]
        _drop_cache_additions(model.env, cached_before)

        _debug.pipeline(
            "backend.memory.search",
            model=model._name,
            scanned=len(all_ids),
            matched=len(matching),
            returned=len(ids),
            ordered=bool(order),
            check_access=check_access,
        )
        query = Query(model.env, model._table, model._table_sql)
        query._ids = tuple(ids)
        return query

    def as_query(self, model: BaseModel, ordered: bool = True) -> Query:
        query = Query(model.env, model._table, model._table_sql)
        query._ids = tuple(model._ids)
        return query

    def ancestors(
        self, model: BaseModel, parent_field: str, ids: typing.Collection[int]
    ) -> list[tuple[int, int | None]]:
        rows: dict[int, int | None] = {}
        frontier = list(ids)
        while frontier:
            next_frontier = []
            for id_ in frontier:
                if id_ in rows:
                    continue
                row = self.storage.get_row(model._table, id_)
                if row is None:
                    continue
                parent_id = row.get(parent_field) or None
                rows[id_] = parent_id
                if parent_id and parent_id not in rows:
                    next_frontier.append(parent_id)
            frontier = next_frontier
        return list(rows.items())

    def descendants(
        self,
        model: BaseModel,
        parent_field: str,
        root_ids: typing.Collection[int],
        *,
        domain: Domain,
        step_domain: Domain,
        same_columns: typing.Sequence[str] = (),
    ) -> Query:
        found: OrderedSet[int] = OrderedSet(
            model._search(domain & Domain("id", "in", list(root_ids))).get_result_ids()
        )
        frontier = list(found)
        while frontier:
            parents = model.browse(frontier)
            children = model.browse(
                model._search(
                    domain & step_domain & Domain(parent_field, "in", frontier)
                ).get_result_ids()
            )

            def same_key(record):
                # COALESCE(col::text, '') on the SQL side: only NULL collapses
                # to '', a stored 0 or false compares as its text -- which
                # takes the stored cell, since the cache reads NULL as the
                # type's falsy value
                row = self.storage.get_row(model._table, record.id) or {}
                key = []
                for column in same_columns:
                    value = row.get(column)
                    if value is None:
                        key.append("")
                    elif value is True or value is False:
                        key.append("true" if value else "false")
                    else:
                        key.append(str(value))
                return tuple(key)

            parent_values = {parent.id: same_key(parent) for parent in parents}
            frontier = [
                typing.cast("int", child.id)
                for child in children
                if child.id not in found
                and same_key(child) == parent_values[child[parent_field].id]
            ]
            found.update(frontier)
        return self.as_query(model.browse(list(found)), ordered=False)

    def read_group_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        groupby: typing.Sequence[str],
        aggregates: typing.Sequence[str],
        having: typing.Any,
        order: str | None,
        limit: int | None,
        offset: int,
    ) -> list[tuple]:
        return _InMemoryReadGroup(
            model, domain, groupby, aggregates, self.storage
        ).rows(having, order, limit, offset)

    def read_grouping_sets_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        grouping_sets: typing.Sequence[typing.Sequence[str]],
        groupby_terms: typing.Mapping[str, SQL],
        aggregates: typing.Sequence[str],
        order: str | None,
    ) -> list[tuple]:
        # one row per group of every set, shaped as GROUPING SETS answers: the
        # GROUPING() mask first (a bit per distinct term, set when the term is
        # absent from the set), then every groupby column (NULL when absent),
        # then the aggregates; each set sorted on its own by the order terms it
        # carries, as the SQL sort leaves the absent columns NULL
        all_specs = list(groupby_terms)
        mask_by_term = {
            term: 1 << index
            for index, term in enumerate(reversed(list(unique(groupby_terms.values()))))
        }
        rows: list[tuple] = []
        seen: set[frozenset] = set()
        for grouping_set in grouping_sets:
            terms = frozenset(groupby_terms[spec] for spec in grouping_set)
            if terms in seen:
                # SQL groups a set given twice once; the mixin copies its rows
                continue
            seen.add(terms)
            # a spec compiling to a term the set carries groups the same rows
            present = [spec for spec in all_specs if groupby_terms[spec] in terms]
            mask = sum(m for term, m in mask_by_term.items() if term not in terms)
            set_order = _order_within_grouping_set(
                order, present, aggregates, all_specs
            )
            group = _InMemoryReadGroup(model, domain, present, aggregates, self.storage)
            for row in group.rows(None, set_order, None, 0):
                values = dict(zip(present, row[: len(present)], strict=True))
                rows.append(
                    (
                        mask,
                        *(values.get(spec) for spec in all_specs),
                        *row[len(present) :],
                    )
                )
        _debug.pipeline(
            "backend.memory.grouping_sets",
            model=model._name,
            sets=len(grouping_sets),
            groupby=len(all_specs),
            aggregates=len(aggregates),
            rows=len(rows),
        )
        return rows

    def get_existing_ids(self, model: BaseModel, ids: typing.Iterable[int]) -> set[int]:
        return set(self.storage.get_existing_ids(model._table, list(ids)))

    def has_rows_beyond(self, model: BaseModel, count: int) -> bool:
        return self.storage.get_row_count(model._table) > count

    def has_cycle(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        ids: typing.Collection[int],
    ) -> bool:
        # the reachability CTE over the relation rows: a source that reaches
        # itself closes a cycle
        edges: defaultdict[int, set[int]] = defaultdict(set)
        for _row_id, row in self._iter_m2m_rows(relation):
            source, destination = row.get(column1), row.get(column2)
            if source is not None and destination is not None:
                edges[source].add(destination)
        for source in ids:
            seen: set[int] = set()
            frontier = set(edges.get(source, ()))
            while frontier:
                if source in frontier:
                    return True
                seen.update(frontier)
                frontier = {
                    destination
                    for node in frontier
                    for destination in edges.get(node, ())
                    if destination not in seen
                }
        return False

    def increment_columns_skip_locked(
        self, model: BaseModel, columns: typing.Sequence[str], ids: typing.Sequence[int]
    ) -> int:
        table = model._table
        updates = []
        for id_ in ids:
            row = self.storage.get_row(table, id_)
            if row is not None:
                updates.append(
                    (id_, {column: (row.get(column) or 0) + 1 for column in columns})
                )
        self.storage.update_rows(table, updates)
        return len(updates)

    def lock_for_update(
        self, model: BaseModel, *, allow_referencing: bool = False
    ) -> None:
        ids = {id_ for id_ in model._ids if id_}
        if not ids:
            return
        if len(self.storage.get_existing_ids(model._table, list(ids))) != len(ids):
            raise LockError(model.env._("Cannot grab a lock on records"))

    def try_lock_for_update(
        self,
        model: BaseModel,
        *,
        allow_referencing: bool = False,
        limit: int | None = None,
    ) -> BaseModel:
        # the PostgreSQL twin's selection rule: saturating new ids win the
        # whole limit; otherwise the limit buys real rows only, and every
        # new id rides along, all in the recordset's order
        new_ids, real = partition(lambda i: isinstance(i, NewId), model._ids)
        if limit is not None and len(new_ids) >= limit:
            return model.browse(new_ids[:limit])
        existing = self.storage.get_existing_ids(model._table, real)
        lockable_real = [
            i for i in model._ids if not isinstance(i, NewId) and i in existing
        ]
        if limit is not None:
            lockable_real = lockable_real[: limit - len(new_ids)]
        valid = set(lockable_real) | set(new_ids)
        return model.browse(i for i in model._ids if i in valid)

    def unlink_rows(self, model: BaseModel, sub_ids: tuple[int, ...]) -> None:
        env = model.env
        wanted = set(sub_ids)
        # what the database's foreign keys do on DELETE -- cascade through,
        # null out or refuse the referencing many2one columns, and drop the
        # rows of every many2many relation table naming the ids -- planned
        # in full first, so a refusal deep in a cascade deletes nothing
        plan = _ForeignKeyPlan(self, env.registry)
        plan.add_removal(model, wanted)

        many2one_fields = env.registry.many2one_company_dependents[model._name]
        uninstalling = env.context.get(MODULE_UNINSTALL_FLAG)
        if many2one_fields and not uninstalling:
            PostgresBackend._unlink_default_guard(model, sub_ids, many2one_fields)
        # the company-dependent many2one references live in json objects the
        # foreign keys do not see: refused or cleared here, as the SQL branch
        # does with a jsonpath scan -- every refusal found before any clearing
        clearing: list[tuple[Field, int, dict]] = []
        for field in many2one_fields:
            referrer = env[field.model_name]
            # the SQL branch scans after its DELETE: a referrer the batch
            # deletes, directly or through a foreign key, refuses nothing
            doomed = plan.rows.get(referrer._table, ())
            for row_id in self.storage.get_table_ids(referrer._table):
                if row_id in doomed:
                    continue
                row = self.storage.get_row(referrer._table, row_id)
                values = row.get(field.name) if row else None
                if not isinstance(values, dict):
                    continue
                hit = {key for key, value in values.items() if value in wanted}
                if not hit:
                    continue
                if field.ondelete == "restrict" and not uninstalling:
                    raise UserError(
                        _(
                            "You cannot delete %(to_delete_record)s, as it is used by %(on_restrict_record)s",
                            to_delete_record=model.browse(values[next(iter(hit))]),
                            on_restrict_record=referrer.browse(row_id),
                        )
                    )
                cleared = {
                    key: None if key in hit else value for key, value in values.items()
                }
                clearing.append((field, row_id, cleared))

        for field, row_id, cleared in clearing:
            self.storage.update_rows(
                env[field.model_name]._table, [(row_id, {field.name: cleared})]
            )
        plan.apply(self.storage)
        for field in {field for field, _row_id, _cleared in clearing}:
            row_ids = [r for f, r, _c in clearing if f is field]
            env[field.model_name].browse(row_ids).modified([field.name])
        env.registry.metaschema.discard_defaults(env, model.browse(sub_ids))

    def _iter_m2m_rows(self, relation: str):
        for row_id in self.storage.get_table_ids(relation):
            row = self.storage.get_row(relation, row_id)
            if row is not None:
                yield row_id, row

    def _read_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        ids: typing.Collection[int],
    ) -> list[tuple[int, int]]:
        wanted = set(ids)
        return [
            (row[column1], row[column2])
            for _row_id, row in self._iter_m2m_rows(relation)
            if row.get(column1) in wanted
        ]

    def set_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int]
    ) -> list[tuple[int, str]]:
        table, parent_column = model._table, model._parent_name
        updated: list[tuple[int, str]] = []
        for id_ in ids:
            row = self.storage.get_row(table, id_)
            if row is None:
                continue
            parent_row = (
                self.storage.get_row(table, row[parent_column])
                if row.get(parent_column)
                else None
            )
            prefix = (parent_row or {}).get("parent_path") or ""
            updated.append((id_, f"{prefix}{id_}/"))
        self.storage.update_rows(
            table, [(id_, {"parent_path": path}) for id_, path in updated]
        )
        return updated

    def records_with_parent_changed(
        self, model: BaseModel, parent_to_ids: dict[typing.Any, list[int]]
    ) -> list[int]:
        table, parent_column = model._table, model._parent_name
        changed: list[int] = []
        for parent_id, ids in parent_to_ids.items():
            for id_ in ids:
                row = self.storage.get_row(table, id_)
                if row is None:
                    continue
                stored = row.get(parent_column) or None
                if (stored != parent_id) if parent_id else (stored is not None):
                    changed.append(id_)
        return sorted(changed)

    def move_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int], prefix: str
    ) -> dict[int, str]:
        table = model._table
        moved: dict[int, str] = {}
        for node_id in ids:
            node = self.storage.get_row(table, node_id)
            node_path = (node or {}).get("parent_path")
            if not node_path:
                continue
            cut = len(node_path) - len(f"{node_id}/")
            for child_id in self.storage.get_table_ids(table):
                child = self.storage.get_row(table, child_id)
                child_path = (child or {}).get("parent_path") or ""
                if child_path.startswith(node_path):
                    moved[child_id] = f"{prefix}{child_path[cut:]}"
        self.storage.update_rows(
            table, [(id_, {"parent_path": path}) for id_, path in moved.items()]
        )
        return moved

    def read_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, list[int]]:
        position = {id2: index for index, id2 in enumerate(query.get_result_ids())}
        group: dict[int, list[int]] = defaultdict(list)
        for id1, id2 in self._read_m2m_pairs(
            records, relation, column1, column2, records.ids
        ):
            if id2 in position:
                group[id1].append(id2)
        for ids2 in group.values():
            ids2.sort(key=position.__getitem__)
        return group

    def count_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, int]:
        groups = self.read_m2m_groups(records, relation, column1, column2, query)
        return {id1: len(ids2) for id1, ids2 in groups.items()}

    def link_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        existing: set[tuple] = {
            (row.get(column1), row.get(column2))
            for _row_id, row in self._iter_m2m_rows(relation)
        }
        to_insert = []
        for pair in pairs:
            key = tuple(pair)
            if key not in existing:
                existing.add(key)
                to_insert.append(key)
        if to_insert:
            self.storage.insert_rows(relation, [column1, column2], to_insert)

    def unlink_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        doomed = {tuple(pair) for pair in pairs}
        row_ids = [
            row_id
            for row_id, row in self._iter_m2m_rows(relation)
            if (row.get(column1), row.get(column2)) in doomed
        ]
        if row_ids:
            self.storage.remove_rows(relation, row_ids)
