# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# pylint: disable=sql-injection

import logging
import psycopg2

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
           AND n.nspname = 'public'
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
           AND n.nspname = 'public'
    """
    cr.execute(query, (tablename,))
    return cr.fetchone()[0] if cr.rowcount else None

def create_model_table(cr, tablename, comment=None, columns=(), bigint_id=False):
    """ Create the table for a model. """
    colspecs = ['id {}SERIAL NOT NULL'.format('BIG' if bigint_id else '')] + [
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
        Also include the configuration of referenced Many2one columns.
    """
    # Do not select the field `character_octet_length` from `information_schema.columns`
    # because specific access right restriction in the context of shared hosting (Heroku, OVH, ...)
    # might prevent a postgres user to read this field.
    query='''SELECT column_name, udt_name, character_maximum_length, is_nullable
             FROM information_schema.columns WHERE table_name=%(tablename)s
             UNION
             SELECT c.table_name || '.' || c.column_name, c.udt_name, NULL, c.is_nullable
             FROM information_schema.columns c
             JOIN information_schema.constraint_column_usage ccu
                 ON ccu.table_name=c.table_name AND ccu.column_name=c.column_name
             JOIN information_schema.key_column_usage AS kcu
                 ON kcu.constraint_name=ccu.constraint_name
             WHERE kcu.table_name=%(tablename)s'''
    cr.execute(query, {'tablename': tablename})
    return {row['column_name']: row for row in cr.dictfetchall()}

def column_type(cr, table, column):
    """ Return the sql column type """
    cr.execute(
        """ SELECT udt_name FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s """, (table, column))
    row = cr.fetchone()
    return row[0] if row else None

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
    converted = False
    if columntype == 'int8' and column_type(cr, tablename, columnname) == 'int4':
        convert_column_int4_to_int8(cr, tablename, columnname)
        converted = True
    if not converted:
        try:
            with cr.savepoint(flush=False):
                cr.execute('ALTER TABLE "{}" ALTER COLUMN "{}" TYPE {}'.format(tablename, columnname, columntype),
                           log_exceptions=False)
                converted = True
        except psycopg2.NotSupportedError:
            pass
    if not converted:
        # can't do inplace change -> use a casted temp column
        query = '''
            ALTER TABLE "{0}" RENAME COLUMN "{1}" TO __temp_type_cast;
            ALTER TABLE "{0}" ADD COLUMN "{1}" {2};
            UPDATE "{0}" SET "{1}"= __temp_type_cast::{2};
            ALTER TABLE "{0}" DROP COLUMN  __temp_type_cast CASCADE;
        '''
        cr.execute(query.format(tablename, columnname, columntype))
    _schema.debug("Table %r: column %r changed to type %s", tablename, columnname, columntype)

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

def create_index(cr, indexname, tablename, expressions):
    """ Create the given index unless it exists. """
    if index_exists(cr, indexname):
        return
    args = ', '.join(expressions)
    cr.execute('CREATE INDEX "{}" ON "{}" ({})'.format(indexname, tablename, args))
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

    :type int size: varchar size, optional
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


def increment_field_skiplock(record, field):
    """
        Increment 'friendly' the [field] of the current [record](s)
        If record is locked, we just skip the update.
        It doesn't invalidate the cache since the update is not critical.

        :rtype: bool - if field has been incremented or not
    """
    if not record:
        return False

    assert record._fields[field].type == 'integer'

    cr = record._cr
    query = """
        UPDATE {table} SET {field} = {field} + 1 WHERE id IN (
            SELECT id from {table} WHERE id in %(ids)s FOR UPDATE SKIP LOCKED
        ) RETURNING id
    """.format(table=record._table, field=field)
    cr.execute(query, {'ids': tuple(record.ids)})

    return bool(cr.fetchone())


def get_fk_constraints(cr, table, column):
    """ Get the FK constraints that are based on the given column. """
    cr.execute(
        """
        SELECT kcu.table_name, kcu.column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_schema = kcu.constraint_schema
                AND tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_schema = tc.constraint_schema
                AND ccu.constraint_name = tc.constraint_name
        JOIN pg_constraint pgc
            ON pgc.conname = tc.constraint_name
                AND tc.table_name = pgc.conrelid::regclass::text
        WHERE ccu.table_name = %s
            AND ccu.column_name = %s
            AND constraint_type = 'FOREIGN KEY'
        """, (table, column))
    return cr.fetchall()


