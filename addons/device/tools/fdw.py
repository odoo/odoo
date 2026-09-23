"""Schema management for a log table that lives in another database.

A data-log table may be a ``postgres_fdw`` foreign table pointing at a
dedicated database. The ORM then cannot manage its schema (``ALTER FOREIGN
TABLE`` does not create indexes or constraints) and Postgres cannot enforce
the foreign keys that tie the log to ``device_device`` and ``res_company``.
This module replaces both: it mirrors the model's columns and indexes onto the
remote table through ``dblink``, and installs row triggers on the local side
that do what the foreign keys used to do.
"""

import logging
import re

from odoo.db import schema as sql
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def is_foreign(cr, table: str) -> bool:
    return sql.get_table_kind(cr, table) == sql.TableKind.Foreign


def foreign_server(cr, table: str) -> str | None:
    cr.execute(
        SQL(
            """
            SELECT s.srvname
              FROM pg_foreign_table ft
              JOIN pg_class c ON c.oid = ft.ftrelid
              JOIN pg_foreign_server s ON s.oid = ft.ftserver
             WHERE c.relname = %s
               AND c.relnamespace = current_schema::regnamespace
            """,
            table,
        )
    )
    row = cr.fetchone()
    return row[0] if row else None


def dblink_available(cr) -> bool:
    cr.execute("SELECT 1 FROM pg_extension WHERE extname = 'dblink'")
    return bool(cr.fetchone())


def remote_exec(cr, server: str, statement: str) -> None:
    """Run one DDL statement on the foreign server through ``dblink``.

    The foreign server name doubles as the ``dblink`` connection name, so the
    same user mapping ``postgres_fdw`` uses is reused and no password lives in
    Python.
    """
    cr.execute(SQL("SELECT dblink_exec(%s, %s)", server, statement))


def remote_index_exists(cr, server: str, indexname: str) -> bool:
    cr.execute(
        SQL(
            "SELECT * FROM dblink(%s, %s) AS t(n int)",
            server,
            f"SELECT 1 FROM pg_indexes WHERE indexname = '{indexname}'",
        )
    )
    return bool(cr.fetchone())


def missing_columns(model, existing: dict) -> list[tuple[str, str]]:
    """Stored columns the model declares that the table does not have.

    :param dict existing: ``sql.get_table_columns`` output for the table
    :return: ``(column name, SQL type)`` pairs in column order
    """
    return [
        (field.name, field.column_type[1])
        for field in sorted(model._fields.values(), key=lambda f: f.column_order)
        if field.store and field.column_type and field.name not in existing
    ]


def checked_references(model) -> list[tuple[str, str, bool]]:
    """Many2one columns whose target the triggers must verify.

    :return: ``(column, referenced table, required)`` for every field named in
             the model's ``_fdw_checked_references``
    """
    refs = []
    for name in model._fdw_checked_references:
        field = model._fields[name]
        # A projected field has no column; checking NEW.<name> would fail
        # every insert.
        if not field.store:
            continue
        refs.append((name, model.env[field.comodel_name]._table, bool(field.required)))
    return refs


