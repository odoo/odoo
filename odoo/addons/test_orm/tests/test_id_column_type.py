from unittest.mock import patch

from odoo.modules import db
from odoo.tests import common, tagged
from odoo.tools import SQL, sql


def column_type(cr, table, column):
    cr.execute(SQL(
        """ SELECT format_type(a.atttypid, NULL)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = %s AND c.relnamespace = current_schema::regnamespace
            AND a.attname = %s AND a.attnum > 0 """,
        table, column,
    ))
    row = cr.fetchone()
    return row[0] if row else None


@tagged('post_install', '-at_install')
class TestIdColumnType(common.TransactionCase):
    """ Identifier columns follow the width the database was created with. """

    def test_registry_matches_database(self):
        """ the width detected by the registry is the one in database """
        witness = column_type(self.env.cr, db.ID_COLUMN_WITNESS_TABLE, 'id')
        expected = sql.ID_COLUMN_TYPE_BIG if witness == 'bigint' else sql.ID_COLUMN_TYPE_SMALL
        self.assertEqual(self.env.registry.id_column_type, expected)

    def test_detection_without_witness_table(self):
        """ a database being created, without base tables yet, uses bigint """
        with patch.object(db, 'ID_COLUMN_WITNESS_TABLE', 'no_such_table_at_all'):
            self.assertEqual(db.id_column_type(self.env.cr), sql.ID_COLUMN_TYPE_BIG)

    def test_identifier_columns_are_homogeneous(self):
        """ every "id" column and every column referencing one has the same width """
        expected = self.env.registry.id_column_type[0]
        self.env.cr.execute("""
            SELECT c.relname, a.attname, format_type(a.atttypid, NULL)
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relkind = 'r' AND a.attname = 'id' AND a.attnum > 0
            AND NOT a.attisdropped
            AND c.relnamespace = current_schema::regnamespace
            AND a.atttypid <> %s::regtype
        """, (expected,))
        self.assertFalse(self.env.cr.fetchall(), "some id columns have another width")

        # a foreign key never crosses widths
        self.env.cr.execute("""
            SELECT c.relname, a.attname
            FROM pg_constraint fk
            JOIN pg_class c ON c.oid = fk.conrelid
            JOIN pg_attribute a ON a.attrelid = fk.conrelid AND a.attnum = ANY (fk.conkey)
            JOIN pg_attribute r ON r.attrelid = fk.confrelid AND r.attnum = ANY (fk.confkey)
            WHERE fk.contype = 'f' AND a.atttypid <> r.atttypid
            AND c.relnamespace = current_schema::regnamespace
        """)
        self.assertFalse(self.env.cr.fetchall(), "some foreign keys mix int4 and int8")

    def test_fields_follow_the_database(self):
        """ identifier fields are given the database's width, not their own """
        expected = self.env.registry.id_column_type
        model = self.env['test_orm.message']
        for name in ('id', 'discussion', 'author'):
            field = model._fields[name]
            with self.subTest(field=name):
                self.assertTrue(field._id_column)
                self.assertEqual(field.db_column_type(model), expected)

    def test_identifier_column_is_never_converted(self):
        """ an identifier column of the other width is left untouched """
        model = self.env['test_orm.mixed']
        field = model._fields['many2one_reference']
        other = 'int4' if self.env.registry.id_column_type[0] == 'int8' else 'int8'
        column = {'udt_name': other, 'is_nullable': 'YES'}

        with patch.object(field.__class__, '_convert_db_column') as convert:
            field.update_db_column(model, column)
        self.assertFalse(convert.called, "an identifier column must not be converted")

    def test_company_dependent_identifier_stays_jsonb(self):
        """ a company-dependent many2one is stored as jsonb, not as an id column """
        model = self.env['test_orm.company']
        field = model._fields['tag_id']
        self.assertTrue(field.company_dependent)
        self.assertTrue(field._id_column)
        self.assertEqual(field.db_column_type(model), ('jsonb', 'jsonb'))
        self.assertEqual(column_type(self.env.cr, model._table, 'tag_id'), 'jsonb')

    def test_other_columns_are_still_converted(self):
        """ the exemption is limited to identifier columns """
        model = self.env['test_orm.message']
        field = model._fields['name']
        self.assertFalse(field._id_column)
        column = {'udt_name': 'int4', 'is_nullable': 'YES'}

        with patch.object(field.__class__, '_convert_db_column') as convert:
            field.update_db_column(model, column)
        self.assertTrue(convert.called, "a regular column must still be converted")
