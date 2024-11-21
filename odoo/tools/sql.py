# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=sql-injection
from __future__ import annotations

import enum
import json
import logging
import re
from binascii import crc32
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from odoo.fields import Field
    from collections.abc import Iterable

import psycopg2

from .misc import named_to_positional_printf

__all__ = [
    "SQL",
    "create_index",
    "create_unique_index",
    "drop_view_if_exists",
    "escape_psql",
    "index_exists",
    "make_identifier",
    "make_index_name",
    "reverse_order",
]

_schema = logging.getLogger('odoo.schema')

IDENT_RE = re.compile(r'^[a-z0-9_][a-z0-9_$\-]*$', re.I)

_CONFDELTYPES = {
    'RESTRICT': 'r',
    'NO ACTION': 'a',
    'CASCADE': 'c',
    'SET NULL': 'n',
    'SET DEFAULT': 'd',
}


class SQL:
    """ An object that wraps SQL code with its parameters, like::

        sql = SQL("UPDATE TABLE foo SET a = %s, b = %s", 'hello', 42)
        cr.execute(sql)

    The code is given as a ``%``-format string, and supports either positional
    arguments (with `%s`) or named arguments (with `%(name)s`). Escaped
    characters (like ``"%%"``) are not supported, though. The arguments are
    meant to be merged into the code using the `%` formatting operator.

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
    `psycopg2.sql <https://www.psycopg.org/docs/sql.html>`.

    The second purpose of the wrapper is to discourage SQL injections. Indeed,
    if ``code`` is a string literal (not a dynamic string), then the SQL object
    made with ``code`` is guaranteed to be safe, provided the SQL objects
    within its parameters are themselves safe.

    The wrapper may also contain some metadata ``to_flush``.  If not ``None``,
    its value is a field which the SQL code depends on.  The metadata of a
    wrapper and its parts can be accessed by the iterator ``sql.to_flush``.
    """
    __slots__ = ('__code', '__params', '__to_flush')

    __code: str
    __params: tuple
    __to_flush: tuple

    # pylint: disable=keyword-arg-before-vararg
    def __init__(self, code: (str | SQL) = "", /, *args, to_flush: (Field | None) = None, **kwargs):
        if isinstance(code, SQL):
            if args or kwargs or to_flush:
                raise TypeError("SQL() unexpected arguments when code has type SQL")
            self.__code = code.__code
            self.__params = code.__params
            self.__to_flush = code.__to_flush
            return

        # validate the format of code and parameters
        if args and kwargs:
            raise TypeError("SQL() takes either positional arguments, or named arguments")

        if kwargs:
            code, args = named_to_positional_printf(code, kwargs)
        elif not args:
            code % ()  # check that code does not contain %s
            self.__code = code
            self.__params = ()
            self.__to_flush = () if to_flush is None else (to_flush,)
            return

        code_list = []
        params_list = []
        to_flush_list = []
        for arg in args:
            if isinstance(arg, SQL):
                code_list.append(arg.__code)
                params_list.extend(arg.__params)
                to_flush_list.extend(arg.__to_flush)
            else:
                code_list.append("%s")
                params_list.append(arg)
        if to_flush is not None:
            to_flush_list.append(to_flush)

        self.__code = code % tuple(code_list)
        self.__params = tuple(params_list)
        self.__to_flush = tuple(to_flush_list)

    @property
    def code(self) -> str:
        """ Return the combined SQL code string. """
        return self.__code

    @property
    def params(self) -> list:
        """ Return the combined SQL code params as a list of values. """
        return list(self.__params)

    @property
    def to_flush(self) -> Iterable[Field]:
        """ Return an iterator on the fields to flush in the metadata of
        ``self`` and all of its parts.
        """
        return self.__to_flush

    def __repr__(self):
        return f"SQL({', '.join(map(repr, [self.__code, *self.__params]))})"

    def __bool__(self):
        return bool(self.__code)

    def __eq__(self, other):
        return isinstance(other, SQL) and self.__code == other.__code and self.__params == other.__params

    def __iter__(self):
        """ Yields ``self.code`` and ``self.params``. This was introduced for
        backward compatibility, as it enables to access the SQL and parameters
        by deconstructing the object::

            sql = SQL(...)
            code, params = sql
        """
        yield self.code
        yield self.params

    def join(self, args: Iterable) -> SQL:
        """ Join SQL objects or parameters with ``self`` as a separator. """
        args = list(args)
        # optimizations for special cases
        if len(args) == 0:
            return SQL()
        if len(args) == 1 and isinstance(args[0], SQL):
            return args[0]
        if not self.__params:
            return SQL(self.__code.join("%s" for arg in args), *args)
        # general case: alternate args with self
        items = [self] * (len(args) * 2 - 1)
        for index, arg in enumerate(args):
            items[index * 2] = arg
        return SQL("%s" * len(items), *items)

    @classmethod
    def identifier(cls, name: str, subname: (str | None) = None, to_flush: (Field | None) = None) -> SQL:
        """ Return an SQL object that represents an identifier. """
        assert name.isidentifier() or IDENT_RE.match(name), f"{name!r} invalid for SQL.identifier()"
        if subname is None:
            return cls(f'"{name}"', to_flush=to_flush)
        assert subname.isidentifier() or IDENT_RE.match(subname), f"{subname!r} invalid for SQL.identifier()"
        return cls(f'"{name}"."{subname}"', to_flush=to_flush)


