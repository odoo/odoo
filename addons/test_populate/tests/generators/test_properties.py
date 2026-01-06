from odoo.tests.common import TransactionCase

from odoo.addons.populate.generators import Generator, get_fields_vals
from odoo.addons.populate.utils.orm import VirtualField


class TestPropertiesGenerators(TransactionCase):
    """Test the properties-related generators."""

    def setUp(self):
        super().setUp()
        self.project = self.env['test_populate.project'].create({
            'name': 'Test Project',
            'attributes_definition': [],
        })

        self.task_model = self.env['test_populate.task']
        self.attributes_field = self.task_model._fields['attributes']
        self.attributes_definition_field = self.env['test_populate.project']._fields['attributes_definition']

    def test_property_definition_basic(self):
        PropertyDefinition = Generator.by_name('properties.definition')

        generator = PropertyDefinition(
            field=self.attributes_definition_field,
            env=self.env,
            valid_fields=['attributes_definition'],
            count=3,
            allowed_types=['char', 'integer', 'boolean'],
        )

        definition = generator.next({})

        self.assertIsInstance(definition, list)
        self.assertEqual(len(definition), 3)

        for prop in definition:
            self.assertIn('name', prop)
            self.assertIn('string', prop)
            self.assertIn('type', prop)
            self.assertIn(prop['type'], ['char', 'integer', 'boolean'])

    def test_property_definition_with_selection(self):
        PropertyDefinition = Generator.by_name('properties.definition')

        possible_values = ['Red', 'Green', 'Blue']
        generator = PropertyDefinition(
            field=self.attributes_definition_field,
            env=self.env,
            valid_fields=['attributes_definition'],
            count=2,
            allowed_types=['selection'],
            possible_values=possible_values,
        )

        definition = generator.next({})

        self.assertEqual(len(definition), 2)
        for prop in definition:
            self.assertEqual(prop['type'], 'selection')
            self.assertIn('selection', prop)
            selection_values = [opt[1] for opt in prop['selection']]
            self.assertEqual(set(selection_values), set(possible_values))

    def test_property_definition_with_tags(self):
        PropertyDefinition = Generator.by_name('properties.definition')

        possible_values = ['urgent', 'important', 'review']
        generator = PropertyDefinition(
            field=self.attributes_definition_field,
            env=self.env,
            valid_fields=['attributes_definition'],
            count=1,
            allowed_types=['tags'],
            possible_values=possible_values,
        )

        definition = generator.next({})

        self.assertEqual(len(definition), 1)
        prop = definition[0]
        self.assertEqual(prop['type'], 'tags')
        self.assertIn('tags', prop)
        tag_values = [tag[1] for tag in prop['tags']]
        self.assertEqual(set(tag_values), set(possible_values))

    def test_property_definition_with_virtual_fields(self):
        PropertyDefinition = Generator.by_name('properties.definition')
        PropertyProp = Generator.by_name('properties.prop')

        # Create virtual field generators for individual properties
        color_gen = PropertyProp(
            field=VirtualField('test_populate.project', 'prop_color'),
            env=self.env,
            valid_fields=['prop_color', 'prop_priority', 'attributes_definition'],
            prop_type='selection',
            string='Color',
            possible_values=['Red', 'Green', 'Blue'],
        )

        priority_gen = PropertyProp(
            field=VirtualField('test_populate.project', 'prop_priority'),
            env=self.env,
            valid_fields=['prop_color', 'prop_priority', 'attributes_definition'],
            prop_type='integer',
            string='Priority',
        )

        # Create a definition generator that depends on virtual fields
        definition_gen = PropertyDefinition(
            field=self.attributes_definition_field,
            env=self.env,
            valid_fields=['prop_color', 'prop_priority', 'attributes_definition'],
            props=['prop_color', 'prop_priority'],
        )

        # Generate the individual properties
        color_prop = color_gen.next({})
        priority_prop = priority_gen.next({})

        # Generate the definition using the properties
        known_vals = {
            'prop_color': color_prop,
            'prop_priority': priority_prop,
        }
        definition = definition_gen.next(known_vals)

        self.assertIsInstance(definition, list)
        self.assertEqual(len(definition), 2)

        for prop in definition:
            self.assertIn('name', prop)
            self.assertIn('string', prop)
            self.assertIn('type', prop)

    def test_property_definition_raises(self):
        PropertyDefinition = Generator.by_name('properties.definition')

        # Should raise if props and count are both provided
        with self.assertRaises(ValueError) as cm:
            PropertyDefinition(
                field=self.attributes_definition_field,
                env=self.env,
                props=['field1'],
                count=3,
            )
        self.assertIn("neither `count`", str(cm.exception))

        # Should raise if selection/tags without possible_values
        with self.assertRaises(ValueError) as cm:
            PropertyDefinition(
                field=self.attributes_definition_field,
                env=self.env,
                count=2,
                allowed_types=['selection'],
            )
        self.assertIn("possible_values", str(cm.exception))

    def test_property_prop_basic(self):
        PropertyProp = Generator.by_name('properties.prop')

        generator = PropertyProp(
            field=VirtualField('test_populate.project', 'color_prop'),
            env=self.env,
            valid_fields=['color_prop'],
            prop_type='char',
            string='Color Code',
        )

        prop = generator.next({})

        self.assertIsInstance(prop, dict)
        self.assertIn('name', prop)
        self.assertEqual(prop['string'], 'Color Code')
        self.assertEqual(prop['type'], 'char')

    def test_property_prop_selection(self):
        PropertyProp = Generator.by_name('properties.prop')

        possible_values = ['Low', 'Medium', 'High']
        generator = PropertyProp(
            field=VirtualField('test_populate.project', 'priority'),
            env=self.env,
            valid_fields=['priority'],
            prop_type='selection',
            string='Priority Level',
            possible_values=possible_values,
        )

        prop = generator.next({})

        self.assertEqual(prop['type'], 'selection')
        self.assertIn('selection', prop)
        selection_keys = [opt[0] for opt in prop['selection']]
        selection_values = [opt[1] for opt in prop['selection']]

        self.assertEqual(selection_keys, ['0', '1', '2'], "Keys should be string indices")
        self.assertEqual(selection_values, possible_values)

    def test_property_prop_tags(self):
        PropertyProp = Generator.by_name('properties.prop')

        possible_values = ['bug', 'feature', 'enhancement']
        generator = PropertyProp(
            field=VirtualField('test_populate.project', 'labels'),
            env=self.env,
            valid_fields=['labels'],
            prop_type='tags',
            string='Labels',
            possible_values=possible_values,
        )

        prop = generator.next({})

        self.assertEqual(prop['type'], 'tags')
        self.assertIn('tags', prop)

        # Tags should have format (id, label, color)
        for tag in prop['tags']:
            self.assertEqual(len(tag), 3)
            self.assertIsInstance(tag[0], str)  # id
            self.assertIn(tag[1], possible_values)  # label
            self.assertIsInstance(tag[2], int)  # color (1-11)
            self.assertGreaterEqual(tag[2], 1)
            self.assertLessEqual(tag[2], 11)

    def test_property_prop_invalid_type(self):
        PropertyProp = Generator.by_name('properties.prop')

        with self.assertRaises(ValueError) as cm:
            PropertyProp(
                field=VirtualField('test_populate.project', 'test'),
                env=self.env,
                valid_fields=['test'],
                prop_type='invalid_type',
                string='Test',
            )
        self.assertIn("ALLOWED_TYPES", str(cm.exception))

    def test_property_prop_missing_possible_values(self):
        PropertyProp = Generator.by_name('properties.prop')

        with self.assertRaises(ValueError) as cm:
            PropertyProp(
                field=VirtualField('test_populate.project', 'test'),
                env=self.env,
                valid_fields=['test'],
                prop_type='selection',
                string='Test Selection',
            )
        self.assertIn("possible_values", str(cm.exception))

    def test_property_value_basic(self):
        # First, set up a project with properties definition
        self.project.write({
            'attributes_definition': [{
                'name': 'color',
                'string': 'Color',
                'type': 'char',
            }, {
                'name': 'priority',
                'string': 'Priority',
                'type': 'integer',
            }],
        })

        PropertyValue = Generator.by_name('properties.value')

        generator = PropertyValue(
            field=self.attributes_field,
            env=self.env,
        )

        # PropertyValue depends on the definition_record (project_id)
        known_vals = {'project_id': self.project.id}
        values = generator.next(known_vals)

        self.assertIsInstance(values, dict)
        self.assertIn('color', values)
        self.assertIn('priority', values)

        # Values should be generated (random in this case)
        self.assertIsInstance(values['color'], str)
        self.assertIsInstance(values['priority'], int)

    def test_property_value_with_tags(self):
        self.project.write({
            'attributes_definition': [{
                'name': 'labels',
                'string': 'Labels',
                'type': 'tags',
                'tags': [
                    ('t1', 'urgent', 1),
                    ('t2', 'review', 5),
                    ('t3', 'important', 10),
                ],
            }],
        })

        PropertyValue = Generator.by_name('properties.value')

        generator = PropertyValue(
            field=self.attributes_field,
            env=self.env,
            valid_fields=['project_id', 'attributes'],
        )

        known_vals = {'project_id': self.project.id}
        values = generator.next(known_vals)

        self.assertIsInstance(values, dict)
        self.assertIn('labels', values)

        # Tags value should be a list of tag IDs
        self.assertIsInstance(values['labels'], list)
        valid_tag_ids = {'t1', 't2', 't3'}
        for tag_id in values['labels']:
            self.assertIn(tag_id, valid_tag_ids)

    def test_property_value_empty_definition(self):
        # Context: There is no entries in the containers definition (the project).
        PropertyValue = Generator.by_name('properties.value')

        generator = PropertyValue(
            field=self.attributes_field,
            env=self.env,
            valid_fields=['project_id', 'attributes'],
        )

        known_vals = {'project_id': self.project.id}
        values = generator.next(known_vals)

        self.assertEqual(values, {})

    def test_property_value_auto_depends_on_definition_record(self):
        PropertyValue = Generator.by_name('properties.value')

        generator = PropertyValue(
            field=self.attributes_field,
            env=self.env,
            valid_fields=['project_id', 'attributes'],
        )

        self.assertIn('project_id', generator.depends)

    def test_properties_integration_full_workflow(self):
        PropertyDefinition = Generator.by_name('properties.definition')
        PropertyProp = Generator.by_name('properties.prop')
        PropertyValue = Generator.by_name('properties.value')
        valid_fields = ['prop_color', 'prop_size', 'attributes_definition', 'attributes', 'project_id']

        # Define property structure using virtual fields
        color_prop_gen = PropertyProp(
            field=VirtualField('test_populate.project', 'prop_color'),
            env=self.env,
            valid_fields=valid_fields,
            prop_type='selection',
            string='Favorite Color',
            possible_values=['Red', 'Green', 'Blue'],
        )

        size_prop_gen = PropertyProp(
            field=VirtualField('test_populate.project', 'prop_size'),
            env=self.env,
            valid_fields=valid_fields,
            prop_type='integer',
            string='Size',
        )

        definition_gen = PropertyDefinition(
            field=self.attributes_definition_field,
            env=self.env,
            valid_fields=valid_fields,
            props=['prop_color', 'prop_size'],
        )

        generators = {
            'prop_color': color_prop_gen,
            'prop_size': size_prop_gen,
            'attributes_definition': definition_gen,
        }

        project_vals = get_fields_vals(generators)
        project = self.env['test_populate.project'].create({
            'name': 'Test Properties',
            **project_vals,
        })

        self.assertTrue(project.attributes_definition)
        self.assertEqual(len(project.attributes_definition), 2)

        value_gen = PropertyValue(
            field=self.attributes_field,
            env=self.env,
            valid_fields=['project_id', 'attributes'],
        )

        prop_values = value_gen.next({'project_id': project.id})

        task = self.task_model.create({
            'name': 'Test Task',
            'project_id': project.id,
            'attributes': prop_values,
        })

        self.assertTrue(task.attributes)

    def test_property_definition_convert_to_kwargs(self):
        PropertyDefinition = Generator.by_name('properties.definition')

        attrs = {
            'generator': 'properties.definition',
            'count': '5',
            'allowed_types': "['char', 'integer', 'boolean']",
            'possible_values': "['opt1', 'opt2', 'opt3']",
        }

        kwargs = PropertyDefinition.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['count'], 5)
        self.assertEqual(kwargs['allowed_types'], ['char', 'integer', 'boolean'])
        self.assertEqual(kwargs['possible_values'], ['opt1', 'opt2', 'opt3'])

    def test_property_prop_convert_to_kwargs(self):
        PropertyProp = Generator.by_name('properties.prop')

        attrs = {
            'generator': 'properties.prop',
            'prop_type': 'selection',
            'string': 'Test Property',
            'possible_values': "['A', 'B', 'C']",
        }

        kwargs = PropertyProp.convert_to_kwargs(attrs)

        self.assertEqual(kwargs['prop_type'], 'selection')
        self.assertEqual(kwargs['string'], 'Test Property')
        self.assertEqual(kwargs['possible_values'], ['A', 'B', 'C'])

    def test_property_value_falsy_dependency_returns_empty(self):
        PropertyValue = Generator.by_name('properties.value')

        generator = PropertyValue(
            field=self.attributes_field,
            env=self.env,
            valid_fields=['project_id', 'attributes'],
        )

        # With a Falsy project_id, should return an empty dict
        values = generator.next({'project_id': False})

        self.assertEqual(values, {})
