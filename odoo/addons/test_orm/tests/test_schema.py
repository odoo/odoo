from odoo.models import MetaModel
from odoo.tests import Like, common, tagged
from odoo.tools import SQL
from odoo.tools.translate import FIELD_TRANSLATE

from odoo.addons.base.models.ir_model import field_xmlid, model_xmlid, selection_xmlid


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestReflection(common.TransactionCase):
    """ Test the reflection into 'ir.model', 'ir.model.fields', etc. """

    def assertModelXID(self, record):
        """ Check the XML id of the given 'ir.model' record. """
        xid = model_xmlid('test_orm', record.model)
        self.assertEqual(record, self.env.ref(xid))

    def assertFieldXID(self, record):
        """ Check the XML id of the given 'ir.model.fields' record. """
        xid = field_xmlid('test_orm', record.model, record.name)
        self.assertEqual(record, self.env.ref(xid))

    def assertSelectionXID(self, record):
        """ Check the XML id of the given 'ir.model.fields.selection' record. """
        xid = selection_xmlid('test_orm', record.field_id.model, record.field_id.name, record.value)
        self.assertEqual(record, self.env.ref(xid))

    def test_models_fields(self):
        """ check that all models and fields are reflected as expected. """
        model_names = ['domain.bool', 'decimal.precision.test', *(
            cls._name
            for cls in MetaModel._module_to_models__['test_orm']
            if cls._name.startswith('test_orm')
        )]

        ir_models = self.env['ir.model'].search([('model', 'in', list(model_names))])
        self.assertEqual(len(ir_models), len(set(model_names)))
        for ir_model in ir_models:
            with self.subTest(model=ir_model.model):
                model = self.env[ir_model.model]
                self.assertModelXID(ir_model)
                self.assertEqual(ir_model.name, model._description or False)
                self.assertEqual(ir_model.state, 'manual' if model._custom else 'base')
                self.assertEqual(ir_model.transient, bool(model._transient))
                self.assertItemsEqual(ir_model.mapped('field_id.name'), list(model._fields))
                for ir_field in ir_model.field_id:
                    with self.subTest(field=ir_field.name):
                        field = model._fields[ir_field.name]
                        self.assertFieldXID(ir_field)
                        self.assertEqual(ir_field.model, field.model_name)
                        self.assertEqual(ir_field.field_description, field.string)
                        self.assertEqual(ir_field.help, field.help or False)
                        self.assertEqual(ir_field.ttype, field.type)
                        self.assertEqual(ir_field.state, 'manual' if field.manual else 'base')
                        self.assertEqual(ir_field.index, bool(field.index))
                        self.assertEqual(ir_field.store, bool(field.store))
                        self.assertEqual(ir_field.copied, bool(field.copy))
                        self.assertEqual(ir_field.related, field.related or False)
                        self.assertEqual(ir_field.readonly, bool(field.readonly))
                        self.assertEqual(ir_field.required, bool(field.required))
                        self.assertEqual(ir_field.selectable, bool(field.search or field.store))
                        self.assertEqual(FIELD_TRANSLATE.get(ir_field.translate or None, True), field.translate)
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
                        if field.type == 'selection':
                            selection = [(sel.value, sel.name) for sel in ir_field.selection_ids]
                            if isinstance(field.selection, list):
                                self.assertEqual(selection, field.selection)
                            else:
                                self.assertEqual(selection, [])
                            for sel in ir_field.selection_ids:
                                self.assertSelectionXID(sel)

                        field_description = field.get_description(self.env)
                        if field.type in ('many2many', 'one2many'):
                            self.assertFalse(field_description['sortable'])
                            self.assertIsInstance(field_description['domain'], (list, str))
                        elif field.store and field.column_type:
                            self.assertEqual(field_description['sortable'], field.type != 'binary')