def existing_tables(cr, tablenames):
    """ Return the names of existing tables among ``tablenames``. """
    cr.execute(SQL("""
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON (n.oid = c.relnamespace)
         WHERE c.relname IN %s
           AND c.relkind IN ('r', 'v', 'm')
           AND n.nspname = current_schema
    """, tuple(tablenames)))
    return [row[0] for row in cr.fetchall()]


def table_exists(cr, tablename):
    """ Return whether the given table exists. """
    return len(existing_tables(cr, {tablename})) == 1


class TableKind(enum.Enum):
    Regular = 'r'
    Temporary = 't'
    View = 'v'
    Materialized = 'm'
    Foreign = 'f'
    Other = None


def table_kind(cr, tablename: str) -> TableKind | None:
    """ Return the kind of a table, if ``tablename`` is a regular or foreign
    table, or a view (ignores indexes, sequences, toast tables, and partitioned
    tables; unlogged tables are considered regular)
    """
    cr.execute(SQL("""
        SELECT c.relkind, c.relpersistence
          FROM pg_class c
          JOIN pg_namespace n ON (n.oid = c.relnamespace)
         WHERE c.relname = %s
           AND n.nspname = current_schema
    """, tablename))
    if not cr.rowcount:
        return None

    kind, persistence = cr.fetchone()
    # special case: permanent, temporary, and unlogged tables differ by their
    # relpersistence, they're all "ordinary" (relkind = r)
    if kind == 'r':
        return TableKind.Temporary if persistence == 't' else TableKind.Regular

    try:
        return TableKind(kind)
    except ValueError:
        # NB: or raise? unclear if it makes sense to allow table_kind to
        #     "work" with something like an index or sequence
        return TableKind.Other


# prescribed column order by type: columns aligned on 4 bytes, columns aligned
# on 1 byte, columns aligned on 8 bytes(values have been chosen to minimize
# padding in rows; unknown column types are put last)
SQL_ORDER_BY_TYPE = defaultdict(lambda: 16, {
    'int4': 1,          # 4 bytes aligned on 4 bytes
    'varchar': 2,       # variable aligned on 4 bytes
    'date': 3,          # 4 bytes aligned on 4 bytes
    'jsonb': 4,         # jsonb
    'text': 5,          # variable aligned on 4 bytes
    'numeric': 6,       # variable aligned on 4 bytes
    'bool': 7,          # 1 byte aligned on 1 byte
    'timestamp': 8,     # 8 bytes aligned on 8 bytes
    'float8': 9,        # 8 bytes aligned on 8 bytes
})


def create_model_table(cr, tablename, comment=None, columns=()):
    """ Create the table for a model. """
    colspecs = [
        SQL('id SERIAL NOT NULL'),
        *(SQL("%s %s", SQL.identifier(colname), SQL(coltype)) for colname, coltype, _ in columns),
        SQL('PRIMARY KEY(id)'),
    ]
    queries = [
        SQL("CREATE TABLE %s (%s)", SQL.identifier(tablename), SQL(", ").join(colspecs)),
    ]
    if comment:
        queries.append(SQL(
            "COMMENT ON TABLE %s IS %s",
            SQL.identifier(tablename), comment,
        ))
    for colname, _, colcomment in columns:
        queries.append(SQL(
            "COMMENT ON COLUMN %s IS %s",
            SQL.identifier(tablename, colname), colcomment,
        ))
    cr.execute(SQL("; ").join(queries))

    _schema.debug("Table %r: created", tablename)


