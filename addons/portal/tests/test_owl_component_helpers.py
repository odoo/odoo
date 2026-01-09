# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from lxml import etree
from markupsafe import Markup

from odoo.tests.common import TransactionCase

from odoo.addons.portal.models.ir_qweb import owl_props, owl_component


class TestOwlComponentHelpers(TransactionCase):
    """Test the owl_props and owl_component helper functions.

    These helpers simplify embedding OWL components in server-rendered QWeb
    templates by providing easy serialization of Python objects to JSON props.
    """

    def test_owl_props_simple_dict(self):
        """Test owl_props with a simple dictionary."""
        result = owl_props({'key': 'value', 'number': 42})
        # Result should be a valid JSON string
        parsed = json.loads(str(result))
        self.assertEqual(parsed, {'key': 'value', 'number': 42})

    def test_owl_props_nested_dict(self):
        """Test owl_props with nested dictionaries."""
        result = owl_props({
            'outer': {
                'inner': 'value',
                'list': [1, 2, 3]
            }
        })
        parsed = json.loads(str(result))
        self.assertEqual(parsed['outer']['inner'], 'value')
        self.assertEqual(parsed['outer']['list'], [1, 2, 3])

    def test_owl_props_with_extra_kwargs(self):
        """Test owl_props merges extra keyword arguments."""
        result = owl_props({'key': 'value'}, extra_key='extra_value', another=123)
        parsed = json.loads(str(result))
        self.assertEqual(parsed['key'], 'value')
        self.assertEqual(parsed['extra_key'], 'extra_value')
        self.assertEqual(parsed['another'], 123)

    def test_owl_props_single_record(self):
        """Test owl_props with a single ORM record."""
        partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })
        result = owl_props(partner, fields=['name', 'email'])
        parsed = json.loads(str(result))

        # Should include id (always added) plus requested fields
        self.assertEqual(parsed['id'], partner.id)
        self.assertEqual(parsed['name'], 'Test Partner')
        self.assertEqual(parsed['email'], 'test@example.com')

    def test_owl_props_record_default_fields(self):
        """Test owl_props with a record using default fields."""
        partner = self.env['res.partner'].create({
            'name': 'Default Fields Partner',
        })
        result = owl_props(partner)
        parsed = json.loads(str(result))

        # Default should include id and display_name
        self.assertEqual(parsed['id'], partner.id)
        self.assertEqual(parsed['display_name'], 'Default Fields Partner')

    def test_owl_props_multiple_records(self):
        """Test owl_props with multiple ORM records."""
        partners = self.env['res.partner'].create([
            {'name': 'Partner 1'},
            {'name': 'Partner 2'},
        ])
        result = owl_props(partners, fields=['name'])
        parsed = json.loads(str(result))

        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['name'], 'Partner 1')
        self.assertEqual(parsed[1]['name'], 'Partner 2')

    def test_owl_props_empty_recordset(self):
        """Test owl_props with an empty recordset."""
        empty_partners = self.env['res.partner'].browse([])
        result = owl_props(empty_partners)
        parsed = json.loads(str(result))
        self.assertEqual(parsed, [])

    def test_owl_props_record_in_dict(self):
        """Test owl_props with a record nested in a dictionary."""
        partner = self.env['res.partner'].create({'name': 'Nested Partner'})
        result = owl_props({
            'partner': partner,
            'extra': 'value'
        }, fields=['name'])
        parsed = json.loads(str(result))

        self.assertEqual(parsed['extra'], 'value')
        self.assertEqual(parsed['partner']['name'], 'Nested Partner')

    def test_owl_props_xss_safety(self):
        """Test owl_props escapes potentially dangerous characters."""
        result = owl_props({'script': '</script><script>alert("xss")</script>'})
        # The result should escape < and > for safety when embedded in HTML
        result_str = str(result)
        self.assertNotIn('</script>', result_str)
        # Should use unicode escapes
        self.assertIn('\\u003c', result_str)  # <
        self.assertIn('\\u003e', result_str)  # >

    def test_owl_component_simple(self):
        """Test owl_component generates correct markup."""
        result = owl_component('my.component')

        self.assertIsInstance(result, Markup)
        tree = etree.fromstring(str(result))
        self.assertEqual(tree.tag, 'owl-component')
        self.assertEqual(tree.get('name'), 'my.component')

    def test_owl_component_with_props(self):
        """Test owl_component with props."""
        result = owl_component('my.component', {'key': 'value', 'num': 42})

        tree = etree.fromstring(str(result))
        self.assertEqual(tree.get('name'), 'my.component')

        props_json = tree.get('props')
        self.assertIsNotNone(props_json)
        parsed_props = json.loads(props_json)
        self.assertEqual(parsed_props['key'], 'value')
        self.assertEqual(parsed_props['num'], 42)

    def test_owl_component_with_attrs(self):
        """Test owl_component with additional attributes."""
        result = owl_component('my.component', {'key': 'value'}, class_='my-class', id='my-id')

        tree = etree.fromstring(str(result))
        self.assertEqual(tree.get('name'), 'my.component')
        self.assertEqual(tree.get('class'), 'my-class')
        self.assertEqual(tree.get('id'), 'my-id')

    def test_owl_component_underscore_to_hyphen(self):
        """Test owl_component handles underscores in attribute names correctly.

        - Trailing underscores are stripped (class_ -> class)
        - Internal underscores are converted to hyphens (data_test -> data-test)
        """
        result = owl_component('my.component', None, data_test='value', aria_label='label', class_='my-class')

        tree = etree.fromstring(str(result))
        self.assertEqual(tree.get('data-test'), 'value')
        self.assertEqual(tree.get('aria-label'), 'label')
        self.assertEqual(tree.get('class'), 'my-class')  # trailing underscore stripped

    def test_owl_component_escapes_name(self):
        """Test owl_component escapes special characters in name."""
        result = owl_component('my.component<script>')

        # Should not contain unescaped script tag
        self.assertNotIn('<script>', str(result))
        self.assertIn('&lt;script&gt;', str(result))

    def test_owl_component_none_attrs_ignored(self):
        """Test owl_component ignores None attribute values."""
        result = owl_component('my.component', None, class_='visible', hidden=None)

        tree = etree.fromstring(str(result))
        self.assertEqual(tree.get('class'), 'visible')
        self.assertIsNone(tree.get('hidden'))