def get_sequences(cr, table, column):
    """ Get any sequences that are owned by the given column """
    cr.execute(
        """
        SELECT d.objid::regclass
        FROM pg_depend d
        JOIN pg_sequence s ON s.seqrelid = d.objid
        JOIN pg_attribute a ON a.attrelid = d.refobjid
            AND a.attnum = d.refobjsubid
        WHERE d.refobjid = %s::regclass and a.attname = %s
            AND d.refobjsubid > 0
            AND d.classid = 'pg_class'::regclass;
        """, (table, column))
    return [row[0] for row in cr.fetchall()]


def get_views(cr, table, column):
    """ Get all views that (recursively) depend on the given column.
    https://stackoverflow.com/questions/4462908
    """
    cr.execute(
        """
        WITH RECURSIVE view_deps AS (
            SELECT DISTINCT dependent_ns.nspname as schema,
                dependent_view.relname as view,
                1 AS level
            FROM pg_depend
            JOIN pg_rewrite
                ON pg_depend.objid = pg_rewrite.oid
            JOIN pg_class as dependent_view
                ON pg_rewrite.ev_class = dependent_view.oid
            JOIN pg_class as source_table
                ON pg_depend.refobjid = source_table.oid
            JOIN pg_namespace dependent_ns
                ON dependent_ns.oid = dependent_view.relnamespace
            JOIN pg_namespace source_ns
                ON source_ns.oid = source_table.relnamespace
            JOIN pg_attribute
                ON pg_depend.refobjid = pg_attribute.attrelid
                    AND pg_depend.refobjsubid = pg_attribute.attnum
            WHERE source_ns.nspname = 'public'
                AND source_table.relname = %s
                AND pg_attribute.attnum > 0
                AND pg_attribute.attname = %s
            UNION
            SELECT DISTINCT dependent_ns.nspname as schema,
                dependent_view.relname as view,
                level + 1
            FROM pg_depend
            JOIN pg_rewrite
                ON pg_depend.objid = pg_rewrite.oid
            JOIN pg_class as dependent_view
                ON pg_rewrite.ev_class = dependent_view.oid
            JOIN pg_class as source_table
                ON pg_depend.refobjid = source_table.oid
            JOIN pg_namespace dependent_ns
                ON dependent_ns.oid = dependent_view.relnamespace
            JOIN pg_namespace source_ns
                ON source_ns.oid = source_table.relnamespace
            INNER JOIN view_deps vd
                ON vd.schema = source_ns.nspname
                    AND vd.view = source_table.relname
                    AND dependent_view.relname != vd.view
        )
        SELECT view, pgv.definition
        FROM view_deps
        JOIN pg_views pgv ON pgv.viewname = view
        GROUP BY view, definition
        ORDER BY MIN(level) ASC;
        """, (table, column))
    return [row for row in cr.fetchall()]


def convert_column_int4_to_int8(cr, table, column):
    """ Migrate an integer column, and its FK reference columns recursively,
    to a bigint column. Postgresql supports changing the column type, but
    only if there are no dependent views so we drop those and recreate them
    later.
    """
    views = get_views(cr, table, column)
    for view in views:
        cr.execute('DROP VIEW "%s"' % view[0])

    _schema.info('Changing column type of %s.%s from int4 to int8', table, column)
    if column_type(cr, table, column) == 'int8':
        # Allow for the fact that a column was already (manually) migrated instead of
        # insisting on an unnecessary, time consuming 'alter column' statement.
        _schema.info('Column type of %s.%s is already int8', table, column)
    else:
        cr.execute('ALTER TABLE "{}" ALTER COLUMN "{}" TYPE {}'.format(
            table, column, 'int8'), log_exceptions=False)

    if cr._cnx.server_version >= 100000:
        # Update sequence owned by the column to BIGINT. Before Postgres 10.0,
        # sequences were BIGINT by default and the 'AS BIGINT' syntax is not
        # supported
        for sequence in get_sequences(cr, table, column):
            _schema.info('Updating type of sequence %s', sequence)
            cr.execute('ALTER SEQUENCE "{}" AS BIGINT'.format(sequence))

    for constraint in get_fk_constraints(cr, table, column):
        # Call this code recursively on any column with an FK constaint
        convert_column_int4_to_int8(cr, constraint[0], constraint[1])

    for view in views:
        cr.execute('CREATE VIEW "%s" AS %s' % view)
