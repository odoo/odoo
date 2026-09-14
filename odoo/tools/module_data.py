from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from odoo.db.schema import (
    column_exists,
    get_tables_existing,
    rename_column,
    table_exists,
)
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

if TYPE_CHECKING:
    from typing import Any, Protocol

    from odoo.db import BaseCursor

    class _SqlCursor(Protocol):
        """The four members these helpers touch.

        Narrower than `BaseCursor` on purpose: a migration script or a test can hand
        them anything that answers SQL, which is how `tests/test_module_data.py`
        exercises the statements without a database.
        """

        rowcount: int

        def execute(self, query: Any, params: Any = None) -> Any: ...
        def fetchall(self) -> list[tuple[Any, ...]]: ...
        def fetchone(self) -> tuple[Any, ...] | None: ...


_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def adopt_xmlids(
    cr: _SqlCursor,
    from_module: str,
    to_module: str,
    names: Iterable[str],
    renamed: Mapping[str, str] | None = None,
) -> int:
    moved = 0
    targets = {**dict.fromkeys(names), **(renamed or {})}
    for old, new in targets.items():
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET module = %s, name = %s "
                "WHERE module = %s AND name = %s",
                to_module,
                new or old,
                from_module,
                old,
            )
        )
        moved += cr.rowcount
    _debug.lifecycle(
        "module_data.xmlids_adopted",
        from_module=from_module,
        to_module=to_module,
        requested=len(targets),
        moved=moved,
    )
    if moved:
        _logger.info("%s adopted %d record(s) from %s", to_module, moved, from_module)
    return moved


def remove_xmlid_records(cr: BaseCursor, module: str, names: Iterable[str]) -> int:
    cr.execute(
        SQL(
            "SELECT model, res_id FROM ir_model_data "
            "WHERE module = %s AND name = ANY(%s)",
            module,
            list(names),
        )
    )
    by_model: dict[str, list[int]] = defaultdict(list)
    for model, res_id in cr.fetchall():
        by_model[model].append(res_id)
    tables = {model: model.replace(".", "_") for model in by_model}
    existing = set(get_tables_existing(cr, tables.values()))
    deleted = 0
    for model, ids in by_model.items():
        if tables[model] not in existing:
            _debug.logic(
                "module_data.records_table_missing",
                module=module,
                model=model,
                records=len(ids),
            )
            continue
        cr.execute(
            SQL("DELETE FROM %s WHERE id = ANY(%s)", SQL.identifier(tables[model]), ids)
        )
        deleted += cr.rowcount
    cr.execute(
        SQL(
            "DELETE FROM ir_model_data WHERE module = %s AND name = ANY(%s)",
            module,
            list(names),
        )
    )
    _debug.lifecycle(
        "module_data.xmlid_records_removed",
        module=module,
        models=sorted(by_model),
        deleted=deleted,
        xmlids=cr.rowcount,
    )
    return deleted


def retire_empty_module(cr: _SqlCursor, module: str) -> None:
    cr.execute(SQL("SELECT 1 FROM ir_model_data WHERE module = %s LIMIT 1", module))
    if cr.fetchone():
        _debug.logic("module_data.module_kept", module=module, reason="has_xmlids")
        return
    cr.execute(
        SQL(
            "UPDATE ir_module_module SET state = 'uninstalled', db_version = NULL "
            "WHERE name = %s AND state != 'uninstalled'",
            module,
        )
    )
    retired = cr.rowcount > 0
    cr.execute(
        SQL(
            "DELETE FROM ir_module_module_dependency "
            "WHERE module_id = (SELECT id FROM ir_module_module WHERE name = %s)",
            module,
        )
    )
    _debug.lifecycle("module_data.module_retired", module=module, retired=retired)
    if retired:
        _logger.info("%s retired: every record it shipped now lives elsewhere", module)


READONLY_FORERUNNERS: Mapping[str, str] = {
    "stock_group_readonly": "stock",
    "sale_group_readonly": "sale",
    "purchase_group_readonly": "purchase",
    "mrp_group_readonly": "mrp",
}
READONLY_MERGED_MODULE = "group_readonly"
_ACCESS_PREFIX = "access_"
_READONLY_SUFFIX = "_readonly"