def table_columns(cr, tablename):
    """ Return a dict mapping column names to their configuration. The latter is
        a dict with the data from the table ``information_schema.columns``.
    """
    # Do not select the field `character_octet_length` from `information_schema.columns`
    # because specific access right restriction in the context of shared hosting (Heroku, OVH, ...)
    # might prevent a postgres user to read this field.
    cr.execute(SQL(
        ''' SELECT column_name, udt_name, character_maximum_length, is_nullable
            FROM information_schema.columns WHERE table_name=%s ''',
        tablename,
    ))
    return {row['column_name']: row for row in cr.dictfetchall()}


def column_exists(cr, tablename, columnname):
    """ Return whether the given column exists. """
    cr.execute(SQL(
        """ SELECT 1 FROM information_schema.columns
            WHERE table_name=%s AND column_name=%s """,
        tablename, columnname,
    ))
    return cr.rowcount


def create_column(cr, tablename, columnname, columntype, comment=None):
    """ Create a column with the given type. """
    sql = SQL(
        "ALTER TABLE %s ADD COLUMN %s %s %s",
        SQL.identifier(tablename),
        SQL.identifier(columnname),
        SQL(columntype),
        SQL("DEFAULT false" if columntype.upper() == 'BOOLEAN' else ""),
    )
    if comment:
        sql = SQL("%s; %s", sql, SQL(
            "COMMENT ON COLUMN %s IS %s",
            SQL.identifier(tablename, columnname), comment,
        ))
    cr.execute(sql)
    _schema.debug("Table %r: added column %r of type %s", tablename, columnname, columntype)


def rename_column(cr, tablename, columnname1, columnname2):
    """ Rename the given column. """
    cr.execute(SQL(
        "ALTER TABLE %s RENAME COLUMN %s TO %s",
        SQL.identifier(tablename),
        SQL.identifier(columnname1),
        SQL.identifier(columnname2),
    ))
    _schema.debug("Table %r: renamed column %r to %r", tablename, columnname1, columnname2)


def convert_column(cr, tablename, columnname, columntype):
    """ Convert the column to the given type. """
    using = SQL("%s::%s", SQL.identifier(columnname), SQL(columntype))
    _convert_column(cr, tablename, columnname, columntype, using)


def convert_column_translatable(cr, tablename, columnname, columntype):
    """ Convert the column from/to a 'jsonb' translated field column. """
    drop_index(cr, make_index_name(tablename, columnname), tablename)
    if columntype == "jsonb":
        using = SQL(
            "CASE WHEN %s IS NOT NULL THEN jsonb_build_object('en_US', %s::varchar) END",
            SQL.identifier(columnname), SQL.identifier(columnname),
        )
    else:
        using = SQL("%s->>'en_US'", SQL.identifier(columnname))
    _convert_column(cr, tablename, columnname, columntype, using)


def _convert_column(cr, tablename, columnname, columntype, using: SQL):
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s DROP DEFAULT, ALTER COLUMN %s TYPE %s USING %s",
        SQL.identifier(tablename), SQL.identifier(columnname),
        SQL.identifier(columnname), SQL(columntype), using,
    )
    try:
        with cr.savepoint(flush=False):
            cr.execute(query, log_exceptions=False)
    except psycopg2.NotSupportedError:
        drop_depending_views(cr, tablename, columnname)
        cr.execute(query)
    _schema.debug("Table %r: column %r changed to type %s", tablename, columnname, columntype)


def drop_depending_views(cr, table, column):
    """drop views depending on a field to allow the ORM to resize it in-place"""
    for v, k in get_depending_views(cr, table, column):
        cr.execute(SQL(
            "DROP %s IF EXISTS %s CASCADE",
            SQL("MATERIALIZED VIEW" if k == "m" else "VIEW"),
            SQL.identifier(v),
        ))
        _schema.debug("Drop view %r", v)