def trigger_statements(
    table: str,
    references: list[tuple[str, str, bool]],
    pointers: list[tuple[str, str]],
) -> list[str]:
    """DDL that stands in for the foreign keys a foreign table cannot carry.

    Three guards, all row-level and idempotent to (re)install:

    - ``BEFORE INSERT`` on the log table: every checked reference must exist
      locally. Insert-only on purpose — an ``UPDATE OF`` trigger would make
      ``postgres_fdw`` fetch and update row by row instead of shipping the
      statement (measured 3.5 s vs 0.4 s per 20k rows).
    - ``AFTER DELETE`` on the log table: pointers held by other tables are set
      to NULL, like ``ON DELETE SET NULL`` did.
    - ``BEFORE DELETE`` on each referenced table: a row with history cannot be
      deleted, like ``ON DELETE RESTRICT`` — archiving is the supported path.

    :param str table: the log table name
    :param list references: ``checked_references`` output
    :param list pointers: ``(table, column)`` pairs pointing at the log's id
    :return: SQL statements, in execution order
    """
    stmts = []

    checks = []
    for column, ref_table, _required in references:
        checks.append(
            f"IF NEW.{column} IS NOT NULL AND NOT EXISTS "
            f"(SELECT 1 FROM {ref_table} WHERE id = NEW.{column}) THEN\n"
            f"    RAISE EXCEPTION USING ERRCODE = 'foreign_key_violation', "
            f"MESSAGE = '{table}.{column}=' || NEW.{column} "
            f"|| ' does not exist in {ref_table}';\n"
            f"  END IF;"
        )
    if checks:
        fn = f"{table}_fdw_fk_check"
        body = "\n  ".join(checks)
        stmts.append(
            f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$\n"
            f"BEGIN\n  {body}\n  RETURN NEW;\nEND $$"
        )
        stmts.append(f"DROP TRIGGER IF EXISTS trg_{fn} ON {table}")
        stmts.append(
            f"CREATE TRIGGER trg_{fn} BEFORE INSERT ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {fn}()"
        )

    if pointers:
        fn = f"{table}_fdw_unlink_pointer"
        body = "\n  ".join(
            f"UPDATE {ptr_table} SET {ptr_column} = NULL WHERE {ptr_column} = OLD.id;"
            for ptr_table, ptr_column in pointers
        )
        stmts.append(
            f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$\n"
            f"BEGIN\n  {body}\n  RETURN OLD;\nEND $$"
        )
        stmts.append(f"DROP TRIGGER IF EXISTS trg_{fn} ON {table}")
        stmts.append(
            f"CREATE TRIGGER trg_{fn} AFTER DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {fn}()"
        )

    for column, ref_table, _required in references:
        fn = f"{ref_table}_fdw_no_delete_{table}"
        stmts.append(
            f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$\n"
            f"BEGIN\n"
            f"  IF EXISTS (SELECT 1 FROM {table} WHERE {column} = OLD.id LIMIT 1) THEN\n"
            f"    RAISE EXCEPTION USING ERRCODE = 'foreign_key_violation', "
            f"MESSAGE = '{ref_table} ' || OLD.id "
            f"|| ' still has rows in {table}; archive it instead';\n"
            f"  END IF;\n"
            f"  RETURN OLD;\nEND $$"
        )
        stmts.append(f"DROP TRIGGER IF EXISTS trg_{fn} ON {ref_table}")
        stmts.append(
            f"CREATE TRIGGER trg_{fn} BEFORE DELETE ON {ref_table} "
            f"FOR EACH ROW EXECUTE FUNCTION {fn}()"
        )
    return stmts


def drop_pointer_foreign_keys(cr, pointers: list[tuple[str, str]]) -> list[str]:
    """Drop the FK constraints that used to protect the pointer columns.

    After the log table is swapped for a foreign one, a leftover constraint
    still references the renamed local table by OID, so every new pointer
    value would fail its check.

    :return: names of the constraints dropped
    """
    dropped = []
    for ptr_table, ptr_column in pointers:
        cr.execute(
            SQL(
                """
                SELECT con.conname
                  FROM pg_constraint con
                  JOIN pg_attribute att
                    ON att.attrelid = con.conrelid AND att.attnum = ANY(con.conkey)
                 WHERE con.contype = 'f'
                   AND con.conrelid = %s::regclass
                   AND att.attname = %s
                """,
                ptr_table,
                ptr_column,
            )
        )
        for (conname,) in cr.fetchall():
            sql.drop_constraint(cr, ptr_table, conname)
            dropped.append(conname)
    return dropped


def sync_foreign_schema(model) -> None:
    """Bring the remote table and the local guards in line with the model.

    Called from ``_auto_init`` instead of the ORM's own schema pass when the
    model's table is foreign. Columns and indexes are created on the remote
    server; the foreign table then learns the new columns; the triggers are
    (re)installed locally.

    :raises UserError: when ``dblink`` is missing, listing the DDL that would
                       have run so it can be applied by hand
    """
    cr = model.env.cr
    table = model._table
    server = foreign_server(cr, table)
    existing = sql.get_table_columns(cr, table)
    columns = missing_columns(model, existing)

    remote_ddl = [
        f"ALTER TABLE public.{table} ADD COLUMN IF NOT EXISTS {name} {coltype}"
        for name, coltype in columns
    ]
    for obj in model._table_objects.values():
        clause = getattr(obj, "_get_definition_clause", None)
        if clause is None:
            continue
        definition = clause(model.pool)
        if not definition:
            continue
        indexname = obj.get_full_name(model)
        unique = "UNIQUE " if getattr(obj, "unique", False) else ""
        remote_ddl.append(
            f"CREATE {unique}INDEX IF NOT EXISTS {indexname} "
            f"ON public.{table} {definition}"
        )

    if remote_ddl and not dblink_available(cr):
        raise UserError(
            f"{model._name} is backed by foreign table {table!r} but the dblink "
            "extension is not installed, so its schema cannot be synchronised. "
            "Install dblink or run this on the remote database:\n"
            + ";\n".join(remote_ddl)
        )

    for statement in remote_ddl:
        _logger.info("FDW %s: %s", server, statement)
        remote_exec(cr, server, statement)
    for name, coltype in columns:
        cr.execute(
            SQL(
                "ALTER FOREIGN TABLE %s ADD COLUMN %s %s",
                SQL.identifier(table),
                SQL.identifier(name),
                SQL(coltype),  # noqa: E8501  the ORM's own column_type
            )
        )

    pointers = list(model._fdw_pointer_columns)
    for conname in drop_pointer_foreign_keys(cr, pointers):
        _logger.info("FDW %s: dropped pointer constraint %s", table, conname)
    references = checked_references(model)
    for trigger, on_table in stale_guard_triggers(cr, table, references):
        _logger.info("FDW %s: dropped stale guard %s on %s", table, trigger, on_table)
        cr.execute(
            SQL(
                "DROP TRIGGER IF EXISTS %s ON %s",
                SQL.identifier(trigger),
                SQL.identifier(on_table),
            )
        )
    # The statements carry no "%" (messages are built with ||), so SQL() takes
    # them verbatim without a parameter round-trip.
    for statement in trigger_statements(table, references, pointers):
        if _installs_existing_trigger(cr, statement):
            # a DROP/CREATE takes a lock on a table live workers read (GPS
            # ingest), and an upgrade that queues behind one deadlocks
            continue
        cr.execute(SQL(statement))