def _readonly_merged_name(name: str, domain: str) -> str:
    if name.startswith(_ACCESS_PREFIX) and name.endswith(_READONLY_SUFFIX):
        return f"{name[: -len(_READONLY_SUFFIX)]}_{domain}{_READONLY_SUFFIX}"
    return name


def absorb_readonly_forerunners(cr: _SqlCursor) -> int:
    moved = 0
    for module, domain in READONLY_FORERUNNERS.items():
        cr.execute(SQL("SELECT id, name FROM ir_model_data WHERE module = %s", module))
        rows = cr.fetchall()
        for row_id, name in rows:
            cr.execute(
                SQL(
                    "UPDATE ir_model_data SET module = %s, name = %s WHERE id = %s",
                    READONLY_MERGED_MODULE,
                    _readonly_merged_name(name, domain),
                    row_id,
                )
            )
        moved += len(rows)
        if rows:
            _logger.info(
                "%s absorbed %d record(s) from %s",
                READONLY_MERGED_MODULE,
                len(rows),
                module,
            )
            retire_empty_module(cr, module)
    return moved


_EXPRESSION_SOURCES = (
    ("ir_ui_view", ("arch_db",), (), "model", False),
    (
        "mail_template",
        ("body_html", "subject"),
        (
            "email_from",
            "email_to",
            "email_cc",
            "partner_to",
            "reply_to",
            "scheduled_date",
        ),
        "model_id",
        True,
    ),
    ("ir_act_server", (), ("code",), "model_id", True),
    ("ir_filters", (), ("domain", "context", "sort"), "model_id", False),
    ("ir_act_window", (), ("domain", "context"), "res_model", False),
)

_RENAMEABLE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_.]*\Z")
_REPLACEMENT = re.compile(r"\A[A-Za-z_][A-Za-z0-9_.()]*\Z")


def rename_in_stored_expressions(
    cr: BaseCursor,
    old: str,
    new: str,
    *,
    model: str | None = None,
) -> int:
    if not _RENAMEABLE.match(old) or not _REPLACEMENT.match(new):
        raise ValueError(f"cannot rewrite {old!r} to {new!r}: unsupported characters")
    if model is None and "." not in old:
        raise ValueError(f"{old!r} is a bare field name and needs model= to scope it")

    pattern = r"\y%s\y" % old.replace(".", r"\.")
    tables = set(get_tables_existing(cr, [name for name, *_ in _EXPRESSION_SOURCES]))
    rewritten = 0
    for (
        table,
        jsonb_columns,
        text_columns,
        scope_column,
        scope_is_id,
    ) in _EXPRESSION_SOURCES:
        if table not in tables:
            continue
        scope = SQL("")
        if model is not None:
            scope = SQL(
                " AND %s = (SELECT id FROM ir_model WHERE model = %s)"
                if scope_is_id
                else " AND %s = %s",
                SQL.identifier(scope_column),
                model,
            )
        assignments = SQL(", ").join(
            SQL(
                "%s = regexp_replace(%s::text, %s, %s, 'g')%s",
                SQL.identifier(column),
                SQL.identifier(column),
                pattern,
                new,
                SQL("::jsonb") if is_jsonb else SQL(""),
            )
            for column, is_jsonb in (
                *((name, True) for name in jsonb_columns),
                *((name, False) for name in text_columns),
            )
        )
        guard = SQL(" OR ").join(
            SQL("%s::text ~ %s", SQL.identifier(column), pattern)
            for column in (*jsonb_columns, *text_columns)
        )
        cr.execute(
            SQL(
                "UPDATE %s SET %s WHERE (%s)%s",
                SQL.identifier(table),
                assignments,
                guard,
                scope,
            )
        )
        rewritten += cr.rowcount
        _debug.perf.count(
            "module_data.expressions_rewritten",
            table=table,
            old=old,
            new=new,
            model=model,
            rows=cr.rowcount,
        )
    if rewritten:
        _logger.info(
            "renamed %s to %s in %d stored expression(s)%s",
            old,
            new,
            rewritten,
            f" of {model}" if model else "",
        )
    return rewritten