def get_depending_views(cr, table, column):
    # http://stackoverflow.com/a/11773226/75349
    cr.execute(SQL("""
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
    """, table, column))
    return cr.fetchall()


def set_not_null(cr, tablename, columnname):
    """ Add a NOT NULL constraint on the given column. """
    query = SQL(
        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL",
        SQL.identifier(tablename), SQL.identifier(columnname),
    )
    try:
        with cr.savepoint(flush=False):
            cr.execute(query, log_exceptions=False)
            _schema.debug("Table %r: column %r: added constraint NOT NULL", tablename, columnname)
    except Exception:
        raise Exception("Table %r: unable to set NOT NULL on column %r", tablename, columnname)


def drop_not_null(cr, tablename, columnname):
    """ Drop the NOT NULL constraint on the given column. """
    cr.execute(SQL(
        "ALTER TABLE %s ALTER COLUMN %s DROP NOT NULL",
        SQL.identifier(tablename), SQL.identifier(columnname),
    ))
    _schema.debug("Table %r: column %r: dropped constraint NOT NULL", tablename, columnname)


def constraint_definition(cr, tablename, constraintname):
    """ Return the given constraint's definition. """
    cr.execute(SQL("""
        SELECT COALESCE(d.description, pg_get_constraintdef(c.oid))
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        LEFT JOIN pg_description d ON c.oid = d.objoid
        WHERE t.relname = %s AND conname = %s
    """, tablename, constraintname))
    return cr.fetchone()[0] if cr.rowcount else None


def add_constraint(cr, tablename, constraintname, definition):
    """ Add a constraint on the given table. """
    if "%" in definition:
        definition = definition.replace("%", "%%")
    query1 = SQL(
        "ALTER TABLE %s ADD CONSTRAINT %s %s",
        SQL.identifier(tablename), SQL.identifier(constraintname), SQL(definition),
    )
    query2 = SQL(
        "COMMENT ON CONSTRAINT %s ON %s IS %s",
        SQL.identifier(constraintname), SQL.identifier(tablename), definition,
    )
    try:
        with cr.savepoint(flush=False):
            cr.execute(query1, log_exceptions=False)
            cr.execute(query2, log_exceptions=False)
            _schema.debug("Table %r: added constraint %r as %s", tablename, constraintname, definition)
    except Exception:
        raise Exception("Table %r: unable to add constraint %r as %s", tablename, constraintname, definition)


def drop_constraint(cr, tablename, constraintname):
    """ drop the given constraint. """
    try:
        with cr.savepoint(flush=False):
            cr.execute(SQL(
                "ALTER TABLE %s DROP CONSTRAINT %s",
                SQL.identifier(tablename), SQL.identifier(constraintname),
            ))
            _schema.debug("Table %r: dropped constraint %r", tablename, constraintname)
    except Exception:
        _schema.warning("Table %r: unable to drop constraint %r!", tablename, constraintname)


def add_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """ Create the given foreign key, and return ``True``. """
    cr.execute(SQL(
        "ALTER TABLE %s ADD FOREIGN KEY (%s) REFERENCES %s(%s) ON DELETE %s",
        SQL.identifier(tablename1), SQL.identifier(columnname1),
        SQL.identifier(tablename2), SQL.identifier(columnname2),
        SQL(ondelete),
    ))
    _schema.debug("Table %r: added foreign key %r references %r(%r) ON DELETE %s",
                  tablename1, columnname1, tablename2, columnname2, ondelete)
    return True


