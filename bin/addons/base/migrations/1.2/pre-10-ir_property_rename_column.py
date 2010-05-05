# -*- coding: utf8 -*-

__name__ = "ir.property: Rename column value to value_reference"

def migrate(cr, version):
    rename_column(cr, 'ir_property', 'value', 'value_reference')

def column_exists(cr, table, column):
    cr.execute("SELECT count(1)"
               "  FROM pg_class c, pg_attribute a"
               " WHERE c.relname=%s"
               "   AND c.oid=a.attrelid"
               "   AND a.attname=%s",
               (table, column))
    return cr.fetchone()[0] != 0

def rename_column(cr, table, old, new):
    if column_exists(cr, table, old) and not column_exists(cr, table, new):
        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, old, new))

