import typing
from collections import defaultdict
from itertools import batched, chain
from operator import attrgetter
from typing import Self

from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import OrderedSet, clean_context
from odoo.tools.cache import TransactionMemo
from odoo.tools.misc import PENDING

from ... import decorators as api
from ..._typing import ValuesType
from ...helpers import get_or_create_class_memo
from ...primitives import (
    INSERT_BATCH_SIZE,
    Command,
)
from ._crud_common import (
    _BAD_NAMES_LOG,
    _orm_crud,
    get_forbidden_field_names,
)
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from ..._typing import BaseModel
    from ...fields.base import Field
    from ...fields.relational._base import _RelationalMulti

_debug = DebugLog(__name__)


class CreateMixin(_ModelStubs):
    __slots__ = ()

    @api.model
    def default_get(self, fields: list[str]) -> ValuesType:
        env = self.env
        _fields = self._fields
        defaults = {}
        parent_fields = defaultdict(list)
        ir_defaults = env.registry.metaschema.model_defaults(env, self._name)
        context_defaults = env._context_defaults

        for name in fields:
            if name in context_defaults:
                defaults[name] = context_defaults[name]
                continue

            field = _fields.get(name)
            if not field:
                continue

            if not (field.default or field.inherited or name in ir_defaults):
                continue

            if not field.company_dependent and name in ir_defaults:
                defaults[name] = ir_defaults[name]
                continue

            if field.default:
                defaults[name] = field.default(self)
                continue

            if field.company_dependent and name in ir_defaults:
                defaults[name] = ir_defaults[name]
                continue

            if (
                field.inherited
                and self._has_field_access(field, "write")
                and field.related_field is not None
            ):
                field = field.related_field
                parent_fields[field.model_name].append(field.name)

        for fname, value in defaults.items():
            field = _fields.get(fname)
            if field is not None:
                value = field.convert_to_cache(value, self, validate=False)
                defaults[fname] = field.convert_to_write(value, self)

        for model, names in parent_fields.items():
            defaults.update(env[model].default_get(names))

        _debug.logic(
            "create.default_get",
            model=self._name,
            requested=len(fields),
            resolved=len(defaults),
            from_context=sum(1 for name in fields if name in context_defaults),
            from_ir_default=sum(1 for name in fields if name in ir_defaults),
            parent_models=len(parent_fields),
        )
        return defaults

    @api.model
    def _add_missing_default_values(
        self,
        values: ValuesType,
        _missing_defaults_cache: dict[frozenset[str], list[str]] | None = None,
    ) -> ValuesType:
        vals_keys = frozenset(values)
        if _missing_defaults_cache is not None and vals_keys in _missing_defaults_cache:
            missing_defaults = _missing_defaults_cache[vals_keys]
        else:
            avoid_models = set()

            def collect_models_to_avoid(model):
                for parent_mname, parent_fname in model._inherits.items():
                    if parent_fname in values:
                        avoid_models.add(parent_mname)
                    else:
                        collect_models_to_avoid(self.env[parent_mname])

            collect_models_to_avoid(self)

            def avoid(field):
                if avoid_models:
                    while field.inherited:
                        field = field.related_field
                        if field.model_name in avoid_models:
                            return True
                return False

            missing_defaults = [
                name
                for name, field in self._fields.items()
                if name not in values
                if not avoid(field)
            ]
            _debug.logic(
                "create.missing_defaults_computed",
                model=self._name,
                given=len(values),
                missing=len(missing_defaults),
                avoided_parents=len(avoid_models),
                cached=_missing_defaults_cache is not None,
            )
            if _missing_defaults_cache is not None:
                _missing_defaults_cache[vals_keys] = missing_defaults

        if missing_defaults:
            defaults = self.default_get(missing_defaults)
            _fields = self._fields
            for name, value in defaults.items():
                field_type = _fields[name].type
                if not value:
                    continue
                if field_type == "many2many":
                    if isinstance(value[0], int):
                        defaults[name] = [Command.set(value)]
                elif field_type == "one2many" and isinstance(value[0], dict):
                    defaults[name] = [Command.create(x) for x in value]
            defaults.update(values)

        else:
            defaults = dict(values)

        cls = type(self)
        properties_names = get_or_create_class_memo(
            cls,
            "_properties_field_names__",
            lambda: tuple(
                fname for fname, field in self._fields.items() if field.is_properties
            ),
        )
        for name in properties_names:
            defaults[name] = self._fields[name]._add_default_values(self.env, defaults)

        return defaults

    def _create_check_field_access(
        self, vals_list: list[ValuesType]
    ) -> OrderedSet[str]:
        field_names = OrderedSet(fname for vals in vals_list for fname in vals)
        field_names.update(
            field_name
            for context_key in self.env.context
            if context_key.startswith("default_")
            and (field_name := context_key.removeprefix("default_"))
            and field_name in self._fields
        )
        self._check_fields_write_access(field_names)
        _debug.pipeline(
            "create.field_access_checked",
            model=self._name,
            records=len(vals_list),
            fields=len(field_names),
        )
        return field_names

    def _create_partition_values(
        self, new_vals_list: list[ValuesType]
    ) -> tuple[list[dict], dict]:
        data_list = []
        inverses_by_hook: defaultdict[typing.Any, OrderedSet] = defaultdict(OrderedSet)
        bypass_access_ids: defaultdict[Field, OrderedSet] = defaultdict(OrderedSet)

        for vals in new_vals_list:
            precomputed = vals.pop("__precomputed__", ())

            data: dict[str, typing.Any] = {}
            data["stored"] = stored = {}
            data["inversed"] = inversed = {}
            data["cached_only"] = cached_only = {}
            inherited: defaultdict[str, dict] = defaultdict(dict)
            data["inherited"] = inherited
            data["protected"] = protected = set()
            for key, val in vals.items():
                field = self._fields.get(key)
                if not field:
                    raise ValueError(f"Invalid field {key!r} on model {self._name!r}")
                if field.store:
                    stored[key] = val
                if field.inherited and field.related_field is not None:
                    inherited[field.related_field.model_name][key] = val
                elif field.inverse and field not in precomputed:
                    inversed[key] = val
                    inverses_by_hook[field.inverse].add(field)
                elif not field.store and not field.compute:
                    cached_only[key] = val
                if (
                    field.compute and (not field.readonly or field.precompute)
                ) or key in cached_only:
                    protected.update(self.pool.field_computed.get(field, [field]))
                if field.is_many2one and field.bypass_search_access and not self.env.su:
                    if co_id := field.convert_to_cache(val, self):
                        bypass_access_ids[field].add(co_id)

            data_list.append(data)

        _debug.pipeline(
            "create.partitioned",
            model=self._name,
            records=len(data_list),
            inverse_hooks=len(inverses_by_hook),
            bypass_access_fields=len(bypass_access_ids),
        )
        for field, co_ids in bypass_access_ids.items():
            self.env[field.comodel_name].browse(co_ids).check_access("read")
        return data_list, inverses_by_hook

    def _create_parent_records(self, data_list: list[dict]) -> None:
        for model_name, parent_name in self._inherits.items():
            parent_data_list = []
            for data in data_list:
                if not data["stored"].get(parent_name):
                    parent_data_list.append(data)
                elif data["inherited"][model_name]:
                    parent = self.env[model_name].browse(data["stored"][parent_name])
                    parent.write(data["inherited"][model_name])

            if parent_data_list:
                _debug.pipeline(
                    "create.parent_records",
                    model=self._name,
                    parent=model_name,
                    records=len(parent_data_list),
                )
                parents = self.env[model_name].create(
                    [data["inherited"][model_name] for data in parent_data_list]
                )
                for parent, data in zip(parents, parent_data_list, strict=True):
                    data["stored"][parent_name] = parent.id

    def _create_apply_inverses(self, data_list: list[dict], inverses_by_hook) -> None:
        protected_fields = [(data["protected"], data["record"]) for data in data_list]
        with self.env.protecting(protected_fields):
            for data in data_list:
                if vals := data["cached_only"]:
                    data["record"]._update_cache(vals)
            for fields in inverses_by_hook.values():
                inv_names = {field.name for field in fields}
                inv_rec_ids = []
                for data in data_list:
                    if inv_names.isdisjoint(data["inversed"]):
                        continue
                    record = data["record"]
                    record._update_cache(
                        {
                            fname: value
                            for fname, value in data["inversed"].items()
                            if fname in inv_names and fname not in data["stored"]
                        }
                    )
                    inv_rec_ids.append(record.id)

                inv_records = self.browse(inv_rec_ids)
                _debug.pipeline(
                    "create.inverse_hook",
                    model=self._name,
                    field=next(iter(fields)).name,
                    fields=len(fields),
                    records=len(inv_rec_ids),
                )
                next(iter(fields)).apply_inverse(inv_records)
                inv_relational_fnames = [
                    field.name
                    for field in fields
                    if field.is_x2many and not field.store
                ]
                inv_records.invalidate_recordset(fnames=inv_relational_fnames)

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        if not isinstance(vals_list, (list, tuple)):
            raise TypeError(
                f"create() expects a list of dicts, got {type(vals_list).__name__}"
            )
        if not vals_list:
            return self.browse()

        TransactionMemo.discard_for_model(self.env, self._name)
        prof = _OrmProfile(_orm_crud)

        if self.env.transaction.observers:
            fnames = frozenset(fname for vals in vals_list for fname in vals)
            self.env.transaction.observe_operation(
                "create", self._name, len(vals_list), fnames
            )

        self = self.browse()
        self.check_access("create")

        field_names = self._create_check_field_access(vals_list)
        prof.mark("acl")

        new_vals_list = self._prepare_create_values(vals_list)
        data_list, inverses_by_hook = self._create_partition_values(new_vals_list)
        prof.mark("prep")

        self._create_parent_records(data_list)
        prof.mark("parent")

        records = self._create(data_list)
        prof.mark("sql")

        self._create_apply_inverses(data_list, inverses_by_hook)
        prof.mark("trigger")

        self._check_created(data_list)

        if self._check_company_auto:
            records._check_company()

        prof.stop("validate")
        prof.report(
            _orm_crud,
            "create %s: %d records, %d fields",
            self._name,
            len(records),
            len(field_names),
        )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "create", self._name, len(records), prof.elapsed
            )

        _debug.lifecycle(
            "create.records",
            model=self._name,
            records=len(records),
            fields=len(field_names),
            uid=self.env.uid,
            company_checked=self._check_company_auto,
        )
        self._create_update_xmlids(records, vals_list)
        return records

    def _check_created(self, data_list: list[dict]) -> None:
        # The second half of write's two passes: every constraint that reads a
        # field inverted in this batch runs once the inverses have written, on
        # every record of the batch, including one that constrains a stored field
        # as well and was therefore left out of the stored pass in _create.
        inversed_names = {name for data in data_list for name in data["inversed"]}
        if inversed_names:
            self.browse([data["record"].id for data in data_list])._check_fields(
                inversed_names
            )

    def _prepare_create_values(self, vals_list: list[ValuesType]) -> list[ValuesType]:
        bad_names = get_forbidden_field_names(self)

        cls = type(self)
        precompute_readonly = get_or_create_class_memo(
            cls,
            "_precompute_readonly_names__",
            lambda: frozenset(
                fname
                for fname, field in self._fields.items()
                if field.precompute and field.readonly
            ),
        )
        if precompute_readonly:
            bad_names |= precompute_readonly

        missing_defaults_cache: dict[frozenset[str], list[str]] = {}

        result_vals_list = []
        for vals in vals_list:
            vals = self._add_missing_default_values(vals, missing_defaults_cache)

            for fname in bad_names:
                vals.pop(fname, None)
            if self._log_access:
                vals.setdefault("create_uid", self.env.uid)
                vals.setdefault("create_date", self.env.cr.now())
                vals.setdefault("write_uid", self.env.uid)
                vals.setdefault("write_date", self.env.cr.now())

            result_vals_list.append(vals)

        _debug.pipeline(
            "create.values_prepared",
            model=self._name,
            records=len(result_vals_list),
            forbidden=len(bad_names),
            precompute_readonly=len(precompute_readonly),
            default_sets=len(missing_defaults_cache),
        )
        self._add_precomputed_values(result_vals_list)

        return result_vals_list

    def _add_precomputed_values(self, vals_list: list[ValuesType]) -> None:
        precomputable = {
            fname: field for fname, field in self._fields.items() if field.precompute
        }
        if not precomputable:
            return

        vals_list_todo = [
            vals
            for vals in vals_list
            if any(fname not in vals for fname in precomputable)
        ]
        if not vals_list_todo:
            return

        records = self.browse().concat(*(self.new(vals) for vals in vals_list_todo))
        _debug.pipeline(
            "create.precompute",
            model=self._name,
            records=len(vals_list_todo),
            fields=len(precomputable),
        )

        givens = [
            {
                fname: value
                for fname, value in vals.items()
                if (field := self._fields.get(fname)) is not None and field.compute
            }
            for vals in vals_list_todo
        ]

        with _debug.perf(
            "create.precompute_values",
            cr=self.env.cr,
            model=self._name,
            records=len(vals_list_todo),
            fields=len(precomputable),
        ):
            try:
                for vals in vals_list_todo:
                    vals["__precomputed__"] = set()

                for fname, field in precomputable.items():
                    todo = [
                        (record, vals, given)
                        for record, vals, given in zip(
                            records, vals_list_todo, givens, strict=True
                        )
                        if fname not in vals
                    ]
                    if not todo:
                        continue
                    for record, _vals, given in todo:
                        if given:
                            record._update_cache(given, validate=False)
                    reads_as_su = bool(field.groups) and field.compute_sudo
                    for record, vals, _given in todo:
                        source = record.sudo() if reads_as_su else record
                        vals[fname] = field.convert_to_write(source[fname], self)
                        vals["__precomputed__"].add(field)
            finally:
                self._discard_precompute_scratch(records)

    def _discard_precompute_scratch(self, records: Self) -> None:
        ids = records._ids
        if not ids:
            return
        env = self.env
        for field in self._fields.values():
            field._invalidate_cache(env, ids)

    @api.model
    def _create(self, data_list: list[ValuesType]) -> Self:
        if not data_list:
            raise ValueError("_create() called with empty data_list")
        prof = _OrmProfile(_orm_crud)

        ids: list[int] = []
        other_fields: OrderedSet[Field] = OrderedSet()
        batches = 0  # debuglog

        for data_sublist in batched(data_list, INSERT_BATCH_SIZE, strict=False):
            batches += 1  # debuglog
            stored_list = [data["stored"] for data in data_sublist]
            fnames = sorted({name for stored in stored_list for name in stored})

            columns: list[str] = []
            col_fields: list[Field] = []
            for fname in fnames:
                field = self._fields[fname]
                if field.column_type:
                    columns.append(fname)
                    col_fields.append(field)
                else:
                    other_fields.add(field)

                if field.is_properties:
                    other_fields.add(field)

            self._update_html_columns(stored_list, col_fields)
            ids.extend(
                self.env.backend.create_rows(self, stored_list, columns, col_fields)
            )

        _debug.pipeline(
            "create.rows_inserted",
            model=self._name,
            records=len(ids),
            batches=batches,
            other_fields=len(other_fields),
        )
        prof.mark("sql")

        records, inverses_update = self._update_create_cache(ids, data_list)
        prof.mark("cache")

        for field, updates in inverses_update.items():
            field._update_inverses(
                [
                    (self.browse(record_ids), value)
                    for value, record_ids in updates.items()
                ]
            )
        prof.mark("inverses")

        records._update_parent_path_on_create()

        protected = [(data["protected"], data["record"]) for data in data_list]
        with self.env.protecting(protected):
            records.modified(self._fields, create=True)

            if other_fields:
                others = records.with_context(clean_context(self.env.context))
                for field in sorted(other_fields, key=attrgetter("_sequence")):
                    field.create(
                        [
                            (
                                typing.cast("BaseModel", other),
                                data["stored"][field.name],
                            )
                            for other, data in zip(others, data_list, strict=True)
                            if field.name in data["stored"]
                        ]
                    )

                records.modified([field.name for field in other_fields], create=True)

        if self._constrained_projection_names:
            _debug.logic(
                "create.projection_constraints",
                model=self._name,
                records=len(records),
                fields=sorted(self._constrained_projection_names),
            )
        records._check_fields(
            chain(
                (name for data in data_list for name in data["stored"]),
                # a related field without a column is in no `stored` list, and a
                # new record has a value for it as soon as its path is written
                self._constrained_projection_names,
            ),
            {name for data in data_list for name in data["inversed"]},
        )
        records.check_access("create")

        prof.stop("trigger")
        prof.report(_orm_crud, "_create %s: %d records", self._name, len(records))
        return records

    def _update_html_columns(
        self, stored_list: list[dict], col_fields: list[Field]
    ) -> None:
        html_fields = [field for field in col_fields if field.is_html]
        for stored in stored_list:
            for field in html_fields:
                if field.name in stored:
                    stored[field.name] = field.convert_to_column(
                        stored[field.name], self, stored
                    )

    def _update_create_cache(
        self, ids: list[int], data_list: list[dict]
    ) -> tuple[Self, dict]:
        records = self.browse(ids)
        inverses_update: defaultdict[Field, defaultdict[typing.Any, list[int]]] = (
            defaultdict(lambda: defaultdict(list))
        )
        common_set_vals = _BAD_NAMES_LOG

        env = self.env
        _stored_x2m_fields: list[_RelationalMulti] = []
        _stored_scalar_caches = []
        for field in self._fields.values():
            if not field.store:
                continue
            if field.is_x2many:
                _stored_x2m_fields.append(typing.cast("_RelationalMulti", field))
            else:
                default = PENDING if field.is_stored_computed else None
                _stored_scalar_caches.append(
                    (field, field.name, field._get_cache(env), default)
                )

        _fields = self._fields
        _field_inverses = self.pool.field_inverses

        vals_list = []
        set_vals_list = []
        record_ids = []
        for data, record in zip(
            data_list, records.with_context(bin_size=False), strict=True
        ):
            data["record"] = record
            vals = dict(
                {k: v for d in data["inherited"].values() for k, v in d.items()},
                **data["stored"],
            )
            vals_list.append((vals, record, data["stored"]))
            set_vals_list.append(common_set_vals.union(vals))
            record_ids.append(record._ids[0])

        supplied = set().union(*set_vals_list) if set_vals_list else set()
        # a new row has no relation rows: the empty value is primed in the
        # creating scope and mirrored to the superuser one, where a compute_sudo
        # compute reads it -- unmirrored, that read fetched the relation
        for field in _stored_x2m_fields:
            field._update_cache(records, (), created=True)
        for _field, fname, cache, default in _stored_scalar_caches:
            if fname not in supplied:
                cache.update(dict.fromkeys(record_ids, default))
            else:
                cache.update(
                    (rid, default)
                    for rid, set_vals in zip(record_ids, set_vals_list, strict=True)
                    if fname not in set_vals
                )

        for vals, record, stored in vals_list:
            for fname, value in vals.items():
                field = _fields[fname]
                if field.is_x2many:
                    continue
                if field.is_html:
                    if fname not in stored:
                        continue
                    cache_value = field.convert_to_cache(value, record, validate=False)
                else:
                    cache_value = field.convert_to_cache(value, record)
                field._update_cache(record, cache_value)
                if (
                    field.is_many2one or field.is_many2one_reference
                ) and _field_inverses[field]:
                    inverses_update[field][cache_value].append(record.id)

        _debug.perf.count(
            "create.cache_primed",
            model=self._name,
            records=len(record_ids),
            x2many_fields=len(_stored_x2m_fields),
            scalar_fields=len(_stored_scalar_caches),
            supplied=len(supplied),
            inverse_updates=sum(len(updates) for updates in inverses_update.values()),
        )
        return records, inverses_update

    @api.model
    def _create_update_xmlids(self, records: Self, vals_list: list[ValuesType]) -> None:
        import_module = self.env.context.get("_import_current_module")
        if not import_module:
            return

        noupdate = self.env.context.get("noupdate", False)
        xids = (v.get("id") for v in vals_list)
        entries = [
            {
                "xml_id": (xid if "." in xid else f"{import_module}.{xid}"),
                "record": rec,
                "noupdate": noupdate,
            }
            for rec, xid in zip(records, xids, strict=True)
            if xid and isinstance(xid, str)
        ]
        _debug.lifecycle(
            "create.xmlids_updated",
            model=self._name,
            module=import_module,
            records=len(records),
            xmlids=len(entries),
            noupdate=noupdate,
        )
        self.env.registry.xmlids.update(self.env, entries)

    def _update_parent_path_on_create(self) -> None:
        if not self._parent_store:
            return

        updated = self.env.backend.set_parent_paths(self, self.ids)

        _debug.perf.count(
            "create.parent_path_updated",
            model=self._name,
            records=len(self),
            rows=len(updated),
        )
        self._fields["parent_path"]._update_cache_items(self.env, updated)
