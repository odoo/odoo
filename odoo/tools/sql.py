import enum
import logging
import re
import warnings
from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

import psycopg
from psycopg import sql as _sql

from odoo.libs.json import dumps as json_dumps

if TYPE_CHECKING:
    from odoo.fields import Field


from odoo.libs.sql import (
    escape_psql,
    make_identifier,
    make_index_name,
    pg_varchar,
    reverse_order,
)

from .misc import named_to_positional_printf

__all__ = [
    "SQL",
    "create_index",
    "drop_view_if_exists",
    "escape_psql",
    "index_exists",
    "make_identifier",
    "make_index_name",
    "pattern_to_translated_trigram_pattern",
    "pg_varchar",
    "reverse_order",
    "value_to_translated_trigram_pattern",
]

_schema = logging.getLogger("odoo.schema")

IDENT_RE = re.compile(r"^[a-z0-9_][a-z0-9_$\-]*$", re.IGNORECASE)

# Pre-compiled regexes for trigram pattern escaping (ilike operations)
_WILDCARD_ESCAPE_RE = re.compile(r"(_|%|\\)")
_TRIGRAM_PATTERN_RE = re.compile(
    r"""
    (
        (?:.)*?           # 0 or more characters including newline
        (?<!\\)(?:\\\\)*  # 0 or even number of backslashes
    )
    (?:_|%|$)             # a non-escaped wildcard character or end of string
    """,
    re.VERBOSE | re.DOTALL,
)
_PG_UNESCAPE_RE = re.compile(r"\\(.|$)", re.DOTALL)

_CONFDELTYPES = {
    "RESTRICT": "r",
    "NO ACTION": "a",
    "CASCADE": "c",
    "SET NULL": "n",
    "SET DEFAULT": "d",
}