CRON_ACTION_SUFFIX = "_ir_actions_server"


def rehome_cron_xmlids(
    cr: _SqlCursor,
    from_module: str,
    to_module: str,
    renamed: Mapping[str, str],
) -> int:
    """Move `ir.cron` xmlids together with their server-action companions.

    Loading a cron from XML registers two xmlids, not one: the cron itself and
    the `ir.actions.server` it delegates to, named `<cron xmlid>_ir_actions_server`.
    A migration that renames or rehomes only the first leaves the second owned by
    a module that no longer declares it, and nothing goes wrong until that module
    is next in `updated_modules`. Then `ir.model.data._process_end()` reads the
    companion as stale and deletes it, which
    `ir_cron_ir_actions_server_id_fkey` refuses because it is `RESTRICT`.

    That failure lands in the stale-data sweep, which runs *after* every module
    has upgraded and committed, so an otherwise complete `-u all` exits non-zero
    with the whole database already migrated. Renaming the pair together is what
    keeps the sweep from ever seeing a half-moved cron.
    """
    pairs = {}
    for old, new in renamed.items():
        pairs[old] = new
        pairs[old + CRON_ACTION_SUFFIX] = new + CRON_ACTION_SUFFIX
    return adopt_xmlids(cr, from_module, to_module, (), pairs)


def repair_orphaned_cron_actions(cr: _SqlCursor) -> int:
    """Re-point companions left behind by a cron rename that moved only the cron.

    Only the companions that still drive a live `ir.cron` are repaired, because
    those are the ones whose deletion the foreign key refuses. The companion is
    re-pointed at the module and name its cron now answers to, never deleted: the
    server action carries the cron's `state`, `code` and `model_id`, so dropping
    it would take the schedule with it.

    A companion that drives no cron is ordinary dead data and is left alone --
    the owning module's own sweep removes it correctly, and a module whose sweep
    can never run is a different defect that has to name its rows deliberately.

    Idempotent, and safe on a database that has nothing to repair.
    """
    cr.execute(
        SQL(
            """
            SELECT stale.id, stale.module, stale.name, cron_data.module, cron_data.name
              FROM ir_model_data stale
              JOIN ir_cron cron ON cron.ir_actions_server_id = stale.res_id
              JOIN ir_model_data cron_data
                ON cron_data.model = 'ir.cron' AND cron_data.res_id = cron.id
             WHERE stale.model = 'ir.actions.server'
               AND stale.name LIKE %s
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data owner
                    WHERE owner.model = 'ir.cron'
                      AND owner.module = stale.module
                      AND owner.name = left(stale.name, -%s)
               )
            """,
            f"%{CRON_ACTION_SUFFIX}",
            len(CRON_ACTION_SUFFIX),
        )
    )
    repaired = 0
    for data_id, old_module, old_name, module, cron_name in cr.fetchall():
        name = cron_name + CRON_ACTION_SUFFIX
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET module = %s, name = %s "
                "WHERE id = %s AND NOT EXISTS ("
                "    SELECT 1 FROM ir_model_data taken"
                "     WHERE taken.module = %s AND taken.name = %s AND taken.id != %s"
                ")",
                module,
                name,
                data_id,
                module,
                name,
                data_id,
            )
        )
        _debug.logic(
            "module_data.cron_action_repointed",
            xmlid=f"{old_module}.{old_name}",
            target=f"{module}.{name}",
            applied=bool(cr.rowcount),
        )
        if cr.rowcount:
            repaired += 1
            _logger.info(
                "re-pointed %s.%s to %s.%s, the cron it actually drives",
                old_module,
                old_name,
                module,
                name,
            )
    return repaired


