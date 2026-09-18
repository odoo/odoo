import typing
from itertools import batched

from odoo.db.schema import column_exists
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools.cache import TransactionMemo

from ...fields.reference import REFERENCE_VERIFIED_CACHE_KEY, Reference
from ...primitives import MODULE_UNINSTALL_FLAG
from ._crud_common import (
    _orm_crud,
    _unlink,
)
from ._model_stubs import _ModelStubs

_UNLINK_LOG_MAX_IDS = 1000

_debug = DebugLog(__name__)


class UnlinkMixin(_ModelStubs):
    __slots__ = ()

    def unlink(self) -> typing.Literal[True]:
        if not self:
            return True

        TransactionMemo.discard_for_model(self.env, self._name)
        prof = _OrmProfile(_orm_crud)

        if self.env.transaction.observers:
            self.env.transaction.observe_operation(
                "unlink", self._name, len(self), frozenset()
            )

        self.check_access("unlink")
        prof.mark("acl")

        _debug.lifecycle(
            "unlink.records",
            model=self._name,
            records=len(self),
            uid=self.env.uid,
            uninstalling=bool(self.env.context.get(MODULE_UNINSTALL_FLAG)),
        )
        ondelete_run = 0  # debuglog
        for func in self._ondelete_methods:
            if func._ondelete or not self.env.context.get(MODULE_UNINSTALL_FLAG):
                ondelete_run += 1  # debuglog
                func(self)
        _debug.pipeline(
            "unlink.ondelete",
            model=self._name,
            records=len(self),
            methods=len(self._ondelete_methods),
            run=ondelete_run,
        )
        prof.mark("ondelete")

        self._unlink_inheritance_rows_cascaded()

        self._discard_pending_recomputes()
        self.env.flush_all()
        prof.mark("flush")

        cr = self.env.cr
        ir_model_data_unlink = self.env.registry.xmlids.records_of(self)
        ir_attachment_unlink = self.env.registry.file_store.of_records(self)

        with self.env.protecting(self._fields.values(), self):
            self._modified_before(self._fields)

        self._discard_pending_recomputes()
        prof.mark("before")

        deleted_ids: list[int] = self.ids
        for sub_ids in batched(deleted_ids, cr.BATCH_SIZE, strict=False):
            self._unlink_process_batch(sub_ids)
        prof.mark("sql")

        if self.env.context.get(MODULE_UNINSTALL_FLAG):
            self.env.invalidate_all(flush=False)
            self.env.cr.cache.pop(REFERENCE_VERIFIED_CACHE_KEY, None)
        else:
            self._invalidate_after_unlink()

        _debug.pipeline(
            "unlink.cascade",
            model=self._name,
            records=len(deleted_ids),
            xmlids=len(ir_model_data_unlink),
            attachments=len(ir_attachment_unlink),
            uninstalling=bool(self.env.context.get(MODULE_UNINSTALL_FLAG)),
        )
        if ir_model_data_unlink:
            ir_model_data_unlink.unlink()
        if ir_attachment_unlink:
            ir_attachment_unlink.unlink()

        self._log_unlinked_ids(deleted_ids)

        prof.stop("invalidate")
        self._log_unlink_profile(prof, len(deleted_ids))

        return True

    def _unlink_inheritance_rows_cascaded(self) -> None:
        referrers = self.env.registry.cascades_into_inheritance_trees.get(self._name)
        if not referrers:
            return
        for model_name, path in referrers:
            model = self.env[model_name].sudo().with_context(active_test=False)
            if not model._is_path_in_database(path):
                continue
            rows = model.search([(path, "in", self.ids)])  # noqa: E8507  model varies
            if model_name == self._name:
                rows -= self
            _debug.pipeline(
                "unlink.inheritance_rows_cascaded",
                model=self._name,
                referrer=model_name,
                path=path,
                rows=len(rows),
            )
            rows.unlink()

    def _is_path_in_database(self, path: str) -> bool:
        model = self
        for name in path.split("."):
            if not column_exists(self.env.cr, model._table, name):
                return False
            model = self.env[model._fields[name].comodel_name]
        return True

    def _discard_pending_recomputes(self) -> None:
        core = self.env.core
        if core.has_pending():
            model_name = self._name
            pending_ids = self._ids
            discarded = 0  # debuglog
            for field in core.get_pending_fields():
                if field.model_name == model_name:
                    discarded += 1  # debuglog
                    core.mark_done(field, pending_ids)
            if _debug.logic.enabled and discarded:
                _debug.logic(
                    "unlink.pending_recomputes_discarded",
                    model=model_name,
                    records=len(pending_ids),
                    fields=discarded,
                )

    def _log_unlinked_ids(self, deleted_ids: list[int]) -> None:
        if len(deleted_ids) <= _UNLINK_LOG_MAX_IDS:
            _unlink.info(
                "User #%s deleted %s records with IDs: %r",
                self.env.uid,
                self._name,
                deleted_ids,
            )
        else:
            _unlink.info(
                "User #%s deleted %s records: %d IDs in [%s..%s], first %d: %r",
                self.env.uid,
                self._name,
                len(deleted_ids),
                min(deleted_ids),
                max(deleted_ids),
                _UNLINK_LOG_MAX_IDS,
                deleted_ids[:_UNLINK_LOG_MAX_IDS],
            )

    def _log_unlink_profile(self, prof: _OrmProfile, record_count: int) -> None:
        prof.report(_orm_crud, "unlink %s: %d records", self._name, record_count)
        if prof.agg and self.env.transaction.observers:
            self.env.transaction.observe_timing(
                "unlink", self._name, record_count, prof.elapsed
            )

    def _invalidate_after_unlink(self) -> None:
        env = self.env
        registry = env.registry
        cascades = registry.models_cascading_from
        # the row a subtype deleted is the row every other model of its
        # table-inheritance tree still holds in cache
        gone = {self._name, *env._table_inheritance_tree(self._name)}
        todo = list(gone)
        while todo:
            for model_name in cascades.get(todo.pop(), ()):
                if model_name not in gone:
                    gone.add(model_name)
                    todo.append(model_name)
        fields_by_comodel = registry.fields_by_comodel
        for model_name in gone:
            for field in env[model_name]._fields.values():
                field._invalidate_cache(env, keep_dirty=True)
            for field in fields_by_comodel.get(model_name, ()):
                field._invalidate_cache(env, keep_dirty=True)
        for field in registry.fields_reading_through_a_reference:
            field._invalidate_cache(env, keep_dirty=True)
        _debug.logic(
            "unlink.invalidated_models",
            model=self._name,
            models=len(gone),
            reference_fields=len(registry.fields_reading_through_a_reference),
        )
        Reference.discard_verified_models(env, gone)
        self._invalidate_ref_cache(gone)

    def _invalidate_ref_cache(self, model_names: typing.Iterable[str]) -> None:
        names = set(model_names)
        keys = self.env.transaction.forget_refs_of(names)
        if keys:
            _debug.logic(
                "unlink.ref_cache_evicted",
                model=self._name,
                models=len(names),
                keys=keys,
            )

    def _unlink_process_batch(self, sub_ids: tuple[int, ...]) -> None:
        self.env.backend.unlink_rows(self, sub_ids)
        _debug.perf.count("unlink.batch", model=self._name, records=len(sub_ids))