def get_foreign_keys(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    deltype = _CONFDELTYPES[ondelete.upper()]
    cr.execute(SQL(
        """
            SELECT fk.conname as name
            FROM pg_constraint AS fk
            JOIN pg_class AS c1 ON fk.conrelid = c1.oid
            JOIN pg_class AS c2 ON fk.confrelid = c2.oid
            JOIN pg_attribute AS a1 ON a1.attrelid = c1.oid AND fk.conkey[1] = a1.attnum
            JOIN pg_attribute AS a2 ON a2.attrelid = c2.oid AND fk.confkey[1] = a2.attnum
            WHERE fk.contype = 'f'
            AND c1.relname = %s
            AND a1.attname = %s
            AND c2.relname = %s
            AND a2.attname = %s
            AND fk.confdeltype = %s
        """,
        tablename1, columnname1, tablename2, columnname2, deltype,
    ))
    return [r[0] for r in cr.fetchall()]


def fix_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """ Update the foreign keys between tables to match the given one, and
        return ``True`` if the given foreign key has been recreated.
    """
    # Do not use 'information_schema' here, as those views are awfully slow!
    deltype = _CONFDELTYPES.get(ondelete.upper(), 'a')
    cr.execute(SQL(
        """ SELECT con.conname, c2.relname, a2.attname, con.confdeltype as deltype
              FROM pg_constraint as con, pg_class as c1, pg_class as c2,
                   pg_attribute as a1, pg_attribute as a2
             WHERE con.contype='f' AND con.conrelid=c1.oid AND con.confrelid=c2.oid
               AND array_lower(con.conkey, 1)=1 AND con.conkey[1]=a1.attnum
               AND array_lower(con.confkey, 1)=1 AND con.confkey[1]=a2.attnum
               AND a1.attrelid=c1.oid AND a2.attrelid=c2.oid
               AND c1.relname=%s AND a1.attname=%s """,
        tablename1, columnname1,
    ))
    found = False
    for fk in cr.fetchall():
        if not found and fk[1:] == (tablename2, columnname2, deltype):
            found = True
        else:
            drop_constraint(cr, tablename1, fk[0])
    if not found:
        return add_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete)


def index_exists(cr, indexname):
    """ Return whether the given index exists. """
    cr.execute(SQL("SELECT 1 FROM pg_indexes WHERE indexname=%s", indexname))
    return cr.rowcount


def check_index_exist(cr, indexname):
    assert index_exists(cr, indexname), f"{indexname} does not exist"


def create_index(cr, indexname, tablename, expressions, method='btree', where=''):
    """ Create the given index unless it exists. """
    if index_exists(cr, indexname):
        return
    cr.execute(SQL(
        "CREATE INDEX %s ON %s USING %s (%s)%s",
        SQL.identifier(indexname),
        SQL.identifier(tablename),
        SQL(method),
        SQL(", ").join(SQL(expression) for expression in expressions),
        SQL(" WHERE %s", SQL(where)) if where else SQL(),
    ))
    _schema.debug("Table %r: created index %r (%s)", tablename, indexname, ", ".join(expressions))


def create_unique_index(cr, indexname, tablename, expressions):
    """ Create the given index unless it exists. """
    if index_exists(cr, indexname):
        return
    cr.execute(SQL(
        "CREATE UNIQUE INDEX %s ON %s (%s)",
        SQL.identifier(indexname),
        SQL.identifier(tablename),
        SQL(", ").join(SQL(expression) for expression in expressions),
    ))
    _schema.debug("Table %r: created index %r (%s)", tablename, indexname, ", ".join(expressions))


def drop_index(cr, indexname, tablename):
    """ Drop the given index if it exists. """
    cr.execute(SQL("DROP INDEX IF EXISTS %s", SQL.identifier(indexname)))
    _schema.debug("Table %r: dropped index %r", tablename, indexname)


def drop_view_if_exists(cr, viewname):
    kind = table_kind(cr, viewname)
    if kind == TableKind.View:
        cr.execute(SQL("DROP VIEW %s CASCADE", SQL.identifier(viewname)))
    elif kind == TableKind.Materialized:
        cr.execute(SQL("DROP MATERIALIZED VIEW %s CASCADE", SQL.identifier(viewname)))


def escape_psql(to_escape):
    return to_escape.replace('\\', r'\\').replace('%', r'\%').replace('_', r'\_')


def pg_varchar(size=0):
    """ Returns the VARCHAR declaration for the provided size:

    * If no size (or an empty or negative size is provided) return an
      'infinite' VARCHAR
    * Otherwise return a VARCHAR(n)

    :param int size: varchar size, optional
    :rtype: str
    """
    if size:
        if not isinstance(size, int):
            raise ValueError("VARCHAR parameter should be an int, got %s" % type(size))
        if size > 0:
            return 'VARCHAR(%d)' % size
    return 'VARCHAR'