class SQL:
    """An object that wraps SQL code with its parameters, like::

        sql = SQL("UPDATE TABLE foo SET a = %s, b = %s", 'hello', 42)
        cr.execute(sql)

    The code is given as a ``%``-format string, and supports either positional
    arguments (with `%s`) or named arguments (with `%(name)s`). The arguments
    are meant to be merged into the code using the `%` formatting operator.
    Note that the character ``%`` must always be escaped (as ``%%``), even if
    the code does not have parameters, like in ``SQL("foo LIKE 'a%%'")``.

    The SQL wrapper is designed to be composable: the arguments can be either
    actual parameters, or SQL objects themselves::

        sql = SQL(
            "UPDATE TABLE %s SET %s",
            SQL.identifier(tablename),
            SQL("%s = %s", SQL.identifier(columnname), value),
        )

    The combined SQL code is given by ``sql.code``, while the corresponding
    combined parameters are given by the list ``sql.params``. This allows to
    combine any number of SQL terms without having to separately combine their
    parameters, which can be tedious, bug-prone, and is the main downside of
    `psycopg.sql <https://www.psycopg.org/psycopg3/docs/basic/adapt.html>`.

    The second purpose of the wrapper is to discourage SQL injections. Indeed,
    if ``code`` is a string literal (not a dynamic string), then the SQL object
    made with ``code`` is guaranteed to be safe, provided the SQL objects
    within its parameters are themselves safe.

    The wrapper may also contain some metadata ``to_flush``.  If not ``None``,
    its value is a field which the SQL code depends on.  The metadata of a
    wrapper and its parts can be accessed by the iterator ``sql.to_flush``.
    """

    __slots__ = ("__code", "__params", "__to_flush")

    __code: str
    __params: tuple
    __to_flush: tuple[Field, ...]

    # pylint: disable=keyword-arg-before-vararg
    def __init__(
        self,
        code: str | SQL = "",
        /,
        *args,
        to_flush: Field | Iterable[Field] | None = None,
        **kwargs,
    ):
        if isinstance(code, SQL):
            if args or kwargs or to_flush:
                raise TypeError("SQL() unexpected arguments when code has type SQL")
            self.__code = code.__code
            self.__params = code.__params
            self.__to_flush = code.__to_flush
            return

        # validate the format of code and parameters
        if args and kwargs:
            raise TypeError(
                "SQL() takes either positional arguments, or named arguments"
            )

        if kwargs:
            code, args = named_to_positional_printf(code, kwargs)
        elif not args:
            code % ()  # check that code does not contain %s
            self.__code = code
            self.__params = ()
            if to_flush is None:
                self.__to_flush = ()
            elif hasattr(to_flush, "__iter__"):
                self.__to_flush = tuple(to_flush)
            else:
                self.__to_flush = (to_flush,)
            return

        code_list = []
        params_list = []
        to_flush_list = []
        for arg in args:
            if isinstance(arg, SQL):
                code_list.append(arg.__code)
                params_list.extend(arg.__params)
                to_flush_list.extend(arg.__to_flush)
            elif isinstance(arg, tuple):
                # Expand tuples to (%s, %s, ...) with individual values.
                # This supports VALUES (%s) row syntax and other multi-value
                # positions.  Use a list for a single array parameter instead.
                code_list.append("(%s)" % ", ".join(["%s"] * len(arg)))
                params_list.extend(arg)
            else:
                code_list.append("%s")
                params_list.append(arg)
        if to_flush is not None:
            if hasattr(to_flush, "__iter__"):
                to_flush_list.extend(to_flush)
            else:
                to_flush_list.append(to_flush)

        self.__code = code.replace("%%", "%%%%") % tuple(code_list)
        self.__params = tuple(params_list)
        self.__to_flush = tuple(to_flush_list)

    @property
    def code(self) -> str:
        """Return the combined SQL code string."""
        return self.__code

    @property
    def params(self) -> tuple:
        """Return the combined SQL code params as a tuple of values."""
        return self.__params

    @property
    def to_flush(self) -> Iterable[Field]:
        """Return an iterator on the fields to flush in the metadata of
        ``self`` and all of its parts.
        """
        return self.__to_flush

    def render(self) -> str:
        """Render to a fully-formatted SQL string with parameters inlined.

        Uses psycopg's adapter system for safe value quoting.  Useful for
        embedding a parameterized SQL fragment into a larger raw SQL string
        (e.g. inside an f-string that will later be passed to ``cr.execute()``
        with its own separate parameters).
        """
        if not self.__params:
            return self.__code
        return self.__code % tuple(str(_sql.quote(v)) for v in self.__params)

    def __repr__(self):
        return f"SQL({', '.join(map(repr, [self.__code, *self.__params]))})"

    def __bool__(self):
        return bool(self.__code)

    def __eq__(self, other):
        return (
            isinstance(other, SQL)
            and self.__code == other.__code
            and self.__params == other.__params
        )

    def __hash__(self):
        return hash((self.__code, self.__params))

    def __iter__(self):
        """Yields ``self.code`` and ``self.params``. This was introduced for
        backward compatibility, as it enables to access the SQL and parameters
        by deconstructing the object::

            sql = SQL(...)
            code, params = sql
        """
        warnings.warn(
            "Deprecated since 19.0, use code and params properties directly",
            DeprecationWarning, stacklevel=2,
        )
        yield self.code
        yield self.params

    def join(self, args: Iterable) -> SQL:
        """Join SQL objects or parameters with ``self`` as a separator."""
        items = args if isinstance(args, list) else list(args)
        if len(items) == 0:
            return SQL.EMPTY
        if len(items) == 1 and isinstance(items[0], SQL):
            return items[0]
        if not self.__params:
            return SQL(self.__code.join("%s" for _ in items), *items)
        # general case: alternate items with self
        result = [self] * (len(items) * 2 - 1)
        for index, arg in enumerate(items):
            result[index * 2] = arg
        return SQL("%s" * len(result), *result)

    # Module-level empty singleton, set after class definition
    EMPTY: SQL

    @classmethod
    def identifier(
        cls,
        name: str,
        subname: str | None = None,
        to_flush: Field | None = None,
    ) -> SQL:
        """Return an SQL object that represents an identifier."""
        assert name.isidentifier() or IDENT_RE.match(
            name
        ), f"{name!r} invalid for SQL.identifier()"
        if subname is None:
            return cls(f'"{name}"', to_flush=to_flush)
        assert subname.isidentifier() or IDENT_RE.match(
            subname
        ), f"{subname!r} invalid for SQL.identifier()"
        return cls(f'"{name}"."{subname}"', to_flush=to_flush)


# Immutable singleton for empty SQL — avoids repeated allocations
SQL.EMPTY = SQL()


