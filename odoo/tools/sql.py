# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# pylint: disable=sql-injection

import logging
import json
import re
import psycopg2
from psycopg2.sql import SQL, Identifier

import odoo.sql_db
from collections import defaultdict
from contextlib import closing

_schema = logging.getLogger('odoo.schema')

_CONFDELTYPES = {
    'RESTRICT': 'r',
    'NO ACTION': 'a',
    'CASCADE': 'c',
    'SET NULL': 'n',
    'SET DEFAULT': 'd',
}

def existing_tables(cr, tablenames):
    """ Return the names of existing tables among ``tablenames``. """
    query = """
        SELECT c.relname
          FROM pg_class c
          JOIN pg_namespace n ON (n.oid = c.relnamespace)
         WHERE c.relname IN %s
           AND c.relkind IN ('r', 'v', 'm')
           AND n.nspname = current_schema
    """
    cr.execute(query, [tuple(tablenames)])
    return [row[0] for row in cr.fetchall()]

def table_exists(cr, tablename):
    """ Return whether the given table exists. """
    return len(existing_tables(cr, {tablename})) == 1

def table_kind(cr, tablename):
    """ Return the kind of a table: ``'r'`` (regular table), ``'v'`` (view),
        ``'f'`` (foreign table), ``'t'`` (temporary table),
        ``'m'`` (materialized view), or ``None``.
    """
    query = """
        SELECT c.relkind
          FROM pg_class c
          JOIN pg_namespace n ON (n.oid = c.relnamespace)
         WHERE c.relname = %s
           AND n.nspname = current_schema
    """
    cr.execute(query, (tablename,))
    return cr.fetchone()[0] if cr.rowcount else None

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
    colspecs = ['id SERIAL NOT NULL'] + [
        '"{}" {}'.format(columnname, columntype)
        for columnname, columntype, columncomment in columns
    ]
    cr.execute('CREATE TABLE "{}" ({}, PRIMARY KEY(id))'.format(tablename, ", ".join(colspecs)))

    queries, params = [], []
    if comment:
        queries.append('COMMENT ON TABLE "{}" IS %s'.format(tablename))
        params.append(comment)
    for columnname, columntype, columncomment in columns:
        queries.append('COMMENT ON COLUMN "{}"."{}" IS %s'.format(tablename, columnname))
        params.append(columncomment)
    if queries:
        cr.execute("; ".join(queries), params)

    _schema.debug("Table %r: created", tablename)

def table_columns(cr, tablename):
    """ Return a dict mapping column names to their configuration. The latter is
        a dict with the data from the table ``information_schema.columns``.
    """
    # Do not select the field `character_octet_length` from `information_schema.columns`
    # because specific access right restriction in the context of shared hosting (Heroku, OVH, ...)
    # might prevent a postgres user to read this field.
    query = '''SELECT column_name, udt_name, character_maximum_length, is_nullable
               FROM information_schema.columns WHERE table_name=%s'''
    cr.execute(query, (tablename,))
    return {row['column_name']: row for row in cr.dictfetchall()}

def column_exists(cr, tablename, columnname):
    """ Return whether the given column exists. """
    query = """ SELECT 1 FROM information_schema.columns
                WHERE table_name=%s AND column_name=%s """
    cr.execute(query, (tablename, columnname))
    return cr.rowcount

def create_column(cr, tablename, columnname, columntype, comment=None):
    """ Create a column with the given type. """
    coldefault = (columntype.upper()=='BOOLEAN') and 'DEFAULT false' or ''
    cr.execute('ALTER TABLE "{}" ADD COLUMN "{}" {} {}'.format(tablename, columnname, columntype, coldefault))
    if comment:
        cr.execute('COMMENT ON COLUMN "{}"."{}" IS %s'.format(tablename, columnname), (comment,))
    _schema.debug("Table %r: added column %r of type %s", tablename, columnname, columntype)

