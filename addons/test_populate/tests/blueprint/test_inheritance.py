from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestBlueprintInheritance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_blueprint = cls.env['populate.blueprint'].create({
            'name': 'Base Blueprint',
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" count="100" id="customers">
                        <field name="name" generator="textual.char" length="25"/>
                        <field name="email" generator="textual.char" length="30"/>
                        <field name="age" generator="scalar.integer" start="18" end="65"/>
                    </model>
                    <model name="test_populate.supplier" count="50" id="suppliers">
                        <field name="name" generator="textual.char" length="20"/>
                        <field name="rating" generator="scalar.float" start="1.0" end="5.0"/>
                    </model>
                </data>
            ''',
        })

    def test_inherit_modify_model_attributes(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Modify Count',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">500</attribute>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertEqual(customer_model['count'], 500)
        self.assertEqual(customer_model['ref'], 'customers')
        self.assertIn('name', customer_model['fields'])

    def test_inherit_add_model_after(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Add After',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="after">
                        <model name="test_populate.product" count="200" id="products">
                            <field name="name" generator="textual.char" length="15"/>
                            <field name="price" generator="scalar.float" start="5.0" end="100.0"/>
                        </model>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        model_names = [m['name'] for m in definition]

        self.assertEqual(len(definition), 3)
        customer_idx = model_names.index('test_populate.customer')
        product_idx = model_names.index('test_populate.product')
        self.assertEqual(product_idx, customer_idx + 1)

    def test_inherit_add_model_before(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Add Before',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.supplier" position="before">
                        <model name="test_populate.product" count="75">
                            <field name="name" generator="textual.char" length="10"/>
                        </model>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        model_names = [m['name'] for m in definition]

        self.assertEqual(len(definition), 3)
        product_idx = model_names.index('test_populate.product')
        supplier_idx = model_names.index('test_populate.supplier')
        self.assertEqual(product_idx, supplier_idx - 1)

    def test_inherit_replace_model(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Replace',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" id="customers" position="replace">
                        <model name="test_populate.customer" count="1000" id="big_customers">
                            <field name="name" generator="textual.char" length="50"/>
                            <field name="email" generator="textual.char" length="40"/>
                            <field name="is_vip" eval="True"/>
                        </model>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertEqual(len(definition), 2)
        self.assertEqual(customer_model['count'], 1000)
        self.assertEqual(customer_model['ref'], 'big_customers')
        self.assertIn('is_vip', customer_model['fields'])
        self.assertNotIn('age', customer_model['fields'])

    def test_inherit_add_field_inside_model(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Add Fields',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="inside">
                        <field name="phone" generator="textual.char" length="15"/>
                        <field name="is_vip" generator="scalar.boolean"/>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertIn('name', customer_model['fields'])
        self.assertIn('email', customer_model['fields'])
        self.assertIn('phone', customer_model['fields'])
        self.assertIn('is_vip', customer_model['fields'])

    def test_inherit_using_xpath(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - XPath',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@name='test_populate.supplier']" position="attributes">
                        <attribute name="count">200</attribute>
                    </xpath>
                    <xpath expr="//model[@name='test_populate.supplier']" position="inside">
                        <field name="is_active" generator="scalar.boolean"/>
                    </xpath>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        supplier_model = next(m for m in definition if m['name'] == 'test_populate.supplier')

        self.assertEqual(supplier_model['count'], 200)
        self.assertIn('is_active', supplier_model['fields'])

    def test_inherit_delete_model(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Delete',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.supplier" position="replace"/>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        model_names = [m['name'] for m in definition]

        self.assertEqual(len(definition), 1)
        self.assertIn('test_populate.customer', model_names)
        self.assertNotIn('test_populate.supplier', model_names)

    def test_inherit_multiple_modifications(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Multiple Mods',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">250</attribute>
                    </model>
                    <model name="test_populate.supplier" position="inside">
                        <field name="country_code" generator="choice.selection"/>
                    </model>
                    <model name="test_populate.supplier" position="after">
                        <model name="test_populate.product" count="100">
                            <field name="name" generator="textual.char"/>
                        </model>
                    </model>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')
        supplier_model = next(m for m in definition if m['name'] == 'test_populate.supplier')

        self.assertEqual(len(definition), 3)
        self.assertEqual(customer_model['count'], 250)
        self.assertIn('country_code', supplier_model['fields'])

    def test_inherit_xpath_with_id_selector(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - XPath ID',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@id='customers']" position="attributes">
                        <attribute name="count">999</attribute>
                    </xpath>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertEqual(customer_model['count'], 999)

    def test_inherit_modify_field_inside_model(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Modify Field',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@name='test_populate.customer']/field[@name='name']" position="attributes">
                        <attribute name="length">100</attribute>
                    </xpath>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertEqual(customer_model['fields']['name']['length'], '100')

    def test_inherit_replace_field(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Replace Field',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@name='test_populate.customer']/field[@name='email']" position="replace">
                        <field name="email" generator="textual.char" length="100" unique="True"/>
                    </xpath>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertEqual(customer_model['fields']['email']['length'], '100')
        self.assertEqual(customer_model['fields']['email']['unique'], 'True')

    def test_inherit_add_field_after_existing(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Field After',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@name='test_populate.customer']/field[@name='name']" position="after">
                        <field name="first_name" generator="textual.char" length="15"/>
                        <field name="last_name" generator="textual.char" length="15"/>
                    </xpath>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertIn('first_name', customer_model['fields'])
        self.assertIn('last_name', customer_model['fields'])

    def test_inherit_remove_field(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint - Remove Field',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <xpath expr="//model[@name='test_populate.customer']/field[@name='age']" position="replace"/>
                </data>
            ''',
        })

        definition = child_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')

        self.assertIn('name', customer_model['fields'])
        self.assertIn('email', customer_model['fields'])
        self.assertNotIn('age', customer_model['fields'])


