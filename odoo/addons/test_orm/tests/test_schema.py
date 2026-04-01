from odoo.fields import Domain
from odoo.tests import common
from odoo.tools.translate import FIELD_TRANSLATE

from odoo.addons.base.models.ir_model import field_xmlid, model_xmlid, selection_xmlid


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
        model_names = [
            'decimal.precision.test',
            'domain.bool',
            'test_orm.any.child',
            'test_orm.any.parent',
            'test_orm.any.tag',
            'test_orm.attachment',
            'test_orm.attachment.host',
            'test_orm.autovacuumed',
            'test_orm.bar',
            'test_orm.binary_svg',
            'test_orm.cascade',
            'test_orm.category',
            'test_orm.city',
            'test_orm.company',
            'test_orm.company.attr',
            'test_orm.compute.container',
            'test_orm.compute.dynamic.depends',
            'test_orm.compute.inverse',
            'test_orm.compute.member',
            'test_orm.compute.onchange',
            'test_orm.compute.onchange.line',
            'test_orm.compute.readonly',
            'test_orm.compute.readwrite',
            'test_orm.compute.sudo',
            'test_orm.compute.unassigned',
            'test_orm.compute_editable',
            'test_orm.compute_editable.line',
            'test_orm.computed.modifier',
            'test_orm.country',
            'test_orm.course',
            'test_orm.create.performance',
            'test_orm.create.performance.line',
            'test_orm.creativework.book',
            'test_orm.creativework.edition',
            'test_orm.creativework.movie',
            'test_orm.crew',
            'test_orm.custom.table_query',
            'test_orm.custom.table_query_sql',
            'test_orm.custom.view',
            'test_orm.discussion',
            'test_orm.display',
            'test_orm.emailmessage',
            'test_orm.employer',
            'test_orm.empty_char',
            'test_orm.empty_int',
            'test_orm.field_with_caps',
            'test_orm.foo',
            'test_orm.group',
            'test_orm.hierarchy.head',
            'test_orm.hierarchy.node',
            'test_orm.indexed_translation',
            'test_orm.inverse_m2o_ref',
            'test_orm.lesson',
            'test_orm.message',
            'test_orm.mixed',
            'test_orm.mixin',
            'test_orm.model.all_access',
            'test_orm.model.no_access',
            'test_orm.model.some_access',
            'test_orm.model2.some_access',
            'test_orm.model3.some_access',
            'test_orm.model_a',
            'test_orm.model_active_field',
            'test_orm.model_b',
            'test_orm.model_binary',
            'test_orm.model_child',
            'test_orm.model_child_m2o',
            'test_orm.model_child_nocheck',
            'test_orm.model_constrained_unlinks',
            'test_orm.model_image',
            'test_orm.model_many2one_reference',
            'test_orm.model_parent',
            'test_orm.model_parent_m2o',
            'test_orm.model_selection_base',
            'test_orm.model_selection_non_stored',
            'test_orm.model_selection_related',
            'test_orm.model_selection_related_updatable',
            'test_orm.model_selection_required',
            'test_orm.model_selection_required_for_write_override',
            'test_orm.model_shared_cache_compute_line',
            'test_orm.model_shared_cache_compute_parent',
            'test_orm.modified',
            'test_orm.modified.line',
            'test_orm.monetary_base',
            'test_orm.monetary_custom',
            'test_orm.monetary_inherits',
            'test_orm.monetary_order',
            'test_orm.monetary_order_line',
            'test_orm.monetary_related',
            'test_orm.move',
            'test_orm.move_line',
            'test_orm.multi',
            'test_orm.multi.line',
            'test_orm.multi.line2',
            'test_orm.multi.tag',
            'test_orm.multi_compute_inverse',
            'test_orm.onchange.partial.view',
            'test_orm.one2many',
            'test_orm.one2many.line',
            'test_orm.order',
            'test_orm.order.line',
            'test_orm.partner',
            'test_orm.payment',
            'test_orm.person',
            'test_orm.person.account',
            'test_orm.pirate',
            'test_orm.precompute',
            'test_orm.precompute.combo',
            'test_orm.precompute.editable',
            'test_orm.precompute.line',
            'test_orm.precompute.monetary',
            'test_orm.precompute.readonly',
            'test_orm.precompute.required',
            'test_orm.prefetch',
            'test_orm.prefetch.line',
            'test_orm.prisoner',
            'test_orm.recursive',
            'test_orm.recursive.line',
            'test_orm.recursive.order',
            'test_orm.recursive.task',
            'test_orm.recursive.tree',
            'test_orm.related',
            'test_orm.related_bar',
            'test_orm.related_foo',
            'test_orm.related_inherits',
            'test_orm.related_translation_1',
            'test_orm.related_translation_2',
            'test_orm.related_translation_3',
            'test_orm.req_m2o',
            'test_orm.req_m2o_transient',
            'test_orm.selection',
            'test_orm.shared.compute',
            'test_orm.ship',
            'test_orm.state_mixin',
            'test_orm.team',
            'test_orm.team.member',
            'test_orm.transient_model',
            'test_orm.trigger.left',
            'test_orm.trigger.middle',
            'test_orm.trigger.right',
            'test_orm.unsearchable.o2m',
            'test_orm.user',
            'test_orm.view.str.id',
        ]
        ir_models = self.env['ir.model'].search([('model', 'in', model_names)])
        self.assertEqual(len(ir_models), len(model_names))
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
                            self.assertTrue(field_description['sortable'])


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
        model = self.env['test_orm.foo']
        self.assertEqual(model._table, 'test_orm_foo')

        # retrieve schema data about that table
        table_data = self.get_table_data('test_orm_foo')
        self.assertEqual(table_data, {
            'is_insertable_into': 'YES',
            'is_typed': 'NO',
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_foo',
            'table_schema': 'public',
            'table_type': 'BASE TABLE',
            'user_defined_type_catalog': None,
            'user_defined_type_name': None,
            'user_defined_type_schema': None,
        })

        # retrieve schema data about the table's columns
        columns_data = self.get_columns_data('test_orm_foo')
        self.assertEqual(set(columns_data),
                         {'id', 'create_date', 'create_uid', 'write_date',
                          'write_uid', 'name', 'value1', 'value2', 'text'})

        # retrieve schema data about the table's foreign keys
        foreign_keys = self.get_foreign_keys('test_orm_foo')
        self.assertItemsEqual(foreign_keys, [
            ('test_orm_foo', 'create_uid', 'res_users', 'id', 'SET NULL'),
            ('test_orm_foo', 'write_uid', 'res_users', 'id', 'SET NULL'),
        ])

    def test_10_boolean(self):
        """ check the database representation of a boolean field """
        model = self.env['test_orm.message']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['important'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'important',
            'data_type': 'boolean',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_message',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'bool',
            'udt_schema': 'pg_catalog',
        })

    def test_10_integer(self):
        """ check the database representation of an integer field """
        model = self.env['test_orm.category']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['color'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'color',
            'data_type': 'integer',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': 32,
            'numeric_precision_radix': 2,
            'numeric_scale': 0,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_category',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'int4',
            'udt_schema': 'pg_catalog',
        })

    def test_10_float(self):
        """ check the database representation of a float field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['number'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'number',
            'data_type': 'numeric',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': 10,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'numeric',
            'udt_schema': 'pg_catalog',
        })

    def test_10_monetary(self):
        """ check the database representation of a monetary field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['amount'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'amount',
            'data_type': 'numeric',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': 10,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'numeric',
            'udt_schema': 'pg_catalog',
        })

    def test_10_char(self):
        """ check the database representation of a char field """
        model = self.env['res.country']
        self.assertTrue(type(model).code.required)
        self.assertEqual(type(model).code.size, 2)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['code'], {
            'character_maximum_length': 2,
            'column_default': None,
            'column_name': 'code',
            'data_type': 'character varying',
            'datetime_precision': None,
            'is_nullable': 'NO',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'res_country',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'varchar',
            'udt_schema': 'pg_catalog',
        })

        model = self.env['test_orm.message']
        self.assertFalse(type(model).name.required)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['name'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'name',
            'data_type': 'character varying',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_message',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'varchar',
            'udt_schema': 'pg_catalog',
        })

        model = self.env['test_orm.category']
        self.assertTrue(type(model).name.required)
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['name'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'name',
            'data_type': 'character varying',
            'datetime_precision': None,
            'is_nullable': 'NO',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_category',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'varchar',
            'udt_schema': 'pg_catalog',
        })

    def test_10_text(self):
        """ check the database representation of a text field """
        model = self.env['test_orm.message']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['body'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'body',
            'data_type': 'text',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_message',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'text',
            'udt_schema': 'pg_catalog',
        })

    def test_10_html(self):
        """ check the database representation of an html field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['comment1'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'comment1',
            'data_type': 'text',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'text',
            'udt_schema': 'pg_catalog',
        })

    def test_10_date(self):
        """ check the database representation of a date field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['date'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'date',
            'data_type': 'date',
            'datetime_precision': 0,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'date',
            'udt_schema': 'pg_catalog',
        })

    def test_10_datetime(self):
        """ check the database representation of a datetime field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['create_date'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'create_date',
            'data_type': 'timestamp without time zone',
            'datetime_precision': 6,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'timestamp',
            'udt_schema': 'pg_catalog',
        })

    def test_10_selection(self):
        """ check the database representation of a selection field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['lang'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'lang',
            'data_type': 'character varying',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'varchar',
            'udt_schema': 'pg_catalog',
        })

    def test_10_reference(self):
        """ check the database representation of a reference field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['reference'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'reference',
            'data_type': 'character varying',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': None,
            'numeric_precision_radix': None,
            'numeric_scale': None,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'varchar',
            'udt_schema': 'pg_catalog',
        })

    def test_10_many2one(self):
        """ check the database representation of a many2one field """
        model = self.env['test_orm.mixed']
        columns_data = self.get_columns_data(model._table)
        self.assertEqual(columns_data['currency_id'], {
            'character_maximum_length': None,
            'column_default': None,
            'column_name': 'currency_id',
            'data_type': 'integer',
            'datetime_precision': None,
            'is_nullable': 'YES',
            'is_updatable': 'YES',
            'numeric_precision': 32,
            'numeric_precision_radix': 2,
            'numeric_scale': 0,
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_mixed',
            'table_schema': 'public',
            'udt_catalog': self.cr.dbname,
            'udt_name': 'int4',
            'udt_schema': 'pg_catalog',
        })
        foreign_keys = self.get_foreign_keys(model._table)
        self.assertIn(
            ('test_orm_mixed', 'currency_id', 'res_currency', 'id', 'SET NULL'),
            foreign_keys,
        )

    def test_10_many2many(self):
        """ check the database representation of a many2many field """
        model = self.env['test_orm.discussion']
        field = type(model).categories
        comodel = self.env[field.comodel_name]
        self.assertTrue(field.relation)
        self.assertTrue(field.column1)
        self.assertTrue(field.column2)

        columns_data = self.get_columns_data(model._table)
        self.assertNotIn('categories', columns_data)

        table_data = self.get_table_data(field.relation)
        self.assertEqual(table_data, {
            'is_insertable_into': 'YES',
            'is_typed': 'NO',
            'table_catalog': self.cr.dbname,
            'table_name': 'test_orm_discussion_category',
            'table_schema': 'public',
            'table_type': 'BASE TABLE',
            'user_defined_type_catalog': None,
            'user_defined_type_name': None,
            'user_defined_type_schema': None,
        })

        columns_data = self.get_columns_data(field.relation)
        self.assertEqual(columns_data, {
            field.column1: {
                'character_maximum_length': None,
                'column_default': None,
                'column_name': 'discussion',
                'data_type': 'integer',
                'datetime_precision': None,
                'is_nullable': 'NO',
                'is_updatable': 'YES',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'table_catalog': self.cr.dbname,
                'table_name': 'test_orm_discussion_category',
                'table_schema': 'public',
                'udt_catalog': self.cr.dbname,
                'udt_name': 'int4',
                'udt_schema': 'pg_catalog',
            },
            field.column2: {
                'character_maximum_length': None,
                'column_default': None,
                'column_name': 'category',
                'data_type': 'integer',
                'datetime_precision': None,
                'is_nullable': 'NO',
                'is_updatable': 'YES',
                'numeric_precision': 32,
                'numeric_precision_radix': 2,
                'numeric_scale': 0,
                'table_catalog': self.cr.dbname,
                'table_name': 'test_orm_discussion_category',
                'table_schema': 'public',
                'udt_catalog': self.cr.dbname,
                'udt_name': 'int4',
                'udt_schema': 'pg_catalog',
            },
        })

        foreign_keys = self.get_foreign_keys(field.relation)
        self.assertItemsEqual(foreign_keys, [
            (field.relation, field.column1, model._table, 'id', 'CASCADE'),
            (field.relation, field.column2, comodel._table, 'id', 'CASCADE'),
        ])

    def test_20_unique_indexes(self):
        """ Test uniqueness of indexes:
        - test_orm.order.line_short_field_name
        - test_orm.order.line.short_field_name
        """
        tablenames = ('test_orm_order', 'test_orm_order_line')
        self.env.cr.execute("""
            SELECT tablename
            FROM pg_indexes
            WHERE tablename IN %s AND indexdef LIKE %s
        """, [tablenames, '%short_field_name%'])
        tables = {table for table, in self.env.cr.fetchall()}
        self.assertEqual(tables, {'test_orm_order', 'test_orm_order_line'})

    def test_21_too_long_indexes(self):
        """ Test too long indexes name:

        Both indexes share same truncated name
        'test_orm_order_line__very_very_very_very_very_long_field_nam'
        if no strategy is done to avoid duplicate too long index names

        -  test_orm.order.line.very_very_very_very_very_long_field_name_1
        -> test_orm_order_line__very_very_very_very_very_long_field_name_1_index
        => test_orm_order_line__very_very_very_very_very_long_ea4b39c9

        -  test_orm.order.line.very_very_very_very_very_long_field_name_2
        -> test_orm_order_line__very_very_very_very_very_long_field_name_2_index
        => test_orm_order_line__very_very_very_very_very_long_dba32354
        """
        self.env.cr.execute("""
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = 'test_orm_order_line' AND indexdef LIKE %s
        """, ['%very_very_very_very_long_field_name%'])
        nb_field_index, = self.env.cr.fetchone()
        self.assertEqual(nb_field_index, 2)

    def test_one2many_domain(self):
        model = self.env['test_orm.inverse_m2o_ref']
        field = model._fields['model_ids']
        self.assertEqual(
            field.get_comodel_domain(model),
            Domain('const', '=', True) & Domain('res_model', '=', model._name),
        )
        self.assertEqual(
            field.get_description(self.env, ['domain'])['domain'],
            "([('const', '=', True)]) + ([('res_model', '=', 'test_orm.inverse_m2o_ref')])",
            "res_model should appear in the descripton of the domain",
        )