def rename_field(
    cr: BaseCursor,
    model: str,
    old: str,
    new: str,
    *,
    values: Mapping[str, str] | None = None,
) -> None:
    # A stored field renamed in place, not dropped and re-added: the column keeps
    # its data, and the `ir.model.fields` row keeps its id -- which is what every
    # `mail.tracking.value`, export template and access record points at, so a
    # drop-and-add would delete that history with the old row. Its external id
    # and, for a Selection, the value rows and their external ids follow.
    table = model.replace(".", "_")
    column_renamed = column_exists(cr, table, old) and not column_exists(cr, table, new)
    _debug.lifecycle(
        "module_data.rename_field",
        model=model,
        old=old,
        new=new,
        column_renamed=column_renamed,
        values=len(values or {}),
    )
    if column_renamed:
        rename_column(cr, table, old, new)
        if values:
            for old_value, new_value in values.items():
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE %s = %s",
                        SQL.identifier(table),
                        SQL.identifier(new),
                        new_value,
                        SQL.identifier(new),
                        old_value,
                    )
                )

    cr.execute(
        SQL(
            "SELECT id FROM ir_model_fields WHERE model = %s AND name = %s",
            model,
            old,
        )
    )
    row = cr.fetchone()
    if row is None:
        _debug.logic(
            "module_data.rename_field_skipped", model=model, old=old, reason="no_row"
        )
        return
    field_id = row[0]
    cr.execute(
        SQL(
            "SELECT 1 FROM ir_model_fields WHERE model = %s AND name = %s",
            model,
            new,
        )
    )
    if cr.fetchone():
        _debug.logic(
            "module_data.rename_field_skipped",
            model=model,
            old=old,
            reason="target_exists",
        )
        return
    cr.execute(SQL("UPDATE ir_model_fields SET name = %s WHERE id = %s", new, field_id))
    xmlid_model = table
    cr.execute(
        SQL(
            "UPDATE ir_model_data SET name = %s "
            "WHERE model = 'ir.model.fields' AND name = %s",
            f"field_{xmlid_model}__{new}",
            f"field_{xmlid_model}__{old}",
        )
    )
    if not values:
        return
    for old_value, new_value in values.items():
        cr.execute(
            SQL(
                "UPDATE ir_model_fields_selection SET value = %s "
                "WHERE field_id = %s AND value = %s",
                new_value,
                field_id,
                old_value,
            )
        )
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET name = %s "
                "WHERE model = 'ir.model.fields.selection' AND name = %s",
                f"selection__{xmlid_model}__{new}__{new_value}",
                f"selection__{xmlid_model}__{old}__{old_value}",
            )
        )
    _logger.info("renamed %s.%s to %s", model, old, new)


MODEL_NAME_COLUMNS = (
    "model",
    "res_model",
    "model_name",
    "src_model",
    "parent_res_model",
    "relation",
    "res_model_name",
    "alias_model",
    "resource",
)
_MODEL_EXPRESSION_COLUMNS = (
    ("ir_act_window", ("domain", "context")),
    ("ir_act_server", ("code",)),
    ("ir_filters", ("domain", "context", "sort")),
    ("ir_ui_view", ("arch_db",)),
    ("ir_embedded_actions", ("domain", "context")),
)


def rename_model(cr: BaseCursor, old: str, new: str) -> dict[str, str]:
    # Exact names only, never LIKE '%old%': `crm_team` is a prefix of
    # `crm_team_member`, and a substring rewrite renames both.
    old_table, new_table = old.replace(".", "_"), new.replace(".", "_")
    relations = _rename_model_relations(cr, old, old_table, new_table)
    _rename_table_with_dependents(cr, old_table, new_table)
    _rewrite_model_registry(cr, old, new, old_table, new_table)
    _repoint_model_name_columns(cr, old, new)
    _rewrite_reference_values(cr, old, new)
    _rewrite_quoted_model_names(cr, old, new)
    _debug.lifecycle(
        "module_data.rename_model", old=old, new=new, relations=len(relations)
    )
    _logger.info(
        "renamed model %s to %s, with %d join table(s)%s",
        old,
        new,
        len(relations),
        "".join(f", {a} -> {b}" for a, b in relations.items()),
    )
    return relations