class TestInheritanceChaining(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_blueprint = cls.env['populate.blueprint'].create({
            'name': 'Base Blueprint',
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" count="100" id="customers">
                        <field name="name" generator="textual.char" length="25"/>
                        <field name="email" generator="textual.char" length="30"/>
                        <field name="age" generator="scalar.integer" start="18" end="65"/>
                    </model>
                    <model name="test_populate.supplier" count="50" id="suppliers">
                        <field name="name" generator="textual.char" length="20"/>
                        <field name="rating" generator="scalar.float" start="1.0" end="5.0"/>
                    </model>
                </data>
            ''',
        })

    def test_inherit_chained_inheritance(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">200</attribute>
                    </model>
                </data>
            ''',
        })

        grandchild_blueprint = self.env['populate.blueprint'].create({
            'name': 'Grandchild Blueprint',
            'inherit_id': child_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="inside">
                        <field name="notes" generator="textual.text" length="100"/>
                    </model>
                    <model name="test_populate.supplier" position="attributes">
                        <attribute name="count">150</attribute>
                    </model>
                </data>
            ''',
        })

        definition = grandchild_blueprint.definition
        customer_model = next(m for m in definition if m['name'] == 'test_populate.customer')
        supplier_model = next(m for m in definition if m['name'] == 'test_populate.supplier')

        self.assertEqual(customer_model['count'], 200)
        self.assertIn('notes', customer_model['fields'])
        self.assertEqual(supplier_model['count'], 150)

    def test_inherit_recursion_prevention(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">200</attribute>
                    </model>
                </data>
            ''',
        })

        with self.assertRaises(ValidationError):
            self.base_blueprint.write({'inherit_id': child_blueprint.id})

    def test_inherit_self_reference_prevention(self):
        with self.assertRaises(ValidationError):
            self.base_blueprint.write({'inherit_id': self.base_blueprint.id})

    def test_inherit_from_json_only_parent_fails(self):
        json_blueprint = self.env['populate.blueprint'].create({
            'name': 'JSON Blueprint',
            'definition_json': [{'name': 'test_populate.product', 'count': 10, 'fields': {}}],
        })

        with self.assertRaises(ValueError):
            # Raised from reading .definition in the _check_definition python constraint
            self.env['populate.blueprint'].create({
                'name': 'Child of JSON Blueprint',
                'inherit_id': json_blueprint.id,
                'definition_xml': '''
                    <data>
                        <model name="test_populate.product" position="attributes">
                            <attribute name="count">50</attribute>
                        </model>
                    </data>
                ''',
            })

    def test_get_resolved_definition_without_inheritance(self):
        resolved = self.base_blueprint._get_resolved_definition()

        self.assertIsNotNone(resolved)
        self.assertIn('test_populate.customer', resolved)
        self.assertIn('test_populate.supplier', resolved)

    def test_get_resolved_definition_with_inheritance(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">777</attribute>
                    </model>
                </data>
            ''',
        })

        resolved = child_blueprint._get_resolved_definition()

        self.assertIn('count="777"', resolved)

    def test_inherit_no_xml_definition_uses_json(self):
        json_blueprint = self.env['populate.blueprint'].create({
            'name': 'JSON Only Blueprint',
            'definition_json': [
                {'name': 'test_populate.product', 'count': 42, 'fields': {'name': {'generator': 'textual.char'}}},
            ],
        })

        self.assertEqual(json_blueprint.definition[0]['count'], 42)
        self.assertIsNone(json_blueprint._get_resolved_definition())

    def test_inherited_blueprint_instantiation(self):
        child_blueprint = self.env['populate.blueprint'].create({
            'name': 'Child Blueprint for Instantiation',
            'inherit_id': self.base_blueprint.id,
            'definition_xml': '''
                <data>
                    <model name="test_populate.customer" position="attributes">
                        <attribute name="count">10</attribute>
                    </model>
                    <model name="test_populate.supplier" position="attributes">
                        <attribute name="count">5</attribute>
                    </model>
                </data>
            ''',
        })

        session = self.env['populate.session'].create({
            'blueprint_id': child_blueprint.id,
        })

        self.assertEqual(len(session.job_ids), 2)

        customer_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.customer')
        supplier_job = session.job_ids.filtered(lambda j: j.model_name == 'test_populate.supplier')

        self.assertEqual(customer_job.record_count, 10)
        self.assertEqual(supplier_job.record_count, 5)
