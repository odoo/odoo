from __future__ import annotations

import enum
import logging
import re
import typing
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

import psycopg

from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL, get_index_name

if TYPE_CHECKING:
    from odoo.db import BaseCursor
else:
    BaseCursor = typing.Any

_schema = logging.getLogger("odoo.schema")
_debug = DebugLog(__name__)


class RowCountReader(typing.Protocol):
    @property
    def rowcount(self) -> int: ...

    def execute(
        self, query: typing.Any, /, *args: typing.Any, **kwargs: typing.Any
    ) -> typing.Any: ...


_SQL_TYPE_TOKEN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*"
    r"(\([A-Za-z0-9_, ]*\))?"
    r"(\[\])*"
    r"( +[A-Za-z][A-Za-z0-9_]*)*"
)
_SQL_NAME_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _get_invalid_name_message(kind: str, value: object) -> str:
    return f"{kind} {value!r} is not a PostgreSQL name: refusing to build DDL from it"


def _refuse_column_type(
    columntype: str, tablename: str, columnname: str | None
) -> ValueError:
    _debug.logic(
        "schema.ddl_refused",
        table=tablename,
        column=columnname,
        kind="column type",
        value=columntype,
    )
    return ValueError(_get_invalid_name_message("column type", columntype))


_CONFDELTYPES = {
    "RESTRICT": "r",
    "NO ACTION": "a",
    "CASCADE": "c",
    "SET NULL": "n",
    "SET DEFAULT": "d",
}


class TableKind(enum.Enum):
    Regular = "r"
    Temporary = "t"
    View = "v"
    Materialized = "m"
    Foreign = "f"
    Partitioned = "p"
    Other = None


_EXISTING_RELKINDS: tuple[str, ...] = tuple(
    kind.value
    for kind in TableKind
    if kind not in (TableKind.Temporary, TableKind.Other)
)


def get_tables_existing(cr: BaseCursor, tablenames: Iterable[str]) -> list[str]:
    asked = list(tablenames)
    cr.execute(
        SQL(
            """
            SELECT c.relname
            FROM pg_class c
            WHERE c.relname = ANY(%s)
                AND c.relkind = ANY(%s)
                AND c.relnamespace = current_schema::regnamespace
            """,
            asked,
            list(_EXISTING_RELKINDS),
        )
    )
    found = [row[0] for row in cr.fetchall()]
    _debug.logic("schema.tables_existing", asked=len(asked), found=len(found))
    return found


class FunctionStatus(enum.IntEnum):
    MISSING = 0
    PRESENT = 1
    INDEXABLE = 2


def get_unaccent_status(cr: BaseCursor) -> FunctionStatus:
    cr.execute("""
        SELECT p.provolatile
        FROM pg_proc p
        WHERE p.proname = 'unaccent'
            AND p.pronamespace = current_schema::regnamespace
            AND p.pronargs = 1
    """)
    result = cr.fetchone()
    if not result:
        status = FunctionStatus.MISSING
    elif result[0] == "i":
        status = FunctionStatus.INDEXABLE
    else:
        status = FunctionStatus.PRESENT
    _debug.logic("schema.unaccent_status", status=status.name)
    return status


def has_trigram(cr: BaseCursor) -> bool:
    cr.execute("""
        SELECT 1 FROM pg_proc
        WHERE proname = 'word_similarity'
            AND pronamespace = current_schema::regnamespace
    """)
    available = bool(cr.fetchone())
    _debug.logic("schema.trigram_status", available=available)
    return available


def table_exists(cr: BaseCursor, tablename: str) -> bool:
    exists = len(get_tables_existing(cr, {tablename})) == 1
    _debug.logic("schema.table_exists", table=tablename, exists=exists)
    return exists


def get_table_kind(cr: BaseCursor, tablename: str) -> TableKind | None:
    cr.execute(
        SQL(
            """
            SELECT c.relkind, c.relpersistence
            FROM pg_class c
            WHERE c.relname = %s
            AND c.relnamespace = current_schema::regnamespace
            """,
            tablename,
        )
    )
    row = cr.fetchone()
    if row is None:
        _debug.logic("schema.table_kind", table=tablename, kind=None)
        return None

    kind, persistence = row
    if kind == "r":
        result = TableKind.Temporary if persistence == "t" else TableKind.Regular
    else:
        try:
            result = TableKind(kind)
        except ValueError:
            result = TableKind.Other
    _debug.logic(
        "schema.table_kind",
        table=tablename,
        kind=kind,
        persistence=persistence,
        result=result.name,
    )
    return result


