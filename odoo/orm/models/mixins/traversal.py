"""
Traversal operations mixin for BaseModel.

This module contains methods for traversing and transforming recordsets:
mapped, filtered, grouped, sorted, and update.
"""

import functools
import typing
from collections import defaultdict
from collections.abc import Callable
from operator import itemgetter

from odoo.libs._field_access import batch_cache_filter as _batch_cache_filter
from odoo.libs._field_access import batch_cache_get as _batch_cache_get
from odoo.libs._field_access import batch_cache_values as _batch_cache_values
from odoo.libs.constants import PREFETCH_MAX
from odoo.tools import SQL
from odoo.tools.misc import PENDING, SENTINEL

from ... import decorators as api
from ..._typing import DomainType, Self
from ...domain import Domain
from ...parsing import regex_order

T = typing.TypeVar("T")

# Field types where convert_to_record(value, rec) is identity when value is not None.
# For these types we bypass singleton record creation AND method dispatch in mapped().
_MAPPED_IDENTITY_TYPES = frozenset(
    {
        "boolean",
        "date",
        "datetime",
        "selection",
        "integer",
        "float",
        "monetary",
    }
)
_MAPPED_CHAR_TEXT = frozenset({"char", "text"})


@functools.total_ordering
class ReversibleComparator:
    """A comparator that supports reverse ordering and None handling."""

    __slots__ = ("__item", "__none_first", "__reverse")

    def __init__(self, item, reverse: bool, none_first: bool):
        self.__item = item
        self.__reverse = reverse
        self.__none_first = none_first

    def __lt__(self, other: ReversibleComparator) -> bool:
        item = self.__item
        item_cmp = other.__item
        # Check None before equality — equality on nested comparators
        # can crash if one item is None and the other is a comparator.
        if item is None:
            return False if item_cmp is None else self.__none_first
        if item_cmp is None:
            return not self.__none_first
        if item == item_cmp:
            return False
        if self.__reverse:
            item, item_cmp = item_cmp, item
        return item < item_cmp

    def __eq__(self, other) -> bool:
        if other.__class__ is not ReversibleComparator:
            return NotImplemented
        return self.__item == other.__item

    def __hash__(self):
        return hash(self.__item)

    def __repr__(self):
        return f"<ReversibleComparator {self.__item!r}{' reverse' if self.__reverse else ''}>"


