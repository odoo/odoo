# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSalePropertyField(TransactionCase):

    def test_res_partner_propety_field_shown_in_website_form(self):
        """Test that a property field defined on res.partner is correctly shown in the website form."""
        definition = self.env['properties.base.definition'] \
            ._get_definition_for_property_field('res.partner', 'properties')
        definition.write({
            'properties_definition': [{
                'name': 'website_color',
                'type': 'char',
            }]
        })
        self.assertEqual(
            definition.properties_definition,
            [{'name': 'website_color', 'type': 'char'}]
        )
        fields = self.env['ir.model'].get_authorized_fields('res.partner', {})
        self.assertIn(
            'website_color',
            fields,
            "Property field 'website_color' is not shown in the website form"
        )
        property_field = fields['website_color']
        self.assertEqual(property_field['type'], 'char')
        self.assertFalse(property_field.get('required'))
        self.assertIn('_property', property_field)
        self.assertEqual(property_field['_property']['field'], 'properties')