SQL_ORDER_BY_TYPE = defaultdict(
    lambda: 16,
    {
        "int4": 1,
        "varchar": 2,
        "date": 3,
        "jsonb": 4,
        "text": 5,
        "numeric": 6,
        "bool": 7,
        "timestamp": 8,
        "float8": 9,
    },
)


def create_model_table(
    cr: BaseCursor,
    tablename: str,
    comment: str | None = None,
    columns: Sequence = (),
    inherits: str | None = None,
) -> None:
    for colname, coltype, _ in columns:
        if not _SQL_TYPE_TOKEN.fullmatch(coltype):
            raise _refuse_column_type(coltype, tablename, colname)
    colspecs = [
        *([] if inherits else [SQL("id SERIAL NOT NULL")]),
        *(
            SQL("%s %s", SQL.identifier(colname), SQL(coltype))
            for colname, coltype, _ in columns
        ),
        SQL("PRIMARY KEY(id)"),
    ]
    queries = [
        SQL(
            "CREATE TABLE %s (%s)%s",
            SQL.identifier(tablename),
            SQL(", ").join(colspecs),
            SQL(" INHERITS (%s)", SQL.identifier(inherits)) if inherits else SQL(""),
        ),
    ]
    if comment:
        queries.append(
            SQL(
                "COMMENT ON TABLE %s IS %s",
                SQL.identifier(tablename),
                comment,
            )
        )
    for colname, _, colcomment in columns:
        if colcomment:
            queries.append(
                SQL(
                    "COMMENT ON COLUMN %s IS %s",
                    SQL.identifier(tablename, colname),
                    colcomment,
                )
            )
    with _debug.perf(
        "schema.create_table",
        cr=cr,
        table=tablename,
        columns=len(columns),
        comments=len(queries) - 1,
    ):
        cr.execute(SQL("; ").join(queries))

    _schema.debug("Table %r: created", tablename)


def get_table_columns(cr: BaseCursor, tablename: str) -> dict[str, dict]:
    with _debug.perf("schema.table_columns", cr=cr, table=tablename) as span:
        cr.execute(
            SQL(
                """
                SELECT a.attname AS column_name,
                    t.typname AS udt_name,
                    CASE WHEN a.atttypmod > 0 AND t.typname IN ('varchar', 'bpchar')
                            THEN a.atttypmod - 4
                            ELSE NULL
                    END AS character_maximum_length,
                    CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END AS is_nullable
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE c.relname = %s
                    AND c.relnamespace = current_schema::regnamespace
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                """,
                tablename,
            )
        )
        columns = {row["column_name"]: row for row in cr.dictfetchall()}
        span.set(columns=len(columns))
    return columns


def column_exists(cr: RowCountReader, tablename: str, columnname: str) -> bool:
    cr.execute(
        SQL(
            """
            SELECT 1
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = %s
               AND a.attname = %s
               AND c.relnamespace = current_schema::regnamespace
               AND a.attnum > 0
               AND NOT a.attisdropped
            """,
            tablename,
            columnname,
        )
    )
    exists = bool(cr.rowcount)
    _debug.logic(
        "schema.column_exists", table=tablename, column=columnname, exists=exists
    )
    return exists


def create_column(
    cr: BaseCursor,
    tablename: str,
    columnname: str,
    columntype: str,
    comment: str | None = None,
) -> None:
    if not _SQL_TYPE_TOKEN.fullmatch(columntype):
        raise _refuse_column_type(columntype, tablename, columnname)
    sql = SQL(
        "ALTER TABLE %s ADD COLUMN %s %s%s",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
        SQL(columntype),
        SQL(" DEFAULT false" if columntype.upper() == "BOOLEAN" else ""),
    )
    if comment:
        sql = SQL(
            "%s; %s",
            sql,
            SQL(
                "COMMENT ON COLUMN %s IS %s",
                SQL.identifier(tablename, columnname),
                comment,
            ),
        )
    with _debug.perf(
        "schema.add_column",
        cr=cr,
        table=tablename,
        column=columnname,
        type=columntype,
        default_false=columntype.upper() == "BOOLEAN",
        comment=bool(comment),
    ):
        cr.execute(sql)
    _schema.debug(
        "Table %r: added column %r of type %s",
        tablename,
        columnname,
        columntype,
    )