@tagged('at_install', '-post_install')
class TestSchema(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env['test_orm.schema']
        cls.columns_data = cls._get_columns_data(cls.model._table)

    def _get_table_data(self, table_name):
        query = SQL("""
            SELECT table_catalog, table_schema, table_type,
                   user_defined_type_catalog, user_defined_type_schema,
                   user_defined_type_name, is_insertable_into, is_typed
              FROM information_schema.tables
             WHERE table_name=%(table_name)s
        """, table_name=table_name)
        return self.env.execute_query_dict(query)[0]

    @classmethod
    def _get_columns_data(cls, table_name):
        query = SQL("""
            SELECT character_maximum_length, column_default, column_name, data_type,
                   datetime_precision, is_nullable, is_updatable, numeric_precision,
                   numeric_precision_radix, numeric_scale, table_catalog, table_schema,
                   udt_catalog, udt_name, udt_schema
              FROM information_schema.columns
             WHERE table_name=%(table_name)s
            """, table_name=table_name,
        )
        return {row.pop('column_name'): row for row in cls.env.execute_query_dict(query)}

    def _get_foreign_keys(self, table_name, column_name):
        query = SQL("""
            SELECT kcu.table_name as table_restricted_by_constraint,
                   kcu.column_name as column_restricted_by_constraint,
                   ccu.table_name as table_used_by_constraint,
                   ccu.column_name as column_used_by_constraint,
                   rc.delete_rule
              FROM information_schema.referential_constraints rc,
                   information_schema.key_column_usage kcu,
                   information_schema.constraint_column_usage ccu
             WHERE kcu.constraint_schema=rc.constraint_schema
               AND kcu.constraint_name=rc.constraint_name
               AND ccu.constraint_schema=rc.constraint_schema
               AND ccu.constraint_name=rc.constraint_name
               AND kcu.table_name=%(table_name)s
               AND kcu.column_name=%(column_name)s
        """, table_name=table_name, column_name=column_name)
        return self.env.execute_query_dict(query)[0]

    def _get_indexdef(self, table_names, indexdef):
        if isinstance(table_names, str):
            table_names = (table_names,)

        query = SQL("""
            SELECT indexdef
              FROM pg_indexes
             WHERE tablename IN %(table_names)s
               AND indexdef LIKE %(indexdef)s
        """, table_names=table_names, indexdef=indexdef)
        return self.env.execute_query_dict(query)

    def _expected_table_data(self, override=None):
        return {
            'is_insertable_into': 'YES',
            'is_typed': 'NO',
            'table_catalog': self.cr.dbname,
            'table_schema': 'public',
            'table_type': 'BASE TABLE',
            'user_defined_type_catalog': None,
            'user_defined_type_name': None,
            'user_defined_type_schema': None,
        } | (override or {})

    def _expected_column_data(self, override=None):
        return {
            'character_maximum_length': None,
            'column_default': None,
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_schema': 'pg_catalog',
        } | (override or {})

    def test_table(self):
        table = self.model._table

        self.assertEqual(
            self._get_table_data(table),
            self._expected_table_data(),
        )

        self.assertEqual(sorted(self.columns_data.keys()), [
            'binary_without_attachment', 'boolean', 'char', 'create_date', 'create_uid',
            'currency_id', 'date', 'datetime', 'float_double_precision', 'float_numeric', 'html',
            'id', 'image_without_attachment', 'index_btree', 'index_btree_not_null',
            'index_trigram', 'integer', 'json', 'many2one_id', 'many2one_reference', 'monetary',
            'properties', 'properties_definition', 'reference', 'required', 'res_model',
            'selection', 'size', 'text', 'very_very_very_very_very_long_field_name_1',
            'very_very_very_very_very_long_field_name_2', 'write_date', 'write_uid',
        ])

        for column in ('create_uid', 'write_uid'):
            self.assertEqual(
                self._get_foreign_keys(table, column), {
                    'table_restricted_by_constraint': table,
                    'column_restricted_by_constraint': column,
                    'table_used_by_constraint': 'res_users',
                    'column_used_by_constraint': 'id',
                    'delete_rule': 'SET NULL',
                },
            )

    def test_integer_field(self):
        self.assertEqual(
            self.columns_data.get('integer'),
            self._expected_column_data(override={
                'data_type': 'integer',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'udt_name': 'int4',
            }),
        )

    def test_float_double_precision_field(self):
        self.assertEqual(
            self.columns_data.get('float_double_precision'),
            self._expected_column_data(override={
                'data_type': 'double precision',
                'numeric_precision': 53,
                'numeric_precision_radix': 2,
                'udt_name': 'float8',
            }),
        )

    def test_float_numeric_field(self):
        self.assertEqual(
            self.columns_data.get('float_numeric'),
            self._expected_column_data(override={
                'data_type': 'numeric',
                'numeric_precision_radix': 10,
                'udt_name': 'numeric',
            }),
        )

    def test_monetary_field(self):
        self.assertEqual(
            self.columns_data.get('monetary'),
            self._expected_column_data(override={
                'data_type': 'numeric',
                'numeric_precision_radix': 10,
                'udt_name': 'numeric',
            }),
        )

    def test_text_field(self):
        self.assertEqual(
            self.columns_data.get('text'),
            self._expected_column_data(override={
                'data_type': 'text',
                'udt_name': 'text',
            }),
        )

    def test_html_field(self):
        self.assertEqual(
            self.columns_data.get('html'),
            self._expected_column_data(override={
                'data_type': 'text',
                'udt_name': 'text',
            }),
        )

    def test_char_field(self):
        self.assertEqual(
            self.columns_data.get('char'),
            self._expected_column_data(override={
                'data_type': 'character varying',
                'udt_name': 'varchar',
            }),
        )

    def test_date_field(self):
        self.assertEqual(
            self.columns_data.get('date'),
            self._expected_column_data(override={
                'data_type': 'date',
                'datetime_precision': 0,
                'udt_name': 'date',
            }),
        )

    def test_datetime_field(self):
        self.assertEqual(
            self.columns_data.get('datetime'),
            self._expected_column_data(override={
                'data_type': 'timestamp without time zone',
                'datetime_precision': 6,
                'udt_name': 'timestamp',
            }),
        )

    def test_selection_field(self):
        self.assertEqual(
            self.columns_data.get('selection'),
            self._expected_column_data(override={
                'data_type': 'character varying',
                'udt_name': 'varchar',
            }),
        )

    def test_binary_field_with_attachment(self):
        self.assertIsNone(self.columns_data.get('binary_with_attachment'))

    def test_binary_field_without_attachment(self):
        self.assertEqual(
            self.columns_data.get('binary_without_attachment'),
            self._expected_column_data(override={
                'data_type': 'bytea',
                'udt_name': 'bytea',
            }),
        )

    def test_image_field_with_attachment(self):
        self.assertIsNone(self.columns_data.get('image_with_attachment'))

    def test_image_field_without_attachment(self):
        self.assertEqual(
            self.columns_data.get('image_without_attachment'),
            self._expected_column_data(override={
                'data_type': 'bytea',
                'udt_name': 'bytea',
            }),
        )

    def test_boolean_field(self):
        self.assertEqual(
            self.columns_data.get('boolean'),
            self._expected_column_data(override={
                'data_type': 'boolean',
                'udt_name': 'bool',
            }),
        )

    def test_id_field(self):
        self.assertEqual(
            self.columns_data.get('id'),
            self._expected_column_data(override={
                'column_default': "nextval('test_orm_schema_id_seq'::regclass)",
                'data_type': 'integer',
                'is_nullable': 'NO',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'udt_name': 'int4',
            }),
        )

    def test_json_field(self):
        self.assertEqual(
            self.columns_data.get('json'),
            self._expected_column_data(override={
                'data_type': 'jsonb',
                'udt_name': 'jsonb',
            }),
        )

    def test_properties_field(self):
        self.assertEqual(
            self.columns_data.get('properties'),
            self._expected_column_data(override={
                'data_type': 'jsonb',
                'udt_name': 'jsonb',
            }),
        )

    def test_properties_definition_field(self):
        self.assertEqual(
            self.columns_data.get('properties_definition'),
            self._expected_column_data(override={
                'data_type': 'jsonb',
                'udt_name': 'jsonb',
            }),
        )

    def test_reference_field(self):
        self.assertEqual(
            self.columns_data.get('reference'),
            self._expected_column_data(override={
                'data_type': 'character varying',
                'udt_name': 'varchar',
            }),
        )

    def test_many2one_reference_field(self):
        self.assertEqual(
            self.columns_data.get('many2one_reference'),
            self._expected_column_data(override={
                'data_type': 'integer',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'udt_name': 'int4',
            }),
        )

    def test_many2one_field(self):
        self.assertEqual(
           self.columns_data.get('many2one_id'),
            self._expected_column_data(override={
                'data_type': 'integer',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'udt_name': 'int4',
            }),
        )

        self.assertEqual(
            self._get_foreign_keys(self.model._table, 'many2one_id'), {
                'table_restricted_by_constraint': self.model._table,
                'column_restricted_by_constraint': 'many2one_id',
                'table_used_by_constraint': 'test_orm_schema_relations',
                'column_used_by_constraint': 'id',
                'delete_rule': 'SET NULL',
            },
        )

    def test_one2many_field(self):
        self.assertIsNone(self.columns_data.get('one2many_ids'))

    def test_many2many_field(self):
        join_table = type(self.model).many2many_ids
        comodel = self.env[join_table.comodel_name]

        self.assertIsNone(self.columns_data.get('many2many_ids'))

        self.assertEqual(
            self._get_table_data(join_table.relation),
            self._expected_table_data(),
        )

        join_table_columns_data = self._get_columns_data(join_table.relation)

        for column, model in ((join_table.column1, self.model._table), (join_table.column2, comodel._table)):
            self.assertEqual(
                join_table_columns_data.get(column),
                self._expected_column_data(override={
                    'data_type': 'integer',
                    'is_nullable': 'NO',
                    'numeric_precision': 32,
                    'numeric_precision_radix': 2,
                    'numeric_scale': 0,
                    'udt_name': 'int4',
                }),
            )

            self.assertEqual(
                self._get_foreign_keys(join_table.relation, column), {
                    'table_restricted_by_constraint': join_table.relation,
                    'column_restricted_by_constraint': column,
                    'table_used_by_constraint': model,
                    'column_used_by_constraint': 'id',
                    'delete_rule': 'CASCADE',
                },
            )

    def test_required_attribute(self):
        self.assertEqual(
            self.columns_data.get('required'),
            self._expected_column_data(override={
                'data_type': 'character varying',
                'is_nullable': 'NO',
                'udt_name': 'varchar',
            }),
        )

    def test_size_attribute(self):
        self.assertEqual(
            self.columns_data.get('size'),
            self._expected_column_data(override={
                'character_maximum_length': 3,
                'data_type': 'character varying',
                'udt_name': 'varchar',
            }),
        )

    def test_index_btree_attribute(self):
        indexdef = self._get_indexdef(self.model._table, '%(index_btree)%')

        self.assertEqual(indexdef, [{'indexdef': Like('...USING btree (index_btree)...')}])

    def test_index_btree_not_null_attribute(self):
        indexdef = self._get_indexdef(self.model._table, '%(index_btree_not_null)%')

        self.assertEqual(indexdef, [{'indexdef': Like('...USING btree (index_btree_not_null) WHERE (index_btree_not_null IS NOT NULL)...')}])

    def test_index_trigram_attribute(self):
        indexdef = self._get_indexdef(self.model._table, '%(index_trigram%gin_trgm_ops)%')

        self.assertEqual(indexdef, [{'indexdef': Like('...USING gin...index_trigram...gin_trgm_ops...')}])

    def test_index_conflict_attribute(self):
        # commit /odoo/odoo/pull/100736
        table_names = ('test_orm_schema', 'test_orm_schema_index')
        indexdef = self._get_indexdef(table_names, '%(btree)%')

        self.assertEqual(indexdef, [{'indexdef': Like('...USING btree (btree)...')}])

    def test_long_index_attribute(self):
        # commit /odoo/odoo/pull/100736
        indexdef = self._get_indexdef(self.model._table, '%very_very_very_very_long_field_name%')

        self.assertCountEqual(indexdef, [
            {'indexdef': Like('...USING btree...very_very_very_very_very_long_field_name_1...')},
            {'indexdef': Like('...USING btree...very_very_very_very_very_long_field_name_2...')},
        ])
