import logging
from collections.abc import Collection
from typing import Any, Self

from psycopg.types.json import Json, Jsonb

from odoo import fields, models
from odoo.api import ValuesType
from odoo.db import schema as sql
from odoo.exceptions import AccessError
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import normalize_identifier
from odoo.tools import SQL, OrderedSet
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _get_owner_ids_by_name(records: models.BaseModel) -> dict[str, set[int]]:
    names = list({record.name for record in records})
    if not names:
        return {}
    return {
        name: set(ids)
        for name, ids in records.env.execute_query(
            SQL(
                "SELECT name, array_agg(id) FROM %s WHERE name = ANY(%s) GROUP BY name",
                SQL.identifier(records._table),
                names,
            )
        )
    }


class IrModelConstraint(models.Model):
    _name = "ir.model.constraint"
    _is_registry_metadata = True
    _description = "Model Constraint"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Constraint",
        index=True,
        readonly=True,
        required=True,
        help="PostgreSQL constraint or foreign key name.",
    )
    definition = fields.Char(
        readonly=True,
        help="PostgreSQL constraint definition",
    )
    message = fields.Char(
        translate=True,
        help="Error message returned when the constraint is violated.",
    )
    model = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    module = fields.Many2one(
        comodel_name="ir.module.module",
        index=True,
        readonly=True,
        required=True,
        ondelete="cascade",
    )
    type = fields.Char(
        string="Constraint Type",
        size=1,
        readonly=True,
        required=True,
        help="Type of the constraint: `f` for a foreign key, `u` for other constraints.",
    )

    _module_name_uniq = models.Constraint(
        "UNIQUE (name, module)",
        "Constraints with the same name are unique per module.",
    )

    def unlink(self) -> bool:
        self.check_access("unlink")
        owners = _get_owner_ids_by_name(self)
        _debug.lifecycle("unlink_constraints", count=len(self), names=len(owners))

        for data in self.sorted(key="id", reverse=True):
            name = data.name
            if not owners[name].issubset(self._ids):
                _debug.logic("constraint_kept_shared_owner", name=name)
                continue

            hname = normalize_identifier(name)
            if data.type not in ("f", "u", "i"):
                _debug.logic("constraint_kept_unknown_type", name=name, type=data.type)
                continue

            tables = [
                table
                for (table,) in self.env.execute_query(
                    SQL(
                        """SELECT cl.relname
                    FROM pg_constraint cs
                    JOIN pg_class cl
                    ON (cs.conrelid = cl.oid)
                    WHERE cs.conname = %s
                    AND cl.relnamespace = current_schema::regnamespace
                    """,
                        hname,
                    )
                )
            ]
            for table in tables:
                _debug.lifecycle("constraint_dropped", name=name, table=table)
                self.env.execute_query(
                    SQL(
                        "ALTER TABLE %s DROP CONSTRAINT %s",
                        SQL.identifier(table),
                        SQL.identifier(hname),
                    )
                )
                _logger.info(
                    "Dropped CONSTRAINT %s@%s (table %s)",
                    name,
                    data.model.model,
                    table,
                )
            if not tables:
                _debug.lifecycle("index_dropped", name=name)
                self.env.execute_query(
                    SQL("DROP INDEX IF EXISTS %s", SQL.identifier(hname))
                )
                _logger.info("Dropped INDEX %s@%s", name, data.model.model)

        return super().unlink()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=constraint.name + "_copy")
            for constraint, vals in zip(self, vals_list, strict=True)
        ]

    def _reflect_constraint(
        self,
        model: Any,
        conname: str,
        type: str,
        definition: str,
        module: str,
        message: str | None = None,
    ) -> Self | None:
        if not module:
            _debug.logic("reflect_constraint.skipped", name=conname, reason="no_module")
            return None
        if type not in ("f", "u", "i"):
            _debug.logic(
                "reflect_constraint.rejected", name=conname, reason="invalid_type"
            )
            raise ValueError(
                f"Invalid constraint type {type!r}: expected 'f', 'u', or 'i'."
            )
        rows = self.env.execute_query_dict(
            SQL(
                """SELECT c.id, type, definition, message->'en_US' as message
            FROM ir_model_constraint c, ir_module_module m
            WHERE c.module = m.id AND c.name = %s AND m.name = %s
            """,
                conname,
                module,
            )
        )
        if not rows:
            _debug.lifecycle(
                "constraint_inserted", name=conname, module=module, type=type
            )
            [[cons_id]] = self.env.execute_query(
                SQL(
                    """
                INSERT INTO ir_model_constraint
                    (name, create_date, write_date, create_uid, write_uid, module, model, type, definition, message)
                VALUES (%s,
                        now() AT TIME ZONE 'UTC',
                        now() AT TIME ZONE 'UTC',
                        %s, %s,
                        (SELECT id FROM ir_module_module WHERE name=%s),
                        (SELECT id FROM ir_model WHERE model=%s),
                        %s, %s, %s)
                RETURNING id
                """,
                    conname,
                    self.env.uid,
                    self.env.uid,
                    module,
                    model._name,
                    type,
                    definition,
                    Json({"en_US": message}),
                )
            )
            return self.browse(cons_id)
        [cons] = rows
        cons_id = cons.pop("id")
        if cons != {"type": type, "definition": definition, "message": message}:
            _debug.lifecycle(
                "constraint_updated", name=conname, module=module, type=type
            )
            self.env.execute_query(
                SQL(
                    """
                UPDATE ir_model_constraint
                SET write_date=now() AT TIME ZONE 'UTC',
                    write_uid = %s, type = %s, definition = %s, message = %s
                WHERE id = %s""",
                    self.env.uid,
                    type,
                    definition,
                    Json({"en_US": message}),
                    cons_id,
                )
            )
            return self.browse(cons_id)
        _debug.logic("constraint_unchanged", name=conname, module=module)
        return None

    def _reflect_constraints(self, model_names: list[str]) -> None:
        expected = self._prepare_expected_constraints(model_names)
        if not expected:
            _debug.logic("reflect_constraints.skipped", models=len(model_names))
            return

        changed = self._get_changed_constraints(expected)
        cons_ids = self._merge_constraints(changed) if changed else {}
        _debug.pipeline(
            "reflect_constraints",
            models=len(model_names),
            expected=len(expected),
            changed=len(changed),
        )

        data_list = []
        for name, module in expected:
            xml_id = f"{module}.constraint_{name}"
            cons_id = cons_ids.get((name, module))
            if cons_id:
                data_list.append({"xml_id": xml_id, "record": self.browse(cons_id)})
            else:
                self.env["ir.model.data"]._load_xmlid(xml_id)
        _debug.pipeline(
            "reflect_constraints.xmlids",
            updated=len(data_list),
            loaded=len(expected) - len(data_list),
        )
        if data_list:
            self.env["ir.model.data"]._update_xmlids(data_list)

    def _prepare_expected_constraints(
        self, model_names: list[str]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        expected: dict[tuple[str, str], dict[str, Any]] = {}
        for model_name in model_names:
            model = self.env[model_name]
            for conname, cons in model._table_objects.items():
                module = cons._module
                if not conname or not module:
                    _debug.logic(
                        "expected_constraint.skipped",
                        model=model_name,
                        name=conname,
                        reason="missing_name_or_module",
                    )
                    _logger.warning("Missing module or constraint name for %s", cons)
                    continue
                message = cons.message
                if not isinstance(message, str) or not message:
                    message = None
                expected[(conname, module)] = {
                    "model": model_name,
                    "type": "i" if isinstance(cons, models.Index) else "u",
                    "definition": cons.get_definition(model.pool),
                    "message": message,
                }
        return expected

    def _get_changed_constraints(
        self, expected: dict[tuple[str, str], dict[str, Any]]
    ) -> dict[tuple[str, str], dict[str, Any]]:
        existing = {
            (name, module): row
            for name, module, *row in self.env.execute_query(
                SQL(
                    """SELECT c.name, m.name, c.type, c.definition,
                              c.message->>'en_US'
                       FROM ir_model_constraint c
                       JOIN ir_module_module m ON c.module = m.id
                       WHERE c.name = ANY(%s)""",
                    list({name for name, _module in expected}),
                )
            )
        }
        return {
            key: vals
            for key, vals in expected.items()
            if existing.get(key) != [vals["type"], vals["definition"], vals["message"]]
        }

    def _merge_constraints(
        self, changed: dict[tuple[str, str], dict[str, Any]]
    ) -> dict[tuple[str, str], int]:
        module_ids = dict(
            self.env.execute_query(
                SQL(
                    "SELECT name, id FROM ir_module_module WHERE name = ANY(%s)",
                    list({module for _name, module in changed}),
                )
            )
        )
        get_model_id = self.env["ir.model"]._get_id
        values = SQL(", ").join(
            SQL(
                "(%s, %s, %s, %s, %s, %s)",
                name,
                module_ids[module],
                get_model_id(vals["model"]),
                vals["type"],
                vals["definition"],
                Jsonb({"en_US": vals["message"]}),
            )
            for (name, module), vals in changed.items()
        )
        result = self.env.execute_query(
            SQL(
                """
                MERGE INTO ir_model_constraint t
                USING (VALUES %(values)s)
                    AS s(name, module, model, type, definition, message)
                ON t.name = s.name AND t.module = s.module
                WHEN MATCHED THEN
                    UPDATE SET write_date = now() AT TIME ZONE 'UTC',
                               write_uid = %(uid)s,
                               type = s.type,
                               definition = s.definition,
                               message = s.message
                WHEN NOT MATCHED THEN
                    INSERT (name, module, model, type, definition, message,
                            create_date, write_date, create_uid, write_uid)
                    VALUES (s.name, s.module, s.model, s.type, s.definition,
                            s.message,
                            now() AT TIME ZONE 'UTC',
                            now() AT TIME ZONE 'UTC',
                            %(uid)s, %(uid)s)
                RETURNING NEW.id, NEW.name, NEW.module
                """,
                values=values,
                uid=self.env.uid,
            )
        )
        module_names = {mid: mname for mname, mid in module_ids.items()}
        _debug.perf.count("merge_constraints", changed=len(changed), merged=len(result))
        return {
            (name, module_names[module_id]): cons_id
            for cons_id, name, module_id in result
        }


class IrModelRelation(models.Model):
    _name = "ir.model.relation"
    _is_registry_metadata = True
    _description = "Relation Model"
    _allow_sudo_commands = False

    name = fields.Char(
        string="Relation Name",
        index=True,
        required=True,
        help="PostgreSQL table name implementing a many2many relation.",
    )
    model = fields.Many2one(
        comodel_name="ir.model",
        index=True,
        required=True,
        ondelete="cascade",
    )
    module = fields.Many2one(
        comodel_name="ir.module.module",
        index=True,
        required=True,
        ondelete="cascade",
    )

    def _uninstall_module_data(self) -> None:
        if not self.env.is_system():
            _debug.logic(
                "uninstall_relations.rejected", uid=self.env.uid, reason="not_system"
            )
            raise AccessError(
                _("Administrator access is required to uninstall a module")
            )

        owners = _get_owner_ids_by_name(self)

        to_drop = OrderedSet()
        for data in self.sorted(key="id", reverse=True):
            name = data.name
            if not owners[name].issubset(self._ids):
                _debug.logic("relation_kept_shared_owner", name=name)
                continue
            if sql.table_exists(self.env.cr, name):
                to_drop.add(name)

        _debug.lifecycle("uninstall_relations", count=len(self), drop=list(to_drop))
        self.unlink()

        for table in to_drop:
            self.env.cr.execute(SQL("DROP TABLE %s CASCADE", SQL.identifier(table)))
            _logger.info("Dropped table %s", table)

    def _reflect_relations(
        self,
        items: Collection[tuple[str, str, str]],
        *,
        model_tables: Collection[str] = (),
    ) -> None:
        # Older registries could reflect a payload model's table as a disposable
        # Many2many relation. Remove that metadata without uninstalling its table,
        # including on passes which have no new field-owned relations to reflect.
        if model_tables:
            stale = self.search([("name", "in", model_tables)])
            _debug.lifecycle(
                "reflect_relations.model_tables_unlinked",
                tables=len(model_tables),
                stale=len(stale),
            )
            stale.unlink()
        expected: dict[tuple[str, str], str] = {}
        for model_name, table, module in items:
            if table in model_tables:
                continue
            expected.setdefault((table, module), model_name)
        if not expected:
            _debug.logic("reflect_relations.skipped", items=len(items))
            return

        existing = set(
            self.env.execute_query(
                SQL(
                    """SELECT r.name, m.name
                       FROM ir_model_relation r
                       JOIN ir_module_module m ON r.module = m.id
                       WHERE r.name = ANY(%s)""",
                    list({table for table, _module in expected}),
                )
            )
        )
        missing = {key: name for key, name in expected.items() if key not in existing}
        _debug.pipeline(
            "reflect_relations",
            expected=len(expected),
            existing=len(existing),
            missing=len(missing),
        )
        if not missing:
            return

        module_ids = dict(
            self.env.execute_query(
                SQL(
                    "SELECT name, id FROM ir_module_module WHERE name = ANY(%s)",
                    list({module for _table, module in missing}),
                )
            )
        )
        get_model_id = self.env["ir.model"]._get_id
        rows = []
        for (table, module), model_name in missing.items():
            module_id = module_ids.get(module)
            model_id = get_model_id(model_name)
            if module_id is None or model_id is None:
                _debug.logic(
                    "reflect_relations.unresolved",
                    table=table,
                    model=model_name,
                    reason="unknown_module" if module_id is None else "unknown_model",
                )
                _logger.warning(
                    "Cannot reflect m2m table %r of %r: unknown %s",
                    table,
                    model_name,
                    "module " + repr(module) if module_id is None else "model",
                )
                continue
            rows.append(
                SQL(
                    "(%s::varchar, %s::integer, %s::integer)",
                    table,
                    module_id,
                    model_id,
                )
            )
        if not rows:
            _debug.logic("reflect_relations.nothing_to_insert", missing=len(missing))
            return

        _debug.lifecycle("reflect_relations.inserted", rows=len(rows))
        self.env.execute_query(
            SQL(
                """INSERT INTO ir_model_relation
                       (name, module, model,
                        create_date, write_date, create_uid, write_uid)
                   SELECT v.name, v.module, v.model,
                          now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                          %(uid)s, %(uid)s
                     FROM (VALUES %(values)s) AS v(name, module, model)""",
                values=SQL(", ").join(rows),
                uid=self.env.uid,
            )
        )