def convert_column(
    cr: BaseCursor, tablename: str, columnname: str, columntype: str
) -> None:
    if not _SQL_TYPE_TOKEN.fullmatch(columntype):
        raise _refuse_column_type(columntype, tablename, columnname)
    using = SQL("%s::%s", SQL.identifier(columnname), SQL(columntype))
    _convert_column(cr, tablename, columnname, columntype, using)


def convert_column_translatable(
    cr: BaseCursor, tablename: str, columnname: str, columntype: str
) -> None:
    _debug.pipeline(
        "schema.translatable_conversion",
        table=tablename,
        column=columnname,
        direction="to_jsonb" if columntype == "jsonb" else "from_jsonb",
        type=columntype,
    )
    drop_index(cr, get_index_name(tablename, columnname), tablename)
    if columntype == "jsonb":
        using = SQL(
            "CASE WHEN %s IS NOT NULL THEN jsonb_build_object('en_US', %s::varchar) END",
            SQL.identifier(columnname),
            SQL.identifier(columnname),
        )
    else:
        using = SQL("%s->>'en_US'", SQL.identifier(columnname))
    _convert_column(cr, tablename, columnname, columntype, using)


def _convert_column(
    cr: BaseCursor, tablename: str, columnname: str, columntype: str, using: SQL
) -> None:
    if not _SQL_TYPE_TOKEN.fullmatch(columntype):
        raise _refuse_column_type(columntype, tablename, columnname)
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT, ALTER COLUMN %s TYPE %s USING %s",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
        SQL.identifier(columnname),
        SQL(columntype),
        using,
    )
    with _debug.perf(
        "schema.convert_column",
        cr=cr,
        table=tablename,
        column=columnname,
        type=columntype,
    ) as span:
        try:
            with cr.savepoint(flush=False):
                cr.execute(query, log_exceptions=False)
        except psycopg.NotSupportedError as exc:
            span.set(views_dropped=True)
            _debug.logic(
                "schema.convert_column_blocked_by_views",
                table=tablename,
                column=columnname,
                sqlstate=getattr(exc, "sqlstate", None),
            )
            drop_views_depending_on_table(cr, tablename, columnname)
            cr.execute(query)
    _schema.debug(
        "Table %r: column %r changed to type %s",
        tablename,
        columnname,
        columntype,
    )


def drop_views_depending_on_table(cr: BaseCursor, table: str, column: str) -> None:
    views = get_views_depending_on_table(cr, table, column)
    _debug.pipeline(
        "schema.dependent_views_dropped", table=table, column=column, count=len(views)
    )
    for v, k in views:
        with _debug.perf("schema.drop_view", cr=cr, view=v, materialized=k == "m"):
            cr.execute(
                SQL(
                    "DROP %s IF EXISTS %s CASCADE",
                    SQL("MATERIALIZED VIEW" if k == "m" else "VIEW"),
                    SQL.identifier(v),
                )
            )
        _schema.debug("Drop view %r", v)


def get_views_depending_on_table(
    cr: BaseCursor, table: str, column: str
) -> list[tuple[str, str]]:
    cr.execute(
        SQL(
            """
            SELECT distinct dependee.relname, dependee.relkind
            FROM pg_depend
            JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
            JOIN pg_class as dependee ON pg_rewrite.ev_class = dependee.oid
            JOIN pg_class as dependent ON pg_depend.refobjid = dependent.oid
            JOIN pg_attribute ON pg_depend.refobjid = pg_attribute.attrelid
                AND pg_depend.refobjsubid = pg_attribute.attnum
            WHERE dependent.relname = %s
                AND pg_attribute.attnum > 0
                AND pg_attribute.attname = %s
                AND dependee.relkind in ('v', 'm')
                AND dependee.relnamespace = current_schema::regnamespace
            """,
            table,
            column,
        )
    )
    return cr.fetchall()


