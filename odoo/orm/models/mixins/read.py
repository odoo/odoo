import logging
import typing
from collections import deque
from typing import Self

from odoo.exceptions import AccessError, MissingError
from odoo.libs.accel import batch_cache_fill as _batch_cache_fill
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import OrderedSet, frozendict, ormcache
from odoo.tools.misc import PENDING, SENTINEL

from ... import decorators as api
from ..._typing import ValuesType
from ...fields._field_description import description_key
from ...primitives import LOG_ACCESS_COLUMNS
from ._cache_scan import can_scan_read, is_cache_detached
from ._model_stubs import _ModelStubs
from .access import AccessMixin

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence

    from ...fields.base import Field
    from ...tools import Query

_logger = logging.getLogger("odoo.models")
_orm_read = logging.getLogger("odoo.orm.read")
_debug = DebugLog(__name__)


class PrefetchBatchDenied(AccessError):
    pass


class ReadMixin(_ModelStubs):
    __slots__ = ()

    @api.model
    def fields_get(
        self,
        allfields: Collection[str] | None = None,
        attributes: Collection[str] | None = None,
    ) -> dict[str, ValuesType]:
        if isinstance(allfields, str):
            raise TypeError(
                f"fields_get() takes a collection of field names, got the string "
                f"{allfields!r}; pass [{allfields!r}]"
            )
        res = {}
        wanted = set(allfields) if allfields else None
        key = description_key(attributes)
        described = self._get_field_descriptions_static(
            key, None if wanted is None else tuple(sorted(wanted))
        )
        for fname, field in self._fields.items():
            if wanted is not None and fname not in wanted:
                continue
            if not self._has_field_access(field, "read"):
                continue

            description = field._get_description_from_parts(self.env, *described[fname])
            if "readonly" in description:
                description["readonly"] = description[
                    "readonly"
                ] or not self._has_field_access(field, "write")
            res[fname] = description

        _debug.perf.count(
            "read.fields_get",
            model=self._name,
            requested=len(allfields) if allfields else None,
            described=len(res),
            attributes=len(attributes) if attributes is not None else None,
        )
        return res

    @api.model
    @ormcache(
        "attributes", "field_names", "self.env.lang", "self.env.su", cache="default"
    )
    def _get_field_descriptions_static(
        self,
        attributes: tuple[str, ...] | None,
        field_names: tuple[str, ...] | None,
    ) -> frozendict[str, tuple[frozendict, tuple[str, ...]]]:
        """Per field, the memoised half of its description and the names of
        the attributes ``fields_get`` evaluates on every call. Keyed on what
        the static half reads besides the registry: the language (labels,
        selection labels, decimal precisions) and the superuser flag (a
        non-stored related field sorts only under sudo). Field-level access
        is applied by the caller, never memoised."""
        fields_ = (
            self._fields.values()
            if field_names is None
            else (self._fields[name] for name in field_names if name in self._fields)
        )
        return frozendict(
            {
                field.name: (frozendict(static), dynamic)
                for field in fields_
                for static, dynamic in (field._describe_static(self.env, attributes),)
            }
        )

    @api.readonly
    def read(
        self, fields: Sequence[str] | None = None, load: str = "_classic_read"
    ) -> list[ValuesType]:
        prof = _OrmProfile(_orm_read)

        if not fields:
            fields = self._get_fields_default_read()
        else:
            _model_fields = self._fields
            bad = [
                f for f in fields if not isinstance(f, str) or f not in _model_fields
            ]
            if bad:
                _logger.warning("Invalid field(s) %r on %r, skipping", bad, self._name)
                _debug.logic(
                    "read.invalid_fields_skipped",
                    model=self._name,
                    invalid=len(bad),
                    requested=len(fields),
                )
                fields = [
                    f for f in fields if isinstance(f, str) and f in _model_fields
                ]
            if not self and not self.env.su:
                self._get_fields_to_fetch(fields)
        self._origin.fetch(fields)
        prof.mark("fetch")
        result = self._read_format(fnames=fields, load=load)

        prof.stop("format")
        prof.report(
            _orm_read,
            "read %s: %d records, %d fields",
            self._name,
            len(self),
            len(fields),
        )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "read", self._name, len(self), prof.elapsed
            )

        return result

    # An x2many is read by searching its comodel, which raises for a user without
    # read access to that model, while a many2one merely reads as empty. Such a
    # field cannot be read, so it is not part of "every field" either.
    @api.model
    def _is_readable_by_default(self, field: Field) -> bool:
        return (
            self.env.su
            or not field.is_x2many
            or self.env[field.comodel_name].has_access("read")
        )

    @api.model
    def _get_fields_default_read(self) -> list[str]:
        model_fields = self._fields
        return [
            fname
            for fname in self.fields_get(attributes=())
            if self._is_readable_by_default(model_fields[fname])
        ]

    def _read_format_scalar(
        self, name: str, results: list[dict], use_display_name: bool
    ) -> None:
        env = self.env
        ids = self._ids
        field = self._fields[name]
        field.recompute_pending(self)
        field_cache = field._get_cache(env)
        none_val: typing.Any = field.convert_to_record(None, self[:1])
        if type(field_cache) is dict:
            miss_indices = _batch_cache_fill(
                field_cache, ids, results, name, PENDING, none_val
            )
            if _debug.perf.enabled and miss_indices:
                _debug.perf.count(
                    "read.cache_miss",
                    model=self._name,
                    field=name,
                    records=len(ids),
                    misses=len(miss_indices),
                )
            for idx in miss_indices:
                vals = results[idx]
                if not vals:
                    continue
                try:
                    record = self._read_format_miss_record(ids[idx])
                    vals[name] = field.convert_to_read(
                        record[name], record, use_display_name
                    )
                except MissingError:
                    vals.clear()
            if miss_indices and is_cache_detached(field, env, field_cache):
                _debug.logic(
                    "read.cache_detached_slow_path",
                    model=self._name,
                    field=name,
                    misses=len(miss_indices),
                )
                self._read_format_by_record(
                    name, field, zip(self, results, strict=True), use_display_name
                )
            return
        _detached = False
        for id_, vals in zip(ids, results, strict=True):
            if not vals:
                continue
            cache_value = field_cache.get(id_, SENTINEL)
            if cache_value is SENTINEL or cache_value is PENDING:
                try:
                    record = self._read_format_miss_record(id_)
                    vals[name] = field.convert_to_read(
                        record[name], record, use_display_name
                    )
                except MissingError:
                    vals.clear()
                _detached = _detached or is_cache_detached(field, env, field_cache)
            elif cache_value is None:
                vals[name] = none_val
            else:
                vals[name] = cache_value
        if _detached:
            self._read_format_by_record(
                name, field, zip(self, results, strict=True), use_display_name
            )

    def _read_format_multi(
        self, name: str, field, data: list, use_display_name: bool
    ) -> None:
        if field.store:
            field.recompute_pending(self)
        values_list = []
        records = []
        valid_data = []
        for record, vals in data:
            if not vals:
                continue
            try:
                values_list.append(record[name])
                records.append(record.id)
                valid_data.append((record, vals))
            except MissingError:
                vals.clear()

        multi_results = field.convert_to_read_multi(
            values_list,
            self.browse(records),
            use_display_name or field.is_properties,
        )
        for (_, vals), convert_result in zip(valid_data, multi_results, strict=True):
            vals[name] = convert_result

    def _read_format_stored(
        self, name: str, field, data: list, use_display_name: bool
    ) -> None:
        env = self.env
        field.recompute_pending(self)
        _read_cache = field.read_cache
        convert_to_record = field.convert_to_record
        convert_to_read = field.convert_to_read
        misses = []
        for record, vals in data:
            if not vals:
                continue
            hit, cache_value = _read_cache(record._ids[0], env)
            if not hit:
                misses.append((record, vals))
                continue
            try:
                vals[name] = convert_to_read(
                    convert_to_record(cache_value, record),
                    record,
                    use_display_name,
                )
            except MissingError:
                vals.clear()
            except KeyError:
                misses.append((record, vals))
        if misses:
            self._read_format_by_record(name, field, misses, use_display_name)

    @staticmethod
    def _read_format_by_record(
        name: str, field, data: Iterable[tuple], use_display_name: bool
    ) -> None:
        convert = field.convert_to_read
        for record, vals in data:
            if not vals:
                continue
            try:
                vals[name] = convert(record[name], record, use_display_name)
            except MissingError:
                vals.clear()

    def _read_format(
        self, fnames: Sequence[str], load: str = "_classic_read"
    ) -> list[ValuesType]:
        use_display_name = load == "_classic_read"
        ids = self._ids
        _fields = self._fields

        scalar_fnames = []
        record_fnames = []
        for name in fnames:
            field = _fields[name]
            field.check_read_access(self)
            if can_scan_read(field):
                scalar_fnames.append(name)
            else:
                record_fnames.append(name)

        _debug.pipeline(
            "read.format",
            model=self._name,
            records=len(ids),
            scalar_fields=len(scalar_fnames),
            record_fields=len(record_fnames),
            load=load,
        )
        results = [{"id": id_} for id_ in ids]
        for name in scalar_fnames:
            self._read_format_scalar(name, results, use_display_name)

        if not record_fnames:
            return [vals for vals in results if vals]

        data = list(zip(self, results, strict=True))

        for name in record_fnames:
            field = _fields[name]
            if field.is_properties or field.is_many2one:
                self._read_format_multi(name, field, data, use_display_name)
            elif field.store:
                self._read_format_stored(name, field, data, use_display_name)
            else:
                self._read_format_by_record(name, field, data, use_display_name)

        return [vals for record, vals in data if vals]

    def _read_format_miss_record(self, id_):
        return self.browse((id_,)).with_prefetch(self._prefetch_ids)

    def _fetch_field(self, field: Field) -> None:
        if self.env.context.get("prefetch_fields", True) and field.prefetch:
            fnames = [f.name for f in self._readable_prefetch_fields(field.prefetch)]
            if field.name not in fnames:
                fnames.append(field.name)
        else:
            fnames = [field.name]
        _debug.logic(
            "read.fetch_field",
            model=self._name,
            field=field.name,
            prefetch=field.prefetch,
            fields=len(fnames),
            records=len(self),
        )
        self.fetch(fnames)

    @api.private
    def fetch(self, field_names: Collection[str] | None = None) -> None:
        self = self._origin
        if not self or not (field_names is None or field_names):
            return

        prof = _OrmProfile(_orm_read)

        fields_to_fetch = [
            field
            for field in self._get_fields_to_fetch(
                field_names, ignore_when_in_cache=True
            )
            if field.delegation_key_settled(self.env)
        ]
        self._flush_inheritance_tree_before_fetch(fields_to_fetch)

        in_prefetch_batch = self.env.transaction.prefetch_batch == (
            self._name,
            self._ids,
        )
        if any(field.column_type for field in fields_to_fetch):
            query = self._search([("id", "in", self.ids)], active_test=False)
        else:
            try:
                if not in_prefetch_batch:
                    self.check_access("read")
                elif not self.env.su and self._check_access("read"):
                    raise PrefetchBatchDenied(self._name)
            except MissingError:
                if in_prefetch_batch:
                    raise PrefetchBatchDenied(self._name) from None
                before = len(self)  # debuglog
                self = self.exists()
                _debug.logic(
                    "read.fetch.missing_records_dropped",
                    model=self._name,
                    before=before,
                    after=len(self),
                )
                self.check_access("read")
            if not fields_to_fetch:
                return
            query = self._as_query(ordered=False)

        _debug.pipeline(
            "read.fetch",
            model=self._name,
            records=len(self),
            requested=len(field_names) if field_names is not None else None,
            to_fetch=len(fields_to_fetch),
        )
        fetched = self._fetch_query(query, fields_to_fetch)

        if self.env.transaction.observers:
            self.env.transaction.observe_operation(
                "fetch",
                self._name,
                len(fetched),
                frozenset(field.name for field in fields_to_fetch),
            )

        prof.stop()
        prof.report(
            _orm_read,
            "fetch %s: %d records, %d fields",
            self._name,
            len(self),
            len(fields_to_fetch),
        )

        if fetched != self:
            if in_prefetch_batch:
                raise PrefetchBatchDenied(self._name)
            forbidden = (self - fetched).exists()
            _debug.logic(
                "read.fetch.short",
                model=self._name,
                requested=len(self),
                fetched=len(fetched),
                forbidden=len(forbidden),
            )
            if forbidden:
                raise self.env.registry.access_policy.record_denied_error(
                    self.env, "read", forbidden
                )

    def _flush_inheritance_tree_before_fetch(self, fields_to_fetch) -> None:
        if not self._is_table_inheritance_root():
            return
        for model_name in self.env._table_inheritance_tree(self._name):
            # the tree shares one table: a sibling's dirty value for these rows
            # must reach the table before this SELECT; a pending compute is
            # not this fetch's business
            other = self.env[model_name]
            names = [
                field.name for field in fields_to_fetch if field.name in other._fields
            ]
            if names:
                _debug.pipeline(
                    "read.fetch.flush_inheritance_sibling",
                    model=self._name,
                    sibling=model_name,
                    fields=len(names),
                )
                other._flush_if_dirty([other._fields[name] for name in names])

    def _readable_prefetch_fields(self, prefetch: typing.Any) -> tuple[Field, ...]:
        fields = self.pool.prefetch_fields(self._name, prefetch)
        if self.env.su:
            return fields
        if type(self)._has_field_access is not AccessMixin._has_field_access:
            return tuple(f for f in fields if self._has_field_access(f, "read"))
        return tuple(
            f for f in fields if not f.groups or self._has_field_access(f, "read")
        )

    def _get_fields_to_fetch(
        self,
        field_names: Collection[str] | None = None,
        ignore_when_in_cache: bool = False,
    ) -> list[Field]:
        if field_names is None:
            return list(self._readable_prefetch_fields(True))

        if not field_names:
            return []

        fields_to_fetch: list[Field] = []
        fields_todo: deque[Field] = deque()
        fields_done = {self._fields["id"]}
        for field_name in field_names:
            if not isinstance(field_name, str) or field_name not in self._fields:
                raise ValueError(
                    f"Invalid field {field_name!r} on model {self._name!r}"
                )
            field = self._fields[field_name]
            self._check_field_access(field, "read")
            fields_todo.append(field)

        cached = 0  # debuglog
        expanded = 0  # debuglog
        while fields_todo:
            field = fields_todo.popleft()
            if field in fields_done:
                continue
            fields_done.add(field)
            if ignore_when_in_cache and not any(field._iter_cache_missing_ids(self)):
                cached += 1  # debuglog
                continue
            if field.fetched_with_row:
                fields_to_fetch.append(field)
            else:
                expanded += 1  # debuglog
                for dotname in self.pool.field_depends[field]:
                    dep_field = self._fields[dotname.split(".", 1)[0]]
                    if (not dep_field.store) or (
                        dep_field.prefetch is True
                        and self._has_field_access(dep_field, "read")
                    ):
                        fields_todo.append(dep_field)

        if _debug.logic.enabled and (cached or expanded):
            _debug.logic(
                "read.fields_to_fetch_resolved",
                model=self._name,
                records=len(self),
                requested=len(field_names),
                to_fetch=len(fields_to_fetch),
                already_cached=cached,
                computed_expanded=expanded,
            )
        return fields_to_fetch

    def _fetch_query(self, query: Query, fields: Sequence[Field]) -> Self:
        column_fields: OrderedSet[Field] = OrderedSet()
        other_fields: OrderedSet[Field] = OrderedSet()
        for field in fields:
            if field.name == "id":
                continue
            if not field.fetched_with_row:
                raise RuntimeError(f"_fetch_query expects stored fields, got {field}")
            (column_fields if field.column_type else other_fields).add(field)

        _debug.pipeline(
            "read.fetch_query",
            model=self._name,
            records=len(self),
            column_fields=len(column_fields),
            other_fields=len(other_fields),
        )
        if column_fields and self._table_inheritance_root:
            # a cache miss here says nothing about the other models of the
            # tree, whose dirty values land in the rows this SELECT reads
            self._flush_table_inheritance_siblings(
                [field.name for field in column_fields], self._ids
            )
        return self.env.backend.fetch(self, query, column_fields, other_fields)

    def get_metadata(self) -> list[ValuesType]:

        if self._log_access:
            res = self.read(LOG_ACCESS_COLUMNS)
        else:
            res = [{"id": x} for x in self.ids]

        xml_data = {
            res_id: [
                {"xmlid": xmlid, "noupdate": noupdate}
                for xmlid, noupdate in reversed(xmlids)
            ]
            for res_id, xmlids in self.env.registry.xmlids.of_records(self).items()
        }

        for r in res:
            main = xml_data.get(r["id"], [{}])[-1]
            r["xmlid"] = main.get("xmlid", False)
            r["noupdate"] = main.get("noupdate", False)
            r["xmlids"] = xml_data.get(r["id"], [])[::-1]
        _debug.perf.count(
            "read.metadata",
            model=self._name,
            records=len(res),
            xmlids=sum(len(x) for x in xml_data.values()),
            log_access=self._log_access,
        )
        return res
