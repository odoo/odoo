import functools
import typing
from collections import defaultdict
from operator import itemgetter
from typing import Self

from odoo.libs.accel import batch_cache_filter as _batch_cache_filter
from odoo.libs.accel import batch_cache_get as _batch_cache_get
from odoo.libs.accel import batch_group_ids as _batch_group_ids
from odoo.libs.accel import sort_ids_by_cache as _sort_ids_by_cache
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet
from odoo.tools.misc import PENDING, SENTINEL

from ... import decorators as api
from ..._recordset import is_recordset
from ..._typing import DomainType
from ...domain import Domain
from ...parsing import regex_order
from ...primitives import PREFETCH_MAX
from ._cache_scan import (
    as_scannable_cache,
    can_scan_identity,
    can_scan_sorted,
    can_scan_truthy,
    has_lang_dict_cache,
    is_cache_detached,
)
from ._model_stubs import _ModelStubs

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from ..._typing import BaseModel

T = typing.TypeVar("T")


@functools.total_ordering
class ReversibleComparator:
    __slots__ = ("__item", "__none_first", "__reverse")

    def __init__(self, item, reverse: bool, none_first: bool):
        self.__item = item
        self.__reverse = reverse
        self.__none_first = none_first

    def __lt__(self, other: ReversibleComparator) -> bool:
        item = self.__item
        item_cmp = other.__item
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