def rename_column(
    cr: BaseCursor, tablename: str, columnname: str, newname: str
) -> None:
    with _debug.perf(
        "schema.rename_column",
        cr=cr,
        table=tablename,
        column=columnname,
        new=newname,
    ) as span:
        cr.execute(
            SQL(
                "ALTER TABLE %s RENAME COLUMN %s TO %s",
                SQL.identifier(tablename),
                SQL.identifier(columnname),
                SQL.identifier(newname),
            )
        )
        # PostgreSQL truncates every identifier to 63 bytes when it creates
        # it, so the name a constraint actually carries is the truncated one;
        # a longer literal is rejected as an identifier, not merely unmatched.
        old_constraint = f"{tablename}_{columnname}_not_null"[:63]
        cr.execute(
            SQL(
                """
                SELECT 1
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                WHERE t.relname = %s
                   AND c.conname = %s
                   AND t.relnamespace = current_schema::regnamespace
                """,
                tablename,
                old_constraint,
            )
        )
        has_not_null = bool(cr.fetchone())
        span.set(not_null_renamed=has_not_null)
        _debug.logic(
            "schema.not_null_constraint_follows_rename",
            table=tablename,
            column=columnname,
            found=has_not_null,
        )
        if has_not_null:
            cr.execute(
                SQL(
                    "ALTER TABLE %s RENAME CONSTRAINT %s TO %s",
                    SQL.identifier(tablename),
                    SQL.identifier(old_constraint),
                    SQL.identifier(f"{tablename}_{newname}_not_null"[:63]),
                )
            )
    _schema.debug("Table %r: renamed column %r to %r", tablename, columnname, newname)


def set_not_null(cr: BaseCursor, tablename: str, columnname: str) -> None:
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
    )
    with _debug.perf("schema.set_not_null", cr=cr, table=tablename, column=columnname):
        cr.execute(query, log_exceptions=False)
    _schema.debug(
        "Table %r: column %r: added constraint NOT NULL", tablename, columnname
    )


def get_inherited_columns(
    cr: BaseCursor, tablename: str, columnnames: Iterable[str]
) -> set[str]:
    names = list(columnnames)
    if not names:
        return set()
    cr.execute(
        SQL(
            "SELECT a.attname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = current_schema() AND c.relname = %s "
            "AND a.attname = ANY(%s) AND a.attinhcount > 0",
            tablename,
            names,
        )
    )
    return {name for (name,) in cr.fetchall()}


def drop_columns(
    cr: BaseCursor, tablename: str, columnnames: Iterable[str]
) -> list[str]:
    existing = get_table_columns(cr, tablename)
    requested = list(columnnames)
    dropped = [name for name in requested if name in existing]
    if not dropped:
        _debug.logic(
            "schema.drop_columns.skipped",
            table=tablename,
            requested=requested,
            reason="absent",
        )
        return dropped
    views = sorted(
        {
            view
            for name in dropped
            for view, _kind in get_views_depending_on_table(cr, tablename, name)
        }
    )
    with _debug.perf("schema.drop_columns", cr=cr, table=tablename, columns=dropped):
        cr.execute(
            SQL(
                "ALTER TABLE %s %s",
                SQL.identifier(tablename),
                SQL(", ").join(
                    SQL("DROP COLUMN %s CASCADE", SQL.identifier(name))
                    for name in dropped
                ),
            )
        )
    _debug.pipeline(
        "schema.columns_dropped",
        table=tablename,
        columns=dropped,
        absent=[name for name in requested if name not in existing],
        views=views,
    )
    if views:
        _schema.info(
            "Table %r: dropped columns %s and the views reading them: %s",
            tablename,
            ", ".join(dropped),
            ", ".join(views),
        )
    else:
        _schema.debug("Table %r: dropped columns %s", tablename, ", ".join(dropped))
    return dropped


def drop_not_null(cr: BaseCursor, tablename: str, columnname: str) -> None:
    with _debug.perf("schema.drop_not_null", cr=cr, table=tablename, column=columnname):
        cr.execute(
            SQL(
                "ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL",
                SQL.identifier(tablename),
                SQL.identifier(columnname),
            )
        )
    _schema.debug(
        "Table %r: column %r: dropped constraint NOT NULL",
        tablename,
        columnname,
    )


