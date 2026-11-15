from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields, models
from odoo.models import MetaModel
from odoo.tests import Like, common, tagged
from odoo.tools import SQL, mute_logger
from odoo.tools.translate import FIELD_TRANSLATE

from odoo.addons.base.models.ir_model import field_xmlid, model_xmlid, selection_xmlid


@tagged('at_install', '-post_install')
class TestReflection(common.TransactionCase):
    """ Test the reflection into 'ir.model', 'ir.model.fields', etc. """

    def assertModelXID(self, record):
        """ Check the XML id of the given 'ir.model' record. """
        xid = model_xmlid('test_base', record.model)
        self.assertEqual(record, self.env.ref(xid))

    def assertFieldXID(self, record):
        """ Check the XML id of the given 'ir.model.fields' record. """
        xid = field_xmlid('test_base', record.model, record.name)
        self.assertEqual(record, self.env.ref(xid))

    def assertSelectionXID(self, record):
        """ Check the XML id of the given 'ir.model.fields.selection' record. """
        xid = selection_xmlid('test_base', record.field_id.model, record.field_id.name, record.value)
        self.assertEqual(record, self.env.ref(xid))

    def test_models_fields(self):
        """ check that all models and fields are reflected as expected. """
        model_names = ['domain.bool', *(
            cls._name
            for cls in MetaModel._module_to_models__['test_base']
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
                        self.assertEqual(ir_field.index, 'btree' if field.index is True else field.index or False)
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
                            selection = tuple((sel.value, sel.name) for sel in ir_field.selection_ids)
                            if isinstance(field.selection, tuple):
                                self.assertEqual(selection, field.selection)
                            else:
                                self.assertEqual(selection, ())
                            for sel in ir_field.selection_ids:
                                self.assertSelectionXID(sel)

                        field_description = field.get_description(self.env)
                        if field.type in ('many2many', 'one2many'):
                            self.assertFalse(field_description['sortable'])
                            self.assertIsInstance(field_description['domain'], (list, str))
                        elif field.store and field.column_type:
                            self.assertEqual(field_description['sortable'], field.type != 'binary')

    def test_init_models_follows_field_dependencies(self):
        """Follow current fields transitively, without following unrelated fields on added models."""
        self.env.transaction.will_change_registry()
        registry = self.registry
        body = registry['test_orm.message']._fields['body']
        message_name = registry['test_orm.related']._fields['message_name']
        inherited_message_name = registry['test_orm.related_inherits']._fields['message_name']
        foo_id = registry['test_orm.related']._fields['foo_id']
        bar_id = registry['test_orm.related_foo']._fields['bar_id']
        metadata = self.env['ir.model']
        # Simulate a replaced field, repeated paths, and a cycle; record the
        # initialized scope at its reflection boundary without replacing init_models().
        old_message_name = SimpleNamespace(model_name=message_name.model_name, name=message_name.name)
        with (
            patch.dict(registry.field_setup_dependents, {
                body: (old_message_name,),
                message_name: (inherited_message_name, inherited_message_name),
                inherited_message_name: (message_name,),
                foo_id: (bar_id,),
            }, clear=True),
            patch.object(type(metadata), '_reflect_models', wraps=metadata._reflect_models) as reflect_models,
        ):
            reflected = registry.init_models(self.cr, ['test_orm.message'], {})
            self.assertEqual(list(reflect_models.call_args.args[0]), ['test_orm.message'])
            self.assertEqual(reflected, [
                'test_orm.message', 'test_orm.related', 'test_orm.related_inherits',
            ])
            # Selecting the related model explicitly also makes its other fields traversal roots.
            reflected = registry.init_models(self.cr, [
                'test_orm.message', 'test_orm.related', 'test_orm.message',
            ], {})
            self.assertEqual(list(reflect_models.call_args.args[0]), [
                'test_orm.message', 'test_orm.related', 'test_orm.related_foo',
            ])
            self.assertEqual(reflected, [
                'test_orm.message', 'test_orm.related', 'test_orm.related_inherits', 'test_orm.related_foo',
            ])
            reflect_models.reset_mock()
            self.assertEqual(registry.init_models(self.cr, [], {}), [])
            reflect_models.assert_not_called()
            # Visit test_orm.related through non-stored message_name first,
            # then through stored foo_id. The second path must request initialization.
            with patch.dict(registry.field_setup_dependents, {inherited_message_name: (foo_id,)}):
                reflected = registry.init_models(self.cr, ['test_orm.message'], {})
                initialized = reflect_models.call_args.args[0]
                self.assertIn('test_orm.related', initialized)
                self.assertLessEqual(set(initialized), set(reflected))

    def test_init_models_follows_fields_of_loaded_module(self):
        """When loading a module, only fields defined by that module are traversal roots."""
        self.env.transaction.will_change_registry()
        registry = self.registry
        body = registry['test_orm.message']._fields['body']
        message_name = registry['test_orm.related']._fields['message_name']
        self.assertIn('test_base', body._modules)
        self.assertNotIn('test_unrelated_module', body._modules)
        with patch.dict(registry.field_setup_dependents, {body: (message_name,)}, clear=True):
            # the module defines body: follow it
            reflected = registry.init_models(self.cr, ['test_orm.message'], {'module': 'test_base'})
            self.assertEqual(reflected, ['test_orm.message', 'test_orm.related'])
            # the module defines none of the fields (e.g. methods-only extension): do not follow
            reflected = registry.init_models(self.cr, ['test_orm.message'], {'module': 'test_unrelated_module'})
            self.assertEqual(reflected, ['test_orm.message'])

    def test_partial_setup_discards_dependencies_of_rebuilt_delegated_fields(self):
        """Rebuilding a delegated model must not retain dependency caches for its old fields."""
        self.env.transaction.will_change_registry()
        old_fields = set(self.registry['test_orm.related_inherits']._fields.values())
        self.registry._setup_models__(self.cr, ['test_orm.message'])
        replaced_fields = old_fields - set(self.registry['test_orm.related_inherits']._fields.values())
        self.assertTrue(replaced_fields)
        self.assertFalse(replaced_fields & self.registry.field_depends.keys())
        self.assertFalse(replaced_fields & self.registry.field_depends_context.keys())


class SchemaCommon:
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


@tagged('at_install', '-post_install')
class TestSchema(SchemaCommon, common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env['test_orm.schema']
        cls.columns_data = cls._get_columns_data(cls.model._table)

    def test_table(self):
        table = self.env['test_orm.schema_table']._table

        self.assertEqual(
            self._get_table_data(table),
            self._expected_table_data(),
        )

        self.assertEqual(sorted(self._get_columns_data(table).keys()), [
            'boolean', 'char', 'create_date', 'create_uid', 'float', 'id', 'integer', 'write_date', 'write_uid',
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

    def test_default_on_module_install(self):
        company = self.env.ref('base.main_company')
        field = company._fields['test_orm_schema_default']

        # The main company predates test_orm, so this metadata comes from adding
        # the field to a populated table during module installation.
        # PostgreSQL stores a fast default in pg_attribute instead of rewriting
        # every row. pg_attrdef must have no entry for the column so future
        # defaults stay under ORM control.
        self.assertEqual(self.env.execute_query(SQL(
            """ SELECT attribute.atthasmissing,
                       attribute.attmissingval::text,
                       definition.oid IS NULL
                  FROM pg_attribute attribute
             LEFT JOIN pg_attrdef definition
                    ON definition.adrelid = attribute.attrelid
                   AND definition.adnum = attribute.attnum
                 WHERE attribute.attrelid = %s::regclass
                   AND attribute.attname = %s """,
            company._table, field.name,
        )), [(True, '{42}', True)])
        self.assertEqual(company.test_orm_schema_default, 42)

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
            self.columns_data.get('float'),
            self._expected_column_data(override={
                'data_type': 'double precision',
                'numeric_precision': 53,
                'numeric_precision_radix': 2,
                'udt_name': 'float8',
            }),
        )

    def test_float_numeric_field(self):
        self.assertEqual(
            self.columns_data.get('numeric'),
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
            self.columns_data.get('moment'),
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
                'table_used_by_constraint': 'test_orm_mixed_relations',
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


@tagged('at_install', '-post_install')
class TestRelatedFieldReflection(SchemaCommon, common.TransactionCase):
    """Check that changing a source field also updates fields related to it on other models.

    setUp() extends fields on test_orm.message after creating records with their
    original definitions. test_orm.related exposes stored and non-stored related fields,
    test_orm.related_inherits obtains copies through _inherits, and
    test_orm.related_stored stores related values in its own table.

    Initialization starts from only the changed source and its inheritance
    descendants. The tests check that related models are discovered, their Python
    definitions and ir.model.fields metadata are refreshed, and stored columns
    are migrated without losing data. Models reached only through non-stored fields
    need no table initialization.
    """

    def setUp(self):
        super().setUp()
        source_model_class = self.registry['test_orm.message']

        self.env['test_orm.message'].search([('code', '=', False)]).write({'code': 'Code'})
        self.message = self.env['test_orm.message'].create({
            'body': 'Existing message body', 'subject': 'Existing message subject', 'code': 'Initial', 'score': 1.25,
            'content': '<p>Existing content</p>',
        })
        self.stored_message = self.env['test_orm.related_stored'].create({'message': self.message.id})

        # Flush pending computes with the old field types before changing their definition.
        self.env.flush_all()
        self.columns_before = self._get_columns_data(self.stored_message._table)
        self.reference_table_before = self._get_foreign_keys(
            self.stored_message._table, 'message_reference_id',
        )['table_used_by_constraint']
        self.related_auto_init = self.startPatcher(patch.object(self.registry['test_orm.related'], '_auto_init'))
        self.inherited_auto_init = self.startPatcher(patch.object(self.registry['test_orm.related_inherits'], '_auto_init'))
        self.related_init = self.startPatcher(patch.object(self.registry['test_orm.related'], 'init'))
        self.inherited_init = self.startPatcher(patch.object(self.registry['test_orm.related_inherits'], 'init'))

        module = SimpleNamespace(name='test_base')
        self.env.transaction.will_change_registry()
        # Load only the extension below, rather than all original test_base model
        # definitions. Cleanup restores the module's list and removes the extension.
        self.startPatcher(patch.dict(MetaModel._module_to_models__, {module.name: []}))
        # registry.load() changes this tuple of Python base classes. SQL rollback
        # cannot undo that change, so restore it before rollback rebuilds the registry.
        self.addCleanup(setattr, source_model_class, '_base_classes__', source_model_class._base_classes__)

        class MessageExtension(models.Model):
            _inherit = 'test_orm.message'

            body = fields.Text(
                translate=True, string='Updated body', help='Updated message help', groups='base.group_system',
            )
            subject = fields.Char(translate=True, help='Updated message help', groups='base.group_system')
            code = fields.Char(size=32, trim=False, string='Expanded code', required=True, index=True)
            score = fields.Float(digits=(16, 4), min_display_digits=2, aggregator='avg')
            reference_id = fields.Many2one(
                'res.partner', context={'active_test': False}, domain=[('is_company', '=', True)],
            )
            content = fields.Html(
                sanitize=False, sanitize_tags=False, sanitize_attributes=False,
                sanitize_style=True, strip_style=True, strip_classes=True,
            )
            state = fields.Selection(selection_add=[('done', 'Done')])

        with patch.object(self.registry, 'ready', False):
            model_names = self.registry.load(module)

        # Stored translated related fields warn about multilingual recomputation;
        # these tests exercise schema and metadata updates instead.
        with mute_logger('py.warnings'):
            self.registry._setup_models__(self.cr, [])
        initial_models = self.registry.descendants(model_names, '_inherit', '_inherits')
        reflected = self.registry.init_models(self.cr, initial_models, {'module': module.name}, install=False)
        self.env['ir.model.fields']._reflect_field_groups(reflected)

    def test_related_models_are_initialized_only_for_stored_fields(self):
        """Initialize stored related fields, while only reflecting non-stored delegated fields."""
        self.related_auto_init.assert_called_once_with()
        self.inherited_auto_init.assert_not_called()
        self.related_init.assert_called_once_with()
        self.inherited_init.assert_not_called()

    def test_related_translation_updates_columns_and_preserves_values(self):
        """Inherited translation converts stored columns to JSONB without losing values or overriding translate=False."""
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                self.assertTrue(self.registry[model_name]._fields['message_name'].translate)
                self.assertEqual(self.env['ir.model.fields']._get(model_name, 'message_name').translate, 'standard')

        columns = self._get_columns_data(self.stored_message._table)
        self.assertEqual(columns['message_name']['udt_name'], 'jsonb')
        self.assertEqual(columns['message_name_untranslated']['udt_name'], 'varchar')
        self.assertFalse(self.stored_message._fields['message_name_untranslated'].translate)
        self.assertFalse(
            self.env['ir.model.fields']
            ._get(self.stored_message._name, 'message_name_untranslated')
            .translate,
        )
        self.assertEqual(self.env.execute_query(SQL(
            """
            SELECT message_name, message_name_untranslated
              FROM %s
             WHERE id = %s
            """,
            SQL.identifier(self.stored_message._table),
            self.stored_message.id,
        )), [
            ({'en_US': 'Existing message subject'}, 'Existing message subject'),
        ])
        self.assertEqual(self.stored_message.message_name, 'Existing message subject')

    def test_related_char_size_and_attributes(self):
        """Source Char changes widen the stored column and refresh size, trim, and labels on related fields."""
        table = self.env['test_orm.related_stored']._table
        self.assertEqual(self.columns_before['message_code']['character_maximum_length'], 8)
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                field = self.registry[model_name]._fields['message_code']
                self.assertEqual(field.size, 32)
                self.assertFalse(field.trim)
                self.assertEqual(field.string, 'Expanded code')
                metadata = self.env['ir.model.fields']._get(model_name, 'message_code')
                self.assertEqual(metadata.size, 32)
                self.assertEqual(metadata.field_description, 'Expanded code')
                # Ordinary related fields do not inherit required or index.
                self.assertFalse(metadata.required)
                self.assertFalse(metadata.index)

        self.assertEqual(self._get_columns_data(table)['message_code']['character_maximum_length'], 32)
        self.assertEqual(self.stored_message.message_code, 'Initial')
        source_table = self.env['test_orm.message']._table
        self.assertEqual(self._get_columns_data(source_table)['code']['is_nullable'], 'NO')
        self.assertEqual(self._get_indexdef(source_table, '%(code)%'), [
            {'indexdef': Like('...USING btree (code)...')},
        ])
        self.assertTrue(self.registry['test_orm.emailmessage']._fields['code'].required)

    def test_related_float_digits_change_column_type(self):
        """Adding source Float digits converts the stored related column to numeric and preserves its value."""
        table = self.env['test_orm.related_stored']._table
        self.assertEqual(self.columns_before['message_score']['udt_name'], 'float8')
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                field = self.registry[model_name]._fields['message_score']
                self.assertEqual(field.get_digits(self.env), (16, 4))
                self.assertEqual(field.get_min_display_digits(self.env), 2)
                self.assertEqual(field.aggregator, 'avg')

        self.assertEqual(self._get_columns_data(table)['message_score']['udt_name'], 'numeric')
        self.assertEqual(self.stored_message.message_score, 1.25)

    def test_related_comodel_changes_foreign_key(self):
        """Changing the source relation from res.users to res.partner updates related metadata and the stored foreign key."""
        table = self.env['test_orm.related_stored']._table
        self.assertEqual(self.reference_table_before, 'res_users')
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                field = self.registry[model_name]._fields['message_reference_id']
                self.assertEqual(field.comodel_name, 'res.partner')
                self.assertEqual(field.context, {'active_test': False})
                self.assertEqual(field.domain, [('is_company', '=', True)])
                self.assertEqual(self.env['ir.model.fields']._get(model_name, field.name).relation, 'res.partner')

        self.assertEqual(
            self._get_foreign_keys(table, 'message_reference_id')['table_used_by_constraint'],
            'res_partner',
        )

    def test_related_html_options_are_reflected(self):
        """Source HTML sanitization options must update related Python fields and their database metadata."""
        expected = {
            'sanitize': False, 'sanitize_tags': False, 'sanitize_attributes': False,
            'sanitize_style': True, 'strip_style': True, 'strip_classes': True,
        }
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            field = self.registry[model_name]._fields['message_content']
            metadata = self.env['ir.model.fields']._get(model_name, field.name)
            for attribute, value in expected.items():
                with self.subTest(model=model_name, attribute=attribute):
                    self.assertEqual(getattr(field, attribute), value)
                    self.assertEqual(metadata[attribute], value)

    def test_related_help_groups_and_explicit_labels(self):
        """Help and groups follow the source, while labels explicitly set on related fields remain unchanged."""
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                field = self.registry[model_name]._fields['message_name']
                metadata = self.env['ir.model.fields']._get(model_name, field.name)
                self.assertEqual(field.help, 'Updated message help')
                self.assertEqual(metadata.help, 'Updated message help')
                self.assertEqual(field.groups, 'base.group_system')
                self.assertEqual(metadata.groups, self.env.ref('base.group_system'))
                label = 'Stored Message Subject' if model_name == 'test_orm.related_stored' else 'Message Body'
                self.assertEqual(field.string, label)
                self.assertEqual(metadata.field_description, label)

    def test_related_selection_follows_source_options(self):
        """Adding a source selection option updates related choices without changing the existing stored value."""
        for model_name in ('test_orm.related', 'test_orm.related_inherits', 'test_orm.related_stored'):
            with self.subTest(model=model_name):
                self.assertEqual(
                    self.registry[model_name]._fields['message_state']._description_selection(self.env),
                    (('new', 'New'), ('done', 'Done')),
                )
        self.assertEqual(self.stored_message.message_state, 'new')