def _rename_table_with_dependents(cr: BaseCursor, old: str, new: str) -> bool:
    if not table_exists(cr, old) or table_exists(cr, new):
        return False
    cr.execute(
        SQL("ALTER TABLE %s RENAME TO %s", SQL.identifier(old), SQL.identifier(new))
    )
    cr.execute(
        SQL(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = %s::regclass AND conname LIKE %s",
            new,
            old.replace("_", "\\_") + "\\_%",
        )
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER TABLE %s RENAME CONSTRAINT %s TO %s",
                SQL.identifier(new),
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        SQL(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema() "
            "AND tablename = %s AND indexname LIKE %s",
            new,
            old.replace("_", "\\_") + "\\_%",
        )
    )
    for (name,) in cr.fetchall():
        cr.execute(
            SQL(
                "ALTER INDEX %s RENAME TO %s",
                SQL.identifier(name),
                SQL.identifier(new + name[len(old) :]),
            )
        )
    cr.execute(
        SQL(
            "SELECT 1 FROM pg_sequences WHERE schemaname = current_schema() "
            "AND sequencename = %s",
            old + "_id_seq",
        )
    )
    if cr.fetchone():
        cr.execute(
            SQL(
                "ALTER SEQUENCE %s RENAME TO %s",
                SQL.identifier(old + "_id_seq"),
                SQL.identifier(new + "_id_seq"),
            )
        )
    return True


def _rename_model_relations(
    cr: BaseCursor, old: str, old_table: str, new_table: str
) -> dict[str, str]:
    cr.execute(
        SQL(
            "SELECT DISTINCT model, relation, relation_table, column1, column2 "
            "FROM ir_model_fields WHERE ttype = 'many2many' "
            "AND relation_table IS NOT NULL AND (model = %s OR relation = %s)",
            old,
            old,
        )
    )
    old_column, new_column = f"{old_table}_id", f"{new_table}_id"
    renamed: dict[str, str] = {}
    for model, relation, relation_table, column1, column2 in cr.fetchall():
        tables = [model.replace(".", "_"), relation.replace(".", "_")]
        target = relation_table
        if relation_table == "_".join(sorted(tables)) + "_rel":
            moved = [new_table if t == old_table else t for t in tables]
            target = "_".join(sorted(moved)) + "_rel"
        if target != relation_table and table_exists(cr, relation_table):
            if table_exists(cr, target):
                raise ValueError(
                    f"both {relation_table} and {target} exist; refusing to guess "
                    "which one holds the links"
                )
            _rename_table_with_dependents(cr, relation_table, target)
            renamed[relation_table] = target
        if table_exists(cr, target):
            for column in (column1, column2):
                if column == old_column and not column_exists(cr, target, new_column):
                    rename_column(cr, target, old_column, new_column)
        cr.execute(
            SQL(
                "UPDATE ir_model_fields SET relation_table = %s, "
                "column1 = CASE WHEN column1 = %s THEN %s ELSE column1 END, "
                "column2 = CASE WHEN column2 = %s THEN %s ELSE column2 END "
                "WHERE ttype = 'many2many' AND relation_table = %s",
                target,
                old_column,
                new_column,
                old_column,
                new_column,
                relation_table,
            )
        )
        if target != relation_table:
            cr.execute(
                SQL(
                    "UPDATE ir_model_relation SET name = %s WHERE name = %s",
                    target,
                    relation_table,
                )
            )
    return renamed