def set_default(cr: BaseCursor, tablename: str, columnname: str, value: object) -> None:
    with _debug.perf(
        "schema.set_default",
        cr=cr,
        table=tablename,
        column=columnname,
        value_type=type(value).__name__,
    ):
        cr.execute(
            SQL(
                "ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s",
                SQL.identifier(tablename),
                SQL.identifier(columnname),
                value,
            )
        )
    _schema.debug(
        "Table %r: column %r: set default to %r", tablename, columnname, value
    )


def get_constraint_definition(
    cr: BaseCursor, tablename: str, constraintname: str
) -> str | None:
    cr.execute(
        SQL(
            """
            SELECT COALESCE(d.description, pg_get_constraintdef(c.oid))
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            LEFT JOIN pg_description d ON c.oid = d.objoid
            WHERE t.relname = %s AND conname = %s
                AND t.relnamespace = current_schema::regnamespace
            """,
            tablename,
            constraintname,
        )
    )
    row = cr.fetchone()
    _debug.logic(
        "schema.constraint_definition",
        table=tablename,
        constraint=constraintname,
        found=row is not None,
    )
    return row[0] if row else None


def add_constraint(
    cr: BaseCursor, tablename: str, constraintname: str, definition: str
) -> None:
    query1 = SQL(
        "ALTER TABLE %s ADD CONSTRAINT %s %s",
        SQL.identifier(tablename),
        SQL.identifier(constraintname),
        SQL(definition.replace("%", "%%")),
    )
    query2 = SQL(
        "COMMENT ON CONSTRAINT %s ON %s IS %s",
        SQL.identifier(constraintname),
        SQL.identifier(tablename),
        definition,
    )
    with _debug.perf(
        "schema.add_constraint",
        cr=cr,
        table=tablename,
        constraint=constraintname,
        kind=definition.split(None, 1)[0].upper() if definition.strip() else "",
    ):
        cr.execute(query1, log_exceptions=False)
        cr.execute(query2, log_exceptions=False)
    _schema.debug(
        "Table %r: added constraint %r as %s",
        tablename,
        constraintname,
        definition,
    )


def drop_constraint(cr: BaseCursor, tablename: str, constraintname: str) -> None:
    with _debug.perf(
        "schema.drop_constraint", cr=cr, table=tablename, constraint=constraintname
    ):
        cr.execute(
            SQL(
                "ALTER TABLE %s DROP CONSTRAINT %s",
                SQL.identifier(tablename),
                SQL.identifier(constraintname),
            )
        )
    _schema.debug("Table %r: dropped constraint %r", tablename, constraintname)


def add_foreign_key(
    cr: BaseCursor,
    tablename1: str,
    columnname1: str,
    tablename2: str,
    columnname2: str,
    ondelete: str,
) -> None:
    if ondelete.upper() not in _CONFDELTYPES:
        _debug.logic(
            "schema.ddl_refused",
            table=tablename1,
            column=columnname1,
            kind="ondelete",
            value=ondelete,
        )
        raise ValueError(
            f"Invalid ON DELETE policy {ondelete!r} for "
            f"{tablename1}.{columnname1}; expected one of "
            f"{sorted(_CONFDELTYPES)}"
        )
    with _debug.perf(
        "schema.add_foreign_key",
        cr=cr,
        table=tablename1,
        column=columnname1,
        references=tablename2,
        ondelete=ondelete,
    ):
        cr.execute(
            SQL(
                "ALTER TABLE %s ADD FOREIGN KEY (%s) REFERENCES %s(%s) ON DELETE %s",
                SQL.identifier(tablename1),
                SQL.identifier(columnname1),
                SQL.identifier(tablename2),
                SQL.identifier(columnname2),
                SQL(ondelete),
            )
        )
    _schema.debug(
        "Table %r: added foreign key %r references %r(%r) ON DELETE %s",
        tablename1,
        columnname1,
        tablename2,
        columnname2,
        ondelete,
    )


_FK_BASE_QUERY = """
    FROM pg_constraint AS fk
    JOIN pg_class AS c1 ON fk.conrelid = c1.oid
    JOIN pg_class AS c2 ON fk.confrelid = c2.oid
    JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid
        AND fk.conkey[1] = a1.attnum
    JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid
        AND fk.confkey[1] = a2.attnum
    WHERE fk.contype = 'f'
        AND array_length(fk.conkey, 1) = 1
        AND c1.relnamespace = current_schema::regnamespace
"""