_TRIGGER_DDL = re.compile(
    r"^(?:DROP TRIGGER IF EXISTS (\w+) ON (\w+)|CREATE TRIGGER (\w+) \w+ \w+ ON (\w+) )"
)


def _installs_existing_trigger(cr, statement: str) -> bool:
    """Whether `statement` drops or creates a guard trigger that is in place.

    A guard's name spells its table, timing and function, so a trigger of
    that name on that table is already the one the statement would install;
    only the function body can change, and CREATE OR REPLACE FUNCTION
    replaces that without touching the table.
    """
    match = _TRIGGER_DDL.match(statement)
    if not match:
        return False
    name = match.group(1) or match.group(3)
    on_table = match.group(2) or match.group(4)
    cr.execute(
        SQL(
            "SELECT 1 FROM pg_trigger WHERE tgname = %s AND tgrelid = to_regclass(%s)",
            name,
            on_table,
        )
    )
    return bool(cr.fetchone())


def stale_guard_triggers(cr, table: str, references) -> list[tuple[str, str]]:
    """Return the guard triggers the model no longer installs.

    :param str table: the log table name
    :param list references: ``checked_references`` output
    :return: ``(trigger, table it is on)`` pairs to drop
    :rtype: list
    """
    # A reference dropped from _fdw_checked_references leaves its
    # <ref>_fdw_no_delete_<table> trigger behind, still querying the log.
    wanted = {
        f"trg_{ref_table}_fdw_no_delete_{table}" for _c, ref_table, _r in references
    }
    cr.execute(
        SQL(
            "SELECT t.tgname, c.relname FROM pg_trigger t"
            " JOIN pg_class c ON c.oid = t.tgrelid"
            " WHERE NOT t.tgisinternal AND t.tgname LIKE %s",
            f"trg\\_%\\_fdw\\_no\\_delete\\_{table}",
        )
    )
    stale = [(name, rel) for name, rel in cr.fetchall() if name not in wanted]
    # A renamed log table keeps its guards under the old name, and their
    # bodies still name the old tables: its insert check fails every insert
    # and its pointer guard every delete. Same for a no-delete guard on a
    # referenced table whose log table no longer exists.
    cr.execute(
        SQL(
            "SELECT t.tgname, c.relname FROM pg_trigger t"
            " JOIN pg_class c ON c.oid = t.tgrelid"
            " WHERE NOT t.tgisinternal AND c.relname = %s"
            " AND (t.tgname LIKE %s OR t.tgname LIKE %s)"
            " AND t.tgname NOT IN %s",
            table,
            "trg\\_%\\_fdw\\_fk\\_check",
            "trg\\_%\\_fdw\\_unlink\\_pointer",
            (f"trg_{table}_fdw_fk_check", f"trg_{table}_fdw_unlink_pointer"),
        )
    )
    stale.extend((name, rel) for name, rel in cr.fetchall())
    cr.execute(
        SQL(
            "SELECT t.tgname, c.relname FROM pg_trigger t"
            " JOIN pg_class c ON c.oid = t.tgrelid"
            " WHERE NOT t.tgisinternal AND t.tgname LIKE %s"
            " AND to_regclass(split_part(t.tgname, '_fdw_no_delete_', 2)) IS NULL",
            "trg\\_%\\_fdw\\_no\\_delete\\_%",
        )
    )
    stale.extend((name, rel) for name, rel in cr.fetchall() if (name, rel) not in stale)
    return stale