def existing_tables(cr, tablenames):
    """Return the names of existing tables among ``tablenames``."""
    cr.execute(
        SQL(
            """
        SELECT c.relname
          FROM pg_class c
         WHERE c.relname = ANY(%s)
           AND c.relkind = ANY(%s)
           AND c.relnamespace = current_schema::regnamespace
    """,
            list(tablenames),
            ["r", "v", "m"],
        )
    )
    return [row[0] for row in cr.fetchall()]


def table_exists(cr, tablename):
    """Return whether the given table exists."""
    return len(existing_tables(cr, {tablename})) == 1


class TableKind(enum.Enum):
    Regular = "r"
    Temporary = "t"
    View = "v"
    Materialized = "m"
    Foreign = "f"
    Other = None


def table_kind(cr, tablename: str) -> TableKind | None:
    """Return the kind of a table, if ``tablename`` is a regular or foreign
    table, or a view (ignores indexes, sequences, toast tables, and partitioned
    tables; unlogged tables are considered regular)
    """
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
    if not cr.rowcount:
        return None

    kind, persistence = cr.fetchone()
    # special case: permanent, temporary, and unlogged tables differ by their
    # relpersistence, they're all "ordinary" (relkind = r)
    if kind == "r":
        return TableKind.Temporary if persistence == "t" else TableKind.Regular

    try:
        return TableKind(kind)
    except ValueError:
        # NB: or raise? unclear if it makes sense to allow table_kind to
        #     "work" with something like an index or sequence
        return TableKind.Other


# prescribed column order by type: columns aligned on 4 bytes, columns aligned
# on 1 byte, columns aligned on 8 bytes(values have been chosen to minimize
# padding in rows; unknown column types are put last)
SQL_ORDER_BY_TYPE = defaultdict(
    lambda: 16,
    {
        "int4": 1,  # 4 bytes aligned on 4 bytes
        "varchar": 2,  # variable aligned on 4 bytes
        "date": 3,  # 4 bytes aligned on 4 bytes
        "jsonb": 4,  # jsonb
        "text": 5,  # variable aligned on 4 bytes
        "numeric": 6,  # variable aligned on 4 bytes
        "bool": 7,  # 1 byte aligned on 1 byte
        "timestamp": 8,  # 8 bytes aligned on 8 bytes
        "float8": 9,  # 8 bytes aligned on 8 bytes
    },
)