def _get_fk_constraints(
    cr: BaseCursor, tablename: str, columnname: str
) -> list[tuple[str, str, str, str]]:
    cr.execute(
        SQL(
            "SELECT fk.conname, c2.relname, a2.attname, fk.confdeltype"
            + _FK_BASE_QUERY
            + "AND c1.relname = %s AND a1.attname = %s",
            tablename,
            columnname,
        )
    )
    rows = cr.fetchall()
    _debug.logic(
        "schema.fk_constraints", table=tablename, column=columnname, found=len(rows)
    )
    return rows


def get_fk_constraints_batch(
    cr: BaseCursor, tablenames: Iterable[str]
) -> list[tuple[str, str, str, str, str, str]]:
    asked = list(tablenames)
    with _debug.perf("schema.fk_constraints_batch", cr=cr, tables=len(asked)) as span:
        cr.execute(
            SQL(
                "SELECT fk.conname, c1.relname, a1.attname, c2.relname, a2.attname, fk.confdeltype"
                + _FK_BASE_QUERY
                + "AND c1.relname = ANY(%s)",
                asked,
            )
        )
        rows = cr.fetchall()
        span.set(found=len(rows))
    return rows


def get_fk_constraint_names(
    cr: BaseCursor,
    tablename1: str,
    columnname1: str,
    tablename2: str,
    columnname2: str,
    ondelete: str,
) -> list[str]:
    deltype = _CONFDELTYPES.get(ondelete.upper(), "a")
    candidates = _get_fk_constraints(cr, tablename1, columnname1)
    names = [
        row[0] for row in candidates if row[1:] == (tablename2, columnname2, deltype)
    ]
    _debug.logic(
        "schema.fk_constraint_names",
        table=tablename1,
        column=columnname1,
        references=tablename2,
        ondelete=ondelete,
        candidates=len(candidates),
        matching=len(names),
    )
    return names


def index_exists(cr: RowCountReader, indexname: str) -> bool:
    cr.execute(
        SQL(
            """
            SELECT 1
            FROM pg_class c
            WHERE c.relname = %s
               AND c.relkind IN ('i', 'I')
               AND c.relnamespace = current_schema::regnamespace
            """,
            indexname,
        )
    )
    exists = bool(cr.rowcount)
    _debug.logic("schema.index_exists", index=indexname, exists=exists)
    return exists


def get_index_definition(
    cr: BaseCursor, indexname: str
) -> tuple[str | None, str | None]:
    cr.execute(
        SQL(
            """
            SELECT idx.indexdef, d.description
            FROM pg_class c
            JOIN pg_indexes idx ON c.relname = idx.indexname
                AND idx.schemaname = current_schema
            LEFT JOIN pg_description d ON c.oid = d.objoid
            WHERE c.relname = %s AND c.relkind IN ('i', 'I')
                AND c.relnamespace = current_schema::regnamespace
            """,
            indexname,
        )
    )
    row = cr.fetchone()
    _debug.logic(
        "schema.index_definition",
        index=indexname,
        found=row is not None,
        commented=bool(row and row[1]),
    )
    return (row[0], row[1]) if row else (None, None)


def get_index_constraint(cr: BaseCursor, indexname: str) -> str | None:
    cr.execute(
        SQL(
            """
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class i ON i.oid = c.conindid
            WHERE i.relname = %s
                AND i.relnamespace = current_schema::regnamespace
            """,
            indexname,
        )
    )
    row = cr.fetchone()
    _debug.logic(
        "schema.index_constraint",
        index=indexname,
        constraint=row[0] if row else None,
    )
    return row[0] if row else None