def rename_column(cr, tablename, columnname1, columnname2):
    """ Rename the given column. """
    cr.execute('ALTER TABLE "{}" RENAME COLUMN "{}" TO "{}"'.format(tablename, columnname1, columnname2))
    _schema.debug("Table %r: renamed column %r to %r", tablename, columnname1, columnname2)

def convert_column(cr, tablename, columnname, columntype):
    """ Convert the column to the given type. """
    using = f'"{columnname}"::{columntype}'
    _convert_column(cr, tablename, columnname, columntype, using)

def convert_column_translatable(cr, tablename, columnname, columntype):
    """ Convert the column from/to a 'jsonb' translated field column. """
    drop_index(cr, f"{tablename}_{columnname}_index", tablename)
    if columntype == "jsonb":
        using = f"""CASE WHEN "{columnname}" IS NOT NULL THEN jsonb_build_object('en_US', "{columnname}"::varchar) END"""
    else:
        using = f""""{columnname}"->>'en_US'"""
    _convert_column(cr, tablename, columnname, columntype, using)

def _convert_column(cr, tablename, columnname, columntype, using):
    query = f'''
        ALTER TABLE "{tablename}"
        ALTER COLUMN "{columnname}" DROP DEFAULT,
        ALTER COLUMN "{columnname}" TYPE {columntype} USING {using}
    '''
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
        cr.execute("DROP {0} VIEW IF EXISTS {1} CASCADE".format("MATERIALIZED" if k == "m" else "", v))
        _schema.debug("Drop view %r", v)

def get_depending_views(cr, table, column):
    # http://stackoverflow.com/a/11773226/75349
    q = """
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
    """
    cr.execute(q, [table, column])
    return cr.fetchall()

def set_not_null(cr, tablename, columnname):
    """ Add a NOT NULL constraint on the given column. """
    query = 'ALTER TABLE "{}" ALTER COLUMN "{}" SET NOT NULL'.format(tablename, columnname)
    try:
        with cr.savepoint(flush=False):
            cr.execute(query, log_exceptions=False)
            _schema.debug("Table %r: column %r: added constraint NOT NULL", tablename, columnname)
    except Exception:
        raise Exception("Table %r: unable to set NOT NULL on column %r", tablename, columnname)

def drop_not_null(cr, tablename, columnname):
    """ Drop the NOT NULL constraint on the given column. """
    cr.execute('ALTER TABLE "{}" ALTER COLUMN "{}" DROP NOT NULL'.format(tablename, columnname))
    _schema.debug("Table %r: column %r: dropped constraint NOT NULL", tablename, columnname)

def constraint_definition(cr, tablename, constraintname):
    """ Return the given constraint's definition. """
    query = """
        SELECT COALESCE(d.description, pg_get_constraintdef(c.oid))
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        LEFT JOIN pg_description d ON c.oid = d.objoid
        WHERE t.relname = %s AND conname = %s;"""
    cr.execute(query, (tablename, constraintname))
    return cr.fetchone()[0] if cr.rowcount else None

def add_constraint(cr, tablename, constraintname, definition):
    """ Add a constraint on the given table. """
    query1 = 'ALTER TABLE "{}" ADD CONSTRAINT "{}" {}'.format(tablename, constraintname, definition)
    query2 = 'COMMENT ON CONSTRAINT "{}" ON "{}" IS %s'.format(constraintname, tablename)
    try:
        with cr.savepoint(flush=False):
            cr.execute(query1, log_exceptions=False)
            cr.execute(query2, (definition,), log_exceptions=False)
            _schema.debug("Table %r: added constraint %r as %s", tablename, constraintname, definition)
    except Exception:
        raise Exception("Table %r: unable to add constraint %r as %s", tablename, constraintname, definition)

def drop_constraint(cr, tablename, constraintname):
    """ drop the given constraint. """
    try:
        with cr.savepoint(flush=False):
            cr.execute('ALTER TABLE "{}" DROP CONSTRAINT "{}"'.format(tablename, constraintname))
            _schema.debug("Table %r: dropped constraint %r", tablename, constraintname)
    except Exception:
        _schema.warning("Table %r: unable to drop constraint %r!", tablename, constraintname)