class TraversalMixin(_ModelStubs):
    __slots__ = ()

    @typing.overload
    def mapped(self, func: str) -> list[typing.Any]: ...

    @typing.overload
    def mapped(self, func: Callable[[Self], T]) -> list[T]: ...

    @api.private
    def mapped(self, func: str | Callable) -> list | Self:
        if not func:
            return self

        if isinstance(func, str):
            *rel_field_names, field_name = func.split(".")
            records = self
            for rel_field_name in rel_field_names:
                records = records[rel_field_name]
            if len(records) > PREFETCH_MAX:
                _debug.logic(
                    "traversal.mapped.prefetch_exceeded",
                    model=records._name,
                    field=field_name,
                    records=len(records),
                )
                records.fetch([field_name])
            field = records._fields[field_name]
            getter = field.__get__
            if field.relational:
                return getter(records)
            if not records:
                return []
            field.check_read_access(records)
            field.recompute_pending(records)
            field_cache = field._get_cache(records.env)
            _SENTINEL = SENTINEL
            _PENDING = PENDING
            _get = field_cache.get
            result: list[typing.Any] = []
            _append = result.append
            if can_scan_identity(field):
                _none_val: typing.Any = field.convert_to_record(None, records[:1])
                result, miss_indices = _batch_cache_get(
                    as_scannable_cache(field_cache), records._ids, PENDING, _none_val
                )
                if miss_indices:
                    rec_list = list(records)
                    for idx in miss_indices:
                        result[idx] = getter(rec_list[idx])
                    if is_cache_detached(field, records.env, field_cache):
                        _debug.logic(
                            "traversal.mapped.cache_detached",
                            model=records._name,
                            field=field_name,
                            records=len(records),
                            misses=len(miss_indices),
                        )
                        return [getter(record) for record in records]
                return result
            else:
                _convert = field.convert_to_record
                _detached = False
                for record in records:
                    value = _get(record._ids[0], _SENTINEL)
                    if value is not _SENTINEL and value is not _PENDING:
                        _append(_convert(value, record))
                    else:
                        _append(getter(record))
                        _detached = _detached or is_cache_detached(
                            field, records.env, field_cache
                        )
                if _detached:
                    _debug.logic(
                        "traversal.mapped.cache_detached",
                        model=records._name,
                        field=field_name,
                        records=len(records),
                    )
                    return [getter(record) for record in records]
            return result

        if self:
            vals = [func(rec) for rec in self]
            if is_recordset(vals[0]):
                return typing.cast("Self", vals[0].union(*vals[1:]))
            return vals
        else:
            single = func(self)
            return typing.cast("Self", single) if is_recordset(single) else []

    @api.private
    def filtered(self, func: str | Callable[[Self], bool] | Domain) -> Self:
        if not func:
            return self
        if not self:
            return self
        narrow = self._narrow
        if callable(func):
            pass
        elif isinstance(func, str):
            if "." in func:
                return narrow(
                    rec_id
                    for rec_id, rec in zip(self._ids, self, strict=True)
                    if any(rec.mapped(func))
                )
            if func == "id":
                return narrow(id_ for id_ in self._ids if id_)
            field = self._fields[func]
            if not can_scan_truthy(field):
                _debug.logic(
                    "traversal.filtered.unscannable_field",
                    model=self._name,
                    field=func,
                    records=len(self),
                )
                _field_get = field.__get__
                return narrow(rec._ids[0] for rec in self if _field_get(rec))
            field.check_read_access(self)
            field.recompute_pending(self)
            field_cache = field._get_cache(self.env)
            passing_ids, miss_indices = _batch_cache_filter(
                as_scannable_cache(field_cache), self._ids, PENDING
            )
            if miss_indices:
                _field_get = field.__get__
                rec_list = list(self)
                for idx in miss_indices:
                    if _field_get(rec_list[idx]):
                        passing_ids.append(rec_list[idx]._ids[0])
                if is_cache_detached(field, self.env, field_cache):
                    _debug.logic(
                        "traversal.filtered.cache_detached",
                        model=self._name,
                        field=func,
                        records=len(self),
                        misses=len(miss_indices),
                    )
                    return narrow(rec._ids[0] for rec in rec_list if _field_get(rec))
                all_passing = set(passing_ids)
                passing_ids = [id_ for id_ in self._ids if id_ in all_passing]
            return narrow(passing_ids)
        elif isinstance(func, Domain):
            return self.filtered_domain(func)
        else:
            raise TypeError(f"Invalid function {func!r} to filter on {self._name}")
        predicate = typing.cast("Callable[[typing.Any], bool]", func)
        return narrow(
            rec_id
            for rec_id, rec in zip(self._ids, self, strict=True)
            if predicate(rec)
        )

    @typing.overload
    def grouped(self, key: str) -> dict[typing.Any, Self]: ...

    @typing.overload
    def grouped(self, key: Callable[[Self], T]) -> dict[T, Self]: ...

    @api.private
    def grouped(self, key: str | Callable) -> dict:
        if not self:
            return {}

        if isinstance(key, str):
            field = self._fields[key]
            if not field.relational:
                field.check_read_access(self)
                field.recompute_pending(self)
                field_cache = field._get_cache(self.env)
                _SENTINEL = SENTINEL
                _PENDING = PENDING
                _get = field_cache.get
                _field_get = field.__get__
                collator: dict[typing.Any, list] = defaultdict(list)
                if can_scan_identity(field):
                    _none_val: typing.Any = field.convert_to_record(None, self[:1])
                    ids = self._ids
                    results, miss_indices = _batch_cache_get(
                        as_scannable_cache(field_cache), ids, PENDING, _none_val
                    )
                    if not miss_indices:
                        collator = _batch_group_ids(ids, results)
                    else:
                        miss_set = set(miss_indices)
                        rec_list = list(self)
                        collator = {}
                        for i, rec_id in enumerate(ids):
                            group_key = (
                                _field_get(rec_list[i]) if i in miss_set else results[i]
                            )
                            group = collator.get(group_key)
                            if group is None:
                                collator[group_key] = [rec_id]
                            else:
                                group.append(rec_id)
                        if is_cache_detached(field, self.env, field_cache):
                            _debug.logic(
                                "traversal.grouped.cache_detached", model=self._name
                            )
                            collator = defaultdict(list)
                            for record in rec_list:
                                collator[_field_get(record)].append(record._ids[0])
                else:
                    _convert = field.convert_to_record
                    _detached = False
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
                            _detached = _detached or is_cache_detached(
                                field, self.env, field_cache
                            )
                        collator[group_key].append(rec_id)
                    if _detached:
                        _debug.logic(
                            "traversal.grouped.cache_detached", model=self._name
                        )
                        collator = defaultdict(list)
                        for record in self:
                            collator[_field_get(record)].append(record._ids[0])
            else:
                key = itemgetter(key)
                collator = defaultdict(list)
                for record in self:
                    collator[key(record)].append(record._ids[0])
        else:
            collator = defaultdict(list)
            for record in self:
                collator[key(record)].append(record._ids[0])

        env = self.env
        prefetch_ids = self._prefetch_ids
        return {
            key: self._spawn(env, tuple(ids), prefetch_ids)
            for key, ids in collator.items()
        }

    @api.private
    def filtered_domain(self, domain: DomainType) -> Self:
        if not self or not domain:
            return self
        records = typing.cast("BaseModel", self)
        predicate = Domain(domain)._as_predicate(records)
        return self._narrow(
            rec_id
            for rec_id, rec in zip(self._ids, records, strict=True)
            if predicate(rec)
        )

    @api.private
    def sorted(
        self,
        key: str | Callable[[Self], typing.Any] | None = None,
        reverse: bool = False,
    ) -> Self:
        if len(self) < 2:
            return self
        if key is None or isinstance(key, str):
            order = self._order if key is None else key
            self._sorted_load_fields(order)
            ids = self._sorted_by_ids(order, reverse)
            if ids is not None:
                return self._spawn(self.env, ids, self._prefetch_ids)
            _debug.logic(
                "traversal.sorted.slow_path",
                model=self._name,
                order=order,
                records=len(self),
            )
            key = self._sorted_order_to_function(order, _checked=True)
        ids = tuple(
            item._ids[0]
            for item in sorted(
                typing.cast("list[Self]", list(self)), key=key, reverse=reverse
            )
        )
        return self._spawn(self.env, ids, self._prefetch_ids)

    def _sorted_load_fields(self, order: str) -> None:
        _fields = self._fields
        for part in order.split(","):
            match = regex_order.match(part)
            if match:
                field = _fields.get(match["field"])
                if field is not None:
                    field.check_read_access(self)
                    field.recompute_pending(self)

    def _sorted_by_ids(self, order: str, reverse: bool) -> tuple | None:
        _PENDING = PENDING
        _fields = self._fields
        env = self.env

        sort_specs = []
        for part in order.split(","):
            match = regex_order.match(part)
            if not match:
                return None
            field_name = match["field"]
            if match["property"]:
                return None
            field = _fields.get(field_name)
            if field is None or not can_scan_sorted(field):
                return None
            if field.is_many2one and env[field.comodel_name]._order != "id":
                return None
            desc = (match["direction"] or "").upper() == "DESC"
            nulls_raw = (match["nulls"] or "").upper()
            nulls_first = (nulls_raw == "NULLS FIRST") if nulls_raw else desc
            cache = None if field_name == "id" else field._get_cache(env)
            sort_specs.append((cache, desc, nulls_first))

        ids = self._ids
        for field_cache, desc, nulls_first in reversed(sort_specs):
            reverse_param = desc != reverse
            if field_cache is None:
                ids = tuple(sorted(ids, reverse=reverse_param))
                continue
            sorted_ids = _sort_ids_by_cache(
                as_scannable_cache(field_cache),
                ids,
                _PENDING,
                reverse_param,
                nulls_first == desc,
            )
            if sorted_ids is None:
                return None
            ids = sorted_ids
        return ids

    @api.model
    def _sorted_order_to_function(
        self, order: str, _checked: bool = False
    ) -> Callable[[Self], typing.Any]:
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
            if field.is_many2one and (not property_name or property_name == "id"):
                seen = _env.context.get("__m2o_order_seen_sorted", ())
                if field in seen:
                    _debug.logic(
                        "traversal.sorted.m2o_order_cycle",
                        model=self._name,
                        field=field_name,
                        depth=len(seen),
                    )
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
            elif field.is_boolean:
                getter = field.get_expression_getter(field_expr)
            elif not property_name and not has_lang_dict_cache(field, _env):
                _get_cache = field._get_cache
                _field_get = field.__get__
                _S = SENTINEL
                _P = PENDING

                def getter(rec):
                    if not _checked:
                        field.check_read_access(rec)
                        field.recompute_pending(rec)
                    value = _get_cache(_env).get(rec._ids[0], _S)
                    if value is _S or value is _P:
                        record_value = _field_get(rec)
                        value = _get_cache(_env).get(rec._ids[0], _S)
                        if value is _S:
                            return record_value
                    return value if value is not False else None

            else:
                raw_getter = field.get_expression_getter(field_expr)

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
    def update(self, values: dict[str, typing.Any]) -> None:
        record = typing.cast("BaseModel", self)
        for name, value in values.items():
            record[name] = value

    def _get_ancestor_ids(self, include_self: bool = False) -> OrderedSet[int]:
        result: OrderedSet[int] = OrderedSet()
        unresolved: list[BaseModel] = []
        has_path = "parent_path" in self._fields
        for record in self:
            rec = typing.cast("BaseModel", record)
            path = rec["parent_path"] if has_path else None
            if path:
                ids = [int(label) for label in path.split("/") if label]
                result.update(ids if include_self else ids[:-1])
            else:
                unresolved.append(rec)
        for rec in unresolved:
            result.update(rec._get_ancestor_ids_by_walking(include_self))
        if _debug.logic.enabled and unresolved:
            _debug.logic(
                "traversal.ancestors_walked",
                model=self._name,
                records=len(self),
                walked=len(unresolved),
                has_parent_path=has_path,
                ancestors=len(result),
            )
        return result

    def _get_ancestor_ids_by_walking(self, include_self: bool) -> list[int]:
        parent_name = self._parent_name
        chain: list[int] = []
        seen: set = set()
        current = self if include_self else self[parent_name]
        while current and current._ids[0] not in seen:
            seen.add(current._ids[0])
            if isinstance(current.id, int):
                chain.append(current.id)
            current = current[parent_name]
        chain.reverse()
        return chain

    def _get_root(self) -> Self:
        self.check_singleton()
        for root_id in self._get_ancestor_ids(include_self=True):
            return self.browse(root_id)
        return self

    def _get_descendant_ids(self, include_self: bool = False) -> OrderedSet[int]:
        if not self.ids:
            return OrderedSet()
        found = OrderedSet(
            self.with_context(active_test=False)
            ._search(Domain("id", "child_of", list(self.ids)))
            .get_result_ids()
        )
        if not include_self:
            found -= OrderedSet(self.ids)
        _debug.perf.count(
            "traversal.descendants",
            model=self._name,
            records=len(self.ids),
            found=len(found),
            include_self=include_self,
        )
        return found

    def _is_descendant_of(self, other: BaseModel, strict: bool = False) -> bool:
        self.check_singleton()
        if not other:
            return False
        other.check_singleton()
        if self == other:
            return not strict
        return other.id in self._get_ancestor_ids()

    def _is_relation_on_self(self, field) -> bool:
        if field.comodel_name == self._name:
            return True
        root = self._table_inheritance_root
        return bool(root) and self.env.registry[field.comodel_name]._table == root

    def _get_hierarchy_table(self, field_name: str) -> str:
        root = self._table_inheritance_root
        if not root or root == self._table:
            return self._table
        root_model = next(
            (
                name
                for name in self.env.registry.model_names_by_inheritance_root.get(
                    root, ()
                )
                if self.env.registry[name]._table == root
            ),
            None,
        )
        if root_model and field_name in self.env.registry[root_model]._fields:
            _debug.logic(
                "traversal.hierarchy.reads_root_table",
                model=self._name,
                table=root,
                field=field_name,
            )
            return root
        return self._table

    def _has_cycle(self, field_name: str | None = None) -> bool:
        if not field_name:
            field_name = self._parent_name

        field = self._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field_name: {field_name!r}")

        if not (
            (field.is_many2many or field.is_many2one)
            and self._is_relation_on_self(field)
            and field.store
        ):
            raise ValueError(
                f"Field must be a many2one or many2many relation on itself: {field_name!r}"
            )

        if not self.ids:
            return False

        self.flush_model([field_name])
        if field.is_many2many:
            relation, column1, column2 = field._get_relation_triple()
        else:
            relation, column1, column2 = (
                self._get_hierarchy_table(field_name),
                "id",
                field_name,
            )
        cyclic = self.env.backend.has_cycle(self, relation, column1, column2, self.ids)
        _debug.perf.count(
            "traversal.cycle_checked",
            model=self._name,
            field=field_name,
            records=len(self.ids),
            many2many=field.is_many2many,
            cyclic=cyclic,
        )
        return cyclic