def create_index(
    cr: BaseCursor,
    indexname: str,
    tablename: str,
    expressions: list[str],
    method: str = "btree",
    where: str = "",
    *,
    comment: str | None = None,
    unique: bool = False,
    check_exists: bool = True,
) -> None:
    if not expressions:
        _debug.logic(
            "schema.ddl_refused", table=tablename, kind="index expressions", value=None
        )
        raise ValueError("Missing expressions")
    if not _SQL_NAME_TOKEN.fullmatch(method):
        _debug.logic(
            "schema.ddl_refused", table=tablename, kind="index method", value=method
        )
        raise ValueError(_get_invalid_name_message("index method", method))
    _debug.pipeline(
        "schema.create_index_requested",
        index=indexname,
        table=tablename,
        method=method,
        expressions=len(expressions),
        partial=bool(where),
        unique=unique,
        check_exists=check_exists,
    )
    if check_exists and index_exists(cr, indexname):
        _debug.logic(
            "schema.index_create_skipped",
            index=indexname,
            table=tablename,
            reason="exists",
        )
        return
    definition = SQL(
        "USING %s (%s)%s",
        SQL(method),
        SQL(", ").join(
            SQL(expression.replace("%", "%%")) for expression in expressions
        ),
        (SQL(" WHERE %s", SQL(where.replace("%", "%%"))) if where else SQL()),
    )
    add_index(cr, indexname, tablename, definition, unique=unique, comment=comment)


def add_index(
    cr: BaseCursor,
    indexname: str,
    tablename: str,
    definition: str | SQL,
    *,
    unique: bool,
    comment: str | None = None,
) -> None:
    if isinstance(definition, str):
        definition = SQL(definition.replace("%", "%%"))
    query = SQL(
        "CREATE %sINDEX %s ON %s %s",
        SQL("UNIQUE ") if unique else SQL(),
        SQL.identifier(indexname),
        SQL.identifier(tablename),
        definition,
    )
    query_comment = (
        SQL(
            "COMMENT ON INDEX %s IS %s",
            SQL.identifier(indexname),
            comment,
        )
        if comment
        else None
    )
    with _debug.perf(
        "schema.create_index",
        cr=cr,
        table=tablename,
        index=indexname,
        unique=unique,
        comment=query_comment is not None,
    ):
        cr.execute(query, log_exceptions=False)
        if query_comment:
            cr.execute(query_comment, log_exceptions=False)
    _schema.debug(
        "Table %r: created index %r (%s)", tablename, indexname, definition.code
    )


def drop_index(cr: BaseCursor, indexname: str, tablename: str) -> None:
    with _debug.perf("schema.drop_index", cr=cr, table=tablename, index=indexname):
        cr.execute(SQL("DROP INDEX IF EXISTS %s", SQL.identifier(indexname)))
    _schema.debug("Table %r: dropped index %r", tablename, indexname)


def drop_view_if_exists(cr: BaseCursor, viewname: str) -> None:
    kind = get_table_kind(cr, viewname)
    _debug.logic(
        "schema.drop_view_if_exists", view=viewname, kind=getattr(kind, "value", None)
    )
    if kind == TableKind.View:
        cr.execute(SQL("DROP VIEW %s CASCADE", SQL.identifier(viewname)))
    elif kind == TableKind.Materialized:
        cr.execute(SQL("DROP MATERIALIZED VIEW %s CASCADE", SQL.identifier(viewname)))


def get_column_names_in_constraint(
    cr: BaseCursor,
    diagnostics: psycopg.errors.Diagnostic,
    *,
    check_catalog: bool = False,
) -> list[str]:
    if column := diagnostics.column_name:
        _debug.logic(
            "schema.constraint_columns_resolved",
            constraint=diagnostics.constraint_name,
            table=diagnostics.table_name,
            columns=1,
            via="diagnostic",
        )
        return [column]
    if not check_catalog:
        _debug.logic(
            "schema.constraint_columns_resolved",
            constraint=diagnostics.constraint_name,
            table=diagnostics.table_name,
            columns=0,
            via="skipped",
        )
        return []
    cr.execute(
        SQL(
            """
            SELECT
                ARRAY(
                    SELECT attname FROM pg_attribute
                    WHERE attrelid = conrelid
                    AND attnum = ANY(conkey)
                ) as "columns"
            FROM pg_constraint
            JOIN pg_class t ON t.oid = conrelid
            WHERE conname = %s
                AND t.relname = %s
                AND t.relnamespace = current_schema::regnamespace
            """,
            diagnostics.constraint_name,
            diagnostics.table_name,
        )
    )
    columns = cr.fetchone()
    _debug.logic(
        "schema.constraint_columns_resolved",
        constraint=diagnostics.constraint_name,
        table=diagnostics.table_name,
        columns=len(columns[0]) if columns else 0,
        via="catalog",
    )
    return columns[0] if columns else []