def add_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """ Create the given foreign key, and return ``True``. """
    query = 'ALTER TABLE "{}" ADD FOREIGN KEY ("{}") REFERENCES "{}"("{}") ON DELETE {}'
    cr.execute(query.format(tablename1, columnname1, tablename2, columnname2, ondelete))
    _schema.debug("Table %r: added foreign key %r references %r(%r) ON DELETE %s",
                  tablename1, columnname1, tablename2, columnname2, ondelete)
    return True

def get_foreign_keys(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    cr.execute(
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
        """, [tablename1, columnname1, tablename2, columnname2, _CONFDELTYPES[ondelete.upper()]]
    )
    return [r[0] for r in cr.fetchall()]

def fix_foreign_key(cr, tablename1, columnname1, tablename2, columnname2, ondelete):
    """ Update the foreign keys between tables to match the given one, and
        return ``True`` if the given foreign key has been recreated.
    """
    # Do not use 'information_schema' here, as those views are awfully slow!
    deltype = _CONFDELTYPES.get(ondelete.upper(), 'a')
    query = """ SELECT con.conname, c2.relname, a2.attname, con.confdeltype as deltype
                  FROM pg_constraint as con, pg_class as c1, pg_class as c2,
                       pg_attribute as a1, pg_attribute as a2
                 WHERE con.contype='f' AND con.conrelid=c1.oid AND con.confrelid=c2.oid
                   AND array_lower(con.conkey, 1)=1 AND con.conkey[1]=a1.attnum
                   AND array_lower(con.confkey, 1)=1 AND con.confkey[1]=a2.attnum
                   AND a1.attrelid=c1.oid AND a2.attrelid=c2.oid
                   AND c1.relname=%s AND a1.attname=%s """
    cr.execute(query, (tablename1, columnname1))
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
    cr.execute("SELECT 1 FROM pg_indexes WHERE indexname=%s", (indexname,))
    return cr.rowcount

def check_index_exist(cr, indexname):
    assert index_exists(cr, indexname), f"{indexname} does not exist"

def create_index(cr, indexname, tablename, expressions, method='btree', where=''):
    """ Create the given index unless it exists. """
    if index_exists(cr, indexname):
        return
    args = ', '.join(expressions)
    if where:
        where = f' WHERE {where}'
    cr.execute(f'CREATE INDEX "{indexname}" ON "{tablename}" USING {method} ({args}){where}')
    _schema.debug("Table %r: created index %r (%s)", tablename, indexname, args)

def create_unique_index(cr, indexname, tablename, expressions):
    """ Create the given index unless it exists. """
    if index_exists(cr, indexname):
        return
    args = ', '.join(expressions)
    cr.execute('CREATE UNIQUE INDEX "{}" ON "{}" ({})'.format(indexname, tablename, args))
    _schema.debug("Table %r: created index %r (%s)", tablename, indexname, args)

def drop_index(cr, indexname, tablename):
    """ Drop the given index if it exists. """
    cr.execute('DROP INDEX IF EXISTS "{}"'.format(indexname))
    _schema.debug("Table %r: dropped index %r", tablename, indexname)

def drop_view_if_exists(cr, viewname):
    cr.execute("DROP view IF EXISTS %s CASCADE" % (viewname,))

def escape_psql(to_escape):
    return to_escape.replace('\\', r'\\').replace('%', '\%').replace('_', '\_')

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

    query = SQL("""
        UPDATE {table}
           SET {sets}
         WHERE id IN (SELECT id FROM {table} WHERE id = ANY(%(ids)s) FOR UPDATE SKIP LOCKED)
    """).format(
        table=Identifier(records._table),
        sets=SQL(', ').join(map(
            SQL('{0} = {0} + 1').format,
            map(Identifier, fields)
        ))
    )

    cr = records._cr
    cr.execute(query, {'ids': records.ids})
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
