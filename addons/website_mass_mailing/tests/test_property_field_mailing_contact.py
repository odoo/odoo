# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMailingPropertyField(TransactionCase):

    def test_mailing_contact_property_field_shown_in_website_form(self):
        """Test that a property field defined on mailing.contact is correctly shown in the website form."""
        definition = self.env['properties.base.definition'] \
            ._get_definition_for_property_field('mailing.contact', 'properties')
        definition.write({
            'properties_definition': [{
                'name': 'contact_color',
                'type': 'char',
            }]
        })
        self.assertEqual(
            definition.properties_definition,
            [{'name': 'contact_color', 'type': 'char'}]
        )
        fields = self.env['ir.model'].get_authorized_fields('mailing.contact', {})
        self.assertIn(
            'contact_color',
            fields,
            "Property field 'contact_color' is not exposed to website form"
        )
        property_field = fields['contact_color']
        self.assertEqual(property_field['type'], 'char')
        self.assertFalse(property_field.get('required'))
        self.assertIn('_property', property_field)
        self.assertEqual(property_field['_property']['field'], 'properties')
