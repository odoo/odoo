import logging
from collections import defaultdict
from typing import Self

from odoo import api, models, tools
from odoo.db.schema import (
    add_constraint,
    column_exists,
    drop_constraint,
    get_constraint_definition,
    table_exists,
)
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, _, frozendict

from .ir_model_common import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MixinTableInheritanceRoot(models.AbstractModel):
    _name = "mixin.table.inheritance.root"
    _description = "Table Inheritance Root"

    def _get_reference_model_name(self) -> str:
        return self._get_root_model_name()

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

    def _holds_referencing_rows(self, model_name: str) -> bool:
        """Whether rows of `model_name` can point at a deleted record.

        Only an ordinary table does. A view or a table query derives its rows,
        so nothing there dangles, and searching one can cost a full scan -- a
        view over the GPS foreign table held an asset unlink for minutes. A
        foreign table carries its own delete guard as a trigger.
        """
        model = self.env[model_name]
        return not model._abstract and model._is_an_ordinary_table()

    @api.model
    @tools.ormcache(cache="stable")
    def _get_fields_ondelete_unenforced(self) -> tuple[tuple[str, str, str], ...]:
        root_models = self._get_model_names_in_root_table()
        _debug.perf.count("ondelete_fields_scanned", root_models=len(root_models))
        return tuple(
            sorted(
                (model_name, field.name, field.ondelete)
                for model_name, model in self.env.registry.items()
                if self._holds_referencing_rows(model_name)
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
                    if self._holds_referencing_rows(model_name)
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
                if self._holds_referencing_rows(model_name)
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

    @api.private
    def init(self) -> None:
        super().init()
        self._check_table_inheritance()
        self._constrain_type_to_table()

    def _register_hook(self) -> None:
        super()._register_hook()
        self._drop_set_aside_member_columns()

    def _drop_set_aside_member_columns(self) -> None:
        """A migration that moves a column off the root sets it aside as
        `legacy_<name>` and drops it; a member table created with its columns
        spelled out keeps its own copy of the set-aside column after the root
        drops it (`attislocal`). Such a copy is nobody's field: it goes, with
        the SQL views that read it, which their modules recreate. This runs
        once the registry is loaded, after every module's migrations, never
        between a module's schema pass and its post-migrate."""
        if not self._is_table_inheritance_root() or self.env.cr.readonly:
            return
        cr = self.env.cr
        cr.execute(
            r"""
            SELECT child.relname, a.attname
              FROM pg_inherits
              JOIN pg_class child ON child.oid = pg_inherits.inhrelid
              JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
              JOIN pg_attribute a ON a.attrelid = child.oid
             WHERE parent.relname = %s
               AND a.attname LIKE 'legacy\_%%'
               AND a.attnum > 0 AND NOT a.attisdropped
               AND NOT EXISTS (
                   SELECT 1 FROM pg_attribute p
                    WHERE p.attrelid = parent.oid AND p.attname = a.attname
                      AND NOT p.attisdropped
               )
            """,
            [self._table],
        )
        fields_by_table = self._get_model_names_by_table()
        for table, column in cr.fetchall():
            declared = any(
                column in self.env[name]._fields for name in fields_by_table.get(table, ())
            )
            if declared:
                continue
            _logger.info(
                "%s: dropping set-aside column %s.%s left behind by a migration.",
                self._name,
                table,
                column,
            )
            cr.execute(
                SQL(
                    "ALTER TABLE %s DROP COLUMN %s CASCADE",
                    SQL.identifier(table),
                    SQL.identifier(column),
                )
            )
            _debug.lifecycle(
                "table_inheritance.set_aside_column_dropped", table=table, column=column
            )

    def _constrain_type_to_table(self) -> None:
        type_field = self._get_type_field_name()
        root_table = self._table_inheritance_root
        if (
            not type_field
            or not root_table
            or self._table == root_table
            or self._get_model_names_by_table().get(self._table) != (self._name,)
            or not table_exists(self.env.cr, self._table)
        ):
            return
        cr = self.env.cr
        name = f"{self._table}_{type_field}_names_model"
        definition = f"CHECK ({type_field} = '{self._name}')"
        current = get_constraint_definition(cr, self._table, name)
        if current == definition:
            return
        cr.execute(
            SQL(
                "SELECT count(*) FROM ONLY %s WHERE %s IS DISTINCT FROM %s",
                SQL.identifier(self._table),
                SQL.identifier(type_field),
                self._name,
            )
        )
        if stray := cr.fetchone()[0]:
            _logger.error(
                "%d row(s) of %s name another model in %s; they block the "
                "constraint that keeps the column and the table in agreement.",
                stray,
                self._table,
                type_field,
            )
            return
        if current:
            drop_constraint(cr, self._table, name)
        add_constraint(cr, self._table, name, definition)
        _debug.lifecycle("type_constrained_to_table", table=self._table)

    def _check_table_inheritance(self) -> None:
        root_table = self._table_inheritance_root
        if not root_table or self._table == root_table:
            return
        if not table_exists(self.env.cr, self._table):
            _debug.lifecycle(
                "table_inheritance.table_absent",
                model=self._name,
                table=self._table,
                root=root_table,
            )
            return
        self.env.cr.execute(
            SQL(
                "SELECT 1 FROM pg_inherits i"
                " JOIN pg_class c ON c.oid = i.inhrelid"
                " JOIN pg_class p ON p.oid = i.inhparent"
                " WHERE c.relname = %s AND p.relname = %s"
                " AND c.relnamespace = current_schema::regnamespace",
                self._table,
                root_table,
            )
        )
        if self.env.cr.fetchone():
            return
        raise ValueError(
            f"{self._name} declares _table_inheritance_root = {root_table!r} but "
            f"table {self._table!r} does not inherit it; the rows of one would be "
            f"invisible to the other."
        )

    def _get_type_field_name(self) -> str:
        """The stored column naming a row's concrete model, cross-checked
        against the table it was found in. Empty where the tree keeps none, and
        then the table alone decides."""
        return "type"

    def _get_model_names_concrete(self) -> dict[int, str]:
        if not self.ids:
            return {}
        root = self.env[self._get_root_model_name()]
        cache = root._get_model_name_concrete.__cache__
        lru = self.pool.ormcache_lrus[cache.cache_name]
        found = {}
        misses = []
        for record_id in self.ids:
            try:
                found[record_id] = lru[cache.key(root, record_id)]
            except KeyError:
                misses.append(record_id)
        if misses:
            generation = cache.get_cache_generation(root)
            queried = root._query_model_names_concrete(misses)
            for record_id, model_name in queried.items():
                cache.add_value(
                    root, record_id, cache_value=model_name, generation=generation
                )
            found.update(queried)
        _debug.perf.count(
            "concrete_models_resolved",
            records=len(self),
            cached=len(self.ids) - len(misses),
            queried=len(misses),
        )
        return {record_id: found.get(record_id, root._name) for record_id in self.ids}

    @tools.ormcache("record_id", cache="default")
    def _get_model_name_concrete(self, record_id: int) -> str:
        return self._query_model_names_concrete([record_id]).get(
            record_id, self._get_root_model_name()
        )

    def _query_model_names_concrete(self, ids: list[int]) -> dict[int, str]:
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
                tuple(ids),
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
            "concrete_models_queried",
            ids=len(ids),
            found=len(found),
            type_mismatched=mismatched,
        )
        return found

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

    def _is_column_dropped(self, model_name: str, field_name: str) -> bool:
        # an uninstall drops columns and tables before the registry forgets them
        model = self.env[model_name]
        return bool(
            self.env.context.get(MODULE_UNINSTALL_FLAG) or model._custom
        ) and not column_exists(self.env.cr, model._table, field_name)

    def _apply_ondelete_unenforced(self) -> None:
        if not self:
            return
        found = defaultdict(list)
        with _debug.perf(
            "ondelete_references_scanned", cr=self.env.cr, records=len(self)
        ) as span:
            fields_scanned = self._get_fields_ondelete_unenforced()
            for model_name, field_name, ondelete in fields_scanned:
                if self._is_column_dropped(model_name, field_name):
                    continue
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
            if self._is_column_dropped(model_name, field_name):
                continue
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
            if self.env.context.get(MODULE_UNINSTALL_FLAG) and not table_exists(
                self.env.cr, relation
            ):
                continue
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