def reverse_order(order):
    """ Reverse an ORDER BY clause """
    items = []
    for item in order.split(','):
        item = item.lower().split()
        direction = 'asc' if item[1:] == ['desc'] else 'desc'
        items.append('%s %s' % (item[0], direction))
    return ', '.join(items)


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
        assert records._fields[field].type == 'integer'

    cr = records._cr
    tablename = records._table
    cr.execute(SQL(
        """
        UPDATE %s
           SET %s
         WHERE id IN (SELECT id FROM %s WHERE id = ANY(%s) FOR UPDATE SKIP LOCKED)
        """,
        SQL.identifier(tablename),
        SQL(', ').join(
            SQL("%s = COALESCE(%s, 0) + 1", SQL.identifier(field), SQL.identifier(field))
            for field in fields
        ),
        SQL.identifier(tablename),
        records.ids,
    ))
    return bool(cr.rowcount)


def value_to_translated_trigram_pattern(value):
    """ Escape value to match a translated field's trigram index content

    The trigram index function jsonb_path_query_array("column_name", '$.*')::text
    uses all translations' representations to build the indexed text. So the
    original text needs to be JSON-escaped correctly to match it.

    :param str value: value provided in domain
    :return: a pattern to match the indexed text
    """
    if len(value) < 3:
        # matching less than 3 characters will not take advantage of the index
        return '%'

    # apply JSON escaping to value; the argument ensure_ascii=False prevents
    # json.dumps from escaping unicode to ascii, which is consistent with the
    # index function jsonb_path_query_array("column_name", '$.*')::text
    json_escaped = json.dumps(value, ensure_ascii=False)[1:-1]

    # apply PG wildcard escaping to JSON-escaped text
    wildcard_escaped = re.sub(r'(_|%|\\)', r'\\\1', json_escaped)

    # add wildcards around it to get the pattern
    return f"%{wildcard_escaped}%"


def pattern_to_translated_trigram_pattern(pattern):
    """ Escape pattern to match a translated field's trigram index content

    The trigram index function jsonb_path_query_array("column_name", '$.*')::text
    uses all translations' representations to build the indexed text. So the
    original pattern needs to be JSON-escaped correctly to match it.

    :param str pattern: value provided in domain
    :return: a pattern to match the indexed text
    """
    # find the parts around (non-escaped) wildcard characters (_, %)
    sub_patterns = re.findall(r'''
        (
            (?:.)*?           # 0 or more charaters including the newline character
            (?<!\\)(?:\\\\)*  # 0 or even number of backslashes to promise the next wildcard character is not escaped
        )
        (?:_|%|$)             # a non-escaped wildcard charater or end of the string
        ''', pattern, flags=re.VERBOSE | re.DOTALL)

    # unescape PG wildcards from each sub pattern (\% becomes %)
    sub_texts = [re.sub(r'\\(.|$)', r'\1', t, flags=re.DOTALL) for t in sub_patterns]

    # apply JSON escaping to sub texts having at least 3 characters (" becomes \");
    # the argument ensure_ascii=False prevents from escaping unicode to ascii
    json_escaped = [json.dumps(t, ensure_ascii=False)[1:-1] for t in sub_texts if len(t) >= 3]

    # apply PG wildcard escaping to JSON-escaped texts (% becomes \%)
    wildcard_escaped = [re.sub(r'(_|%|\\)', r'\\\1', t) for t in json_escaped]

    # replace the original wildcard characters by %
    return f"%{'%'.join(wildcard_escaped)}%" if wildcard_escaped else "%"


def make_identifier(identifier: str) -> str:
    """ Return ``identifier``, possibly modified to fit PostgreSQL's identifier size limitation.
    If too long, ``identifier`` is truncated and padded with a hash to make it mostly unique.
    """
    # if length exceeds the PostgreSQL limit of 63 characters.
    if len(identifier) > 63:
        # We have to fit a crc32 hash and one underscore into a 63 character
        # alias. The remaining space we can use to add a human readable prefix.
        return f"{identifier[:54]}_{crc32(identifier.encode()):08x}"
    return identifier


def make_index_name(table_name: str, column_name: str) -> str:
    """ Return an index name according to conventions for the given table and column. """
    return make_identifier(f"{table_name}__{column_name}_index")
