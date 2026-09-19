import logging

from odoo.db.schema import column_exists, rename_column, table_exists
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def set_aside_root_columns(cr, columns) -> None:
    """Rename the root's copy of each column to `legacy_<name>` before the
    schema pass, so that a subtype gets a column of its own instead of
    inheriting the root's. The values wait in the set-aside column for
    `land_set_aside_columns`."""
    if not table_exists(cr, "resource_asset"):
        return
    for column in columns:
        if column_exists(cr, "resource_asset", column):
            rename_column(cr, "resource_asset", column, f"legacy_{column}")


def _tables_of_tree(cr) -> list[str]:
    cr.execute(
        """
        SELECT child.relname
          FROM pg_inherits
          JOIN pg_class child ON child.oid = pg_inherits.inhrelid
          JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
         WHERE parent.relname = 'resource_asset'
        """
    )
    return ["resource_asset", *(row[0] for row in cr.fetchall())]


def _views_reading(cr, table: str, column: str) -> list[str]:
    cr.execute(
        """
        SELECT DISTINCT dependee.relname
          FROM pg_depend d
          JOIN pg_rewrite r ON r.oid = d.objid
          JOIN pg_class dependee ON dependee.oid = r.ev_class
          JOIN pg_class ref ON ref.oid = d.refobjid
          JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
         WHERE ref.relname = %s AND a.attname = %s AND dependee.relkind IN ('v', 'm')
        """,
        [table, column],
    )
    return [row[0] for row in cr.fetchall()]


def land_set_aside_columns(cr, table: str, columns, module: str) -> None:
    """Copy each set-aside value into the subtype table's own column where it
    exists, then drop the set-aside column from every table of the tree: a
    member table created with its columns spelled out keeps a copy after the
    root drops (attislocal). A SQL view reading the column goes with it and
    its module recreates it on update."""
    if not table_exists(cr, table):
        return
    for column in columns:
        legacy = f"legacy_{column}"
        if column_exists(cr, table, legacy) and column_exists(cr, table, column):
            cr.execute(
                SQL(
                    "UPDATE %s SET %s = %s WHERE %s IS NULL AND %s IS NOT NULL",
                    SQL.identifier(table),
                    SQL.identifier(column),
                    SQL.identifier(legacy),
                    SQL.identifier(column),
                    SQL.identifier(legacy),
                )
            )
        for tree_table in _tables_of_tree(cr):
            if not column_exists(cr, tree_table, legacy):
                continue
            views = _views_reading(cr, tree_table, legacy)
            if views:
                _logger.warning(
                    "%s: dropping %s.%s takes the SQL view(s) %s with it; update the "
                    "module that owns each to recreate it.",
                    module,
                    tree_table,
                    legacy,
                    ", ".join(views),
                )
            cr.execute(
                SQL(
                    "ALTER TABLE %s DROP COLUMN %s CASCADE",
                    SQL.identifier(tree_table),
                    SQL.identifier(legacy),
                )
            )


def move_rows_into_subtype_table(cr, kind_code: str, table: str) -> int:
    """Parent to child is a DELETE and an INSERT, because PostgreSQL moves no
    row between them. An id survives it only because the whole tree shares one
    sequence, and the DELETE is possible only because the root holds no
    foreign key into it."""
    if not table_exists(cr, table):
        return 0
    cr.execute("SELECT id FROM resource_asset_kind WHERE code = %s", [kind_code])
    row = cr.fetchone()
    if not row:
        return 0
    cr.execute(
        SQL(
            """
            WITH moved AS (
                DELETE FROM ONLY resource_asset WHERE kind_id = %(kind)s RETURNING *
            )
            INSERT INTO %(table)s SELECT * FROM moved
            """,
            kind=row[0],
            table=SQL.identifier(table),
        )
    )
    moved = cr.rowcount
    if moved:
        _debug.lifecycle("resource_asset.rows_moved", table=table, rows=moved)
        _logger.info(
            "resource_asset: moved %d %s row(s) into %s.", moved, kind_code, table
        )
    return moved
