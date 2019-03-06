# -*- coding: utf-8 -*-
from odoo.models import MetaModel
from odoo.tests import common


class TestReflection(common.TransactionCase):
    """ Test the reflection into 'ir.model', 'ir.model.fields', etc. """

    def test_models_fields(self):
        """ check that all models and fields are reflected as expected. """
        # retrieve the models defined in this module, and check them
        model_names = {cls._name for cls in MetaModel.module_to_models['test_new_api']}
        ir_models = self.env['ir.model'].search([('model', 'in', list(model_names))])
        self.assertEqual(len(ir_models), len(model_names))
        for ir_model in ir_models:
            model = self.env[ir_model.model]
            self.assertEqual(ir_model.name, model._description or False)
            self.assertEqual(ir_model.state, 'manual' if model._custom else 'base')
            self.assertEqual(ir_model.transient, bool(model._transient))
            self.assertItemsEqual(ir_model.mapped('field_id.name'), list(model._fields))
            for ir_field in ir_model.field_id:
                field = model._fields[ir_field.name]
                self.assertEqual(ir_field.model, field.model_name)
                self.assertEqual(ir_field.field_description, field.string)
                self.assertEqual(ir_field.help, field.help or False)
                self.assertEqual(ir_field.ttype, field.type)
                self.assertEqual(ir_field.state, 'manual' if field.manual else 'base')
                self.assertEqual(ir_field.index, bool(field.index))
                self.assertEqual(ir_field.store, bool(field.store))
                self.assertEqual(ir_field.copied, bool(field.copy))
                self.assertEqual(ir_field.related, bool(field.related) and ".".join(field.related))
                self.assertEqual(ir_field.readonly, bool(field.readonly))
                self.assertEqual(ir_field.required, bool(field.required))
                self.assertEqual(ir_field.selectable, bool(field.search or field.store))
                self.assertEqual(ir_field.translate, bool(field.translate))
                if field.relational:
                    self.assertEqual(ir_field.relation, field.comodel_name)
                if field.type == 'one2many' and field.store:
                    self.assertEqual(ir_field.relation_field, field.inverse_name)
                if field.type == 'many2many' and field.store:
                    self.assertEqual(ir_field.relation_table, field.relation)
                    self.assertEqual(ir_field.column1, field.column1)
                    self.assertEqual(ir_field.column2, field.column2)
                    relation = self.env['ir.model.relation'].search([('name', '=', field.relation)])
                    self.assertTrue(relation)
                    self.assertIn(relation.model.model, [field.model_name, field.comodel_name])


