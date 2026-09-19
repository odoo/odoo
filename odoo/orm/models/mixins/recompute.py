import itertools
import logging
import re
import typing
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from itertools import batched
from typing import Self

from odoo.exceptions import MissingError
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import OrderedSet
from odoo.tools.misc import PENDING

from ... import decorators as api
from ...components.recompute import RecomputeScheduler
from ...domain import Domain, ids_selected_without_query
from ...helpers import get_fields_by_name, get_or_create_class_memo
from ...primitives import NewId
from ..table_objects import Constraint
from ._model_stubs import _ModelStubs

_orm_cache = logging.getLogger("odoo.orm.cache")
_orm_compute = logging.getLogger("odoo.orm.compute")
_debug = DebugLog(__name__)

_SQL_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

if typing.TYPE_CHECKING:
    from ..._typing import IdType
    from ...fields.base import Field
    from ...runtime import TriggerTree


def _fires_constraints(env, field) -> bool:
    if field.store or not field.related:
        return False
    return field.name in env[field.model_name]._constrained_projection_names


class RecomputeMixin(_ModelStubs):
    __slots__ = ()

    @api.private
    def modified(
        self,
        fnames: Collection[str],
        create: bool = False,
        before: bool = False,
    ) -> None:
        if not self or not fnames:
            return

        self._invalidate_inheritance_tree(fnames)

        core = self.env.core

        if before:
            scheduler = core.new_scheduler()
            self._modified_trigger_loop(fnames, False, scheduler)

            _debug.pipeline(
                "recompute.modified_before",
                model=self._name,
                records=len(self),
                fields_to_recompute=len(scheduler.to_recompute),
            )
            for field, ids in scheduler.to_recompute.items():
                records = self.env[field.model_name].browse(ids)
                self.env.add_to_compute(field, records)
        else:
            scheduler = core.new_scheduler(inline=True)
            _debug.pipeline(
                "recompute.modified",
                model=self._name,
                records=len(self),
                fields=len(fnames),
                create=create,
            )
            to_validate: dict = {}
            self._modified_trigger_loop(fnames, create, scheduler, to_validate)
            # a record being created is not whole yet: `_create` checks it in its
            # own pass, once its other fields are in
            being_created = set(self._ids) if create else ()
            for field, ids in to_validate.items():
                records = (
                    self.env[field.model_name]
                    .browse(
                        id_
                        for id_ in ids
                        if field.model_name != self._name or id_ not in being_created
                    )
                    .exists()
                )
                _debug.pipeline(
                    "recompute.projection_constraints",
                    model=field.model_name,
                    field=field.name,
                    records=len(records),
                )
                records._check_fields([field.name])

    def _invalidate_inheritance_tree(self, fnames: Collection[str]) -> None:
        tree = self.env._table_inheritance_tree(self._name) or (
            self._siblings_of_inheritance_subtype()
        )
        if not tree:
            return
        _debug.pipeline(
            "recompute.invalidate_inheritance_tree",
            model=self._name,
            siblings=len(tree),
            records=len(self),
            fields=len(fnames),
        )
        for model_name in tree:
            other = self.env[model_name]
            names = [name for name in fnames if name in other._fields]
            if names:
                other.browse(self._ids).invalidate_recordset(names)

    def _siblings_of_inheritance_subtype(self) -> tuple[str, ...]:
        root = self._table_inheritance_root
        if not root or root == self._table:
            return ()
        return tuple(
            name
            for name in self.env.registry.model_names_by_inheritance_root.get(root, ())
            if name != self._name
        )

    def _modified_before(self, fnames: Collection[str]) -> None:
        return self.modified(fnames, before=True)

    def _modified_traverse(
        self,
        todo: list,
        scheduler,
        debug: bool,
        to_validate: dict | None = None,
    ) -> tuple[int, int]:
        _mark_count = 0
        _invalidate_count = 0
        env = self.env
        for field, records, entry_create in itertools.chain.from_iterable(todo):
            if to_validate is not None and _fires_constraints(env, field):
                to_validate.setdefault(field, OrderedSet()).update(
                    id_ for id_ in records._ids if id_
                )
            cached_ids = None
            if field.recursive and not field.is_stored_computed:
                cached_ids = field._get_all_cache_ids(env).keys()

            recursive_ids = scheduler.schedule_recompute(
                field,
                OrderedSet(records._ids),
                cached_ids=cached_ids,
            )

            if scheduler.to_invalidate:
                for inv_field, inv_ids in scheduler.to_invalidate:
                    inv_field._invalidate_cache(env, inv_ids)
                scheduler.to_invalidate.clear()

            if recursive_ids:
                todo.append(
                    records.browse(recursive_ids)._modified([field], entry_create)
                )

            if debug:
                n = len(recursive_ids) if recursive_ids else len(records)
                if field.is_stored_computed:
                    _mark_count += n
                else:
                    _invalidate_count += n
        return _mark_count, _invalidate_count

    def _modified_trigger_loop(
        self,
        fnames: Collection[str],
        create: bool,
        scheduler: RecomputeScheduler,
        to_validate: dict | None = None,
    ) -> None:
        prof = _OrmProfile(_orm_compute)
        _fnames_list: typing.Any = ()
        _mark_count = 0
        _invalidate_count = 0
        if prof.debug:
            _fnames_list = (
                list(fnames) if not isinstance(fnames, (list, dict)) else fnames
            )

        _field_triggers = self.pool._get_field_triggers()
        _fields = self._fields
        fields = [_fields[fname] for fname in fnames]
        if not any(f in _field_triggers for f in fields):
            _debug.logic(
                "recompute.no_triggers",
                model=self._name,
                records=len(self),
                fields=len(fields),
                create=create,
            )
            prof.stop()
            prof.report(
                _orm_compute,
                "modified %s: %d fields on %d records (create=%s, no triggers)",
                self._name,
                len(_fnames_list),
                len(self),
                create,
            )
            if prof.agg and self.env.transaction.observers:
                self.env.transaction.observe_timing(
                    "modified", self._name, len(self), prof.elapsed
                )
            return

        todo = [self._modified(fields, create)]
        prof.mark("tree")

        _mark_count, _invalidate_count = self._modified_traverse(
            todo, scheduler, prof.debug, to_validate
        )

        _debug.pipeline(
            "recompute.triggers_traversed",
            model=self._name,
            records=len(self),
            fields=len(fields),
            create=create,
            chains=len(todo),
            to_recompute=len(scheduler.to_recompute),
        )
        prof.stop("traverse")
        prof.report(
            _orm_compute,
            "modified %s: %d fields on %d records (create=%s, marked=%d, invalidated=%d)",
            self._name,
            len(_fnames_list),
            len(self),
            create,
            _mark_count,
            _invalidate_count,
        )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "modified", self._name, len(self), prof.elapsed
            )

    def _modified(
        self, fields: list[Field], create: bool
    ) -> Iterable[tuple[Field, Self, bool]]:

        env = self.env
        core = env.core

        def select(field):
            if field.is_stored_computed or _fires_constraints(env, field):
                return True
            if field._is_context_dependent(env):
                return core.has_any_context_cached(field)
            return core.has_any_cached(field)

        tree = self.pool.get_trigger_tree(fields, select=select)
        if not tree:
            return ()

        if len(tree):
            records = self.with_env(env._derive(su=True, active_test=False))
        else:
            records = self
        return records._modified_triggers(tree, create)

    def _modified_triggers(
        self, tree: TriggerTree, create: bool = False
    ) -> Iterable[tuple[Field, Self, bool]]:
        if not self:
            return

        for field in tree.root:
            yield field, self, create

        for field, subtree in tree.items():
            if create and (field.is_many2one or field.is_many2one_reference):
                continue

            model = self.env[field.model_name]
            if self._invalidates_from_cache(field, subtree):
                yield from self._modified_cache_only(field, subtree)
                continue
            for invf in model.pool.field_inverses[field]:
                if not (invf.is_x2many and invf.domain):
                    if invf.is_many2one_reference:
                        rec_ids: OrderedSet[int] = OrderedSet()
                        for rec in self:
                            try:
                                if rec[invf.model_field] == field.model_name:
                                    rec_ids.add(rec[invf.name])
                            except MissingError:
                                continue
                        records = model.browse(rec_ids)
                    else:
                        try:
                            records = self[invf.name]
                        except MissingError:
                            _debug.logic(
                                "recompute.inverse_missing_records",
                                model=self._name,
                                field=invf.name,
                                records=len(self),
                            )
                            records = self.exists()[invf.name]

                    if field.model_name == records._name:
                        if not any(self._ids):
                            records = records.browse(
                                it and NewId(it) for it in records._ids
                            )
                        break
            else:
                self_ids = self._ids
                real_ids = [id_ for id_ in self_ids if id_]
                records = model.browse()
                _debug.logic(
                    "recompute.trigger_search_fallback",
                    model=self._name,
                    via=f"{field.model_name}.{field.name}",
                    records=len(real_ids),
                )
                if real_ids:
                    domain = Domain(field.name, "in", real_ids).optimize_full(model)
                    ids = ids_selected_without_query(domain)
                    if ids is None:
                        records = model.search(domain, order="id")
                    else:
                        records = model.browse(sorted(ids))
                if len(real_ids) != len(self_ids):
                    field_cache = field._get_cache(model.env)
                    cache_records = model.browse(field_cache)
                    new_ids = set(self_ids)
                    records |= cache_records.filtered(
                        lambda r, field=field, new_ids=new_ids: (
                            not set(r[field.name]._ids).isdisjoint(new_ids)
                        )
                    )

            yield from records._modified_triggers(subtree)

    def _invalidates_from_cache(self, field: Field, subtree: TriggerTree) -> bool:
        if len(subtree) or field.is_many2one_reference:
            return False
        if any(
            f.is_stored_computed or f.recursive or _fires_constraints(self.env, f)
            for f in subtree.root
        ):
            return False
        inverses = self.env[field.model_name].pool.field_inverses[field]
        return any(invf.is_x2many and not invf.domain for invf in inverses)

    def _modified_cache_only(
        self, field: Field, subtree: TriggerTree
    ) -> Iterable[tuple[Field, Self, bool]]:
        env = self.env
        model = env[field.model_name]
        self_ids = set(self._ids)
        back = field._get_cache(env)
        if field.is_many2one:

            def points_back(value: typing.Any) -> bool:
                return value in self_ids
        else:
            # a paired x2many caches a tuple of ids, never a bare id
            def points_back(value: typing.Any) -> bool:
                return not self_ids.isdisjoint(value)

        for dependent in subtree.root:
            ids = [
                id_
                for id_ in dependent._get_all_cache_ids(env)
                if id_ not in back or points_back(back[id_])
            ]
            _debug.logic(
                "recompute.invalidated_from_cache",
                model=self._name,
                via=f"{field.model_name}.{field.name}",
                field=dependent.name,
                records=len(ids),
            )
            if ids:
                yield dependent, model.browse(ids), False

    @classmethod
    def _get_stored_computed_fields(cls) -> tuple[Field, ...]:
        return get_or_create_class_memo(
            cls,
            "_stored_computed_fields__",
            lambda: tuple(f for f in cls._fields.values() if f.is_stored_computed),
        )

    @classmethod
    def _get_check_coupled_fields(cls) -> dict[Field, tuple[Field, ...]]:
        def get_check_coupled_fields_uncached() -> dict[Field, tuple[Field, ...]]:
            columns = {
                name: field
                for name, field in cls._fields.items()
                if field.store and field.column_type
            }
            coupled: dict[Field, set[Field]] = defaultdict(set)
            for table_object in cls._table_objects.values():
                if not isinstance(table_object, Constraint):
                    continue
                definition = table_object.get_definition(cls.pool)
                if not definition.lstrip().upper().startswith("CHECK"):
                    continue
                group = {
                    columns[token]
                    for token in _SQL_IDENTIFIER.findall(definition)
                    if token in columns
                }
                for field in group:
                    coupled[field].update(
                        other
                        for other in group
                        if other is not field and other.is_stored_computed
                    )
            return {field: tuple(others) for field, others in coupled.items() if others}

        return get_or_create_class_memo(
            cls, "_check_coupled_fields__", get_check_coupled_fields_uncached
        )

    def _recompute_check_coupled_fields(self) -> None:
        coupled = self._get_check_coupled_fields()
        core = self.env.core
        if not coupled or not core.has_pending():
            return
        for _pass in range(len(coupled) + 1):
            progressed = False
            for field, partners in coupled.items():
                dirty = core.get_dirty(field)
                if not dirty:
                    continue
                for partner in partners:
                    pending = core.get_pending_ids(partner)
                    if ids := [id_ for id_ in dirty if id_ in pending]:
                        _debug.logic(
                            "recompute.flush_check_coupled",
                            model=self._name,
                            dirty=field.name,
                            recomputed=partner.name,
                            records=len(ids),
                        )
                        self._recompute_field(partner, ids)
                        progressed = True
            if not progressed:
                return

    def _recompute_model(self, fnames: Collection[str] | None = None) -> None:
        self._recompute_fields(self._resolve_recompute_fields(fnames), None)

    def _recompute_recordset(self, fnames: Collection[str] | None = None) -> None:
        self._recompute_fields(self._resolve_recompute_fields(fnames), self._ids)

    def _resolve_recompute_fields(
        self, fnames: Collection[str] | None
    ) -> Collection[Field]:
        if fnames is None:
            return self._get_stored_computed_fields()
        return get_fields_by_name(self, fnames)

    def _recompute_fields(
        self, fields: Collection[Field], ids: Sequence[IdType] | None
    ) -> None:
        if not self.env.core.has_pending():
            return
        for field in fields:
            if field.is_stored_computed:
                self._recompute_field(field, ids)

    def _recompute_field(
        self, field: Field, ids: Sequence[IdType] | None = None
    ) -> None:
        ids_to_compute = self.env.core.get_pending_ids(field)
        scoped = ids is not None  # debuglog
        if ids is None:
            ids = ids_to_compute
        else:
            ids = [id_ for id_ in ids if id_ in ids_to_compute]
        if not ids:
            return

        prof = _OrmProfile(_orm_compute)

        records = self.browse(tuple(id_ for id_ in ids if id_))
        _debug.pipeline(
            "recompute.field",
            model=field.model_name,
            field=field.name,
            records=len(records),
            pending=len(ids_to_compute),
            scoped=scoped,
        )
        field.recompute(records)

        prof.stop()
        prof.report(
            _orm_compute,
            "recompute_field %s.%s: %d records",
            field.model_name,
            field.name,
            len(records),
        )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "recompute", field.model_name, len(records), prof.elapsed
            )

    @api.private
    def flush_model(self, fnames: Collection[str] | None = None) -> None:
        self._flush_model_own(fnames)
        if self._table_inheritance_root:
            self._flush_table_inheritance_siblings(fnames)

    def _flush_model_own(self, fnames: Collection[str] | None) -> None:
        fields = self._resolve_recompute_fields(fnames)
        core = self.env.core
        if fnames is not None and not core.has_pending() and not core.is_any_dirty():
            return

        prof = _OrmProfile(_orm_cache)

        self._recompute_fields(fields, None)
        prof.mark("recompute")
        if fnames is None or any(map(core.has_dirty_field, fields)):
            _debug.pipeline(
                "recompute.flush_model",
                model=self._name,
                fields=None if fnames is None else len(fields),
            )
            self._flush()

        prof.stop("flush")
        prof.report(_orm_cache, "flush_model %s", self._name)

    def _flush_table_inheritance_siblings(self, fnames: Collection[str] | None) -> None:
        for name in self.env._table_inheritance_tree(self._name):
            sibling = self.env[name]
            if fnames is None:
                sibling._flush_model_own(None)
                continue
            shared = [fname for fname in fnames if fname in sibling._fields]
            if shared:
                sibling._flush_model_own(shared)

    @api.private
    def flush_recordset(self, fnames: Collection[str] | None = None) -> None:
        named_fields = None if fnames is None else get_fields_by_name(self, fnames)
        if not self:
            return
        core = self.env.core
        if (
            named_fields is not None
            and not core.has_pending()
            and not core.is_any_dirty()
        ):
            return
        self._recompute_fields(
            self._get_stored_computed_fields()
            if named_fields is None
            else named_fields,
            self._ids,
        )
        fields: Collection[Field] = (
            self._fields.values() if named_fields is None else named_fields
        )
        ids = self._ids
        if len(ids) == 1:
            id_ = ids[0]
            dirty = any(id_ in (core.get_dirty(field) or ()) for field in fields)
        else:
            id_set = set(ids)
            dirty = not all(
                id_set.isdisjoint(core.get_dirty(field) or ()) for field in fields
            )
        if dirty:
            _debug.pipeline(
                "recompute.flush_recordset",
                model=self._name,
                records=len(ids),
                fields=None if named_fields is None else len(named_fields),
            )
            self._flush()

    def _flush(self) -> None:
        core = self.env.core
        self._recompute_check_coupled_fields()
        dirty_field_ids = core.pop_dirty_for_model(self._name)
        if not dirty_field_ids:
            return

        prof = _OrmProfile(_orm_cache)

        model = self
        env = self.env
        cls = type(model)

        id_to_fields: dict[int, list] = defaultdict(list)
        for field, ids in dirty_field_ids.items():
            for id_ in ids:
                id_to_fields[id_].append(field)

        dirty_ids = list(id_to_fields)
        prof.mark("collect")

        _debug.pipeline(
            "recompute.flush",
            model=self._name,
            fields=len(dirty_field_ids),
            records=len(dirty_ids),
        )
        _batch_count = 0
        BATCH_SIZE = 1000
        with env.cr.pipeline():
            for some_ids in batched(dirty_ids, BATCH_SIZE, strict=False):
                if prof.debug:
                    _batch_count += 1
                vals_list = []
                _new = object.__new__
                try:
                    for id_ in some_ids:
                        record = _new(cls)
                        record.env = env
                        record._ids = (id_,)
                        record._prefetch_ids = some_ids
                        vals = {}
                        for f in id_to_fields[id_]:
                            col_val = f.get_column_update(record)
                            if col_val is not PENDING:
                                vals[f.name] = col_val
                            elif core.is_pending(f, id_):
                                _debug.logic(
                                    "recompute.flush_deferred_pending",
                                    model=self._name,
                                    field=f.name,
                                    record=id_,
                                )
                                core.mark_dirty(f, (id_,))
                            else:
                                _debug.logic(
                                    "recompute.flush_pending_unscheduled",
                                    model=self._name,
                                    field=f.name,
                                    record=id_,
                                )
                                raise RuntimeError(
                                    f"Cannot flush {f}: the cached value is "
                                    f"PENDING on {self._name}({id_}) but the "
                                    f"field is not scheduled for recomputation, "
                                    f"so the value can never materialize"
                                )
                        vals_list.append(vals)
                except KeyError as e:
                    raise RuntimeError(
                        f"Could not find all values of {self._name}({id_}) to flush them\n"
                        f"    Context: {env.context}\n"
                        f"    Cache: {env.cache!r}"
                    ) from e
                model.browse(some_ids)._write_multi(vals_list)

        prof.stop("update")
        prof.report(
            _orm_cache,
            "_flush %s: %d fields, %d records, %d batches",
            self._name,
            len(dirty_field_ids),
            len(dirty_ids),
            _batch_count,
        )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "flush", self._name, len(dirty_ids), prof.elapsed
            )