class TestOwlHelpersInEnvironment(TransactionCase):
    """Test that owl helpers are available in the frontend template environment."""

    def _get_render_values(self, **extra):
        """Get values dict with owl helpers for template rendering.

        This directly adds the helpers without calling _prepare_frontend_environment
        to avoid dependencies on website module's request context.
        """
        return {'owl_props': owl_props, 'owl_component': owl_component, **extra}

    def test_helpers_in_frontend_environment(self):
        """Test that portal module adds owl helpers to frontend environment."""
        # Verify helpers are the expected functions
        self.assertTrue(callable(owl_props))
        self.assertTrue(callable(owl_component))
        # Verify they produce expected output types
        self.assertIsInstance(owl_props({'test': 1}), str)
        self.assertIsInstance(owl_component('test'), Markup)

    def test_render_template_with_owl_props(self):
        """Test rendering a template using owl_props helper."""
        view = self.env['ir.ui.view'].create({
            'key': 'portal.test_owl_props',
            'type': 'qweb',
            'arch': '''<t t-name="test_owl_props">
                <owl-component name="test.component" t-att-props="owl_props({'key': value})"/>
            </t>'''
        })

        values = self._get_render_values(value='test_value')
        html = view._render_template(view.id, values)
        tree = etree.fromstring(f'<root>{html}</root>')
        owl_comp = tree.find('.//owl-component')

        self.assertIsNotNone(owl_comp)
        self.assertEqual(owl_comp.get('name'), 'test.component')

        props = json.loads(owl_comp.get('props'))
        self.assertEqual(props['key'], 'test_value')

    def test_render_template_with_owl_component(self):
        """Test rendering a template using owl_component helper."""
        view = self.env['ir.ui.view'].create({
            'key': 'portal.test_owl_component',
            'type': 'qweb',
            'arch': '''<t t-name="test_owl_component">
                <t t-out="owl_component('test.component', {'data': data}, class_='my-class')"/>
            </t>'''
        })

        values = self._get_render_values(data='test_data')
        html = view._render_template(view.id, values)
        tree = etree.fromstring(f'<root>{html}</root>')
        owl_comp = tree.find('.//owl-component')

        self.assertIsNotNone(owl_comp)
        self.assertEqual(owl_comp.get('name'), 'test.component')
        self.assertEqual(owl_comp.get('class'), 'my-class')

        props = json.loads(owl_comp.get('props'))
        self.assertEqual(props['data'], 'test_data')

    def test_render_template_with_record_props(self):
        """Test rendering a template with ORM record as props."""
        partner = self.env['res.partner'].create({
            'name': 'Template Test Partner',
            'email': 'template@test.com',
        })

        view = self.env['ir.ui.view'].create({
            'key': 'portal.test_owl_record',
            'type': 'qweb',
            'arch': '''<t t-name="test_owl_record">
                <owl-component name="partner.card" t-att-props="owl_props(partner, fields=['name', 'email'])"/>
            </t>'''
        })

        values = self._get_render_values(partner=partner)
        html = view._render_template(view.id, values)
        tree = etree.fromstring(f'<root>{html}</root>')
        owl_comp = tree.find('.//owl-component')

        props = json.loads(owl_comp.get('props'))
        self.assertEqual(props['id'], partner.id)
        self.assertEqual(props['name'], 'Template Test Partner')
        self.assertEqual(props['email'], 'template@test.com')