class TestSchema(common.TransactionCase):

    def get_table_data(self, tablename):
        query = ''' SELECT table_catalog, table_schema, table_name, table_type,
                           user_defined_type_catalog, user_defined_type_schema,
                           user_defined_type_name, is_insertable_into, is_typed
                    FROM information_schema.tables
                    WHERE table_name=%s '''
        self.cr.execute(query, [tablename])
        return self.cr.dictfetchone()

    def get_columns_data(self, tablename):
        query = ''' SELECT table_catalog, table_schema, table_name, column_name,
                           column_default, data_type, is_nullable, is_updatable,
                           character_maximum_length, numeric_precision,
                           numeric_precision_radix, numeric_scale,
                           datetime_precision, udt_catalog, udt_schema, udt_name
                    FROM information_schema.columns
                    WHERE table_name=%s '''
        self.cr.execute(query, [tablename])
        return {row['column_name']: row for row in self.cr.dictfetchall()}

    def get_foreign_keys(self, tablename):
        query = ''' SELECT a.table_name, a.column_name,
                           b.table_name, b.column_name, c.delete_rule
                    FROM information_schema.referential_constraints c,
                         information_schema.key_column_usage a,
                         information_schema.constraint_column_usage b
                    WHERE a.constraint_schema=c.constraint_schema
                      AND a.constraint_name=c.constraint_name
                      AND b.constraint_schema=c.constraint_schema
                      AND b.constraint_name=c.constraint_name
                      AND a.table_name=%s '''
        self.cr.execute(query, [tablename])
        return self.cr.fetchall()

    def test_00_table(self):
        """ check the database schema of a model """
        model = self.env['test_new_api.foo']
        self.assertEqual(model._table, 'test_new_api_foo')

        # retrieve schema data about that table
        table_data = self.get_table_data('test_new_api_foo')
        self.assertEqual(table_data, {
            'is_insertable_into': u'YES',
            'is_typed': u'NO',
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_foo',
            'table_schema': u'public',
            'table_type': u'BASE TABLE',
            'user_defined_type_catalog': None,
            'user_defined_type_name': None,
            'user_defined_type_schema': None,
        })

        # retrieve schema data about the table's columns
        columns_data = self.get_columns_data('test_new_api_foo')
        self.assertEqual(set(columns_data),
                         {'id', 'create_date', 'create_uid', 'write_date',
                          'write_uid', 'name', 'value1', 'value2'})

        # retrieve schema data about the table's foreign keys
        foreign_keys = self.get_foreign_keys('test_new_api_foo')
        self.assertItemsEqual(foreign_keys, [
            ('test_new_api_foo', 'create_uid', 'res_users', 'id', 'SET NULL'),
            ('test_new_api_foo', 'write_uid', 'res_users', 'id', 'SET NULL'),
        ])

    def test_10_boolean(self):
        """ check the database representation of a boolean field """
        model = self.env['test_new_api.message']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['important'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'important',
            'data_type': u'boolean',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_message',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'bool',
            'udt_schema': u'pg_catalog',
        })

    def test_10_integer(self):
        """ check the database representation of an integer field """
        model = self.env['test_new_api.category']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['color'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'color',
            'data_type': u'integer',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': 32,
            'numeric_precision_radix': 2,
            'numeric_scale': 0,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_category',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'int4',
            'udt_schema': u'pg_catalog',
        })

    def test_10_float(self):
        """ check the database representation of a float field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['number'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'number',
            'data_type': u'numeric',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': 10,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'numeric',
            'udt_schema': u'pg_catalog',
        })

    def test_10_monetary(self):
        """ check the database representation of a monetary field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['amount'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'amount',
            'data_type': u'numeric',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': 10,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'numeric',
            'udt_schema': u'pg_catalog',
        })

    def test_10_char(self):
        """ check the database representation of a char field """
        model = self.env['res.country']
        self.assertFalse(type(model).code.required)
        self.assertEqual(type(model).code.size, 2)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['code'], {
            'character_maximum_length': 2,
            'column_default': None,
            'column_name': u'code',
            'data_type': u'character varying',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'res_country',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'varchar',
            'udt_schema': u'pg_catalog',
        })

        model = self.env['test_new_api.message']
        self.assertFalse(type(model).name.required)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['name'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'name',
            'data_type': u'character varying',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_message',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'varchar',
            'udt_schema': u'pg_catalog',
        })

        model = self.env['test_new_api.category']
        self.assertTrue(type(model).name.required)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['name'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'name',
            'data_type': u'character varying',
            'datetime_precision': None,
            'is_nullable': u'NO',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_category',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'varchar',
            'udt_schema': u'pg_catalog',
        })

    def test_10_text(self):
        """ check the database representation of a text field """
        model = self.env['test_new_api.message']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['body'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'body',
            'data_type': u'text',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_message',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'text',
            'udt_schema': u'pg_catalog',
        })

    def test_10_html(self):
        """ check the database representation of an html field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['comment1'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'comment1',
            'data_type': u'text',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'text',
            'udt_schema': u'pg_catalog',
        })

    def test_10_date(self):
        """ check the database representation of a date field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['date'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'date',
            'data_type': u'date',
            'datetime_precision': 0,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'date',
            'udt_schema': u'pg_catalog',
        })

    def test_10_datetime(self):
        """ check the database representation of a datetime field """
        model = self.env['ir.property']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['value_datetime'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'value_datetime',
            'data_type': u'timestamp without time zone',
            'datetime_precision': 6,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'ir_property',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'timestamp',
            'udt_schema': u'pg_catalog',
        })

        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['create_date'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'create_date',
            'data_type': u'timestamp without time zone',
            'datetime_precision': 6,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'timestamp',
            'udt_schema': u'pg_catalog',
        })

    def test_10_selection(self):
        """ check the database representation of a selection field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['lang'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'lang',
            'data_type': u'character varying',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'varchar',
            'udt_schema': u'pg_catalog',
        })

    def test_10_reference(self):
        """ check the database representation of a reference field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['reference'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'reference',
            'data_type': u'character varying',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'varchar',
            'udt_schema': u'pg_catalog',
        })

    def test_10_many2one(self):
        """ check the database representation of a many2one field """
        model = self.env['test_new_api.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['currency_id'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': u'currency_id',
            'data_type': u'integer',
            'datetime_precision': None,
            'is_nullable': u'YES',
            'is_updatable': u'YES',
            'numeric_precision': 32,
            'numeric_precision_radix': 2,
            'numeric_scale': 0,
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_mixed',
            'table_schema': u'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': u'int4',
            'udt_schema': u'pg_catalog',
        })
        foreign_keys = self.get_foreign_keys(model._table)
        self.assertIn(
            ('test_new_api_mixed', 'currency_id', 'res_currency', 'id', 'SET NULL'),
            foreign_keys,
        )

    def test_10_many2many(self):
        """ check the database representation of a many2many field """
        model = self.env['test_new_api.discussion']
        field = type(model).categories
        comodel = self.env[field.comodel_name]
        self.assertTrue(field.relation)
        self.assertTrue(field.column1)
        self.assertTrue(field.column2)

        columns_data = self.get_columns_data(model._table)
        self.assertNotIn('categories', columns_data)

        table_data = self.get_table_data(field.relation)
        self.assertEqual(table_data, {
            'is_insertable_into': u'YES',
            'is_typed': u'NO',
            'table_catalog': self.cr.dbname,
            'table_name': u'test_new_api_discussion_category',
            'table_schema': u'public',
            'table_type': u'BASE TABLE',
            'user_defined_type_catalog': None,
            'user_defined_type_name': None,
            'user_defined_type_schema': None,
        })

        columns_data = self.get_columns_data(field.relation)
        self.assertEqual(columns_data, {
            field.column1: {
                'character_maximum_length': None,
                'column_default': None,
                'column_name': u'discussion',
                'data_type': u'integer',
                'datetime_precision': None,
                'is_nullable': u'NO',
                'is_updatable': u'YES',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'table_catalog': self.cr.dbname,
                'table_name': u'test_new_api_discussion_category',
                'table_schema': u'public',
                'udt_catalog': self.cr.dbname,
                'udt_name': u'int4',
                'udt_schema': u'pg_catalog',
            },
            field.column2: {
                'character_maximum_length': None,
                'column_default': None,
                'column_name': u'category',
                'data_type': u'integer',
                'datetime_precision': None,
                'is_nullable': u'NO',
                'is_updatable': u'YES',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'table_catalog': self.cr.dbname,
                'table_name': u'test_new_api_discussion_category',
                'table_schema': u'public',
                'udt_catalog': self.cr.dbname,
                'udt_name': u'int4',
                'udt_schema': u'pg_catalog'
            },
        })

        foreign_keys = self.get_foreign_keys(field.relation)
        self.assertItemsEqual(foreign_keys, [
            (field.relation, field.column1, model._table, 'id', 'CASCADE'),
            (field.relation, field.column2, comodel._table, 'id', 'CASCADE'),
        ])
