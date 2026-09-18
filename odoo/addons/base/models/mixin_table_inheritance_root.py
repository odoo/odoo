from collections import defaultdict
from typing import Self

from odoo import api, models, tools
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, _, frozendict

_debug = DebugLog(__name__)


class MixinTableInheritanceRoot(models.AbstractModel):
    _name = "mixin.table.inheritance.root"
    _description = "Table Inheritance Root"

    def _get_root_model_name(self) -> str:
        """The model owning the root table. Not a cache key: `self._name` is
        already one, and resolving this walks the tree."""
        root_table = self._table_inheritance_root
        by_table = self.env.registry.model_names_by_inheritance_root
        for name in by_table.get(root_table, ()):
            if self.env.registry[name]._table == root_table:
                return name
        return self._name

    @api.model
    def _get_model_names_in_tree(self) -> frozenset[str]:
        root_table = self.env.registry[self._get_root_model_name()]._table
        return frozenset(
            self.env.registry.model_names_by_inheritance_root.get(root_table, ())
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_model_names_in_root_table(self) -> frozenset[str]:
        root = self.env.registry[self._get_root_model_name()]
        return frozenset(
            name
            for name, model in self.env.registry.items()
            if model._table == root._table
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_fields_ondelete_unenforced(self) -> tuple[tuple[str, str, str], ...]:
        root_models = self._get_model_names_in_root_table()
        _debug.perf.count("ondelete_fields_scanned", root_models=len(root_models))
        return tuple(
            sorted(
                (model_name, field.name, field.ondelete)
                for model_name, model in self.env.registry.items()
                if not model._abstract
                for field in model._fields.values()
                if field.type == "many2one"
                and field.store
                and not field.related
                and field.comodel_name in root_models
            )
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_relations_ondelete_unenforced(
        self,
    ) -> tuple[tuple[str, str, str, str], ...]:
        root_models = self._get_model_names_in_root_table()
        return tuple(
            sorted(
                {
                    (model_name, field.name, field.relation, column)
                    for model_name, model in self.env.registry.items()
                    if not model._abstract
                    for field in model._fields.values()
                    if field.type == "many2many" and field.store
                    for column, end in (
                        (field.column2, field.comodel_name),
                        (field.column1, model_name),
                    )
                    if end in root_models
                }
            )
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_selections_ondelete_unenforced(self) -> tuple[tuple[str, str], ...]:
        tree_models = self._get_model_names_in_tree()
        return tuple(
            sorted(
                (model_name, field.name)
                for model_name, model in self.env.registry.items()
                if not model._abstract
                for field in model._fields.values()
                if field.type == "reference"
                and field.store
                and (
                    not isinstance(field.selection, list)
                    or any(value in tree_models for value, __ in field.selection)
                )
            )
        )

    @api.model
    @tools.ormcache(cache="stable")
    def _get_model_names_by_table(self) -> frozendict:
        by_table = defaultdict(list)
        for model_name in self._get_model_names_in_tree():
            by_table[self.env[model_name]._table].append(model_name)
        return frozendict({table: tuple(sorted(n)) for table, n in by_table.items()})

    def _get_type_field_name(self) -> str:
        """The stored column naming a row's concrete model, cross-checked
        against the table it was found in. Empty where the tree keeps none, and
        then the table alone decides."""
        return "type"

    def _get_model_names_concrete(self) -> dict[int, str]:
        if not self.ids:
            return {}
        root_name = self._get_root_model_name()
        root = self.env.registry[root_name]
        by_table = self._get_model_names_by_table()
        self.env[root_name].flush_model()
        type_field = self._get_type_field_name()
        self.env.cr.execute(
            SQL(
                "SELECT r.id, c.relname, %s FROM %s r"
                " JOIN pg_class c ON c.oid = r.tableoid WHERE r.id IN %s",
                SQL.identifier("r", type_field) if type_field else SQL("NULL"),
                SQL.identifier(root._table),
                tuple(self.ids),
            )
        )
        found = {}
        mismatched = 0  # debuglog
        for record_id, table, declared in self.env.cr.fetchall():
            candidates = by_table.get(table) or (root_name,)
            if declared in candidates:
                found[record_id] = declared
            else:
                found[record_id] = candidates[0] if len(candidates) == 1 else root_name
                mismatched += 1  # debuglog
        _debug.perf.count(
            "concrete_models_resolved",
            records=len(self),
            found=len(found),
            type_mismatched=mismatched,
        )
        return {record_id: found.get(record_id, root_name) for record_id in self.ids}

    def _get_concrete(self) -> Self:
        self.check_singleton()
        [model_name] = self._get_model_names_concrete().values()
        _debug.logic("concrete_resolved", record=self.id, model=model_name)
        return self.env[model_name].browse(self.id)

    def _get_cache_groups_holding(self) -> set[str]:
        return set()

    _dispatch_write_to_concrete = False

    def write(self, vals):
        if (
            self._dispatch_write_to_concrete
            and self._name == self._get_root_model_name()
        ):
            _debug.logic("write_dispatched_to_concrete", count=len(self))
            return self._write_as_concrete_types(vals)
        return self._write_concrete(vals)

    def _write_as_concrete_types(self, vals) -> bool:
        result = True
        if unsaved := self.filtered(lambda record: not record.id):
            result = unsaved._write_concrete(vals)
        by_model = defaultdict(list)
        for record_id, model_name in self._get_model_names_concrete().items():
            by_model[model_name].append(record_id)
        for model_name, ids in by_model.items():
            records = self.env[model_name].browse(ids)
            if model_name == self._name:
                result = records._write_concrete(vals) and result
            else:
                result = records.write(vals) and result
        return result

    def _write_concrete(self, vals) -> bool:
        return super().write(vals)

    def unlink(self) -> bool:
        if self._name == self._get_root_model_name():
            _debug.logic("unlink_dispatched_to_concrete", count=len(self))
            return self._unlink_as_concrete_types()
        groups = self.exists()._get_cache_groups_holding()
        _debug.lifecycle("unlink", model=self._name, count=len(self))
        with self.env.cr.savepoint():
            self._apply_ondelete_unenforced()
            res = super().unlink()
        if groups:
            self.env.registry.clear_cache(*groups)
        return res

    def _unlink_as_concrete_types(self) -> bool:
        groups = self.exists()._get_cache_groups_holding()
        by_model = defaultdict(list)
        for record_id, model_name in self._get_model_names_concrete().items():
            by_model[model_name].append(record_id)
        result = True
        _debug.pipeline(
            "unlink_as_concrete_types",
            records=len(self),
            models={model: len(ids) for model, ids in by_model.items()},
            cache_groups=sorted(groups),
        )
        with self.env.cr.savepoint():
            for model_name, ids in by_model.items():
                if model_name != self._name:
                    result = self.env[model_name].browse(ids).unlink() and result
                    continue
                records = self.browse(ids)
                records._apply_ondelete_unenforced()
                result = super(MixinTableInheritanceRoot, records).unlink() and result
        if groups:
            self.env.registry.clear_cache(*groups)
        return result

    def _apply_ondelete_unenforced(self) -> None:
        if not self:
            return
        found = defaultdict(list)
        with _debug.perf(
            "ondelete_references_scanned", cr=self.env.cr, records=len(self)
        ) as span:
            fields_scanned = self._get_fields_ondelete_unenforced()
            for model_name, field_name, ondelete in fields_scanned:
                references = (
                    self.env[model_name]
                    .sudo()
                    .with_context(active_test=False)
                    .search([(field_name, "in", self.ids)])  # noqa: E8507  model varies
                )
                if references:
                    found[ondelete].append((model_name, field_name, references))
            span.set(fields=len(fields_scanned))
        _debug.logic(
            "ondelete_unenforced",
            records=self.ids,
            found={key: len(items) for key, items in found.items()},
        )

        if restricted := found.get("restrict"):
            _debug.logic(
                "unlink_restricted",
                records=self.ids,
                referrers=[model_name for model_name, __, __ in restricted],
            )
            raise ValidationError(
                _(
                    "Cannot delete this record: %s",
                    ", ".join(
                        _(
                            "%(count)s %(model)s record(s) still reference it",
                            count=len(references),
                            model=self.env[model_name]._description,
                        )
                        for model_name, __, references in restricted
                    ),
                )
            )
        for __, __, references in found["cascade"]:
            references.unlink()
        for __, field_name, references in found["set null"]:
            references.write({field_name: False})

        values = [
            f"{model_name},{record_id}"
            for model_name in {self._name, self._get_root_model_name()}
            for record_id in self.ids
        ]
        for model_name, field_name in self._get_selections_ondelete_unenforced():
            referring = (
                self.env[model_name]
                .sudo()
                .with_context(active_test=False)
                .search([(field_name, "in", values)])  # noqa: E8507  model varies
            )
            if referring:
                _debug.lifecycle(
                    "reference_fields_cleared",
                    model=model_name,
                    field=field_name,
                    count=len(referring),
                )
                referring.write({field_name: False})

        for (
            model_name,
            field_name,
            relation,
            column,
        ) in self._get_relations_ondelete_unenforced():
            self.env.cr.execute(
                SQL(
                    "DELETE FROM %s WHERE %s IN %s",
                    SQL.identifier(relation),
                    SQL.identifier(column),
                    tuple(self.ids),
                )
            )
            _debug.lifecycle(
                "relation_rows_deleted",
                relation=relation,
                column=column,
                rows=self.env.cr.rowcount,
            )
            self.env[model_name].invalidate_model([field_name])
