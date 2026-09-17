import typing
from collections import defaultdict
from typing import Self

from odoo.exceptions import AccessError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools.cache import TransactionMemo
from odoo.tools.translate import _

from ..._typing import ValuesType
from ._crud_common import (
    _orm_crud,
    get_forbidden_field_names,
)
from ._model_stubs import _ModelStubs

_debug = DebugLog(__name__)


class _WriteFieldPlan(typing.NamedTuple):
    field_values: list
    inverses_by_hook: dict
    fnames_modifying_relations: list
    protected: set
    x2m_inverse_fnames: list


class WriteMixin(_ModelStubs):
    __slots__ = ()

    def _increment_fields_skiplock(self, *fields: str) -> bool:
        if not self:
            return False

        for field in fields:
            if not self._fields[field].is_integer:
                raise ValueError(
                    f"_increment_fields_skiplock: field {field!r} is not an integer"
                )

        # a pending write of a counter lands before the increment, and the
        # cache drops the counters after it: a read in the same transaction
        # answers the incremented value, not the one written or fetched before
        self.flush_recordset(fields)
        updated = self.env.backend.increment_columns_skip_locked(self, fields, self.ids)
        self._invalidate_cache(fields, self._ids, flush=False)
        _debug.logic(
            "write.increment_skiplock",
            model=self._name,
            fields=list(fields),
            records=len(self),
            updated=updated,
        )
        return bool(updated)

    def _write_check_field_access(self, vals: ValuesType) -> None:
        self.check_access("write")
        self._check_fields_write_access(vals)

    def _write_classify_fields(self, vals: ValuesType) -> _WriteFieldPlan:
        plan = _WriteFieldPlan([], defaultdict(list), [], set(), [])
        for fname, value in vals.items():
            field = self._fields[fname]
            plan.field_values.append((field, value))
            if field.inverse:
                if field.is_x2many:
                    plan.x2m_inverse_fnames.append(fname)
                plan.inverses_by_hook[field.inverse].append(field)
            if self.pool.is_modifying_relations(field):
                plan.fnames_modifying_relations.append(fname)
            if field.inverse or (field.compute and not field.readonly):
                if (
                    field.store
                    or not field.is_x2many
                    or (field.related and field._related_names[0] in vals)
                ):
                    plan.protected.update(self.pool.field_computed.get(field, [field]))
        return plan

    def _write_settle_protected(self, plan: _WriteFieldPlan, vals: ValuesType) -> None:
        if plan.x2m_inverse_fnames:
            self._recompute_recordset(plan.x2m_inverse_fnames)
            self.fetch(plan.x2m_inverse_fnames)
            for fname in plan.x2m_inverse_fnames:
                field = self._fields[fname]
                if not field.store:
                    field.__get__(self)

        if plan.protected:
            to_compute = [
                field.name
                for field in plan.protected
                if field.compute and field.name not in vals
            ]
            _debug.logic(
                "write.protected_settled",
                model=self._name,
                records=len(self),
                protected=len(plan.protected),
                x2many_inverses=len(plan.x2m_inverse_fnames),
                to_compute=len(to_compute),
            )
            if to_compute:
                self._recompute_recordset(to_compute)

    def _write_apply_inverses(
        self, inverses_by_hook: dict, real_recs: Self, vals: ValuesType
    ) -> None:
        for fields in inverses_by_hook.values():
            dirty_marked = 0  # debuglog
            for field in fields:
                if (
                    not field.store
                    and (not field.inherited or not field.is_x2many)
                    and any(field._iter_cache_missing_ids(real_recs))
                ):
                    dirty_marked += 1  # debuglog
                    field.mark_dirty(real_recs, vals[field.name])

            _debug.pipeline(
                "write.inverse_hook",
                model=self._name,
                field=fields[0].name,
                fields=len(fields),
                records=len(real_recs),
                dirty_marked=dirty_marked,
            )
            try:
                fields[0].apply_inverse(real_recs)
            except AccessError as e:
                _debug.logic(
                    "write.inverse_access_error",
                    model=self._name,
                    field=fields[0].name,
                    inherited=fields[0].inherited,
                )
                if fields[0].inherited:
                    description = self.env.registry.metaschema.model_description(
                        self.env, self._name
                    )
                    raise AccessError(
                        _(
                            "%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).",
                            previous_message=e.args[0],
                            document_kind=description,
                            document_model=self._name,
                        )
                    ) from e
                raise

    def write(self, vals: ValuesType) -> typing.Literal[True]:
        if not self:
            return True

        TransactionMemo.discard_for_model(self.env, self._name, vals)
        prof = _OrmProfile(_orm_crud)

        if self.env.transaction.observers:
            self.env.transaction.observe_operation(
                "write", self._name, len(self), frozenset(vals)
            )

        self._write_check_field_access(vals)
        prof.mark("acl")
        env = self.env

        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "write.records",
                model=self._name,
                records=len(self),
                uid=env.uid,
                fields=sorted(vals),
            )
        bad_names = get_forbidden_field_names(self)
        vals = {key: val for key, val in vals.items() if key not in bad_names}
        if self._log_access:
            vals.setdefault("write_uid", self.env.uid)
            vals.setdefault("write_date", self.env.cr.now())

        plan = self._write_classify_fields(vals)
        field_values = plan.field_values
        inverses_by_hook = plan.inverses_by_hook
        protected = plan.protected
        _debug.pipeline(
            "write.classified",
            model=self._name,
            records=len(self),
            fields=len(field_values),
            inverse_hooks=len(inverses_by_hook),
            modifying_relations=len(plan.fnames_modifying_relations),
            protected=len(protected),
            x2many_inverses=len(plan.x2m_inverse_fnames),
        )
        self._write_settle_protected(plan, vals)
        prof.mark("classify")

        with env.protecting(protected, self):
            if plan.fnames_modifying_relations:
                self._modified_before(plan.fnames_modifying_relations)
            prof.mark("before")

            _ids = self._ids
            if len(_ids) == 1 and _ids[0]:
                real_recs = self
            else:
                real_recs = self.filtered("id")
                if _debug.logic.enabled and len(real_recs) < len(self):
                    _debug.logic(
                        "write.new_records_skipped",
                        model=self._name,
                        records=len(self),
                        real=len(real_recs),
                    )

            if len(field_values) > 1:
                field_values.sort(key=lambda item: item[0].write_sequence)
            for field, value in field_values:
                field.mark_dirty(self, value)
            if real_recs:
                written_names = [field.name for field, _value in field_values]
                real_recs._evict_x2many_scopes_reading_through(written_names)
                if self._table_inheritance_root:
                    real_recs._invalidate_table_inheritance_siblings(written_names)
            prof.mark("dirty")

            self.modified(vals)
            prof.mark("after")

            if self._parent_store and self._parent_name in vals:
                _debug.pipeline(
                    "write.parent_flushed",
                    model=self._name,
                    records=len(self),
                    parent_field=self._parent_name,
                )
                self.flush_model([self._parent_name])

            inverse_fields = [f.name for fs in inverses_by_hook.values() for f in fs]
            real_recs._check_fields(vals, inverse_fields)
            prof.mark("validate")

            self._write_apply_inverses(inverses_by_hook, real_recs, vals)

            real_recs._check_fields(inverse_fields)

        if self._check_company_auto:
            _debug.pipeline(
                "write.check_company",
                model=self._name,
                records=len(real_recs),
                fields=len(vals),
            )
            self._check_company(list(vals))

        prof.stop("inverse")
        if prof.debug:
            _fnames = (
                ", ".join(sorted(vals)) if len(vals) <= 20 else f"{len(vals)} fields"
            )
            prof.report(
                _orm_crud, "write %s: %d records, %s", self._name, len(self), _fnames
            )
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "write", self._name, len(self), prof.elapsed
            )

        return True

    def _write_multi(self, vals_list: list[ValuesType]) -> None:
        if len(self) != len(vals_list):
            raise ValueError(
                f"_write_multi: len(records)={len(self)} != "
                f"len(vals_list)={len(vals_list)}"
            )

        if not self:
            return

        prof = _OrmProfile(_orm_crud)

        parent_records = (
            self._get_records_with_parent_changed(vals_list)
            if self._parent_store
            else None
        )

        log_vals: ValuesType = (
            {"write_uid": self.env.uid, "write_date": self.env.cr.now()}
            if self._log_access
            else {}
        )
        log_only_ids: dict[str, list] = {fname: [] for fname in log_vals}

        with self.env.cr.pipeline():
            updates = defaultdict(list)
            for id_, vals in zip(self._ids, vals_list, strict=True):
                if not vals:
                    continue
                if log_vals:
                    for fname in log_vals:
                        if fname not in vals:
                            log_only_ids[fname].append(id_)
                    vals = log_vals | vals
                fnames, row = zip(*sorted(vals.items()), strict=False)
                updates[fnames].append((id_,) + row)
            for fnames, rows in updates.items():
                self._execute_update(fnames, rows)

        if _debug.pipeline.enabled:
            _debug.pipeline(
                "write.multi_updated",
                model=self._name,
                records=len(self),
                column_groups=len(updates),
                log_only=sum(len(ids) for ids in log_only_ids.values()),
                parent_changed=len(parent_records) if parent_records else 0,
            )
        self._sync_log_access_cache(log_vals, log_only_ids)

        if parent_records:
            _debug.logic(
                "write.parent_path_changed",
                model=self._name,
                records=len(parent_records),
            )
            parent_records._update_parent_path_on_write()

        prof.stop()
        prof.report(
            _orm_crud,
            "_write_multi %s: %d records, %d column-group(s)",
            self._name,
            len(self),
            len(updates),
        )

    def _sync_log_access_cache(
        self, log_vals: ValuesType, log_only_ids: dict[str, list]
    ) -> None:
        for fname, ids in log_only_ids.items():
            if not ids:
                continue
            field = self._fields[fname]
            records = self.browse(ids)
            field._update_cache(
                records,
                field.convert_to_cache(log_vals[fname], records, validate=False),
            )

    def _execute_update(self, fnames: tuple[str, ...], rows: list[tuple]) -> None:
        _debug.pipeline(
            "write.execute_update",
            model=self._name,
            columns=len(fnames),
            rows=len(rows),
        )
        self.env.backend.update_rows(self, fnames, rows)

    def _get_records_with_parent_changed(self, vals_list: list[ValuesType]) -> Self:
        parent_to_ids = defaultdict(list)
        for id_, vals in zip(self._ids, vals_list, strict=True):
            if self._parent_name in vals:
                parent_to_ids[vals[self._parent_name]].append(id_)

        if not parent_to_ids:
            return self.browse()

        self.flush_recordset([self._parent_name])

        changed = self.env.backend.records_with_parent_changed(self, parent_to_ids)
        _debug.logic(
            "write.parent_candidates_probed",
            model=self._name,
            parents=len(parent_to_ids),
            candidates=sum(len(ids) for ids in parent_to_ids.values()),
            changed=len(changed),
        )
        return self.browse(changed)

    def _update_parent_path_on_write(self) -> None:
        for parent, records in self.grouped(self._parent_name).items():
            prefix = parent.parent_path or ""

            if prefix:
                parent_ids = {int(label) for label in prefix.split("/")[:-1]}
                if not parent_ids.isdisjoint(records._ids):
                    _debug.logic(
                        "write.parent_path_recursion",
                        model=self._name,
                        parent=parent.id,
                        records=len(records),
                    )
                    raise UserError(_("Recursion Detected."))

            updated = self.env.backend.move_parent_paths(self, records.ids, prefix)

            _debug.perf.count(
                "write.parent_path_rewritten",
                model=self._name,
                parent=parent.id,
                records=len(records),
                descendants=len(updated),
            )
            self._fields["parent_path"]._update_cache_items(self.env, updated.items())
            self.browse(updated).modified(["parent_path"])