def create_model_table(cr, tablename, comment=None, columns=()):
    """Create the table for a model."""
    colspecs = [
        SQL("id SERIAL NOT NULL"),
        *(
            SQL(
                "%s %s", SQL.identifier(colname), SQL(coltype)
            )  # pylint: disable=sql-injection
            for colname, coltype, _ in columns
        ),
        SQL("PRIMARY KEY(id)"),
    ]
    queries = [
        SQL(
            "CREATE TABLE %s (%s)",
            SQL.identifier(tablename),
            SQL(", ").join(colspecs),
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
        queries.append(
            SQL(
                "COMMENT ON COLUMN %s IS %s",
                SQL.identifier(tablename, colname),
                colcomment,
            )
        )
    cr.execute(SQL("; ").join(queries))

    _schema.debug("Table %r: created", tablename)


def table_columns(cr, tablename):
    """Return a dict mapping column names to their configuration.

    Each value is a dict with keys ``column_name``, ``udt_name``,
    ``character_maximum_length``, and ``is_nullable`` (matching the legacy
    ``information_schema.columns`` contract).  Uses ``pg_catalog`` directly
    for better performance.
    """
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
    return {row["column_name"]: row for row in cr.dictfetchall()}


def column_exists(cr, tablename, columnname):
    """Return whether the given column exists."""
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
    return cr.rowcount


def create_column(cr, tablename, columnname, columntype, comment=None):
    """Create a column with the given type."""
    sql = SQL(
        "ALTER TABLE %s ADD COLUMN %s %s %s",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
        SQL(columntype),  # pylint: disable=sql-injection
        SQL("DEFAULT false" if columntype.upper() == "BOOLEAN" else ""),
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
    cr.execute(sql)
    _schema.debug(
        "Table %r: added column %r of type %s",
        tablename,
        columnname,
        columntype,
    )


def rename_column(cr, tablename, columnname1, columnname2):
    """Rename the given column."""
    cr.execute(
        SQL(
            "ALTER TABLE %s RENAME COLUMN %s TO %s",
            SQL.identifier(tablename),
            SQL.identifier(columnname1),
            SQL.identifier(columnname2),
        )
    )
    _schema.debug(
        "Table %r: renamed column %r to %r", tablename, columnname1, columnname2
    )


def convert_column(cr, tablename, columnname, columntype):
    """Convert the column to the given type."""
    using = SQL(
        "%s::%s", SQL.identifier(columnname), SQL(columntype)
    )  # pylint: disable=sql-injection
    _convert_column(cr, tablename, columnname, columntype, using)


def convert_column_translatable(cr, tablename, columnname, columntype):
    """Convert the column from/to a 'jsonb' translated field column."""
    drop_index(cr, make_index_name(tablename, columnname), tablename)
    if columntype == "jsonb":
        using = SQL(
            "CASE WHEN %s IS NOT NULL THEN jsonb_build_object('en_US', %s::varchar) END",
            SQL.identifier(columnname),
            SQL.identifier(columnname),
        )
    else:
        using = SQL("%s->>'en_US'", SQL.identifier(columnname))
    _convert_column(cr, tablename, columnname, columntype, using)


def _convert_column(cr, tablename, columnname, columntype, using: SQL):
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT, ALTER COLUMN %s TYPE %s USING %s",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
        SQL.identifier(columnname),
        SQL(columntype),
        using,
    )
    try:
        with cr.savepoint(flush=False):
            cr.execute(query, log_exceptions=False)
    except psycopg.NotSupportedError:
        drop_depending_views(cr, tablename, columnname)
        cr.execute(query)
    _schema.debug(
        "Table %r: column %r changed to type %s",
        tablename,
        columnname,
        columntype,
    )


def drop_depending_views(cr, table, column):
    """drop views depending on a field to allow the ORM to resize it in-place"""
    for v, k in get_depending_views(cr, table, column):
        cr.execute(
            SQL(
                "DROP %s IF EXISTS %s CASCADE",
                SQL("MATERIALIZED VIEW" if k == "m" else "VIEW"),
                SQL.identifier(v),
            )
        )
        _schema.debug("Drop view %r", v)


def get_depending_views(cr, table, column):
    # http://stackoverflow.com/a/11773226/75349
    cr.execute(
        SQL(
            """
        SELECT distinct quote_ident(dependee.relname), dependee.relkind
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


def set_not_null(cr, tablename, columnname):
    """Add a NOT NULL constraint on the given column."""
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
    )
    cr.execute(query, log_exceptions=False)
    _schema.debug(
        "Table %r: column %r: added constraint NOT NULL", tablename, columnname
    )


def drop_not_null(cr, tablename, columnname):
    """Drop the NOT NULL constraint on the given column."""
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


def set_default(cr, tablename, columnname, value):
    """Set a SQL DEFAULT on the given column.

    This ensures the database fills in a default value even when the ORM
    omits the column from INSERT (e.g. when the module that added the
    field is not loaded but the NOT NULL constraint remains).
    """
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


def constraint_definition(cr, tablename, constraintname):
    """Return the given constraint's definition."""
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
    return cr.fetchone()[0] if cr.rowcount else None


def add_constraint(cr, tablename, constraintname, definition):
    """Add a constraint on the given table."""
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
    cr.execute(query1, log_exceptions=False)
    cr.execute(query2, log_exceptions=False)
    _schema.debug(
        "Table %r: added constraint %r as %s",
        tablename,
        constraintname,
        definition,
    )


def drop_constraint(cr, tablename, constraintname):
    """Drop the given constraint."""
    cr.execute(
        SQL(
            "ALTER TABLE %s DROP CONSTRAINT %s",
            SQL.identifier(tablename),
            SQL.identifier(constraintname),
        )
    )
    _schema.debug("Table %r: dropped constraint %r", tablename, constraintname)


def add_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """Create the given foreign key, and return ``True``."""
    cr.execute(
        SQL(
            "ALTER TABLE %s ADD FOREIGN KEY (%s) REFERENCES %s(%s) ON DELETE %s",
            SQL.identifier(tablename1),
            SQL.identifier(columnname1),
            SQL.identifier(tablename2),
            SQL.identifier(columnname2),
            SQL(ondelete),  # pylint: disable=sql-injection
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
    JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid AND fk.conkey[1] = a1.attnum
    JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid AND fk.confkey[1] = a2.attnum
   WHERE fk.contype = 'f'
     AND c1.relnamespace = current_schema::regnamespace
"""


def _get_fk_constraints(cr, tablename, columnname):
    """Return all FK constraints on (tablename, columnname).

    Each result is a tuple (conname, target_table, target_column, confdeltype).
    """
    cr.execute(
        SQL(
            "SELECT fk.conname, c2.relname, a2.attname, fk.confdeltype"
            + _FK_BASE_QUERY
            + "AND c1.relname = %s AND a1.attname = %s",
            tablename,
            columnname,
        )
    )
    return cr.fetchall()


def get_fk_constraints_batch(cr, tablenames):
    """Return all FK constraints on the given tables in a single query.

    Each result is a tuple
    (conname, source_table, source_column, target_table, target_column, confdeltype).
    """
    cr.execute(
        SQL(
            "SELECT fk.conname, c1.relname, a1.attname, c2.relname, a2.attname, fk.confdeltype"
            + _FK_BASE_QUERY
            + "AND c1.relname = ANY(%s)",
            list(tablenames),
        )
    )
    return cr.fetchall()


def get_foreign_keys(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    deltype = _CONFDELTYPES[ondelete.upper()]
    return [
        row[0]
        for row in _get_fk_constraints(cr, tablename1, columnname1)
        if row[1:] == (tablename2, columnname2, deltype)
    ]


def fix_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """Update the foreign keys between tables to match the given one, and
    return ``True`` if the given foreign key has been recreated.
    """
    deltype = _CONFDELTYPES.get(ondelete.upper(), "a")
    found = False
    for conname, target_table, target_col, del_type in _get_fk_constraints(
        cr, tablename1, columnname1
    ):
        if not found and (target_table, target_col, del_type) == (
            tablename2,
            columnname2,
            deltype,
        ):
            found = True
        else:
            drop_constraint(cr, tablename1, conname)
    if found:
        return False
    add_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete)
    return True


def index_exists(cr, indexname):
    """Return whether the given index exists."""
    cr.execute(SQL("SELECT 1 FROM pg_indexes WHERE indexname=%s", indexname))
    return cr.rowcount


def index_definition(cr, indexname):
    """Read the index definition from the database"""
    cr.execute(
        SQL(
            """
        SELECT idx.indexdef, d.description
        FROM pg_class c
        JOIN pg_indexes idx ON c.relname = idx.indexname
        LEFT JOIN pg_description d ON c.oid = d.objoid
        WHERE c.relname = %s AND c.relkind = 'i'
          AND c.relnamespace = current_schema::regnamespace
    """,
            indexname,
        )
    )
    return cr.fetchone() if cr.rowcount else (None, None)


def create_index(
    cr,
    indexname,
    tablename,
    expressions,
    method="btree",
    where="",
    *,
    comment=None,
    unique=False,
):
    """Create the given index unless it exists.

    :param cr: The cursor
    :param indexname: The name of the index
    :param tablename: The name of the table
    :param method: The type of the index (default: btree)
    :param where: WHERE clause for the index (default: '')
    :param comment: The comment to set on the index
    :param unique: Whether the index is unique or not (default: False)
    """
    assert expressions, "Missing expressions"
    if index_exists(cr, indexname):
        return
    definition = SQL(
        "USING %s (%s)%s",
        SQL(method),  # pylint: disable=sql-injection
        SQL(", ").join(
            SQL(expression) for expression in expressions
        ),  # pylint: disable=sql-injection
        (
            SQL(" WHERE %s", SQL(where)) if where else SQL()
        ),  # pylint: disable=sql-injection
    )
    add_index(cr, indexname, tablename, definition, unique=unique, comment=comment)


def add_index(cr, indexname, tablename, definition, *, unique: bool, comment=""):
    """Create an index."""
    if isinstance(definition, str):
        definition = SQL(definition.replace("%", "%%"))  # pylint: disable=sql-injection
    else:
        definition = SQL(definition)  # pylint: disable=sql-injection
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
    cr.execute(query, log_exceptions=False)
    if query_comment:
        cr.execute(query_comment, log_exceptions=False)
    _schema.debug(
        "Table %r: created index %r (%s)", tablename, indexname, definition.code
    )


def drop_index(cr, indexname, tablename):
    """Drop the given index if it exists."""
    cr.execute(SQL("DROP INDEX IF EXISTS %s", SQL.identifier(indexname)))
    _schema.debug("Table %r: dropped index %r", tablename, indexname)


def drop_view_if_exists(cr, viewname):
    kind = table_kind(cr, viewname)
    if kind == TableKind.View:
        cr.execute(SQL("DROP VIEW %s CASCADE", SQL.identifier(viewname)))
    elif kind == TableKind.Materialized:
        cr.execute(SQL("DROP MATERIALIZED VIEW %s CASCADE", SQL.identifier(viewname)))


def increment_fields_skiplock(records, *fields):
    """
    Increment 'friendly' the given `fields` of the current `records`.
    If record is locked, we just skip the update.
    It doesn't invalidate the cache since the update is not critical.

    :param records: recordset to update
    :param fields: integer fields to increment
    :returns: whether the specified fields were incremented on any record.
    :rtype: bool
    """
    if not records:
        return False

    for field in fields:
        assert records._fields[field].type == "integer"

    cr = records.env.cr
    tablename = records._table
    cr.execute(
        SQL(
            """
        UPDATE %s
           SET %s
         WHERE id IN (SELECT id FROM %s WHERE id = ANY(%s) FOR UPDATE SKIP LOCKED)
        """,
            SQL.identifier(tablename),
            SQL(", ").join(
                SQL(
                    "%s = COALESCE(%s, 0) + 1",
                    SQL.identifier(field),
                    SQL.identifier(field),
                )
                for field in fields
            ),
            SQL.identifier(tablename),
            records.ids,
        )
    )
    return bool(cr.rowcount)


def value_to_translated_trigram_pattern(value):
    """Escape value to match a translated field's trigram index content

    The trigram index function jsonb_path_query_array("column_name", '$.*')::text
    uses all translations' representations to build the indexed text. So the
    original text needs to be JSON-escaped correctly to match it.

    :param str value: value provided in domain
    :return: a pattern to match the indexed text
    """
    if len(value) < 3:
        # matching less than 3 characters will not take advantage of the index
        return "%"

    # apply JSON escaping to value; the argument ensure_ascii=False prevents
    # json.dumps from escaping unicode to ascii, which is consistent with the
    # index function jsonb_path_query_array("column_name", '$.*')::text
    json_escaped = json_dumps(value, ensure_ascii=False)[1:-1]

    # apply PG wildcard escaping to JSON-escaped text
    wildcard_escaped = _WILDCARD_ESCAPE_RE.sub(r"\\\1", json_escaped)

    # add wildcards around it to get the pattern
    return f"%{wildcard_escaped}%"


def pattern_to_translated_trigram_pattern(pattern):
    """Escape pattern to match a translated field's trigram index content

    The trigram index function jsonb_path_query_array("column_name", '$.*')::text
    uses all translations' representations to build the indexed text. So the
    original pattern needs to be JSON-escaped correctly to match it.

    :param str pattern: value provided in domain
    :return: a pattern to match the indexed text
    """
    # find the parts around (non-escaped) wildcard characters (_, %)
    sub_patterns = _TRIGRAM_PATTERN_RE.findall(pattern)

    # unescape PG wildcards from each sub pattern (\% becomes %)
    sub_texts = [_PG_UNESCAPE_RE.sub(r"\1", t) for t in sub_patterns]

    # apply JSON escaping to sub texts having at least 3 characters (" becomes \");
    # the argument ensure_ascii=False prevents from escaping unicode to ascii
    json_escaped = [
        json_dumps(t, ensure_ascii=False)[1:-1] for t in sub_texts if len(t) >= 3
    ]

    # apply PG wildcard escaping to JSON-escaped texts (% becomes \%)
    wildcard_escaped = [_WILDCARD_ESCAPE_RE.sub(r"\\\1", t) for t in json_escaped]

    # replace the original wildcard characters by %
    return f"%{'%'.join(wildcard_escaped)}%" if wildcard_escaped else "%"
