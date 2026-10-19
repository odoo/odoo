from odoo.tests import TransactionCase


class TestBlueprintImport(TransactionCase):

    def _create_blueprint_with_xmlid(self, xmlid_name, definition_xml=None, definition_json=None, **values):
        blueprint = self.env['populate.blueprint'].create({
            'name': values.pop('name', xmlid_name),
            'definition_xml': definition_xml,
            'definition_json': definition_json,
            **values,
        })
        self.env['ir.model.data'].create({
            'module': 'test_populate',
            'name': xmlid_name,
            'model': blueprint._name,
            'res_id': blueprint.id,
        })
        return blueprint

    def test_import_is_spliced_in_place_and_namespaced(self):
        source = self._create_blueprint_with_xmlid('import_source', '''
            <data>
                <create model="test_populate.supplier" count="2" id="suppliers">
                    <field name="name" eval="'Supplier'"/>
                </create>
                <create model="test_populate.product" count="3" id="products">
                    <field name="name" eval="'Product'"/>
                    <field name="supplier_id" ref="suppliers"/>
                </create>
            </data>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Import caller',
            'definition_xml': '''
                <data>
                    <create model="test_populate.warehouse" count="1" id="warehouse">
                        <field name="name" eval="'Warehouse'"/>
                    </create>
                    <import ref="test_populate.import_source" as="catalog">
                        <xpath expr="//create[@id='products']" position="attributes">
                            <attribute name="count">7</attribute>
                        </xpath>
                    </import>
                    <create model="test_populate.order.line" count="4" id="lines">
                        <field name="product_id" ref="catalog/products"/>
                    </create>
                </data>
            ''',
        })

        self.assertEqual(
            [block.get('id') for block in caller.definition],
            ['warehouse', 'catalog/suppliers', 'catalog/products', 'lines'],
        )
        self.assertEqual(caller.definition[2]['count'], 7)
        self.assertEqual(caller.definition[2]['fields']['supplier_id']['ref'], 'catalog/suppliers')
        self.assertEqual(caller.definition[3]['fields']['product_id']['ref'], 'catalog/products')

        session = self.env['populate.session'].create({'blueprint_id': caller.id})
        self.assertEqual(
            session.job_ids.mapped('ref'),
            ['warehouse', 'catalog/suppliers', 'catalog/products', 'lines'],
        )

        # Resolving an import instance must not modify its source blueprint.
        self.assertEqual([block.get('id') for block in source.definition], ['suppliers', 'products'])
        self.assertEqual(source.definition[1]['count'], 3)

    def test_nested_namespaces_compose(self):
        self._create_blueprint_with_xmlid('nested_source', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')
        self._create_blueprint_with_xmlid('nested_wrapper', '''
            <data>
                <import ref="test_populate.nested_source" as="catalog"/>
                <create model="test_populate.order.line" count="2" id="lines">
                    <field name="product_id" ref="catalog/products"/>
                </create>
            </data>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Nested import caller',
            'definition_xml': '<import ref="test_populate.nested_wrapper" as="sales"/>',
        })

        self.assertEqual(
            [block.get('id') for block in caller.definition],
            ['sales/catalog/products', 'sales/lines'],
        )
        self.assertEqual(
            caller.definition[1]['fields']['product_id']['ref'],
            'sales/catalog/products',
        )

    def test_import_preserves_dotted_relational_paths(self):
        self._create_blueprint_with_xmlid('dotted_source', '''
            <data>
                <create model="test_populate.supplier" count="2" id="suppliers">
                    <field name="name" eval="'Supplier'"/>
                </create>
                <write model="test_populate.product" ref="suppliers.product_ids">
                    <field name="description" eval="'Imported'"/>
                </write>
            </data>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Dotted import caller',
            'definition_xml': '<import ref="test_populate.dotted_source" as="catalog"/>',
        })

        self.assertEqual(caller.definition[1]['ref'], 'catalog/suppliers.product_ids')

    def test_import_without_namespace_preserves_ids_and_refs(self):
        self._create_blueprint_with_xmlid('unnamespaced_source', '''
            <data>
                <create model="test_populate.product" count="2" id="products">
                    <field name="name" eval="'Product'"/>
                </create>
                <write model="test_populate.product" ref="products">
                    <field name="description" eval="'Imported'"/>
                </write>
            </data>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Unnamespaced import caller',
            'definition_xml': '<import ref="test_populate.unnamespaced_source"/>',
        })

        self.assertEqual(caller.definition[0]['id'], 'products')
        self.assertEqual(caller.definition[1]['ref'], 'products')

    def test_duplicate_ids_after_import_are_rejected(self):
        self._create_blueprint_with_xmlid('duplicate_source', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Imported product'"/>
            </create>
        ''')

        with self.assertRaises(ExceptionGroup) as error:
            self.env['populate.blueprint'].create({
                'name': 'Duplicate import caller',
                'definition_xml': '''
                    <data>
                        <import ref="test_populate.duplicate_source"/>
                        <create model="test_populate.product" count="1" id="products">
                            <field name="name" eval="'Local product'"/>
                        </create>
                    </data>
                ''',
            })

        self.assertIn('declared more than once', str(error.exception.exceptions[0]))

    def test_same_source_can_be_imported_under_distinct_namespaces(self):
        self._create_blueprint_with_xmlid('repeated_source', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Repeated import caller',
            'definition_xml': '''
                <data>
                    <import ref="test_populate.repeated_source" as="sale"/>
                    <import ref="test_populate.repeated_source" as="purchase"/>
                </data>
            ''',
        })

        self.assertEqual(
            [block['id'] for block in caller.definition],
            ['sale/products', 'purchase/products'],
        )

    def test_imported_inheritance_and_caller_inheritance_compose(self):
        base = self._create_blueprint_with_xmlid('inheritance_import_base', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')
        self._create_blueprint_with_xmlid('inheritance_import_child', definition_xml='''
                <xpath expr="//create[@id='products']" position="attributes">
                    <attribute name="count">4</attribute>
                </xpath>
            ''', inherit_id=base.id)
        caller = self._create_blueprint_with_xmlid('inheritance_import_caller', '''
            <import ref="test_populate.inheritance_import_child" as="catalog"/>
        ''')

        inherited_caller = self.env['populate.blueprint'].create({
            'name': 'Inherited import caller',
            'inherit_id': caller.id,
            'definition_xml': '''
                <xpath expr="//create[@id='catalog/products']" position="attributes">
                    <attribute name="count">6</attribute>
                </xpath>
            ''',
        })

        self.assertEqual(caller.definition[0]['count'], 4)
        self.assertEqual(inherited_caller.definition[0]['count'], 6)

    def test_import_specs_can_insert_another_import(self):
        self._create_blueprint_with_xmlid('inserted_import_source', '''
            <create model="test_populate.supplier" count="1" id="suppliers">
                <field name="name" eval="'Supplier'"/>
            </create>
        ''')
        self._create_blueprint_with_xmlid('import_customization_source', '''
            <create model="test_populate.product" count="1" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')

        caller = self.env['populate.blueprint'].create({
            'name': 'Import customization caller',
            'definition_xml': '''
                <import ref="test_populate.import_customization_source" as="outer">
                    <xpath expr="." position="inside">
                        <import ref="test_populate.inserted_import_source" as="contacts"/>
                    </xpath>
                </import>
            ''',
        })

        self.assertEqual(
            [block['id'] for block in caller.definition],
            ['outer/products', 'outer/contacts/suppliers'],
        )

    def test_import_cycle_inserted_by_customization_is_rejected(self):
        self._create_blueprint_with_xmlid('customization_cycle_source', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'Product'"/>
            </create>
        ''')
        caller = self._create_blueprint_with_xmlid('customization_cycle_caller', '''
            <create model="test_populate.supplier" count="1">
                <field name="name" eval="'Supplier'"/>
            </create>
        ''')

        with self.assertRaisesRegex(ValueError, 'Recursive blueprint composition detected'):
            caller.write({'definition_xml': '''
                <import ref="test_populate.customization_cycle_source">
                    <xpath expr="." position="inside">
                        <import ref="test_populate.customization_cycle_caller"/>
                    </xpath>
                </import>
            '''})

    def test_import_rejects_json_only_target(self):
        self._create_blueprint_with_xmlid('json_source', definition_json=[{
            'operation': 'create',
            'model': 'test_populate.product',
            'count': 1,
            'fields': {'name': {'eval': "'Product'"}},
        }])

        with self.assertRaisesRegex(ValueError, 'must use XML'):
            self.env['populate.blueprint'].create({
                'name': 'JSON import caller',
                'definition_xml': '<import ref="test_populate.json_source"/>',
            })

    def test_import_cycle_is_rejected(self):
        first = self._create_blueprint_with_xmlid('cycle_first', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'First'"/>
            </create>
        ''')
        second = self._create_blueprint_with_xmlid('cycle_second', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'Second'"/>
            </create>
        ''')

        first.write({'definition_xml': '<import ref="test_populate.cycle_second"/>'})
        with self.assertRaisesRegex(ValueError, 'Recursive blueprint composition detected'):
            second.write({'definition_xml': '<import ref="test_populate.cycle_first"/>'})

    def test_mixed_import_inheritance_cycle_is_rejected(self):
        first = self._create_blueprint_with_xmlid('mixed_cycle_first', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'First'"/>
            </create>
        ''')
        self._create_blueprint_with_xmlid('mixed_cycle_second', definition_xml='''
                <xpath expr="//create" position="attributes">
                    <attribute name="count">2</attribute>
                </xpath>
            ''', inherit_id=first.id)

        with self.assertRaisesRegex(ValueError, 'Recursive blueprint composition detected'):
            first.write({'definition_xml': '<import ref="test_populate.mixed_cycle_second"/>'})

    def test_importer_definition_is_invalidated_when_source_changes(self):
        source = self._create_blueprint_with_xmlid('mutable_source', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')
        caller = self.env['populate.blueprint'].create({
            'name': 'Mutable import caller',
            'definition_xml': '<import ref="test_populate.mutable_source" as="catalog"/>',
        })
        self.assertEqual(caller.definition[0]['count'], 2)
        existing_session = self.env['populate.session'].create({'blueprint_id': caller.id})
        self.assertEqual(existing_session.job_ids.record_count, 2)

        source.write({'definition_xml': '''
            <create model="test_populate.product" count="5" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        '''})

        self.assertEqual(caller.definition[0]['count'], 5)
        new_session = self.env['populate.session'].create({'blueprint_id': caller.id})
        self.assertEqual(existing_session.job_ids.record_count, 2)
        self.assertEqual(new_session.job_ids.record_count, 5)

    def test_import_accepts_valid_namespace_syntax(self):
        self._create_blueprint_with_xmlid('namespace_source', '''
            <create model="test_populate.product" count="1" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')

        for namespace in ('catalog', '_catalog', 'catalog_2', 'catalog-2', 'Catalog2'):
            with self.subTest(namespace=namespace):
                caller = self.env['populate.blueprint'].create({
                    'name': f"Namespace {namespace}",
                    'definition_xml': (
                        f'<import ref="test_populate.namespace_source" as="{namespace}"/>'
                    ),
                })
                self.assertEqual(caller.definition[0]['id'], f'{namespace}/products')

    def test_importer_definition_is_invalidated_when_source_is_deleted(self):
        source = self._create_blueprint_with_xmlid('deleted_source', '''
            <create model="test_populate.product" count="2" id="products">
                <field name="name" eval="'Product'"/>
            </create>
        ''')
        caller = self.env['populate.blueprint'].create({
            'name': 'Deleted import caller',
            'definition_xml': '<import ref="test_populate.deleted_source" as="catalog"/>',
        })
        self.assertEqual(caller.definition[0]['id'], 'catalog/products')

        source.unlink()

        with self.assertRaisesRegex(ValueError, 'was not found'):
            caller.definition

    def test_import_rejects_misplaced_element(self):
        self._create_blueprint_with_xmlid('misplaced_source', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'Product'"/>
            </create>
        ''')

        with self.assertRaisesRegex(ValueError, 'direct child of <data>'):
            self.env['populate.blueprint'].create({
                'name': 'Misplaced import caller',
                'definition_xml': '''
                    <create model="test_populate.product" count="1">
                        <field name="name" eval="'Product'"/>
                        <import ref="test_populate.misplaced_source"/>
                    </create>
                ''',
            })

    def test_import_validates_target_and_namespace(self):
        invalid_definitions = [
            ('missing ref', '<import/>', 'fully qualified XML ID'),
            ('unqualified target', '<import ref="validation_source"/>', 'fully qualified XML ID'),
            ('missing target', '<import ref="test_populate.does_not_exist"/>', 'was not found'),
            ('wrong target model', '<import ref="base.user_admin"/>', 'not a populate blueprint'),
            ('empty namespace', '<import ref="test_populate.validation_source" as=""/>', 'cannot be empty'),
            ('invalid namespace', '<import ref="test_populate.validation_source" as="catalog/products"/>', 'Invalid import namespace'),
            ('digit-first namespace', '<import ref="test_populate.validation_source" as="2catalog"/>', 'Invalid import namespace'),
            ('hyphen-first namespace', '<import ref="test_populate.validation_source" as="-catalog"/>', 'Invalid import namespace'),
            ('dotted namespace', '<import ref="test_populate.validation_source" as="catalog.products"/>', 'Invalid import namespace'),
            ('spaced namespace', '<import ref="test_populate.validation_source" as="catalog products"/>', 'Invalid import namespace'),
            ('unknown attribute', '<import ref="test_populate.validation_source" alias="catalog"/>', 'Unknown <import> attribute'),
            ('text content', '<import ref="test_populate.validation_source">invalid</import>', 'only contain inheritance specifications'),
            ('tail text content', '''
                <import ref="test_populate.validation_source">
                    <xpath expr="." position="inside"/>invalid
                </import>
            ''', 'only contain inheritance specifications'),
        ]
        self._create_blueprint_with_xmlid('validation_source', '''
            <create model="test_populate.product" count="1">
                <field name="name" eval="'Product'"/>
            </create>
        ''')

        for reason, definition_xml, error in invalid_definitions:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, error):
                self.env['populate.blueprint'].create({
                    'name': reason,
                    'definition_xml': definition_xml,
                })