class TraversalMixin:
    """Mixin providing traversal and transformation operations for recordsets.

    This mixin contains methods for:
    - Mapping over records (mapped)
    - Filtering records (filtered, filtered_domain)
    - Grouping records (grouped)
    - Sorting records (sorted)
    - Updating records (update)
    """

    __slots__ = ()

    @typing.overload
    def mapped(self, func: str) -> list[typing.Any]: ...

    @typing.overload
    def mapped(self, func: Callable[[Self], T]) -> list[T]: ...

    @api.private
    def mapped(self, func):
        """Apply ``func`` on all records in ``self``, and return the result as a
        list or a recordset (if ``func`` return recordsets). In the latter
        case, the order of the returned recordset is arbitrary.

        :param func: a function or a dot-separated sequence of field names
        :return: self if func is falsy, result of func applied to all ``self`` records.

        .. code-block:: python3

            # returns a list of summing two fields for each record in the set
            records.mapped(lambda r: r.field1 + r.field2)

        The provided function can be a string to get field values:

        .. code-block:: python3

            # returns a list of names
            records.mapped('name')

            # returns a recordset of partners
            records.mapped('partner_id')

            # returns the union of all partner banks, with duplicates removed
            records.mapped('partner_id.bank_ids')
        """
        if not func:
            return self  # support for an empty path of fields

        if isinstance(func, str):
            # special case: sequence of field names
            *rel_field_names, field_name = func.split(".")
            records = self
            for rel_field_name in rel_field_names:
                records = records[rel_field_name]
            if len(records) > PREFETCH_MAX:
                # fetch fields for all recordset in case we have a recordset
                # that is larger than the prefetch
                records.fetch([field_name])
            field = records._fields[field_name]
            getter = field.__get__
            if field.relational:
                # union of records
                return getter(records)
            # Non-relational fast path: batch preconditions once, then
            # loop with direct cache access.  Falls back to __get__ on
            # cache miss (handles DB fetch, defaults, new records).
            if not records:
                return []
            field.ensure_access(records[:1])
            field.ensure_computed(records)
            field_cache = field._get_cache(records.env)
            _SENTINEL = SENTINEL
            _PENDING = PENDING
            _get = field_cache.get
            result = []
            _append = result.append
            # Identity-convert optimisation: for most scalar types,
            # convert_to_record(value, rec) == value when value is not
            # None.  Skip convert_to_record method dispatch entirely.
            # We still iterate records (not raw _ids) to preserve the
            # prefetch group — on cache miss, __get__ fetches the whole
            # batch via the shared _prefetch_ids.
            if field.type in _MAPPED_IDENTITY_TYPES or (
                field.type in _MAPPED_CHAR_TEXT and not callable(field.translate)
            ):
                _none_val = field.convert_to_record(None, records[:1])
                result, miss_indices = _batch_cache_get(
                    field_cache, records._ids, PENDING, _none_val
                )
                if miss_indices:
                    # Create singletons only for missed indices — list()
                    # preserves _prefetch_ids (shared from __iter__).
                    rec_list = list(records)
                    for idx in miss_indices:
                        result[idx] = getter(rec_list[idx])
                return result
            else:
                _convert = field.convert_to_record
                for record in records:
                    value = _get(record._ids[0], _SENTINEL)
                    if value is not _SENTINEL and value is not _PENDING:
                        _append(_convert(value, record))
                    else:
                        _append(getter(record))
            return result

        if self:
            # Import here to avoid circular imports
            from ..base import BaseModel

            vals = [func(rec) for rec in self]
            if isinstance(vals[0], BaseModel):
                return vals[0].union(*vals[1:])
            return vals
        else:
            # we want to follow-up the comodel from the function
            # so we pass an empty recordset
            from ..base import BaseModel

            vals = func(self)
            return vals if isinstance(vals, BaseModel) else []

    @api.private
    def filtered(self, func) -> Self:
        """Return the records in ``self`` satisfying ``func``.

        :param func: a function, Domain or a dot-separated sequence of field names
        :return: recordset of records satisfying func, may be empty.

        .. code-block:: python3

            # only keep records whose company is the current user's
            records.filtered(lambda r: r.company_id == user.company_id)

            # only keep records whose partner is a company
            records.filtered("partner_id.is_company")
        """
        if not func:
            # align with mapped()
            return self
        if not self:
            return self
        if callable(func):
            # normal function
            pass
        elif isinstance(func, str):
            if "." in func:
                return self.browse(
                    rec_id
                    for rec_id, rec in zip(self._ids, self, strict=False)
                    if any(rec.mapped(func))
                )
            # Fast path: batch ACL + recompute, then C-level cache scan.
            # Falls back to __get__ only for missed indices (preserves
            # prefetch groups via list(self) which shares _prefetch_ids).
            field = self._fields[func]
            field.ensure_access(self[0:1])
            field.ensure_computed(self)
            field_cache = field._get_cache(self.env)
            passing_ids, miss_indices = _batch_cache_filter(
                field_cache, self._ids, PENDING
            )
            if miss_indices:
                _field_get = field.__get__
                rec_list = list(self)
                for idx in miss_indices:
                    if _field_get(rec_list[idx]):
                        passing_ids.append(rec_list[idx]._ids[0])
                # Re-establish original order: cache-hit IDs come out in
                # order, but miss IDs are appended at the end.  Rebuild
                # using a set + original tuple scan to restore order.
                all_passing = set(passing_ids)
                passing_ids = [id_ for id_ in self._ids if id_ in all_passing]
            return self.browse(passing_ids)
        elif isinstance(func, Domain):
            return self.filtered_domain(func)
        else:
            raise TypeError(f"Invalid function {func!r} to filter on {self._name}")
        return self.browse(rec_id for rec_id, rec in zip(self._ids, self, strict=False) if func(rec))

    @typing.overload
    def grouped(self, key: str) -> dict[typing.Any, Self]: ...

    @typing.overload
    def grouped(self, key: Callable[[Self], T]) -> dict[T, Self]: ...

    @api.private
    def grouped(self, key):
        """Eagerly groups the records of ``self`` by the ``key``, returning a
        dict from the ``key``'s result to recordsets. All the resulting
        recordsets are guaranteed to be part of the same prefetch-set.

        Provides a convenience method to partition existing recordsets without
        the overhead of a :meth:`~._read_group`, but performs no aggregation.

        .. note:: unlike :func:`itertools.groupby`, does not care about input
                  ordering, however the tradeoff is that it can not be lazy

        :param key: either a callable from a :class:`Model` to a (hashable)
                    value, or a field name. In the latter case, it is equivalent
                    to ``itemgetter(key)`` (aka the named field's value)
        """
        if not self:
            return {}

        if isinstance(key, str):
            field = self._fields[key]
            if not field.relational:
                # Scalar fast path: batch ACL + recompute, then direct cache
                # loop.  Groups by convert_to_record(cache_value), falling back
                # to __get__ on cache miss.
                field.ensure_access(self[:1])
                field.ensure_computed(self)
                field_cache = field._get_cache(self.env)
                _SENTINEL = SENTINEL
                _PENDING = PENDING
                _get = field_cache.get
                _field_get = field.__get__
                collator = defaultdict(list)
                # Identity-convert: skip convert_to_record dispatch for
                # types where it's a no-op (same pattern as mapped()).
                if field.type in _MAPPED_IDENTITY_TYPES or (
                    field.type in _MAPPED_CHAR_TEXT and not callable(field.translate)
                ):
                    _none_val = field.convert_to_record(None, self[:1])
                    ids = self._ids
                    results, miss_indices = _batch_cache_get(
                        field_cache, ids, PENDING, _none_val
                    )
                    if not miss_indices:
                        for i, rec_id in enumerate(ids):
                            collator[results[i]].append(rec_id)
                    else:
                        miss_set = set(miss_indices)
                        rec_list = list(self)
                        for i, rec_id in enumerate(ids):
                            if i in miss_set:
                                collator[_field_get(rec_list[i])].append(rec_id)
                            else:
                                collator[results[i]].append(rec_id)
                else:
                    _convert = field.convert_to_record
                    for record in self:
                        rec_id = record._ids[0]
                        value = _get(rec_id, _SENTINEL)
                        if value is not _SENTINEL and value is not _PENDING:
                            try:
                                group_key = _convert(value, record)
                            except KeyError:
                                group_key = _field_get(record)
                        else:
                            group_key = _field_get(record)
                        collator[group_key].append(rec_id)
            else:
                key = itemgetter(key)
                collator = defaultdict(list)
                for record in self:
                    collator[key(record)].append(record._ids[0])
        else:
            collator = defaultdict(list)
            for record in self:
                collator[key(record)].append(record._ids[0])

        cls = type(self)
        env = self.env
        prefetch_ids = self._prefetch_ids
        return {
            key: cls(env, tuple(ids), prefetch_ids) for key, ids in collator.items()
        }

    @api.private
    def filtered_domain(self, domain: DomainType) -> Self:
        """Return the records in ``self`` satisfying the domain and keeping the same order.

        :param domain: :ref:`A search domain <reference/orm/domains>`.
        """
        if not self or not domain:
            return self
        predicate = Domain(domain)._as_predicate(self)
        return self.browse(
            rec_id for rec_id, rec in zip(self._ids, self, strict=False) if predicate(rec)
        )

    @api.private
    def sorted(self, key=None, reverse: bool = False) -> Self:
        """Return the recordset ``self`` ordered by ``key``.

        :param key:
            It can be either of:

            * a function of one argument that returns a comparison key for each record
            * a string representing a comma-separated list of field names with optional
              NULLS (FIRST|LAST), and (ASC|DESC) directions
            * ``None``, in which case records are ordered according the default model's order
        :param reverse: if ``True``, return the result in reverse order

        .. code-block:: python3

            # sort records by name
            records.sorted(key=lambda r: r.name)
            # sort records by name in descending order, then by id
            records.sorted('name DESC, id')
            # sort records using default order
            records.sorted()
        """
        if len(self) < 2:
            return self
        if isinstance(key, str):
            order = key
            # Batch ensure_computed for all sort fields — avoids redundant
            # pending_ids checks in __get__ during O(N log N) comparisons.
            self._sorted_ensure_computed(order)
            # Try ID-based sort: avoids creating N singleton records
            ids = self._sorted_by_ids(order, reverse)
            if ids is not None:
                rs = object.__new__(self.__class__)
                rs.env = self.env
                rs._ids = ids
                rs._prefetch_ids = self._prefetch_ids
                return rs
            key = self._sorted_order_to_function(order)
        elif key is None:
            order = self._order
            self._sorted_ensure_computed(order)
            ids = self._sorted_by_ids(order, reverse)
            if ids is not None:
                rs = object.__new__(self.__class__)
                rs.env = self.env
                rs._ids = ids
                rs._prefetch_ids = self._prefetch_ids
                return rs
            key = self._sorted_order_to_function(order)
        ids = tuple(item._ids[0] for item in sorted(self, key=key, reverse=reverse))
        rs = object.__new__(self.__class__)
        rs.env = self.env
        rs._ids = ids
        rs._prefetch_ids = self._prefetch_ids
        return rs

    def _sorted_ensure_computed(self, order: str) -> None:
        """Pre-trigger access check + recomputation for all sort fields.

        Called before Python's ``sorted()`` so that each per-record key
        extraction can bypass ``__get__`` and read the cache directly.
        """
        _fields = self._fields
        first = self[:1]
        for part in order.split(","):
            match = regex_order.match(part)
            if match:
                field = _fields.get(match["field"])
                if field is not None:
                    field.ensure_access(first)
                    field.ensure_computed(self)

    # Field types eligible for ID-based sort: non-relational, non-boolean
    # scalars whose cache value is directly comparable.  Boolean is excluded
    # because it sorts via expression_getter (not raw cache access).
    _SORTABLE_SCALAR_TYPES = frozenset(
        {
            "char",
            "text",
            "integer",
            "float",
            "monetary",
            "date",
            "datetime",
            "selection",
        }
    )

    def _sorted_by_ids(self, order: str, reverse: bool) -> tuple | None:
        """Try to sort ``self._ids`` directly from cache values.

        Returns the sorted tuple of IDs on success, or ``None`` if the
        fast path is not applicable (relational, property, boolean, or
        cache miss).

        Supports single-field AND multi-field sorts.  This avoids creating
        N singleton record objects that the general ``sorted(self, key=...)``
        path requires.  For 100 records × 2 fields, this eliminates ~100
        object.__new__ calls and ~1600 ReversibleComparator allocations.
        """
        parts = order.split(",")
        _SENTINEL = SENTINEL
        _PENDING = PENDING
        _fields = self._fields
        _SORTABLE = self._SORTABLE_SCALAR_TYPES
        ids = self._ids
        env = self.env
        n = len(ids)

        # Parse all sort parts; bail if any is non-sortable
        sort_specs = []  # list of (field_cache, desc, nulls_first)
        for part in parts:
            match = regex_order.match(part)
            if not match:
                return None
            field_name = match["field"]
            if match["property"]:
                return None
            field = _fields.get(field_name)
            if field is None or field.type not in _SORTABLE:
                return None
            desc = (match["direction"] or "").upper() == "DESC"
            nulls_raw = (match["nulls"] or "").upper()
            nulls_first = (nulls_raw == "NULLS FIRST") if nulls_raw else desc
            sort_specs.append((field._get_cache(env), desc, nulls_first))

        if len(sort_specs) == 1:
            # ── Single-field fast path ──
            field_cache, desc, nulls_first = sort_specs[0]
            values = _batch_cache_values(field_cache, ids, _PENDING)
            if values is None:
                return None

            reverse_param = desc != reverse
            has_nulls = False
            for v in values:
                if v is None or v is False:
                    has_nulls = True
                    break

            _key1 = itemgetter(1)
            if not has_nulls:
                id_value_pairs = list(zip(ids, values, strict=False))
                id_value_pairs.sort(key=_key1, reverse=reverse_param)
                return tuple(pair[0] for pair in id_value_pairs)

            null_high = nulls_first == desc
            _null_rank = 1 if null_high else 0
            _val_rank = 0 if null_high else 1
            _null_key = (_null_rank, "")
            keys = []
            for v in values:
                if v is None or v is False:
                    keys.append(_null_key)
                else:
                    keys.append((_val_rank, v))

            id_key_pairs = list(zip(ids, keys, strict=False))
            id_key_pairs.sort(key=_key1, reverse=reverse_param)
            return tuple(pair[0] for pair in id_key_pairs)

        # ── Multi-field path ──
        # Only handle uniform direction (all ASC or all DESC).
        # Mixed-direction multi-field sorts (e.g. "name ASC, id DESC") are
        # rare and need per-field negation — fall back to record-based path.
        all_desc = sort_specs[0][1]
        for _, desc, _ in sort_specs[1:]:
            if desc != all_desc:
                return None

        # Uniform direction: build composite tuple keys from cache values.
        # The tuple comparison naturally gives multi-field ordering.
        reverse_param = all_desc != reverse
        has_nulls = False
        columns = []
        null_specs = []  # per-field null handling
        for field_cache, desc, nulls_first in sort_specs:
            col = _batch_cache_values(field_cache, ids, _PENDING)
            if col is None:
                return None
            if not has_nulls:
                for v in col:
                    if v is None or v is False:
                        has_nulls = True
                        break
            columns.append(col)
            null_high = nulls_first == desc
            null_specs.append((1 if null_high else 0, 0 if null_high else 1))

        _key1 = itemgetter(1)
        if not has_nulls:
            # No nulls in any field: raw tuple comparison
            keys = [tuple(columns[c][i] for c in range(len(columns))) for i in range(n)]
            id_key_pairs = list(zip(ids, keys, strict=False))
            id_key_pairs.sort(key=_key1, reverse=reverse_param)
            return tuple(pair[0] for pair in id_key_pairs)

        # Null-safe: build (null_rank, value) per field per record
        num_cols = len(columns)
        keys = []
        for i in range(n):
            key = []
            for c in range(num_cols):
                v = columns[c][i]
                _null_rank, _val_rank = null_specs[c]
                if v is None or v is False:
                    key.append((_null_rank, ""))
                else:
                    key.append((_val_rank, v))
            keys.append(tuple(key))

        id_key_pairs = list(zip(ids, keys, strict=False))
        id_key_pairs.sort(key=_key1, reverse=reverse_param)
        return tuple(pair[0] for pair in id_key_pairs)

    @api.model
    def _sorted_order_to_function(self, order: str):
        _env = self.env

        def order_to_function(order_part):
            order_match = regex_order.match(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} to sort")
            field_name = order_match["field"]
            property_name = order_match["property"]
            reverse = (order_match["direction"] or "").upper() == "DESC"
            nulls = (order_match["nulls"] or "").upper()
            if nulls:
                nulls_first = nulls == "NULLS FIRST"
            else:
                nulls_first = reverse

            field = self._fields[field_name]
            field_expr = (
                f"{field_name}.{property_name}" if property_name else field_name
            )
            if field.type == "many2one" and (
                not property_name or property_name == "id"
            ):
                seen = _env.context.get("__m2o_order_seen_sorted", ())
                if field in seen:
                    return lambda _: None
                comodel = _env[field.comodel_name].with_context(
                    __m2o_order_seen_sorted=frozenset((field, *seen))
                )
                func_comodel = comodel._sorted_order_to_function(
                    property_name or comodel._order
                )

                def getter(rec):
                    value = rec[field_name]
                    if not value:
                        return None
                    return func_comodel(value)

            elif field.relational:
                raise ValueError(
                    f"Invalid order on relational field {order_part!r} to sort"
                )
            elif field.type == "boolean":
                getter = field.expression_getter(field_expr)
            elif not property_name:
                # Scalar non-boolean: direct cache access bypasses __get__
                # (ACL + recompute already handled by _sorted_ensure_computed)
                _cache_get = field._get_cache(_env).get
                _field_get = field.__get__
                _S = SENTINEL
                _P = PENDING

                def getter(rec):
                    value = _cache_get(rec._ids[0], _S)
                    if value is _S or value is _P:
                        value = _field_get(rec)
                    return value if value is not False else None

            else:
                raw_getter = field.expression_getter(field_expr)

                def getter(rec):
                    value = raw_getter(rec)
                    return value if value is not False else None

            comparator = functools.partial(
                ReversibleComparator,
                reverse=reverse,
                none_first=nulls_first,
            )
            return lambda rec: comparator(getter(rec))

        item_makers = [order_to_function(order_part) for order_part in order.split(",")]
        if len(item_makers) == 1:
            return item_makers[0]
        return lambda rec: tuple(fn(rec) for fn in item_makers)

    @api.private
    def update(self, values) -> None:
        """Update the records in ``self`` with ``values``."""
        for name, value in values.items():
            self[name] = value

    # -------------------------------------------------------------------------
    # Cycle detection
    # -------------------------------------------------------------------------

    def _has_cycle(self, field_name=None) -> bool:
        """
        Return whether the records in ``self`` are in a loop by following the
        given relationship of the field.
        By default the **parent** field is used as the relationship.

        Note that since the method does not use EXCLUSIVE LOCK for the sake of
        performance, loops may still be created by concurrent transactions.

        :param field_name: optional field name (default: ``self._parent_name``)
        :return: **True** if a loop was found, **False** otherwise.
        """
        if not field_name:
            field_name = self._parent_name

        field = self._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field_name: {field_name!r}")

        if not (
            field.type in ("many2many", "many2one")
            and field.comodel_name == self._name
            and field.store
        ):
            raise ValueError(
                f"Field must be a many2one or many2many relation on itself: {field_name!r}"
            )

        if not self.ids:
            return False

        # must ignore 'active' flag, ir.rules, etc.
        # direct recursive SQL query with cycle detection for performance
        self.flush_model([field_name])
        if field.type == "many2many":
            relation = field.relation
            column1 = field.column1
            column2 = field.column2
        else:
            relation = self._table
            column1 = "id"
            column2 = field_name
        cr = self.env.cr
        cr.execute(
            SQL(
                """
            WITH RECURSIVE __reachability AS (
                SELECT %(col1)s AS source, %(col2)s AS destination
                FROM %(rel)s
                WHERE %(col1)s IN %(ids)s AND %(col2)s IS NOT NULL
            UNION
                SELECT r.source, t.%(col2)s
                FROM __reachability r
                JOIN %(rel)s t ON r.destination = t.%(col1)s AND t.%(col2)s IS NOT NULL
            )
            SELECT 1 FROM __reachability
            WHERE source = destination
            LIMIT 1
            """,
                ids=tuple(self.ids),
                rel=SQL.identifier(relation),
                col1=SQL.identifier(column1),
                col2=SQL.identifier(column2),
            )
        )
        return bool(cr.fetchone())