def _rewrite_model_registry(
    cr: BaseCursor, old: str, new: str, old_table: str, new_table: str
) -> None:
    for statement in (
        "UPDATE ir_model SET model = %s WHERE model = %s",
        "UPDATE ir_model_fields SET model = %s WHERE model = %s",
        "UPDATE ir_model_fields SET relation = %s WHERE relation = %s",
    ):
        cr.execute(SQL(statement, new, old))
    owned = SQL("(SELECT id FROM ir_model WHERE model = %s)", new)
    cr.execute(
        SQL(
            "UPDATE ir_model_constraint SET name = %s || substring(name from %s) "
            "WHERE model = %s AND name LIKE %s",
            new_table + "_",
            len(old_table) + 2,
            owned,
            old_table.replace("_", "\\_") + "\\_%",
        )
    )
    cr.execute(
        SQL(
            "UPDATE ir_model_data SET name = %s WHERE model = 'ir.model' AND name = %s",
            f"model_{new_table}",
            f"model_{old_table}",
        )
    )
    for prefix, xmlid_model, source, scope in (
        ("field_{}__", "ir.model.fields", "ir_model_fields", "model_id"),
        ("selection__{}__", "ir.model.fields.selection", None, None),
        ("model_inherit__{}__", "ir.model.inherit", "ir_model_inherit", "model_id"),
        ("constraint_{}_", "ir.model.constraint", "ir_model_constraint", "model"),
    ):
        old_prefix, new_prefix = prefix.format(old_table), prefix.format(new_table)
        restrict = (
            SQL(
                " AND res_id IN (SELECT id FROM %s WHERE %s = %s)",
                SQL.identifier(source),
                SQL.identifier(scope),
                owned,
            )
            if source
            else SQL()
        )
        cr.execute(
            SQL(
                "UPDATE ir_model_data SET name = %s || substring(name from %s) "
                "WHERE model = %s AND name LIKE %s%s",
                new_prefix,
                len(old_prefix) + 1,
                xmlid_model,
                old_prefix.replace("_", "\\_") + "%",
                restrict,
            )
        )


def _repoint_model_name_columns(cr: BaseCursor, old: str, new: str) -> None:
    cr.execute(
        SQL(
            "SELECT c.table_name, c.column_name FROM information_schema.columns c "
            "JOIN information_schema.tables t ON t.table_schema = c.table_schema "
            "AND t.table_name = c.table_name "
            "WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE' "
            "AND c.data_type IN ('character varying', 'text') "
            "AND c.column_name = ANY(%s)",
            list(MODEL_NAME_COLUMNS),
        )
    )
    for table, column in cr.fetchall():
        cr.execute(
            SQL(
                "UPDATE %s SET %s = %s WHERE %s = %s",
                SQL.identifier(table),
                SQL.identifier(column),
                new,
                SQL.identifier(column),
                old,
            )
        )


def _rewrite_reference_values(cr: BaseCursor, old: str, new: str) -> None:
    cr.execute(
        "SELECT model, name FROM ir_model_fields WHERE ttype = 'reference' AND store"
    )
    for model, field in cr.fetchall():
        table = model.replace(".", "_")
        if not column_exists(cr, table, field):
            continue
        cr.execute(
            SQL(
                "UPDATE %s SET %s = %s || substring(%s from %s) WHERE %s LIKE %s",
                SQL.identifier(table),
                SQL.identifier(field),
                new + ",",
                SQL.identifier(field),
                len(old) + 2,
                SQL.identifier(field),
                old.replace("_", "\\_") + ",%",
            )
        )


def _rewrite_quoted_model_names(cr: BaseCursor, old: str, new: str) -> None:
    existing = set(get_tables_existing(cr, [t for t, _ in _MODEL_EXPRESSION_COLUMNS]))
    for table, columns in _MODEL_EXPRESSION_COLUMNS:
        if table not in existing:
            continue
        for column in columns:
            if not column_exists(cr, table, column):
                continue
            for quote in ("'", '"'):
                needle, replacement = f"{quote}{old}{quote}", f"{quote}{new}{quote}"
                rewritten = SQL(
                    "replace(%s::text, %s, %s)",
                    SQL.identifier(column),
                    needle,
                    replacement,
                )
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE position(%s in %s::text) > 0",
                        SQL.identifier(table),
                        SQL.identifier(column),
                        SQL("%s::jsonb", rewritten)
                        if column == "arch_db"
                        else rewritten,
                        needle,
                        SQL.identifier(column),
                    )
                )
